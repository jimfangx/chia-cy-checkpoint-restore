// Real harness/DPI/dispatcher with a small audited driver. MMIO services used
// by simulation_t are fixtures; this is component integration, not .fsckpt.
#include "emul/simif_emul.h"
#include "core/simulation.h"
#include "entry.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include <vpi_user.h>
#include <filesystem>
#include <fstream>
#include <functional>
#ifdef AGGREGATE_RESTORE
#include "../aggregate_restore.h"
extern "C" int harness_restore_initialize();
extern "C" uint64_t generated_restore_deposit_count();
extern "C" uint64_t harness_restore_deposit_count();
static aggregate_restore_t aggregate;
static std::string aggregate_file, aggregate_negative;
#endif

std::unique_ptr<simif_t> simulator;
static simif_emul_t *emulator = nullptr;
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
  auto list=emulator->checkpoint_axi_owners();
  list.push_back(emulator->checkpoint_host_timing_owner());
  const auto d=driver->checkpoint_driver_owners(), w=driver->checkpoint_widget_owners();
  list.insert(list.end(),d.begin(),d.end());list.insert(list.end(),w.begin(),w.end());return list;
}
}
int entry(int argc,char **argv) {
  try {
    unsigned cut=0; bool restore=false; std::string negative, bundle;
    for(int i=1;i<argc;++i) {
      const std::string a=argv[i];
      if(a.rfind("+source=",0)==0) source=a.substr(8);
      if(a.rfind("+outdir=",0)==0) output=a.substr(8);
      if(a.rfind("+cut=",0)==0) cut=std::stoul(a.substr(5));
      if(a=="+restore") restore=true;
      if(a.rfind("+aggregate=",0)==0) bundle=a.substr(11);
      if(a.rfind("+negative=",0)==0) negative=a.substr(10);
    }
    check(cut>0 && !output.empty());
    std::vector<std::string> args={"+memsize=4096"};
    if(!restore) {
      args.push_back("+fs-driver-cut="+std::to_string(cut));
      args.push_back("+fs-driver-diagnostic="+(output/"software.diag").string());
      args.push_back("+fs-driver-settled"); args.push_back("+fs-driver-lowclock");
    }
    auto *p=new platform_t(args); simulator.reset(p); emulator=p;
    registry=std::make_unique<widget_registry_t>();
    registry->add_widget(new master_t(*p,{0,4,8},0,{}));
    registry->add_widget(new clockmodule_t(*p,{16,20,24,28,32,36},0,{}));
    driver=std::make_unique<driver_t>(*registry,*p);
#ifdef AGGREGATE_RESTORE
    if (restore && !bundle.empty()) {
      aggregate_file=bundle; aggregate_negative=negative;
      p->begin_restored_load(*driver);
      uint32_t banks[3]={0,0,0};
      rejects([&]{ p->begin_restored_load(*driver); });
      rejects([&]{ p->start_driver(*driver); });
      rejects([&]{ p->start_restored_driver(*driver,67,banks); });
      check(rejections==3); rejections=0;
      puts("AGGREGATE_RESERVATION_GUARDS count=3");
      return 0; // Return with clocks held; VPI settles before prevalidation.
    }
#endif
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
#ifdef AGGREGATE_RESTORE
extern "C" int harness_dispatcher_prepare_aggregate() {
  try {
    auto *p=static_cast<platform_t *>(simulator.get());
    uint32_t banks[3]={0,0,0};
    rejects([&]{ p->resume_restored_driver(67,banks); });
    rejects([&]{ p->arm_restored_driver(*driver); });
    auto list=owners();
    if(aggregate_negative=="unsupported") driver->supported=false;
    const auto mmio=p->master->save_checkpoint(), memory=p->slave.at(0)->save_checkpoint(), timing=p->checkpoint_host_timing_owner().second->save_checkpoint();
    try {
      aggregate.prepare(aggregate_file,list);
      if (aggregate_negative=="commit-order") aggregate.commit_rtl();
    }
    catch (...) {
      check(!generated_restore_deposit_count() && !harness_restore_deposit_count() &&
            p->master->save_checkpoint()==mmio && p->slave.at(0)->save_checkpoint()==memory &&
            p->checkpoint_host_timing_owner().second->save_checkpoint()==timing &&
            driver->index==0 && p->calls==0);
      rejects([&]{ aggregate.prepare(aggregate_file,list); });
      rejects([&]{ aggregate.commit_native(); });
      rejects([&]{ aggregate.commit_rtl(); });
      puts("AGGREGATE_REJECTED_UNCHANGED deposits=0 native_loads=0 driver_calls=0 poisoned=1");
      throw;
    }
    check(!generated_restore_deposit_count() && !harness_restore_deposit_count());
    aggregate.commit_native();
    puts("AGGREGATE_ALL_OWNERS_PREVALIDATED_BEFORE_LOAD");
    p->arm_restored_driver(*driver);
    rejects([&]{ p->arm_restored_driver(*driver); });
    rejects([&]{ p->start_driver(*driver); });
    rejects([&]{ p->start_restored_driver(*driver,67,banks); });
    check(rejections==5); puts("HARNESS_DISPATCHER_ARM_GUARDS count=5");
    for(size_t i=0;i<list.size();++i) save_file(output/("initial-"+std::to_string(i)),list[i].second->save_checkpoint());
    save_file(output/"initial.mmio",p->master->save_checkpoint());
    save_file(output/"initial.memory",p->slave.at(0)->save_checkpoint());
    now=1000100; trace.open(output/"driver.trace");check(bool(trace));
    return 0;
  } catch(const std::exception &e) {
    fprintf(stderr,"HARNESS_DISPATCHER_REJECTED_BEFORE_EDGE: %s\n",e.what());
    std::fflush(nullptr);std::_Exit(1);
  }
}

extern "C" int harness_dispatcher_commit_aggregate() {
  try { aggregate.commit_rtl(); return 0; }
  catch(const std::exception &e) { fprintf(stderr,"AGGREGATE_COMMIT_ERROR: %s\n",e.what()); return 1; }
}
#endif
extern "C" void harness_dispatcher_check_native() {
  try {
    // A terminal bootstrap has already joined/deleted the native simulator.
    auto mmio=simulator ? emulator->master->save_checkpoint() : read_file(output/"final.mmio");
    auto memory=simulator ? emulator->slave.at(0)->save_checkpoint() : read_file(output/"final.memory");
    check(mmio==read_file(output/"initial.mmio") && memory==read_file(output/"initial.memory"));
    trace.flush();
    puts("HARNESS_DISPATCHER_NATIVE_UNCHANGED");
  } catch(const std::exception &e) { fprintf(stderr,"native check: %s\n",e.what());std::_Exit(1); }
}
