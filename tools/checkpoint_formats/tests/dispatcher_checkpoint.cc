// Actual simif_emul_t worker and simulation_t flow. MMIO target responses and
// the RTL clock are fixtures: this is dispatcher continuation, not .fsckpt.
#include "emul/simif_emul.h"
#include "core/simulation.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include <filesystem>
#include <fstream>
#include <functional>

static uint64_t now = 1000000;
midas_time_t timestamp() { return now += 100; }
double diff_secs(midas_time_t e, midas_time_t s) { return (e-s)/1000000.0; }

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "dispatcher-fixture"};
void check(bool ok) { if (!ok) throw std::runtime_error("dispatcher assertion"); }
unsigned rejected = 0;
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected dispatcher rejection");
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); check(bool(f));
}
struct platform_t : simif_emul_t {
  uint64_t ticks = 0, calls = 0;
  unsigned index = 0;
  bool yield = true;
  std::ostream *trace = nullptr;
  static std::vector<std::string> memory_args(std::vector<std::string> args) {
    args.push_back("+memsize=4096"); return args;
  }
  platform_t(std::vector<std::string> args = {}) : simif_emul_t(cfg,memory_args(args)) {}
  void write(size_t a, uint32_t d) override {
    ++calls;
    if (trace) *trace << ticks << " W " << a << ' ' << d << '\n';
    if (yield) do_tick();
  }
  uint32_t read(size_t a) override {
    ++calls;
    const uint32_t d = a == 0 ? 1 : a == 4 ? 0x46697265 : a == 16 ? 23 :
                       a == 28 ? 42 : a == 104 ? index * 9 : 0;
    if (trace) *trace << ticks << " R " << a << ' ' << d << '\n';
    if (yield) do_tick();
    return d;
  }
};
struct driver_t : simulation_t {
  platform_t &platform;
  unsigned index = 0, scenario;
  bool supported = true;
  driver_t(widget_registry_t &r, platform_t &p, unsigned scenario)
      : simulation_t(r,{}), platform(p), scenario(scenario) {}
  std::string checkpoint_schema() const override {
    return supported ? "fixture.dispatcher.driver.v1" : "";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    if (!supported || index < 1 || index > 4)
      throw std::runtime_error("unloaded/unsupported fixture driver");
    return {uint8_t(index), uint8_t(scenario)};
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override {
    if (!supported || b.size()!=2 || b[0]<1 || b[0]>4 || b[1]!=scenario)
      throw std::runtime_error("fixture driver mismatch");
  }
  void load_checkpoint(const std::vector<uint8_t> &b) override {
    validate_checkpoint(b); check(index == 0); index = b[0];
  }
  bool simulation_supports_steps() const override { return true; }
  int simulation_run() override { throw std::runtime_error("blocking flow"); }
  bool simulation_run_step() override {
    check(index < 4);
    if (index==0) {
      // Native traffic is intentionally not serviced by fixture MMIO. It must
      // survive capture/loading/bootstrap without an extra native model tick.
      platform.master->read_req(128,2,0);
      uint32_t data=0x12345678; size_t strobe=15;
      platform.master->write_req(256,2,0,&data,&strobe);
      auto &mem=*platform.slave.at(0);
      auto *bytes=static_cast<uint8_t *>(mem.get_data());
      for (size_t i=0;i<mem.get_size();++i) bytes[i]=uint8_t(i*13+7);
      mem.tick(false,true,128,2,2,1,true,256,3,2,1,false,0,{0,0,0},false,false,false);
      check(mem.w_ready() && mem.r_valid());
    }
    platform.index = index;
    platform.write(100,index);
    check(platform.read(104)==index*9);
    return ++index == 4;
  }
  int simulation_run_finalize() override {
    check(index==4);
    if (scenario==3) platform.yield=false; // terminal flow with no further yield
    return scenario==1 ? 7 : 0;
  }
  bool simulation_timed_out() override { return scenario==2; }
  checkpoint_owner_t &base() { return *checkpoint_driver_owners().at(1).second; }
};
struct fixture_t {
  platform_t platform;
  widget_registry_t registry;
  driver_t driver;
  fixture_t(unsigned scenario, std::vector<std::string> args = {})
      : platform(args), driver(registry_with_widgets(), platform, scenario) {}
  widget_registry_t &registry_with_widgets() {
    registry.add_widget(new master_t(platform,{0,4,8},0,{}));
    registry.add_widget(new clockmodule_t(platform,{16,20,24,28,32,36},0,{}));
    return registry;
  }
};
std::unique_ptr<fixture_t> fixture;
std::ofstream trace;
std::filesystem::path output;
bool finished = false, restoring = false;
unsigned scenario = 0;
void snapshot() {
  write(output/"initial.base", fixture->driver.base().save_checkpoint());
  write(output/"initial.driver", fixture->driver.save_checkpoint());
  auto timing = fixture->platform.checkpoint_host_timing_owner().second;
  write(output/"initial.timing", timing->save_checkpoint());
  write(output/"initial.mmio", fixture->platform.master->save_checkpoint());
  write(output/"initial.memory", fixture->platform.slave.at(0)->save_checkpoint());
}
void init(const std::filesystem::path &source, const std::filesystem::path &out,
          bool restore, unsigned cut, unsigned which, uint64_t ticks) {
  output=out; restoring=restore; scenario=which;
  std::vector<std::string> args;
  if (!restore) args={"+fs-driver-cut="+std::to_string(cut),
      "+fs-driver-diagnostic="+(out/"software.diag").string(),
      "+fs-driver-settled", "+fs-driver-lowclock"};
  fixture=std::make_unique<fixture_t>(which,args);
  fixture->platform.ticks=ticks;
  if (restore) {
    auto &p=fixture->platform;
    auto &d=fixture->driver;
    uint32_t low_banks[3]={0,0,0};
    rejects([&]{ p.to_sim(); }); // must not wait on an absent worker
    rejects([&]{ p.start_restored_driver(d,67,low_banks); }); // unloaded flow
    // Every owner validates before the first load. Files were extracted from
    // the real settled diagnostic in a separate process.
    auto base=read(source/"base"), driver=read(source/"driver");
    auto timing=read(source/"timing"), mmio=read(source/"mmio");
    auto memory=read(source/"memory"); auto &mem=*p.slave.at(0);
    auto *t=p.checkpoint_host_timing_owner().second;
    d.base().validate_checkpoint(base); d.validate_checkpoint(driver);
    t->validate_checkpoint(timing); p.master->validate_checkpoint(mmio);
    mem.validate_checkpoint(memory);
    d.base().load_checkpoint(base);
    rejects([&]{ p.start_driver(d); }); // ordinary start must not reinitialize
    rejects([&]{ p.start_restored_driver(d,67,low_banks); }); // concrete owner not loaded
    d.load_checkpoint(driver); t->load_checkpoint(timing); p.master->load_checkpoint(mmio); mem.load_checkpoint(memory);
    low_banks[0]=4; // packed clock is high
    rejects([&]{ p.start_restored_driver(d,67,low_banks); });
    low_banks[0]=0;
    rejects([&]{ p.start_restored_driver(d,67,nullptr); });
    for (uint32_t flag : {1U,2U}) {
      low_banks[0]=flag; // reset or finish is unsupported
      rejects([&]{ p.start_restored_driver(d,67,low_banks); });
    }
    low_banks[0]=0;
    check(p.calls==0 && p.ticks==ticks);
    d.supported=false;
    rejects([&]{ p.start_restored_driver(d,67,low_banks); }); // unknown concrete driver
    d.supported=true;
    snapshot();
    trace.open(out/"trace"); check(bool(trace)); p.trace=&trace;
    std::cout<<"RESTORED_BEFORE_FIRST_EDGE ticks="<<ticks<<" calls=0\n";
    now=1000100;
    finished=p.start_restored_driver(d,67,low_banks);
    // Starting twice must reject without replacing a joinable worker.
    rejects([&]{ p.start_restored_driver(d,67,low_banks); });
    rejects([&]{ p.start_driver(d); });
    std::cout<<"BOOTSTRAP_NO_EDGE ticks="<<p.ticks<<" finished="<<finished<<'\n';
    check(p.ticks==ticks);
    check(p.master->save_checkpoint()==mmio && mem.save_checkpoint()==memory);
    check(mem.w_ready() && mem.r_valid());
    write(output/"bootstrap.mmio",p.master->save_checkpoint());
    write(output/"bootstrap.memory",mem.save_checkpoint());
  } else {
    trace.open(out/"trace"); check(bool(trace)); fixture->platform.trace=&trace;
    fixture->platform.start_driver(fixture->driver);
    rejects([&]{ fixture->platform.start_driver(fixture->driver); });
  }
}
bool tick() {
  auto &p=fixture->platform;
  if (finished) return true;
  ++p.ticks;
  finished=p.to_sim();
  return finished;
}
void settled() {
  auto &p=fixture->platform;
  check(!restoring && p.checkpoint_pending() && p.checkpoint_lowclock());
  const auto ticks=p.ticks;
  write(output/"cut.ticks", {uint8_t(ticks)});
  trace<<"CUT "<<ticks<<'\n';
  uint32_t low_banks[3]={0,0,0};
  finished=p.checkpoint_settled(67,low_banks);
  check(p.ticks==ticks);
}
void finish() {
  check(finished);
  const int code=fixture->platform.end();
  check(code==(scenario==1 ? 7 : scenario==2 ? 1 : 0));
  trace.close();
  std::cout<<"PASS: real dispatcher result="<<code<<" ticks="<<fixture->platform.ticks
           <<" rejections="<<rejected<<'\n';
  fixture.reset();
}
} // namespace

