// Actual concrete FCFS driver and scheduler/loop, independent MMIO fixture.
// These component cuts do not certify generated RTL or whole-runtime restore.
#include "fasedtests/fasedtests_top.cc"
#include "core/simif.h"
#include <filesystem>
#include <fstream>
#include <iostream>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
midas_time_t timestamp() { return 1000000; }
double diff_secs(midas_time_t e, midas_time_t s) { return (e-s)/1000000.0; }

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "fcfs-fixture"};
unsigned rejected = 0;
void check(bool b) { if (!b) throw std::runtime_error("FCFS test assertion"); }
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected FCFS rejection");
}
struct platform_t : simif_t {
  platform_t() : simif_t(cfg) {}
  unsigned samples = 0, scenario = 0;
  uint64_t calls = 0;
  std::ostream *trace = nullptr;
  std::function<void(size_t)> hook;
  void write(size_t a, uint32_t d) override {
    ++calls; if (hook) hook(a);
    if (trace) *trace << "W " << a << ' ' << d << '\n';
  }
  uint32_t read(size_t a) override {
    ++calls; if (hook) hook(a);
    uint32_t d = a == 112 ? (++samples == 2) : a == 200 || a == 300 ? 17 : 0xffffffff;
    if (a == 104) d = 0;
    if (scenario == 1 && a == 308) d = 4;
    if (trace) *trace << "R " << a << ' ' << d << '\n';
    return d;
  }
};
struct fixture_t {
  platform_t platform;
  widget_registry_t registry;
  std::unique_ptr<fasedtests_top_t> driver;
  fixture_t(unsigned scenario = 0, std::vector<std::string> args = {},
            unsigned delta = 0, unsigned model_count = 2) {
    platform.scenario = scenario;
    registry.add_widget(new clockmodule_t(platform, {16,20,24,28,32,36}, 0, {}));
    registry.add_widget(new peek_poke_t(platform, {100,104,108}, 0, {}, {},
                                      {{"done", {112,1}}}));
    for (unsigned i = 0; i < model_count; ++i) {
      unsigned base = 200 + i*100 + delta;
      registry.add_widget(new FASEDMemoryTimingModel(platform,
          AddressMap({{"eventsA",base},{"eventsB",base+8}}, {}), i, {},
          "stats-"+std::to_string(i)+".csv", 1024));
    }
    std::vector<std::string> effective{
      scenario == 2 ? "+max-cycles=0" : "+max-cycles=1000",
      "+expect_eventsA=3", "+expect_eventsA=17", "+expect_eventsB=-1"};
    effective.insert(effective.end(), args.begin(), args.end());
    driver = std::make_unique<fasedtests_top_t>(platform, registry, effective);
  }
  checkpoint_owner_t &owner(const std::string &key) {
    for (const auto &[name, owner] : driver->checkpoint_driver_owners())
      if (name == key) return *owner;
    throw std::runtime_error("missing component owner");
  }
};
const std::vector<std::string> keys{"runtime/simulation", "runtime/scheduler",
                                  "runtime/simulation/fased-run-loop"};
