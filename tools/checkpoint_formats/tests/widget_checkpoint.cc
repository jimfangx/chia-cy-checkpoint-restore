// Concrete widget component checks; the MMIO service is an independent fixture,
// not a generated simulator/harness restore adapter.
#include "bridges/master.h"
#include "bridges/clock.h"
#include "bridges/loadmem.h"
#include "bridges/reset_pulse.h"
#include "bridges/peek_poke.h"
#include "core/config.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>

// Replace only platform/clock services. Compile the actual widget methods.
simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a, d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }
// Advance the fixture wall clock deterministically to exercise both timeouts
// without sleeping. Production timestamp()/diff_secs() are unchanged.
static uint64_t now = 0;
midas_time_t timestamp() { return now += 20000000; }
double diff_secs(midas_time_t end, midas_time_t start) { return (end - start) / 1000000.0; }

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,96}, 1, {}, {}, {0,0}, "widget-fixture"};
unsigned rejected = 0;
void check(bool b) { if (!b) throw std::runtime_error("widget test assertion"); }
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected widget rejection");
}
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  std::ostream *trace = nullptr;
  std::function<void()> hook;
  uint64_t calls = 0;
  unsigned mode = 0;
  void write(size_t a, uint32_t d) override {
    ++calls;
    if (hook) hook();
    if (trace) *trace << "W " << a << ' ' << d << '\n';
  }
  uint32_t read(size_t a) override {
    ++calls;
    if (hook) hook();
    const uint32_t d = a == 0 ? 1 : a == 4 ? 0x46697265 : a == 84 ? 1 :
                       a == 132 ? mode != 1 : a == 136 ? mode != 2 : a ^ 0x13579bdf;
    if (trace) *trace << "R " << a << ' ' << d << '\n';
    return d;
  }
};
struct widgets_t {
  mmio_t mmio;
  master_t master{mmio, {0,4,8}, 0, {}};
  clockmodule_t clock{mmio, {16,20,24,28,32,36}, 0, {}};
  loadmem_t memory{mmio, {64,68,72,76,80,84,88,92,96}, 0, {}, {4,40,96}, 3};
  reset_pulse_t reset{mmio, {112,116}, 0, {"+reset-pulse-length0=7"}, 20, 5};
  peek_poke_t peek{mmio, {128,132,136}, 0, {}, {{"in",{144,3}}}, {{"out",{160,3}}}};
  std::vector<checkpoint_owner_t *> owners{&master,&clock,&memory,&reset,&peek};
};
void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()), b.size());
  check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
