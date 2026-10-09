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
    check(index < 4); // terminal restore must never repeat this operation
    platform.index = index;
    platform.write(100, index);
    check(platform.read(104) == index * 9);
    return ++index == 4;
  }
  int simulation_run_finalize() override {
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
    fixture->driver->base().load_checkpoint(bytes);
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
#else
int main(int argc, char **argv) {
  try {
    if (argc == 2) negative();
    else { check(argc == 6); init(argv[1],argv[2],std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5])); run_flow(); }
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
