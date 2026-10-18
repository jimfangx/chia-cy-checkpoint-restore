// Actual configuration-only widgets; deterministic MMIO services are fixtures.
#include "bridges/master.h"
#include "bridges/clock.h"
#include "bridges/loadmem.h"
#include "bridges/reset_pulse.h"
#include <filesystem>
#include <fstream>
#include <functional>
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

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a, d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }

using bytes_t = std::vector<uint8_t>;
using image_t = std::vector<bytes_t>;
using candidates_t = std::vector<std::unique_ptr<prepared_checkpoint_t>>;
static void check(bool b) { if (!b) throw std::runtime_error("configuration publication assertion"); }
static unsigned rejections = 0;
template<class F> static void reject(F fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("configuration publication accepted invalid candidate");
}
namespace {
const TargetConfig cfg{{4,40,32}, {4,40,96}, 1, {}, {}, {0,0}, "configuration-fixture"};
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  std::ostream *trace = nullptr;
  std::function<void()> hook;
  unsigned calls = 0;
  void write(size_t a, uint32_t d) override {
    ++calls; if (hook) hook();
    if (trace) *trace << "W " << a << ' ' << d << '\n';
  }
  uint32_t read(size_t a) override {
    ++calls; if (hook) hook();
    uint32_t d = a == 0 || a == 84 ? 1 : a == 4 ? 0x46697265 : a ^ 0x13579bdf;
    if (trace) *trace << "R " << a << ' ' << d << '\n';
    return d;
  }
};
struct fixture_t {
  mmio_t mmio;
  master_t master{mmio, {0,4,8}, 0, {}};
  clockmodule_t clock{mmio, {16,20,24,28,32,36}, 0, {}};
  loadmem_t memory{mmio, {64,68,72,76,80,84,88,92,96}, 0, {}, {4,40,96}, 3};
  reset_pulse_t reset{mmio, {112,116}, 0, {"+reset-pulse-length0=7"}, 20, 5};
  checkpoint_owner_t *owners[4]{&master, &clock, &memory, &reset};
  image_t capture() {
    image_t result;
    for (auto *owner : owners) result.push_back(owner->save_checkpoint());
    return result;
  }
  candidates_t prepare(const image_t &image) {
    check(image.size() == 4);
    candidates_t result;
    for (unsigned i = 0; i < 4; ++i)
      result.push_back(owners[i]->prepare_checkpoint_publication(image[i]));
    return result;
  }
  void service(unsigned index, const std::filesystem::path &input) {
    struct data_t {
      mpz_t value;
      data_t() { mpz_init(value); }
      ~data_t() { mpz_clear(value); }
    } data;
    auto result = [&](uint64_t value) { if (mmio.trace) *mmio.trace << "RESULT " << value << '\n'; };
    if (mmio.trace) *mmio.trace << "OP " << index << '\n';
    switch (index) {
    case 0: result(master.is_init_done()); break;
    case 1: result(master.check_fingerprint()); break;
    case 2: master.write_fingerprint(0x12345678); break;
    case 3: result(clock.hcycle()); break;
    case 4: result(clock.tcycle()); break;
    case 5: reset.init(); break;
    case 6: mpz_set_ui(data.value, 0xfeedbeef); memory.write_mem(0x123456789ULL, data.value); break;
    case 7: memory.read_mem(0x3456789abULL, data.value); break;
    case 8: mpz_set_str(data.value, "abcdef0123456789fedcba98", 16); memory.write_mem_chunk(32, data.value, 16); break;
    case 9: memory.zero_out_dram(); break;
    case 10: memory.load_mem_from_file(input.string()); break;
    default: throw std::runtime_error("invalid fixture service");
    }
    char *hex = mpz_get_str(nullptr, 16, data.value);
    if (mmio.trace) *mmio.trace << "GMP " << hex << " FLAGS 0 0\n";
    free(hex);
  }
};
static_assert(!std::is_copy_constructible_v<master_t> && !std::is_move_constructible_v<master_t>);
static_assert(!std::is_copy_constructible_v<clockmodule_t> && !std::is_move_constructible_v<clockmodule_t>);
static_assert(!std::is_copy_constructible_v<loadmem_t> && !std::is_move_constructible_v<loadmem_t>);
static_assert(!std::is_copy_constructible_v<reset_pulse_t> && !std::is_move_constructible_v<reset_pulse_t>);
void seal(candidates_t &c) { for (auto &p : c) p->seal(); }
void publish(candidates_t &c) {
  allocation_failed = false; fail_after = 0;
  for (auto &p : c) { static_assert(noexcept(p->publish())); p->publish(); }
  bool clean = fail_after == 0 && !allocation_failed; fail_after = -1; check(clean);
}
void save(const std::filesystem::path &out, const std::string &name, const image_t &image) {
  for (size_t i = 0; i < image.size(); ++i) {
    std::ofstream f(out / (name + "." + std::to_string(i)), std::ios::binary);
    f.write(reinterpret_cast<const char *>(image[i].data()), image[i].size()); check(bool(f));
  }
}
image_t read(const std::filesystem::path &out, unsigned cut) {
  image_t result;
  for (unsigned i = 0; i < 4; ++i) {
    std::ifstream f(out / ("state-" + std::to_string(cut) + "." + std::to_string(i)), std::ios::binary);
    check(bool(f)); result.emplace_back(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
  }
  return result;
}
void negatives(const image_t &image, const std::filesystem::path &input) {
  fixture_t dest; const auto initial = dest.capture();
  for (unsigned i = 0; i < 4; ++i) {
    for (size_t n = 0; n < image[i].size(); ++n) {
      auto bad = image; bad[i].resize(n); reject([&] { dest.prepare(bad); });
      check(dest.capture() == initial && dest.mmio.calls == 0);
    }
    for (size_t n = 0; n < image[i].size(); ++n) {
      auto bad = image; bad[i][n] ^= 1; reject([&] { dest.prepare(bad); });
      check(dest.capture() == initial && dest.mmio.calls == 0);
    }
    auto bad = image; bad[i].push_back(0); reject([&] { dest.prepare(bad); });
    for (unsigned j = 0; j < 4; ++j) if (j != i)
      reject([&] { dest.owners[j]->prepare_checkpoint_publication(image[i]); });
    { auto c = dest.prepare(image); dest.owners[i]->load_checkpoint(initial[i]);
      reject([&] { c[i]->seal(); }); }
    { auto c = dest.prepare(image); c[i]->seal(); reject([&] { c[i]->seal(); }); }
    { auto c = dest.prepare(image); std::thread t([&] { reject([&] { c[i]->seal(); }); }); t.join(); }
    { auto c = dest.prepare(image), other = dest.prepare(image); seal(c); publish(c);
      reject([&] { c[i]->seal(); }); reject([&] { other[i]->seal(); }); }
    { candidates_t c; { fixture_t dead; c = dead.prepare(image); }
      reject([&] { c[i]->seal(); }); }
  }
  { auto c = dest.prepare(image); } check(dest.capture() == initial && dest.mmio.calls == 0);
  { auto c = dest.prepare(image); seal(c); } check(dest.capture() == initial && dest.mmio.calls == 0);
  for (unsigned phase = 0; phase < 2; ++phase) {
    fixture_t f; auto c = f.prepare(image); if (phase) seal(c);
    c.clear(); check(f.capture() == initial && f.mmio.calls == 0);
    auto next = f.prepare(image); seal(next); publish(next); check(f.capture() == initial && f.mmio.calls == 0);
  }
  checkpoint_owner_t unsupported; reject([&] { unsupported.prepare_checkpoint_publication({}); });
  struct legacy_t : checkpoint_owner_t { std::string checkpoint_schema() const override { return "legacy"; } } legacy;
  reject([&] { legacy.prepare_checkpoint_publication({}); });
  // Every public MMIO-bearing entry rejects preparation and sealing while a
  // call is suspended, and remains poisoned after an interrupted service.
  for (unsigned op = 0; op < 11; ++op) for (bool interrupted : {false, true}) {
    fixture_t f; auto c = f.prepare(image);
    unsigned i = op <= 2 ? 0 : op <= 4 ? 1 : op == 5 ? 3 : 2;
    unsigned checked = 0;
    f.mmio.hook = [&] {
      ++checked;
      reject([&] { f.owners[i]->prepare_checkpoint_publication(image[i]); });
      reject([&] { c[i]->seal(); });
      if (interrupted) throw std::runtime_error("test service interruption");
    };
    if (interrupted) reject([&] { f.service(op, input); }); else f.service(op, input);
    check(checked); f.mmio.hook = {};
    if (interrupted) {
      reject([&] { f.owners[i]->prepare_checkpoint_publication(image[i]); });
      reject([&] { c[i]->seal(); });
    } else { seal(c); publish(c); check(f.capture() == initial); }
  }
  unsigned failures[2]{};
  for (unsigned phase = 0; phase < 2; ++phase) for (long n = 0; ; ++n) {
    candidates_t c; if (phase) c = dest.prepare(image);
    allocation_failed = false; fail_after = n; bool failed = false;
    try { if (phase) seal(c); else c = dest.prepare(image); }
    catch (const std::bad_alloc &) { failed = true; }
    fail_after = -1; check(dest.capture() == initial && dest.mmio.calls == 0);
    if (!failed) { check(!allocation_failed); break; }
    ++failures[phase];
  }
  check(failures[0] && failures[1]);
  std::cout << "CONFIG_NEGATIVE rejections=" << rejections << " prepare_failures=" << failures[0]
            << " seal_failures=" << failures[1] << " unchanged=1 mmio=0\n";
}
fixture_t *fatal_fixture;
const image_t *fatal_expected;
const char *fatal_mode;
void terminated() noexcept {
  fail_after = -1;
  try {
    check(fatal_fixture->capture() == *fatal_expected && fatal_fixture->mmio.calls == 0);
    std::fprintf(stderr, "CONFIG_FATAL mode=%s unchanged=1 mmio=0\n", fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
int test(const char *mode, const char *source, const char *destination, unsigned cut) {
  try {
    std::set_terminate(terminated);
    std::filesystem::create_directories(destination);
    std::filesystem::path out(destination);
    const auto input = out / "input.hex";
    { std::ofstream f(input); f << "0123456789abcdefdeadbeef\n"; }
    fixture_t f; const auto initial = f.capture();
    std::string m(mode);
    if (m == "negative") { negatives(read(source, cut), input); return 0; }
    if (m.find("fatal-") == 0) {
      check(cut < 4); auto c = f.prepare(initial);
      fatal_fixture = &f; fatal_expected = &initial; fatal_mode = mode;
      if (m == "fatal-expired") { auto dead = std::make_unique<fixture_t>(); c = dead->prepare(initial); dead.reset(); }
      else if (m != "fatal-unsealed") seal(c);
      if (m == "fatal-consumed") publish(c);
      else if (m == "fatal-stale") { auto other = f.prepare(initial); seal(other); publish(other); }
      else if (m == "fatal-legacy") f.owners[cut]->load_checkpoint(initial[cut]);
      if (m == "fatal-thread") { std::thread t([&] { c[cut]->publish(); }); t.join(); }
      else c[cut]->publish();
      throw std::runtime_error("fatal misuse returned");
    }
    check(cut <= 11 && (m == "reference" || m == "restore"));
    if (m == "restore") {
      auto c = f.prepare(read(source, cut)); seal(c); publish(c);
      check(f.mmio.calls == 0); save(out, "initial", f.capture());
    }
    std::ofstream trace(out / "trace"); check(bool(trace)); f.mmio.trace = &trace;
    for (unsigned op = m == "reference" ? 0 : cut; op <= 11; ++op) {
      if (m == "reference") save(out, "state-" + std::to_string(op), f.capture());
      if (op < 11) f.service(op, input);
    }
    f.mmio.trace = nullptr; trace.close(); save(out, "final", f.capture());
    std::cout << "CONFIG_PASS first=" << (m == "reference" ? 0 : cut) << " services="
              << (m == "reference" ? 11 : 11-cut) << " mmio=" << f.mmio.calls << '\n';
    return 0;
  } catch (const std::exception &e) { fail_after = -1; std::cerr << e.what() << '\n'; return 1; }
}
} // namespace
#ifdef CONFIGURATION_PUBLICATION_DPI
extern "C" int configuration_publication(const char *mode, const char *source, const char *destination, int cut) {
  return test(mode, source, destination, cut);
}
#else
int main(int argc, char **argv) { return argc == 5 ? test(argv[1], argv[2], argv[3], std::stoul(argv[4])) : 2; }
#endif
