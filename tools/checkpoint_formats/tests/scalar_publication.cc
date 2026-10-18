// Actual mutable scalar host owners; deterministic MMIO/DMA/clock fixtures.
#include "bridges/peek_poke.h"
#include "bridges/cpu_managed_stream.h"
#include "core/bridge_driver.h"
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

FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a, d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }

using bytes_t = std::vector<uint8_t>;
using image_t = std::vector<bytes_t>;
using candidates_t = std::vector<std::unique_ptr<prepared_checkpoint_t>>;
static void check(bool b) { if (!b) throw std::runtime_error("scalar publication assertion"); }
static unsigned rejections = 0;
template<class F> static void reject(F fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("scalar publication accepted invalid candidate");
}
namespace {
const TargetConfig cfg{{4,40,32}, {4,40,96}, 1, {}, {}, {0,0}, "scalar-fixture"};
// Advance only the fixture wall clock so timeout tests never sleep.
static uint64_t now = 0;
midas_time_t timestamp_fixture() { return now += 20000000; }
struct mmio_t : simif_t, CPUManagedStreamIO {
  mmio_t() : simif_t(cfg) {}
  std::ostream *trace = nullptr;
  std::function<void()> hook;
  unsigned calls = 0, mode = 0;
  uint64_t get_beat_bytes() const override { return 64; }
  void write(size_t a, uint32_t d) override {
    ++calls; if (hook) hook();
    if (trace) *trace << "W " << a << ' ' << d << '\n';
  }
  uint32_t read(size_t a) override {
    ++calls; if (hook) hook();
    uint32_t d = a == 132 ? mode != 14 && mode != 17 : a == 136 ? mode != 15 :
                 a == 256 ? (mode == 3 ? 4 : 1) : a == 260 ? (mode == 4 ? 0 : 3) : a ^ 0x13579bdf;
    if (trace) *trace << "R " << a << ' ' << d << '\n';
    return d;
  }
  uint32_t mmio_read(size_t a) override { return read(a); }
  size_t cpu_managed_axi4_write(size_t a, const char *data, size_t size) override {
    ++calls; if (hook) hook();
    if (trace) {
      *trace << "DMA_W " << a << ' ' << size;
      for (size_t i = 0; i < size; ++i) *trace << ' ' << unsigned(uint8_t(data[i]));
      *trace << '\n';
    }
    return size;
  }
  size_t cpu_managed_axi4_read(size_t a, char *data, size_t size) override {
    ++calls; if (hook) hook();
    for (size_t i = 0; i < size; ++i) data[i] = uint8_t(a + i);
    if (trace) *trace << "DMA_R " << a << ' ' << size << '\n';
    return size;
  }
};
struct fixture_t {
  mmio_t mmio;
  peek_poke_t peek{mmio, {128,132,136}, 0, {}, {{"in",{144,3}}}, {{"out",{160,3}}}};
  CPUManagedStreamWidget stream{mmio, 0, {}, {{"from",512,256,4,64}}, {{"to",1024,260,4,64}}};
  checkpoint_owner_t *owners[2]{&peek, &stream};
  image_t capture() {
    image_t result;
    for (auto *owner : owners) result.push_back(owner->save_checkpoint());
    return result;
  }
  candidates_t prepare(const image_t &image) {
    check(image.size() == 2);
    candidates_t result;
    for (unsigned i = 0; i < 2; ++i)
      result.push_back(owners[i]->prepare_checkpoint_publication(image[i]));
    return result;
  }
  void service(unsigned index) {
    struct data_t {
      mpz_t value;
      data_t() { mpz_init(value); }
      ~data_t() { mpz_clear(value); }
    } data;
    auto result = [&](uint64_t value) { if (mmio.trace) *mmio.trace << "RESULT " << value << '\n'; };
    if (mmio.trace) *mmio.trace << "OP " << index << '\n';
    mmio.mode = index;
    char buffer[128]{};
    for (size_t i = 0; i < sizeof buffer; ++i) buffer[i] = uint8_t(i*3);
    switch (index) {
    case 0: stream.init(); break;
    case 1: case 3: result(stream.push(0, buffer, 128, 64)); break;
    case 2: case 4: result(stream.pull(0, buffer, 128, 64)); break;
    case 5: stream.push_flush(0); break;
    case 6: stream.pull_flush(0); break;
    case 7: peek.poke("in", 123, false); break;
    case 8: mpz_set_str(data.value, "abcdef0123456789fedcba98", 16); peek.poke("in", data.value); break;
    case 9: result(peek.peek("out", false)); break;
    case 10: case 18: peek.peek("out", data.value); break;
    case 11: peek.step(17, false); break;
    case 12: result(peek.is_done()); break;
    case 13: peek.poke("in", 321, true); break;
    case 14: case 15: result(peek.peek("out", true)); break;
    case 16: peek.step(11, true); break;
    case 17: peek.poke("in", 777, true); break;
    default: throw std::runtime_error("invalid fixture service");
    }
    if (mmio.trace && (index == 2 || index == 4)) {
      *mmio.trace << "BUFFER";
      for (auto c : buffer) *mmio.trace << ' ' << unsigned(uint8_t(c));
      *mmio.trace << '\n';
    }
    char *hex = mpz_get_str(nullptr, 16, data.value);
    if (mmio.trace) *mmio.trace << "GMP " << hex << " FLAGS " << peek.unstable() << ' ' << peek.timeout() << '\n';
    free(hex);
  }
};
static_assert(!std::is_copy_constructible_v<peek_poke_t> && !std::is_move_constructible_v<peek_poke_t>);
static_assert(!std::is_copy_constructible_v<CPUManagedStreamWidget> && !std::is_move_constructible_v<CPUManagedStreamWidget>);
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
  for (unsigned i = 0; i < 2; ++i) {
    std::ifstream f(out / ("state-" + std::to_string(cut) + "." + std::to_string(i)), std::ios::binary);
    check(bool(f)); result.emplace_back(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
  }
  return result;
}
void negatives(const image_t &image) {
  fixture_t dest; const auto initial = dest.capture();
  unsigned valid_flags = 0;
  for (unsigned i = 0; i < 2; ++i) {
    for (size_t n = 0; n < image[i].size(); ++n) {
      auto bad = image; bad[i].resize(n); reject([&] { dest.prepare(bad); });
      check(dest.capture() == initial && dest.mmio.calls == 0);
    }
    for (size_t n = 0; n < image[i].size(); ++n) {
      if (n == image[i].size()-8) continue; // low allowed flag bit is valid state
      auto bad = image; bad[i][n] ^= 1; reject([&] { dest.prepare(bad); });
      check(dest.capture() == initial && dest.mmio.calls == 0);
    }
    for (unsigned bit = i ? 1 : 2; bit < 64; ++bit) {
      auto bad = image; bad[i][bad[i].size()-8+bit/8] |= uint8_t(1U << (bit%8));
      reject([&] { dest.prepare(bad); });
      check(dest.capture() == initial && dest.mmio.calls == 0);
    }
    auto bad = image; bad[i].push_back(0); reject([&] { dest.prepare(bad); });
    reject([&] { dest.owners[1-i]->prepare_checkpoint_publication(image[i]); });
    { auto c = dest.prepare(image); dest.owners[i]->load_checkpoint(initial[i]);
      reject([&] { c[i]->seal(); }); }
    { auto c = dest.prepare(image); c[i]->seal(); reject([&] { c[i]->seal(); }); }
    { auto c = dest.prepare(image); std::thread t([&] { reject([&] { c[i]->seal(); }); }); t.join(); }
    { fixture_t f; auto c = f.prepare(image), other = f.prepare(image); seal(c); publish(c);
      reject([&] { c[i]->seal(); }); reject([&] { other[i]->seal(); }); }
    { candidates_t c; { fixture_t dead; c = dead.prepare(image); }
      reject([&] { c[i]->seal(); }); }
    { fixture_t f; auto c = f.prepare(image);
      if (i) f.stream.init(); else f.service(14);
      reject([&] { c[i]->seal(); }); }
  }
  // All combinations are valid, including simultaneous peek result bits.
  // Restore both directions from deliberately differing destination scalars.
  for (unsigned pf = 0; pf < 4; ++pf) for (unsigned sf = 0; sf < 2; ++sf) {
    auto wanted = initial;
    wanted[0][wanted[0].size()-8] = pf; wanted[1][wanted[1].size()-8] = sf;
    fixture_t f;
    auto opposite = initial;
    opposite[0][opposite[0].size()-8] = pf ^ 3; opposite[1][opposite[1].size()-8] = sf ^ 1;
    f.peek.load_checkpoint(opposite[0]); f.stream.load_checkpoint(opposite[1]);
    auto c = f.prepare(wanted); seal(c); publish(c);
    check(f.capture() == wanted && f.mmio.calls == 0); ++valid_flags;
  }
  for (unsigned phase = 0; phase < 2; ++phase) {
    fixture_t f; auto c = f.prepare(image); if (phase) seal(c);
    c.clear(); check(f.capture() == initial && f.mmio.calls == 0);
    auto next = f.prepare(image); seal(next); publish(next); check(f.capture() == image && f.mmio.calls == 0);
  }
  checkpoint_owner_t unsupported; reject([&] { unsupported.prepare_checkpoint_publication({}); });
  struct legacy_t : checkpoint_owner_t { std::string checkpoint_schema() const override { return "legacy"; } } legacy;
  reject([&] { legacy.prepare_checkpoint_publication({}); });
  // Every MMIO/DMA-bearing entry rejects while suspended and after interruption.
  for (unsigned op : {1,2,3,4,7,8,9,10,11,12,13,14,15,16,17,18})
    for (bool interrupted : {false, true}) {
      fixture_t f; auto c = f.prepare(image); unsigned i = op < 7 ? 1 : 0, checked = 0;
      f.mmio.hook = [&] {
        ++checked;
        reject([&] { f.owners[i]->prepare_checkpoint_publication(image[i]); });
        reject([&] { c[i]->seal(); });
        if (interrupted) throw std::runtime_error("test service interruption");
      };
      if (interrupted) reject([&] { f.service(op); }); else f.service(op);
      check(checked); f.mmio.hook = {};
      if (interrupted) {
        reject([&] { f.owners[i]->prepare_checkpoint_publication(image[i]); });
        reject([&] { c[i]->seal(); });
      } else {
        const auto calls = f.mmio.calls;
        auto next = f.prepare(image); seal(next); publish(next);
        check(f.capture() == image && f.mmio.calls == calls);
      }
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
  std::cout << "SCALAR_NEGATIVE rejections=" << rejections << " prepare_failures=" << failures[0]
            << " seal_failures=" << failures[1] << " valid_flags=" << valid_flags << " unchanged=1 mmio=0\n";
}
fixture_t *fatal_fixture;
const image_t *fatal_expected;
const char *fatal_mode;
void terminated() noexcept {
  fail_after = -1;
  try {
    check(fatal_fixture->capture() == *fatal_expected && fatal_fixture->mmio.calls == 0);
    std::fprintf(stderr, "SCALAR_FATAL mode=%s unchanged=1 mmio=0\n", fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
int test(const char *mode, const char *source, const char *destination, unsigned cut) {
  try {
    std::set_terminate(terminated);
    std::filesystem::create_directories(destination);
    std::filesystem::path out(destination);
    fixture_t f; const auto initial = f.capture();
    std::string m(mode);
    if (m == "negative") { negatives(read(source, cut)); return 0; }
    if (m.find("fatal-") == 0) {
      check(cut < 2); auto c = f.prepare(initial);
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
    check(cut <= 19 && (m == "reference" || m == "restore"));
    if (m == "restore") {
      auto c = f.prepare(read(source, cut)); seal(c); publish(c);
      check(f.mmio.calls == 0); save(out, "initial", f.capture());
    }
    std::ofstream trace(out / "trace"); check(bool(trace)); f.mmio.trace = &trace;
    for (unsigned op = m == "reference" ? 0 : cut; op <= 19; ++op) {
      if (m == "reference") save(out, "state-" + std::to_string(op), f.capture());
      if (op < 19) f.service(op);
    }
    f.mmio.trace = nullptr; trace.close(); save(out, "final", f.capture());
    std::cout << "SCALAR_PASS first=" << (m == "reference" ? 0 : cut) << " services="
              << (m == "reference" ? 19 : 19-cut) << " mmio=" << f.mmio.calls << '\n';
    return 0;
  } catch (const std::exception &e) { fail_after = -1; std::cerr << e.what() << '\n'; return 1; }
}
} // namespace
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { return dynamic_cast<mmio_t &>(*this); }
midas_time_t timestamp() { return timestamp_fixture(); }
double diff_secs(midas_time_t end, midas_time_t start) { return (end-start)/1000000.0; }
#ifdef SCALAR_PUBLICATION_DPI
extern "C" int scalar_publication(const char *mode, const char *source, const char *destination, int cut) {
  return test(mode, source, destination, cut);
}
#else
int main(int argc, char **argv) { return argc == 5 ? test(argv[1], argv[2], argv[3], std::stoul(argv[4])) : 2; }
#endif