const unsigned operations = 25;
std::filesystem::path out;
std::unique_ptr<widgets_t> widgets;
std::ofstream trace;
unsigned index = 0;
bool restoring = false;
std::string prefix;
void snapshot(const std::string &label) {
  const auto calls = widgets->mmio.calls;
  for (unsigned i = 0; i < widgets->owners.size(); ++i) {
    auto *owner = widgets->owners[i];
    auto data = owner->save_checkpoint();
    owner->validate_checkpoint(data);
    write(out / (label + "." + std::to_string(i) + ".owner"), data);
  }
  check(widgets->mmio.calls == calls);
}
void init(const std::filesystem::path &directory, bool restore, unsigned cut) {
  out = directory; restoring = restore; index = restore ? cut : 0;
  check(index <= operations);
  widgets = std::make_unique<widgets_t>();
  prefix = restore ? "restore-" + std::to_string(cut) : "reference";
  if (restore) {
    std::vector<std::vector<uint8_t>> payloads;
    for (unsigned i = 0; i < widgets->owners.size(); ++i) {
      payloads.push_back(read(out / ("cut-" + std::to_string(cut) + "." + std::to_string(i) + ".owner")));
      widgets->owners[i]->validate_checkpoint(payloads.back());
    }
    for (unsigned i = 0; i < widgets->owners.size(); ++i)
      widgets->owners[i]->load_checkpoint(payloads[i]);
    check(widgets->mmio.calls == 0); // load must precede the first MMIO/edge
    snapshot(prefix + ".initial");
  }
  // Input file is reopened only by its explicit completed-call operation.
  { std::ofstream f(out / "input.hex"); f << "0123456789abcdefdeadbeef\n"; }
  trace.open(out / (prefix + ".trace")); check(bool(trace));
  widgets->mmio.trace = &trace;
}
int step() {
  if (index == operations) {
    if (!restoring) snapshot("cut-" + std::to_string(index));
    snapshot(prefix + ".final");
    trace.close(); widgets.reset(); return 1;
  }
  if (!restoring) snapshot("cut-" + std::to_string(index));
  auto &w = *widgets;
  trace << "OP " << index << '\n';
  w.mmio.mode = index == 19 || index == 22 ? 1 : index == 20 ? 2 : 0;
  struct data_t {
    mpz_t value;
    data_t() { mpz_init(value); }
    ~data_t() { mpz_clear(value); }
  } owned_data;
  auto &data = owned_data.value;
  auto result = [&](uint64_t value) { trace << "RESULT " << value << '\n'; };
  switch (index) {
  case 0: result(w.master.is_init_done()); break;
  case 1: result(w.master.check_fingerprint()); break;
  case 2: w.master.write_fingerprint(0x12345678); break;
  case 3: result(w.clock.hcycle()); break;
  case 4: result(w.clock.tcycle()); break;
  case 5: w.reset.init(); break;
  case 6: mpz_set_ui(data, 0xfeedbeef); w.memory.write_mem(0x123456789ULL, data); break;
  case 7: w.memory.read_mem(0x3456789abULL, data); break;
  case 8: mpz_set_str(data, "abcdef0123456789fedcba98", 16); w.memory.write_mem_chunk(32, data, 16); break;
  case 9: w.memory.zero_out_dram(); break;
  case 10: w.memory.load_mem_from_file((out / "input.hex").string()); break;
  case 11: w.peek.poke("in", 123, false); break;
  case 12: mpz_set_str(data, "abcdef0123456789fedcba98", 16); w.peek.poke("in", data); break;
  case 13: result(w.peek.peek("out", false)); break;
  case 14: w.peek.peek("out", data); break;
  case 15: w.peek.step(17, false); break;
  case 16: result(w.peek.is_done()); break;
  case 17: w.peek.poke("in", 321, true); break;
  case 18: case 19: case 20: result(w.peek.peek("out", true)); break;
  case 21: w.peek.step(11, true); break;
  case 22: w.peek.poke("in", 777, true); break;
  case 23: w.peek.peek("out", data); break;
  case 24: result(w.clock.tcycle()); break;
  }
  char *hex = mpz_get_str(nullptr, 16, data);
  trace << "GMP " << hex << " FLAGS " << w.peek.unstable() << ' ' << w.peek.timeout() << '\n';
  free(hex);
  ++index; return 0;
}
void negatives() {
  const auto root = out;
  widgets_t w;
  for (auto *owner : w.owners) {
    auto good = owner->save_checkpoint();
    auto malformed = [&](std::vector<uint8_t> bad) {
      const auto calls = w.mmio.calls;
      rejects([&] { owner->validate_checkpoint(bad); });
      rejects([&] { owner->load_checkpoint(bad); });
      check(owner->save_checkpoint() == good && w.mmio.calls == calls);
    };
    for (size_t n = 0; n < good.size(); ++n) malformed({good.begin(), good.begin() + n});
    auto bad = good; bad.push_back(0); malformed(bad);
    // Change every configuration byte, including type/version/address/map/geometry.
    for (size_t n = 0; n < good.size() - 8; ++n) { bad = good; bad[n] ^= 1; malformed(bad); }
    bad = good; bad.back() = 0x80; malformed(bad);
    for (auto *other : w.owners) if (other != owner) {
      const auto before = other->save_checkpoint();
      rejects([&] { other->load_checkpoint(good); }); check(other->save_checkpoint() == before);
    }
  }
  // Changed port maps, width, reset selection and MMIO bindings reject before writes.
  master_t master(w.mmio, {0,4,12}, 0, {});
  clockmodule_t clock(w.mmio, {16,20,24,28,32,40}, 0, {});
  loadmem_t memory(w.mmio, {64,68,72,76,80,84,88,92,96}, 0, {}, {4,40,64}, 2);
  reset_pulse_t reset(w.mmio, {112,116}, 0, {"+reset-pulse-length0=8"}, 20, 5);
  peek_poke_t peek(w.mmio, {128,132,136}, 0, {}, {{"renamed",{144,3}}}, {{"out",{160,3}}});
  std::vector<checkpoint_owner_t *> other{&master,&clock,&memory,&reset,&peek};
  for (size_t i = 0; i < other.size(); ++i)
    rejects([&] { other[i]->load_checkpoint(w.owners[i]->save_checkpoint()); });
  // Exercise every public entry point, checking each MMIO suspension and poison
  // after an interrupted operation. Internal file/write and step/poll calls
  // remain covered by the outer guard, without permitting external reentry.
  for (unsigned op = 0; op < operations; ++op) {
    for (bool interrupt : {false, true}) {
      const auto case_out = root / ("negative-op-" + std::to_string(op) +
                                   (interrupt ? "-interrupted" : "-suspended"));
      std::filesystem::create_directories(case_out);
      init(case_out, false, 0); index = op;
      auto &f = *widgets;
      unsigned owner_index = op <= 2 ? 0 : op <= 4 || op == 24 ? 1 : op == 5 ? 3 : op <= 10 ? 2 : 4;
      auto *owner = f.owners[owner_index];
      auto good = owner->save_checkpoint();
      unsigned checked = 0;
      f.mmio.hook = [&] {
        ++checked;
        rejects([&] { owner->save_checkpoint(); });
        rejects([&] { owner->validate_checkpoint(good); });
        rejects([&] { owner->load_checkpoint(good); });
        // Entering another public call on the same widget also rejects.
        if (owner_index == 0) rejects([&] { f.master.is_init_done(); });
        if (owner_index == 1) rejects([&] { f.clock.hcycle(); });
        if (owner_index == 2) rejects([&] { f.memory.zero_out_dram(); });
        if (owner_index == 3) rejects([&] { f.reset.init(); });
        if (owner_index == 4) rejects([&] { f.peek.is_done(); });
        if (interrupt) throw std::runtime_error("injected MMIO interruption");
      };
      if (interrupt) rejects([&] { step(); }); else step();
      check(checked > 0);
      f.mmio.hook = {};
      if (interrupt) {
        rejects([&] { owner->save_checkpoint(); });
        rejects([&] { owner->validate_checkpoint(good); });
        rejects([&] { owner->load_checkpoint(good); });
      } else owner->validate_checkpoint(owner->save_checkpoint());
      trace.close(); widgets.reset();
    }
  }
  checkpoint_owner_t unsupported;
  check(unsupported.checkpoint_schema().empty());
  rejects([&] { unsupported.save_checkpoint(); });
  std::cout << "PASS: widget payload/suspension/reentry/interruption rejections " << rejected << '\n';
}
} // namespace
#ifdef WIDGET_CHECKPOINT_DPI
extern "C" int widget_init(const char *directory, int restore, int cut) {
  try { init(directory, restore, cut); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
extern "C" int widget_step() {
  try { return step(); }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return -1; }
}
extern "C" int widget_negative(const char *directory) {
  try { out=directory; negatives(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#else
int main(int argc, char **argv) {
  try {
    check(argc == 4);
    if (std::string(argv[1]) == "negative") { out=argv[2]; negatives(); }
    else { init(argv[2], std::string(argv[1]) == "restore", std::stoul(argv[3])); while (!step()) {} }
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
