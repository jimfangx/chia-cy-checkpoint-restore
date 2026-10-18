// Actual simulation_t flow, with independent platform/driver services.
// Generated RTL, transport and concrete driver loading are outside this test.
#include "core/simulation.h"
#include "core/simif.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include "core/bridge_driver.h"
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

static_assert(!std::is_copy_constructible_v<simulation_t> &&
              !std::is_move_constructible_v<simulation_t>);

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
static uint64_t now = 1000000;
midas_time_t timestamp() { return now += 100; }
double diff_secs(midas_time_t e, midas_time_t s) { return (e-s)/1000000.0; }

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,96}, 1, {}, {}, {0,0}, "simulation-fixture"};
unsigned rejected = 0;
void check(bool value) { if (!value) throw std::runtime_error("simulation test assertion"); }
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected simulation rejection");
}
struct platform_t : simif_t {
  platform_t() : simif_t(cfg) {}
  unsigned index = 0;
  uint64_t calls = 0;
  std::function<void(size_t)> hook;
  std::ostream *trace = nullptr;
  void write(size_t a, uint32_t d) override {
    ++calls;
    if (hook) hook(a);
    if (trace) *trace << "W " << a << ' ' << d << '\n';
  }
  uint32_t read(size_t a) override {
    ++calls;
    if (hook) hook(a);
    uint32_t d = a == 0 ? 1 : a == 4 ? 0x46697265 : a == 16 ? 23 :
                 a == 28 ? 42 : a == 104 ? index * 9 : 0;
    if (trace) *trace << "R " << a << ' ' << d << '\n';
    return d;
  }
};
struct bridge_t : bridge_driver_t {
  static char KIND;
  bridge_t(platform_t &p) : bridge_driver_t(p, &KIND) {}
  std::string checkpoint_schema() const override { return "fixture.bridge.v1"; }
  void init() override { write(200, 1); }
  void finish() override { write(204, 1); }
};
char bridge_t::KIND;
struct driver_t : simulation_t {
  platform_t &platform;
  unsigned index = 0, scenario;
  bool steps = true;
  std::function<void()> hook;
  driver_t(widget_registry_t &r, platform_t &p, unsigned s,
           std::vector<std::string> args = {}) : simulation_t(r,args), platform(p), scenario(s) {}
  bool simulation_supports_steps() const override { return steps; }
  int simulation_run() override { throw std::runtime_error("unexpected blocking driver"); }
  bool simulation_run_step() override {
    if (hook) hook();
    if (index == 4) {
      std::cerr << "FIRST_MISMATCH fixture_step=5 expected=simulation_run_finalize actual=simulation_run_step acknowledged=4\n";
      throw std::runtime_error("first divergent base lifecycle boundary");
    }
    check(index < 4); // terminal restore must never repeat this operation
    platform.index = index;
    platform.write(100, index);
    check(platform.read(104) == index * 9);
    return ++index == 4;
  }
  int simulation_run_finalize() override {
    if (index != 4) {
      std::cerr << "FIRST_MISMATCH fixture_step=" << index+1
                << " expected=simulation_run_step actual=simulation_run_finalize acknowledged=" << index << '\n';
      throw std::runtime_error("first divergent base lifecycle boundary");
    }
    check(index == 4);
    if (hook) hook();
    platform.write(108, scenario == 1 ? 7 : 0);
    return scenario == 1 ? 7 : 0;
  }
  bool simulation_timed_out() override { if (hook) hook(); return scenario == 2; }
  checkpoint_owner_t &base() {
    auto owners = checkpoint_driver_owners();
    check(owners.size() == 2 && owners[0].second->checkpoint_schema().empty());
    check(owners[1].first == "runtime/simulation/base");
    return *owners[1].second;
  }
};
struct fixture_t {
  platform_t platform;
  widget_registry_t registry;
  std::unique_ptr<driver_t> driver;
  fixture_t(unsigned scenario = 0, std::vector<std::string> args = {}) {
    registry.add_widget(new master_t(platform, {0,4,8}, 0, {}));
    registry.add_widget(new clockmodule_t(platform, {16,20,24,28,32,36}, 0, {}));
    registry.add_widget(new bridge_t(platform));
    driver = std::make_unique<driver_t>(registry,platform,scenario,args);
  }
};
void publish(prepared_checkpoint_t &candidate) {
  allocation_failed = false; fail_after = 0;
  static_assert(noexcept(candidate.publish())); candidate.publish();
  const bool clean = fail_after == 0 && !allocation_failed; fail_after = -1; check(clean);
}
void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()),b.size()); check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
std::unique_ptr<fixture_t> fixture;
std::ofstream trace;
std::filesystem::path output;
bool restoring;
unsigned scenario;
void init(const std::filesystem::path &source, const std::filesystem::path &out,
          bool restore, unsigned cut, unsigned which) {
  output = out; restoring = restore; scenario = which;
  check(cut >= 1 && cut <= 4);
  now = restore ? 1000100 : 1000000;
  fixture = std::make_unique<fixture_t>(which);
  if (restore) {
    auto bytes = read(source / ("cut-"+std::to_string(cut)+".owner"));
    fixture->driver->base().validate_checkpoint(bytes);
#ifdef SIMULATION_PREPARED_PUBLICATION
    auto candidate = fixture->driver->base().prepare_checkpoint_publication(bytes);
    candidate->seal(); publish(*candidate);
#else
    fixture->driver->base().load_checkpoint(bytes);
#endif
    check(fixture->platform.calls == 0 && now == 1000100);
    fixture->driver->index = cut; // separately restored fixture driver owner
    write(out / "initial.owner", fixture->driver->base().save_checkpoint());
    std::cout << "RESTORED_BEFORE_FIRST_EDGE calls=0\n";
  }
}
void run_flow() {
  trace.open(output / "trace"); check(bool(trace));
  fixture->platform.trace = &trace;
  auto &driver = *fixture->driver;
  int result = driver.execute_simulation_flow([&](simulation_t &, bool done) {
    const auto calls = fixture->platform.calls, time = now;
    auto data = driver.base().save_checkpoint();
    driver.base().validate_checkpoint(data);
    check(done == (driver.index == 4));
    rejects([&] { driver.base().load_checkpoint(data); });
    rejects([&] { driver.execute_simulation_flow(); });
    check(data == driver.base().save_checkpoint());
    check(calls == fixture->platform.calls && time == now);
    write(output / ("cut-"+std::to_string(driver.index)+".owner"),data);
  });
  check(result == (scenario == 1 ? 7 : scenario == 2 ? EXIT_FAILURE : 0));
  rejects([&] { driver.base().save_checkpoint(); });
  rejects([&] { driver.execute_simulation_flow(); });
  trace.close();
  fixture.reset();
  std::cout << "PASS: simulation base continuation result=" << result << '\n';
}
void negative() {
  fixture_t reference;
  auto &r = *reference.driver;
  std::vector<uint8_t> payload;
  rejects([&] { r.base().save_checkpoint(); });
  r.execute_simulation_flow([&](simulation_t &, bool) {
    if (payload.empty()) payload = r.base().save_checkpoint();
  });
  fixture_t fresh;
  auto &base = fresh.driver->base();
  auto reject_load = [&](const std::vector<uint8_t> &bytes) {
    rejects([&] { base.validate_checkpoint(bytes); });
    rejects([&] { base.load_checkpoint(bytes); });
    rejects([&] { base.save_checkpoint(); }); // destination is still uninitialized
    check(fresh.platform.calls == 0);
  };
  for (size_t i = 0; i < payload.size(); ++i)
    reject_load({payload.begin(),payload.begin()+i});
  auto bad = payload; bad.push_back(0); reject_load(bad);
  for (size_t i = 0; i < payload.size()-16; ++i) {
    bad = payload; bad[i] ^= 128; reject_load(bad);
  }
  for (auto args : std::vector<std::vector<std::string>>{{"+zero-out-dram"},
        {"+loadmem=program.hex"}, {"+check-fingerprint"}, {"+write-fingerprint=123"}}) {
    fixture_t mismatch(0,args);
    rejects([&] { mismatch.driver->base().load_checkpoint(payload); });
    check(mismatch.platform.calls == 0);
  }
  fixture_t unsupported;
  unsupported.driver->steps = false;
  rejects([&] { unsupported.driver->base().load_checkpoint(payload); });
  base.load_checkpoint(payload);
  rejects([&] { base.load_checkpoint(payload); });
  check(base.save_checkpoint() == payload && fresh.platform.calls == 0);
  fixture_t changed_registry;
  changed_registry.registry.add_widget(new bridge_t(changed_registry.platform));
  rejects([&] { changed_registry.driver->base().load_checkpoint(payload); });
  fixture_t fastload(0, {"+loadmem=ignored.hex", "+fastloadmem"});
  fastload.driver->base().load_checkpoint(payload);
  check(fastload.driver->base().save_checkpoint() == payload && fastload.platform.calls == 0);
  for (unsigned failure = 0; failure < 6; ++failure) {
    fixture_t interrupted;
    auto &d = *interrupted.driver;
    auto suspend = [&] {
      rejects([&] { d.base().save_checkpoint(); });
      rejects([&] { d.base().validate_checkpoint(payload); });
      rejects([&] { d.base().load_checkpoint(payload); });
      rejects([&] { d.execute_simulation_flow(); });
    };
    interrupted.platform.hook = [&](size_t address) {
      suspend();
      if ((failure == 0 && address == 0) || (failure == 2 && address == 108) ||
          (failure == 4 && address == 204) || (failure == 5 && address == 36))
        throw std::runtime_error("injected MMIO interruption");
    };
    d.hook = [&] { suspend(); if (failure == 1) throw std::runtime_error("injected driver interruption"); };
    rejects([&] { d.execute_simulation_flow([&](simulation_t &, bool) {
      if (failure == 3) throw std::runtime_error("injected coordinator interruption");
    }); });
    rejects([&] { d.base().save_checkpoint(); });
    rejects([&] { d.base().load_checkpoint(payload); });
    rejects([&] { d.execute_simulation_flow(); });
  }
  std::cout << "PASS: simulation base rejections " << rejected << '\n';
}

