// Production scheduler/run-loop publication; synthetic returned-call services.
#include "core/systematic_scheduler.h"
#include "core/bridge_run_loop.h"
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <new>
#include <thread>
#include <type_traits>

static thread_local long fail_after = -1;
static thread_local bool allocation_failed = false;
void *operator new(std::size_t n) {
  if (fail_after >= 0 && fail_after-- == 0) {
    fail_after = -1; allocation_failed = true; throw std::bad_alloc();
  }
  if (auto p = std::malloc(n ? n : 1)) return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
static void check(bool ok) { if (!ok) throw std::runtime_error("control publication assertion"); }
static unsigned rejections = 0;
template<class F> static void reject(F fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("control publication accepted invalid candidate");
}
using bytes_t = std::vector<uint8_t>;
using image_t = std::vector<bytes_t>;
using candidates_t = std::vector<std::unique_ptr<prepared_checkpoint_t>>;
struct callback_t final : checkpoint_owner_t {
  std::string checkpoint_schema() const override { return "test.stateless-callback.v1"; }
};
struct fixture_t final : bridge_run_loop_t::services_t {
  callback_t callbacks[2];
  systematic_scheduler_t scheduler{{"+max-cycles=20"}};
  bridge_run_loop_t loop{3};
  unsigned remaining = 0, ordinal = 0, scenario;
  std::ostream *events = nullptr;
  std::function<void()> hook;
  explicit fixture_t(unsigned scenario) : scenario(scenario) {
    scheduler.register_checkpoint_task("a", 0, [this] { event("task 0"); return 3; }, callbacks[0]);
    scheduler.register_checkpoint_task("b", 0, [this] { event("task 1"); return 5; }, callbacks[1]);
  }
  void event(const std::string &s) {
    if (hook) hook();
    if (events) *events << ordinal << ' ' << s << '\n';
  }
  bool horizon_reached() override {
    auto done = scheduler.finished_scheduled_tasks(); event("horizon " + std::to_string(done)); return done;
  }
  void run_tasks() override { event("tasks"); scheduler.run_scheduled_tasks(); }
  void issue_step() override {
    event("step " + std::to_string(scheduler.get_largest_stepsize())); remaining = 2;
  }
  bool step_done() override {
    check(remaining); --remaining; event("done " + std::to_string(remaining == 0)); return remaining == 0;
  }
  void tick_bridge(uint64_t index) override { event("tick " + std::to_string(index)); }
  bool bridge_terminated(uint64_t index) override {
    bool stop = scenario && ordinal >= 30 && index == 1;
    event("terminate " + std::to_string(index) + " " + std::to_string(stop)); return stop;
  }
  int bridge_exit_code(uint64_t index) override { event("status " + std::to_string(index) + " -7"); return -7; }
  image_t capture() { return {scheduler.save_checkpoint(), loop.save_checkpoint()}; }
  candidates_t prepare(const image_t &image) {
    check(image.size() == 2);
    candidates_t result;
    // Exercise the default-unsupported generic API, not concrete overloads.
    checkpoint_owner_t *owners[] = {&scheduler, &loop};
    for (unsigned i = 0; i < 2; ++i) result.push_back(owners[i]->prepare_checkpoint_publication(image[i]));
    return result;
  }
};
static void seal(candidates_t &c) { for (auto &p : c) p->seal(); }
static void publish(candidates_t &c) {
  allocation_failed = false; fail_after = 0;
  for (auto &p : c) { static_assert(noexcept(p->publish())); p->publish(); }
  bool clean = fail_after == 0 && !allocation_failed; fail_after = -1; check(clean);
}
static void save(const std::filesystem::path &out, const std::string &name, const image_t &image) {
  std::filesystem::create_directories(out);
  for (size_t i = 0; i < image.size(); ++i) {
    std::ofstream f(out / (name + "." + std::to_string(i)), std::ios::binary);
    f.write(reinterpret_cast<const char *>(image[i].data()), image[i].size()); check(bool(f));
  }
}
static bytes_t read(const std::filesystem::path &path) {
  std::ifstream f(path, std::ios::binary); check(bool(f));
  return bytes_t(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
}
static image_t load(const std::filesystem::path &src, unsigned cut) {
  return {read(src / ("state-" + std::to_string(cut) + ".0")),
          read(src / ("state-" + std::to_string(cut) + ".1"))};
}
static fixture_t *fatal_fixture;
static const image_t *fatal_expected;
static const char *fatal_mode;
static void terminated() noexcept {
  fail_after = -1;
  try {
    check(fatal_fixture->capture() == *fatal_expected);
    std::fprintf(stderr, "CONTROL_FATAL mode=%s unchanged=1 service_calls=0\n", fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
static void negatives(const image_t &image, unsigned scenario) {
  fixture_t dest(scenario); const auto initial = dest.capture();
  // Exact truncation sweep and representative structural/semantic damage.
  for (unsigned i = 0; i < 2; ++i) {
    for (size_t n = 0; n < image[i].size(); ++n) {
      auto bad = image; bad[i].resize(n); reject([&] { dest.prepare(bad); }); check(dest.capture() == initial);
    }
    for (size_t offset : {size_t(0), size_t(8), size_t(16), size_t(24)}) {
      auto bad = image; bad[i][offset] ^= 0xff; reject([&] { dest.prepare(bad); }); check(dest.capture() == initial);
    }
    auto bad = image; bad[i].push_back(0); reject([&] { dest.prepare(bad); });
  }
  checkpoint_owner_t unsupported;
  reject([&] { unsupported.prepare_checkpoint_publication({}); });
  // An audited legacy schema must not silently enable deferred legacy loading.
  callback_t legacy; reject([&] { legacy.prepare_checkpoint_publication({}); });
  { auto c = dest.prepare(image); } check(dest.capture() == initial);
  { auto c = dest.prepare(image); seal(c); } check(dest.capture() == initial);
  { auto c = dest.prepare(image); seal(c); reject([&] { seal(c); }); }
  { auto c = dest.prepare(image); dest.loop.advance(dest); reject([&] { seal(c); }); }
  dest.loop.load_checkpoint(initial[1]);
  { auto c = dest.prepare(image); dest.scheduler.run_scheduled_tasks(); reject([&] { seal(c); }); }
  dest.scheduler.load_checkpoint(initial[0]);
  { auto c = dest.prepare(image); std::thread t([&] { reject([&] { seal(c); }); }); t.join(); }
  { auto c = dest.prepare(image); dest.scheduler.load_checkpoint(initial[0]); reject([&] { seal(c); }); }
  { auto c = dest.prepare(image); dest.loop.load_checkpoint(initial[1]);
    c[0]->seal(); reject([&] { c[1]->seal(); }); }
  { auto c = dest.prepare(image), other = dest.prepare(image); seal(c); publish(c);
    reject([&] { seal(c); }); reject([&] { seal(other); }); }
  dest.scheduler.load_checkpoint(initial[0]); dest.loop.load_checkpoint(initial[1]);
  { candidates_t c; { fixture_t dead(scenario); c = dead.prepare(image); }
    reject([&] { seal(c); }); }
  for (bool scheduler : {false, true}) {
    fixture_t suspended(scenario); auto c = suspended.prepare(image); bool tested = false;
    suspended.hook = [&] {
      if (!tested) { tested = true; reject([&] { c[scheduler ? 0 : 1]->seal(); }); }
    };
    if (scheduler) suspended.scheduler.run_scheduled_tasks(); else suspended.loop.advance(suspended);
    check(tested);
    fixture_t poisoned(scenario); auto p = poisoned.prepare(image);
    poisoned.hook = [] { throw std::runtime_error("test interrupted service"); };
    reject([&] {
      if (scheduler) poisoned.scheduler.run_scheduled_tasks(); else poisoned.loop.advance(poisoned);
    });
    reject([&] { p[scheduler ? 0 : 1]->seal(); });
  }
  // Exhaust every C++ allocation in the whole paired preparation/sealing pass.
  unsigned failures[2]{};
  for (unsigned phase = 0; phase < 2; ++phase) {
    for (long n = 0; ; ++n) {
      candidates_t c; if (phase) c = dest.prepare(image);
      bool failed = false; allocation_failed = false; fail_after = n;
      try { if (phase) seal(c); else c = dest.prepare(image); }
      catch (const std::bad_alloc &) { failed = true; }
      fail_after = -1;
      check(dest.capture() == initial);
      if (!failed) { check(!allocation_failed); break; }
      ++failures[phase];
    }
    check(failures[phase]);
  }
  std::cout << "CONTROL_NEGATIVE rejections=" << rejections << " prepare_failures=" << failures[0]
            << " seal_failures=" << failures[1] << " unchanged=1\n";
}

static int test(const char *mode, const char *source, const char *destination, unsigned scenario, unsigned cut) {
  try {
    std::set_terminate(terminated);
    fixture_t f(scenario);
    const std::filesystem::path src(source), out(destination);
    const std::string operation(mode);
    if (operation == "negative") { negatives(load(src, cut), scenario); return 0; }
    if (operation.starts_with("fatal-")) {
      auto image = load(src, cut); auto initial = f.capture();
      fatal_fixture = &f; fatal_expected = &initial; fatal_mode = mode;
      auto c = f.prepare(image);
      if (operation == "fatal-expired") {
        { fixture_t dead(scenario); c = dead.prepare(image); seal(c); }
      } else if (operation != "fatal-unsealed") seal(c);
      if (operation == "fatal-legacy") f.scheduler.load_checkpoint(initial[0]);
      if (operation == "fatal-stale") { auto other = f.prepare(initial); seal(other); publish(other); }
      if (operation == "fatal-consumed") {
        publish(c); initial = image;
      }
      if (operation == "fatal-thread") { std::thread t([&] { c[0]->publish(); }); t.join(); }
      else c[0]->publish();
      throw std::runtime_error("fatal publication returned");
    }
    std::filesystem::create_directories(out);
    if (operation == "restore") {
      auto image = load(src, cut); auto c = f.prepare(image);
      // The prepared replacement owns its storage independently of the image.
      image.clear(); image.shrink_to_fit(); seal(c); publish(c);
      save(out, "initial", f.capture());
      auto service = read(src / ("service-" + std::to_string(cut))); check(service.size() == 1);
      f.remaining = service[0]; f.ordinal = cut;
      std::cout << "CONTROL_PRE_SERVICE_READBACK owners=2 ordinal=" << cut << " service_calls=0\n";
    } else check(operation == "reference");
    std::ofstream events(out / "events"); check(bool(events)); f.events = &events;
    while (true) {
      if (operation == "reference") {
        save(out, "state-" + std::to_string(f.ordinal), f.capture());
        std::ofstream service(out / ("service-" + std::to_string(f.ordinal)), std::ios::binary);
        service.put(f.remaining); check(bool(service));
      }
      if (f.loop.finished()) break;
      check(f.ordinal < 1000); f.loop.advance(f); ++f.ordinal;
    }
    save(out, "final", f.capture());
    std::cout << "CONTROL_PASS ordinal=" << f.ordinal << " terminated=" << f.loop.terminated()
              << " exit=" << f.loop.exit_code() << '\n';
    return 0;
  } catch (const std::exception &e) { fail_after = -1; std::cerr << "CONTROL_FAIL " << e.what() << '\n'; return 1; }
}
static_assert(!std::is_copy_constructible_v<systematic_scheduler_t> && !std::is_move_constructible_v<systematic_scheduler_t>);
static_assert(!std::is_copy_constructible_v<bridge_run_loop_t> && !std::is_move_constructible_v<bridge_run_loop_t>);
#ifdef CONTROL_PUBLICATION_DPI
extern "C" int control_publication_test(const char *mode, const char *source, const char *destination,
                                         unsigned scenario, unsigned cut) {
  const auto result = test(mode, source, destination, scenario, cut);
  if (result) std::exit(result);
  return result;
}
#else
int main(int argc, char **argv) { return argc == 6 ? test(argv[1], argv[2], argv[3], std::stoul(argv[4]), std::stoul(argv[5])) : 2; }
#endif