void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()),b.size()); check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
std::unique_ptr<fixture_t> fixture;
std::filesystem::path output;
std::ofstream trace;
unsigned index = 0, scenario = 0;
void snapshot(const std::string &prefix) {
  const auto calls = fixture->platform.calls;
  for (unsigned i = 0; i < keys.size(); ++i) {
    auto &owner = fixture->owner(keys[i]);
    auto bytes = owner.save_checkpoint(); owner.validate_checkpoint(bytes);
    write(output / (prefix+"."+std::to_string(i)+".owner"), bytes);
  }
  write(output / (prefix+".fixture"), {uint8_t(fixture->platform.samples)});
  check(fixture->platform.calls == calls);
}
void init(const std::filesystem::path &source, const std::filesystem::path &out,
          bool restore, unsigned cut, unsigned which) {
  output = out; index = restore ? cut : 0; scenario = which;
  fixture = std::make_unique<fixture_t>(which);
  if (restore) {
    const auto stats0 = read("stats-0.csv"), stats1 = read("stats-1.csv");
    for (unsigned i = 0; i < keys.size(); ++i)
      fixture->owner(keys[i]).validate_checkpoint(read(source / ("cut-"+std::to_string(cut)+"."+std::to_string(i)+".owner")));
    for (unsigned i = 0; i < keys.size(); ++i)
      fixture->owner(keys[i]).load_checkpoint(read(source / ("cut-"+std::to_string(cut)+"."+std::to_string(i)+".owner")));
    fixture->platform.samples = read(source / ("cut-"+std::to_string(cut)+".fixture")).at(0);
    snapshot("initial");
    check(fixture->platform.calls == 0);
    check(read("stats-0.csv") == stats0 && read("stats-1.csv") == stats1);
    std::cout << "RESTORED_BEFORE_FIRST_EDGE calls=0\n";
  }
}
void run_flow() {
  trace.open(output / "trace"); check(bool(trace)); fixture->platform.trace = &trace;
  auto &driver = *fixture->driver;
  bool done = fixture->owner(keys[2]).save_checkpoint().at(24) == 6;
  while (!done) {
    trace << "OP " << ++index << '\n';
    done = driver.simulation_run_step();
    snapshot("cut-"+std::to_string(index));
  }
  snapshot("terminal");
  trace << "FINAL\n";
  int result = driver.simulation_run_finalize();
  check(result == (scenario == 1 ? 1 : 0));
  check(driver.simulation_timed_out() == (scenario == 2));
  rejects([&] { fixture->owner(keys[0]).save_checkpoint(); });
  rejects([&] { fixture->owner(keys[0]).load_checkpoint({}); });
  rejects([&] { driver.simulation_run_step(); });
  rejects([&] { driver.simulation_run_finalize(); });
  trace.close(); fixture.reset();
  std::cout << "PASS: FCFS continuation operations=" << index << " result=" << result << '\n';
}
void negative() {
  fixture_t reference; auto &r = *reference.driver;
  check(reference.owner(keys[0]).checkpoint_schema() == "firesim.simulation.fcfs.v1");
  rejects([&] { reference.owner(keys[0]).save_checkpoint(); });
  r.simulation_run_step(); auto good = reference.owner(keys[0]).save_checkpoint();
  fixture_t fresh;
  auto unchanged = [&] { check(fresh.platform.calls == 0); rejects([&] { fresh.owner(keys[0]).save_checkpoint(); }); };
  auto bad_load = [&](const std::vector<uint8_t> &bad) {
    rejects([&] { fresh.owner(keys[0]).validate_checkpoint(bad); }); rejects([&] { fresh.owner(keys[0]).load_checkpoint(bad); }); unchanged();
  };
  for (size_t size = 0; size < good.size(); ++size) bad_load({good.begin(),good.begin()+size});
  auto bad = good; bad.push_back(0); bad_load(bad);
  for (size_t i = 0; i < good.size(); ++i) { bad = good; bad[i] ^= 128; bad_load(bad); }
  bad = good; bad[bad.size()-8] = 0; bad_load(bad);
  for (auto args : std::vector<std::vector<std::string>>{
       {"+expect_eventsA=18"}, {"+expect_eventsB=0"}, {"+expect_absent=1"},
       {"+profile-interval=3"}, {"+profile-interval=0"}}) {
    fixture_t mismatch(0,args);
    rejects([&] { mismatch.owner(keys[0]).load_checkpoint(good); }); check(mismatch.platform.calls == 0);
  }
  fixture_t different_map(0, {}, 4), different_count(0, {}, 0, 1);
  rejects([&] { different_map.owner(keys[0]).load_checkpoint(good); });
  rejects([&] { different_count.owner(keys[0]).load_checkpoint(good); });
  check(different_map.platform.calls == 0 && different_count.platform.calls == 0);
  fresh.owner(keys[0]).load_checkpoint(good); check(fresh.owner(keys[0]).save_checkpoint() == good);
  rejects([&] { fresh.owner(keys[0]).load_checkpoint(good); });
  rejects([&] { reference.owner(keys[0]).load_checkpoint(good); });
  fixture_t profile(0, {"+profile-interval=3"});
  profile.driver->simulation_run_step();
  rejects([&] { profile.driver->checkpoint_driver_owners(); }); // unaudited closure remains unsupported
  check(profile.platform.calls == 0);
  fixture_t changed_registry;
  changed_registry.driver->simulation_run_step();
  changed_registry.registry.add_widget(new FASEDMemoryTimingModel(changed_registry.platform,
      AddressMap({{"eventsA",400},{"eventsB",408}}, {}), 2, {}, "stats-2.csv", 1024));
  rejects([&] { changed_registry.owner(keys[0]).save_checkpoint(); });
  // Suspended MMIO, recursive driver entry, and interruption in a step or
  // counter finalization must never become a capture/retry boundary.
  for (unsigned operation : {0u, 1u}) {
    fixture_t interrupted; auto &d = *interrupted.driver;
    if (operation) while (!d.simulation_run_step()) {}
    interrupted.platform.hook = [&](size_t) {
      rejects([&] { interrupted.owner(keys[0]).save_checkpoint(); }); rejects([&] { interrupted.owner(keys[0]).validate_checkpoint(good); });
      rejects([&] { interrupted.owner(keys[0]).load_checkpoint(good); }); rejects([&] { d.simulation_run_step(); });
      rejects([&] { d.simulation_run_finalize(); });
      throw std::runtime_error("injected FCFS MMIO interruption");
    };
    if (operation) rejects([&] { d.simulation_run_finalize(); });
    else { d.simulation_run_step(); d.simulation_run_step(); rejects([&] { d.simulation_run_step(); }); }
    rejects([&] { interrupted.owner(keys[0]).save_checkpoint(); }); rejects([&] { interrupted.owner(keys[0]).load_checkpoint(good); });
    rejects([&] { d.simulation_run_step(); }); rejects([&] { d.simulation_run_finalize(); });
  }
  std::cout << "PASS: FCFS rejections " << rejected << '\n';
}
}
#ifdef FCFS_CHECKPOINT_DPI
extern "C" int fcfs_checkpoint_init(const char *source, const char *out, int restore, int cut, int which) {
  try { init(source,out,restore,cut,which); return 0; }
  catch (const std::exception &e) { std::cerr << "REJECTED_BEFORE_FIRST_EDGE: " << e.what() << '\n'; std::exit(1); }
}
extern "C" int fcfs_checkpoint_run() {
  try { run_flow(); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int fcfs_checkpoint_negative() {
  try { negative(); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
#else
int main(int argc, char **argv) {
  try {
    if (argc == 2) negative();
    else { check(argc == 6); init(argv[1],argv[2],std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5])); run_flow(); }
    return 0;
  } catch (const std::exception &e) { std::cerr << "REJECTED_BEFORE_FIRST_EDGE: " << e.what() << '\n'; return 1; }
}
#endif
