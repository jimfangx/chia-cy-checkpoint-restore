// Real harness/DPI/dispatcher with a small audited driver. MMIO services used
// by simulation_t are fixtures; this is component integration, not .fsckpt.
#include "emul/simif_emul.h"
#include "core/simulation.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include <vpi_user.h>
#include <filesystem>
#include <fstream>
#include <functional>

simif_emul_t *simulator = nullptr;
static midas_time_t now = 1000000;
midas_time_t timestamp() { return now += 100; }
double diff_secs(midas_time_t e, midas_time_t s) { return (e-s)/1000000.0; }
namespace {
const TargetConfig cfg{{12,32,32}, {16,34,64}, 1, {}, {}, {256,0}, "harness-dispatcher-fixture"};
std::filesystem::path source, output;
std::ofstream trace;
void check(bool b) { if (!b) throw std::runtime_error("harness dispatcher assertion"); }
std::vector<uint8_t> read_file(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
void save_file(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()),b.size()); check(bool(f));
}
unsigned rejections=0;
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch(const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("expected bootstrap lifecycle rejection");
}
struct platform_t : simif_emul_t {
  bool yield = true;
  unsigned calls = 0;
  platform_t(const std::vector<std::string> &args) : simif_emul_t(cfg,args) {}
  ~platform_t() override {
    save_file(output/"final.mmio",master->save_checkpoint());
    save_file(output/"final.memory",slave.at(0)->save_checkpoint());
  }
  void write(size_t a,uint32_t d) override {
    ++calls; trace << "W " << a << ' ' << d << '\n';
    if (yield) do_tick();
  }
  uint32_t read(size_t a) override {
    ++calls;
    const uint32_t d=a==0 ? 1 : a==4 ? 0x46697265 : a==16 ? 23 : a==28 ? 42 : 0;
    trace << "R " << a << ' ' << d << '\n';
    if (yield) do_tick(); return d;
  }
};
struct driver_t : simulation_t {
  platform_t &p;
  unsigned index=0;
  bool supported=true;
  driver_t(widget_registry_t &r,platform_t &p) : simulation_t(r,{}),p(p) {}
  std::string checkpoint_schema() const override { return supported ? "fixture.harness-dispatcher.v1" : ""; }
  std::vector<uint8_t> save_checkpoint() const override {
    check(supported && index>0 && index<=32); return {uint8_t(index)};
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override {
    check(supported && b.size()==1 && b[0]>0 && b[0]<=32);
  }
  void load_checkpoint(const std::vector<uint8_t> &b) override { validate_checkpoint(b); check(!index); index=b[0]; }
  bool simulation_supports_steps() const override { return true; }
  int simulation_run() override { throw std::runtime_error("blocking driver"); }
  bool simulation_run_step() override {
    if (index==12) {
      // Retain a partial write and two held responses in a real native owner.
      auto &m=*p.slave.at(0); auto *bytes=static_cast<uint8_t *>(m.get_data());
      for(size_t i=0;i<m.get_size();++i) bytes[i]=uint8_t(i*13+7);
      m.tick(false,true,128,2,2,1,true,256,3,2,1,false,0,{0,0},false,false,false);
      p.master->read_req(128,2,0);
    }
    trace << "OP " << index << '\n';
    p.do_tick(); return ++index==32;
  }
  int simulation_run_finalize() override { p.yield=false; return 0; }
};
std::unique_ptr<widget_registry_t> registry;
std::unique_ptr<driver_t> driver;
std::vector<std::pair<std::string,checkpoint_owner_t *>> owners() {
  auto list=simulator->checkpoint_axi_owners();
  list.push_back(simulator->checkpoint_host_timing_owner());
  const auto d=driver->checkpoint_driver_owners(), w=driver->checkpoint_widget_owners();
  list.insert(list.end(),d.begin(),d.end());list.insert(list.end(),w.begin(),w.end());return list;
}
}
int entry(int argc,char **argv) {
  try {
    unsigned cut=0; bool restore=false; std::string negative;
    for(int i=1;i<argc;++i) {
      const std::string a=argv[i];
      if(a.rfind("+source=",0)==0) source=a.substr(8);
      if(a.rfind("+outdir=",0)==0) output=a.substr(8);
      if(a.rfind("+cut=",0)==0) cut=std::stoul(a.substr(5));
      if(a=="+restore") restore=true;
      if(a.rfind("+negative=",0)==0) negative=a.substr(10);
    }
    check(cut>0 && !output.empty());
    std::vector<std::string> args={"+memsize=4096"};
    if(!restore) {
      args.push_back("+fs-driver-cut="+std::to_string(cut));
      args.push_back("+fs-driver-diagnostic="+(output/"software.diag").string());
      args.push_back("+fs-driver-settled"); args.push_back("+fs-driver-lowclock");
    }
    auto *p=new platform_t(args); simulator=p;
    registry=std::make_unique<widget_registry_t>();
    registry->add_widget(new master_t(*p,{0,4,8},0,{}));
    registry->add_widget(new clockmodule_t(*p,{16,20,24,28,32,36},0,{}));
    driver=std::make_unique<driver_t>(*registry,*p);
    if(restore) {
      uint32_t banks[3]={0,0,0};
      rejects([&]{ p->resume_restored_driver(67,banks); });
      rejects([&]{ p->arm_restored_driver(*driver); });
      auto list=owners(); std::vector<std::vector<uint8_t>> payloads;
      for(size_t i=0;i<list.size();++i) {
        auto b=read_file(source/("owner-"+std::to_string(i)));
        list[i].second->validate_checkpoint(b); payloads.push_back(std::move(b));
      }
      for(size_t i=0;i<list.size();++i) list[i].second->load_checkpoint(payloads[i]);
      if(negative=="unsupported") driver->supported=false;
      p->arm_restored_driver(*driver);
      rejects([&]{ p->arm_restored_driver(*driver); });
      rejects([&]{ p->start_driver(*driver); });
      rejects([&]{ p->start_restored_driver(*driver,67,banks); });
      check(rejections==5);
      puts("HARNESS_DISPATCHER_ARM_GUARDS count=5");
      // No worker, MMIO, trace or snapshot was published before validation.
      check(p->calls==0);
      for(size_t i=0;i<list.size();++i) save_file(output/("initial-"+std::to_string(i)),list[i].second->save_checkpoint());
      save_file(output/"initial.mmio",p->master->save_checkpoint());
      save_file(output/"initial.memory",p->slave.at(0)->save_checkpoint());
      now=1000100;
    } else p->start_driver(*driver);
    trace.open(output/"driver.trace");check(bool(trace));
    return 0;
  } catch(const std::exception &e) {
    fprintf(stderr,"HARNESS_DISPATCHER_REJECTED_BEFORE_EDGE: %s\n",e.what());
    std::fflush(nullptr);std::_Exit(1);
  }
}
extern "C" void harness_dispatcher_check_native() {
  try {
    // A terminal bootstrap has already joined/deleted the native simulator.
    auto mmio=simulator ? simulator->master->save_checkpoint() : read_file(output/"final.mmio");
    auto memory=simulator ? simulator->slave.at(0)->save_checkpoint() : read_file(output/"final.memory");
    check(mmio==read_file(output/"initial.mmio") && memory==read_file(output/"initial.memory"));
    trace.flush();
    puts("HARNESS_DISPATCHER_NATIVE_UNCHANGED");
  } catch(const std::exception &e) { fprintf(stderr,"native check: %s\n",e.what());std::_Exit(1); }
}