std::vector<uint8_t> source_payload() {
  fixture_t source;
  std::vector<uint8_t> payload;
  source.driver->execute_simulation_flow([&](simulation_t &, bool) {
    if (payload.empty()) payload = source.driver->base().save_checkpoint();
  });
  return payload;
}
// Freshness is independently witnessed by dispatcher admission; after restore,
// compare the full v1 source bytes, never a projection of just the done flag.
std::vector<uint8_t> observe(fixture_t &f) {
  try { f.driver->require_fresh_dispatcher(); return {}; }
  catch (const std::runtime_error &) { return f.driver->base().save_checkpoint(); }
}
void publication_negative() {
  const auto good = source_payload();
  fixture_t dest; auto &owner = dest.driver->base();
  const auto clock = now;
  auto unchanged = [&] {
    check(observe(dest).empty() && dest.platform.calls == 0 && now == clock && dest.driver->index == 0);
    auto probe = owner.prepare_checkpoint_publication(good); probe->seal();
  };
  auto malformed = [&](const std::vector<uint8_t> &bad) {
    rejects([&] { owner.prepare_checkpoint_publication(bad); }); unchanged();
  };
  for (size_t n=0; n<good.size(); ++n) malformed({good.begin(),good.begin()+n});
  for (size_t n=0; n<good.size()-16; ++n) {
    // Done is a Boolean; both 0 and 1 are legal. All other bits must reject.
    auto bad=good; bad[n]^=128; malformed(bad);
  }
  for (unsigned bit=1; bit<64; ++bit) {
    auto bad=good; bad[good.size()-24+bit/8]^=uint8_t(1U<<(bit%8)); malformed(bad);
  }
  { auto bad=good; bad.push_back(0); malformed(bad); }
  malformed({});
  for (unsigned phase=0; phase<2; ++phase) {
    auto c=owner.prepare_checkpoint_publication(good); if (phase) c->seal(); c.reset(); unchanged();
  }
  { auto c=owner.prepare_checkpoint_publication(good); c->seal(); rejects([&] { c->seal(); }); unchanged(); }
  { auto c=owner.prepare_checkpoint_publication(good);
    std::thread t([&] { rejects([&] { c->seal(); }); }); t.join(); unchanged(); }
  { std::unique_ptr<prepared_checkpoint_t> c;
    { fixture_t dead; c=dead.driver->base().prepare_checkpoint_publication(good); }
    rejects([&] { c->seal(); }); unchanged(); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    auto other=o.prepare_checkpoint_publication(good); c->seal(); publish(*c);
    check(observe(f)==good && f.platform.calls==0 && now==clock);
    rejects([&] { c->seal(); }); rejects([&] { other->seal(); });
    rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    o.load_checkpoint(good); rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    f.driver->steps=false; rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); });
    f.driver->steps=true; c->seal(); unchanged(); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    f.registry.add_widget(new bridge_t(f.platform)); rejects([&] { c->seal(); });
    rejects([&] { o.prepare_checkpoint_publication(good); }); check(f.platform.calls==0); }
  for (auto args : std::vector<std::vector<std::string>>{{"+zero-out-dram"}, {"+loadmem=program.hex"},
        {"+check-fingerprint"}, {"+write-fingerprint=123"}}) {
    fixture_t f(0,args); rejects([&] { f.driver->base().prepare_checkpoint_publication(good); });
    check(f.platform.calls==0); }
  { fixture_t f(0,{"+loadmem=ignored.hex", "+fastloadmem"}); auto &o=f.driver->base();
    auto c=o.prepare_checkpoint_publication(good); c->seal(); publish(*c);
    check(observe(f)==good && f.platform.calls==0); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    f.platform.hook=[&](size_t) {
      rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); });
      throw std::runtime_error("initialization interruption");
    };
    rejects([&] { f.driver->execute_simulation_flow(); });
    rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(good);
    f.driver->execute_simulation_flow([&](simulation_t &,bool) {
      rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); });
    });
    rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); }); }
  const auto after_runs=now;
  // Decode every source scalar into candidate-owned storage, including extreme
  // unsigned baselines. The caller can free or overwrite the source afterward.
  for (unsigned value=0; value<3; ++value) {
    auto input=good; input[input.size()-24]=value%2;
    for (size_t n=input.size()-16; n<input.size(); ++n) input[n]=value==0 ? 0 : value==1 ? 255 : uint8_t(n);
    const auto expected=input; fixture_t f; auto &o=f.driver->base();
    auto c=o.prepare_checkpoint_publication(input); input.assign(1,0); c->seal(); publish(*c);
    check(observe(f)==expected && f.platform.calls==0 && now==after_runs);
  }
  unsigned failures[2]{};
  // Exhaustive allocation-failure sweep, including retry of a partially
  // failed seal. Neither attempt may start or poison the destination.
  for (unsigned phase=0; phase<2; ++phase) for (long n=0; ; ++n) {
    std::unique_ptr<prepared_checkpoint_t> c;
    if (phase) c=owner.prepare_checkpoint_publication(good);
    allocation_failed=false; fail_after=n; bool failed=false;
    try { if (phase) c->seal(); else c=owner.prepare_checkpoint_publication(good); }
    catch (const std::bad_alloc &) { failed=true; }
    fail_after=-1;
    check(observe(dest).empty() && dest.platform.calls==0 && now==after_runs);
    auto probe=owner.prepare_checkpoint_publication(good); probe->seal();
    if (!failed) { check(!allocation_failed); break; }
    ++failures[phase]; if (phase) c->seal();
  }
  check(failures[0] && failures[1]);
  std::cout << "BASE_PUBLICATION_NEGATIVE rejections=" << rejected
            << " prepare_failures=" << failures[0] << " seal_failures=" << failures[1]
            << " unchanged=1 mmio=0\n";
}
fixture_t *fatal_fixture;
std::vector<uint8_t> fatal_expected, fatal_source;
uint64_t fatal_time;
const char *fatal_mode;
void terminated() noexcept {
  fail_after=-1;
  try {
    check(observe(*fatal_fixture)==fatal_expected && fatal_fixture->platform.calls==0 && now==fatal_time);
    if (fatal_expected.empty()) {
      auto probe=fatal_fixture->driver->base().prepare_checkpoint_publication(fatal_source); probe->seal();
    }
    std::fprintf(stderr,"BASE_PUBLICATION_FATAL mode=%s unchanged=1 mmio=0\n",fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
void publication_fatal(const char *mode) {
  std::set_terminate(terminated);
  fatal_source=source_payload(); fatal_time=now;
  fixture_t f; fatal_fixture=&f; fatal_mode=mode;
  auto &o=f.driver->base(); auto c=o.prepare_checkpoint_publication(fatal_source);
  const std::string m(mode);
  if (m=="expired") {
    auto dead=std::make_unique<fixture_t>(); c=dead->driver->base().prepare_checkpoint_publication(fatal_source);
    c->seal(); dead.reset();
  } else if (m!="unsealed") c->seal();
  if (m=="consumed") publish(*c);
  else if (m=="stale") { auto other=o.prepare_checkpoint_publication(fatal_source); other->seal(); publish(*other); }
  else if (m=="legacy") o.load_checkpoint(fatal_source);
  fatal_expected=observe(f);
  if (m=="thread") { std::thread t([&] { c->publish(); }); t.join(); }
  else c->publish();
  std::fprintf(stderr,"BASE_PUBLICATION_UNEXPECTED_RETURN mode=%s\n",mode);
  std::fflush(stderr); std::_Exit(88);
}
}

#ifdef SIMULATION_CHECKPOINT_DPI
extern "C" int simulation_checkpoint_init(const char *source, const char *out, int restore, int cut, int which) {
  try { init(source,out,restore,cut,which); return 0; }
  catch (const std::exception &e) { std::cerr << "REJECTED_BEFORE_FIRST_EDGE: " << e.what() << '\n'; std::exit(1); }
}
extern "C" int simulation_checkpoint_run() {
  try { run_flow(); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int simulation_checkpoint_negative() {
  try { negative(); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int simulation_publication_negative() {
  try { publication_negative(); return 0; }
  catch (const std::exception &e) { fail_after=-1; std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" void simulation_publication_fatal(const char *mode) { publication_fatal(mode); }
extern "C" void simulation_checkpoint_failure() { std::exit(1); }
#else
int main(int argc, char **argv) {
  try {
    if (argc==3 && std::string(argv[1])=="publication-fatal") { publication_fatal(argv[2]); return 1; }
    if (argc==2 && std::string(argv[1])=="publication-negative") { publication_negative(); return 0; }
    if (argc == 2) negative();
    else { check(argc == 6); init(argv[1],argv[2],std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5])); run_flow(); }
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