#ifdef DISPATCHER_CHECKPOINT_DPI
extern "C" void dispatcher_init(const char *source, const char *out, unsigned restore,
                                unsigned cut, unsigned which, unsigned ticks) {
  try { init(source,out,restore,cut,which,ticks); }
  catch (const std::exception &e) {
    std::cerr<<"DISPATCHER_REJECTED_BEFORE_FIRST_EDGE "<<e.what()<<'\n'; std::_Exit(1);
  }
}
extern "C" unsigned dispatcher_tick() { return tick(); }
extern "C" unsigned dispatcher_pending() { return fixture->platform.checkpoint_pending(); }
extern "C" unsigned dispatcher_finished() { return finished; }
extern "C" void dispatcher_settled() { settled(); }
extern "C" void dispatcher_finish() { finish(); }
#else
int main(int argc,char **argv) {
  try {
    check(argc==7);
    init(argv[1],argv[2],std::stoul(argv[3]),std::stoul(argv[4]),std::stoul(argv[5]),std::stoul(argv[6]));
    unsigned edges=0;
    while (!finished) {
      check(++edges<100);
      tick();
      if (fixture->platform.checkpoint_pending()) settled();
    }
    finish(); return 0;
  } catch (const std::exception &e) {
    std::cerr<<"DISPATCHER_REJECTED_BEFORE_FIRST_EDGE "<<e.what()<<'\n'; std::_Exit(1);
  }
}
#endif
