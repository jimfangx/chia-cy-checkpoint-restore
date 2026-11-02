// Actual FASED host adapter with deterministic MMIO, not a full runtime restore.
#include "bridges/fased_memory_timing_model.h"
#include "core/config.h"
#include <filesystem>
#include <functional>
#include <iostream>
#include <memory>
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

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "fased-fixture"};
const std::vector<std::string> names{"hostReadLatency", "hostWriteLatency", "targetReadLatency",
 "targetWriteLatency", "ingressReadLatency", "ingressWriteLatency", "totalReadLatency", "totalWriteLatency"};
void check(bool b) { if (!b) throw std::runtime_error("FASED test assertion"); }
unsigned rejected = 0;
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected FASED rejection");
}
AddressMap address_map(unsigned scenario, unsigned delta = 0) {
  std::vector<std::pair<std::string,uint32_t>> r{{"latency",8+delta},{"cycles",12},{"requests",16}};
  std::vector<std::pair<std::string,uint32_t>> w{{"latency",8+delta}};
  if (scenario != 1 && scenario != 3)
    for (unsigned i=0;i<names.size();++i) {
      const unsigned base=64+i*16;
      r.emplace_back(names[i]+"Hist_dataH",base+8);
      r.emplace_back(names[i]+"Hist_dataL",base+12);
      w.emplace_back(names[i]+"Hist_enable",base);
      w.emplace_back(names[i]+"Hist_addr",base+4);
    }
  if (scenario != 1) {
    r.emplace_back("numRanges",32);
    for (unsigned i=0;i<2;++i) {
      const std::string name=i ? "write" : "read";
      const unsigned base=256+i*16;
      r.emplace_back(name+"Ranges_dataH",base+8);
      r.emplace_back(name+"Ranges_dataL",base+12);
      w.emplace_back(name+"Ranges_enable",base);
      w.emplace_back(name+"Ranges_addr",base+4);
    }
  }
  return {r,w};
}
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  unsigned stage=0, scenario=0;
  uint64_t calls=0;
  std::map<unsigned,unsigned> bins;
  std::ostream *trace=nullptr;
  std::function<void()> hook;
  void write(size_t a,uint32_t d) override {
    ++calls; if (hook) hook();
    if (a>=64 && a%16==4) bins[a-4]=d;
    if (trace) *trace<<"W "<<a<<' '<<d<<'\n';
  }
  uint32_t read(size_t a) override {
    ++calls; if (hook) hook();
    uint32_t d=stage*100+a;
    if (a==32) d=scenario==2 ? 0 : 3;
    if (a>=64) {
      unsigned base=a-a%16;
      uint64_t value=(uint64_t(base<256 ? 1 : 3)<<32)+
        (base<256 ? (base-64)/16 : (base-256)/16)*10000+bins[base]*13+stage*1000;
      d=a%16==8 ? uint32_t(value>>32)|0x80000000 : uint32_t(value);
    }
    if (trace) *trace<<"R "<<a<<' '<<d<<'\n';
    return d;
  }
};
std::vector<uint8_t> read_bytes(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
void write_bytes(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);
  f.write(reinterpret_cast<const char*>(b.data()),b.size()); check(bool(f));
}
std::unique_ptr<FASEDMemoryTimingModel> make(mmio_t &m,const std::string &path="stats.csv",
 unsigned delta=0,size_t memsize=1024,unsigned model=0,
 const std::vector<std::string> &args={"+mm_latency_0=7"}) {
  return std::make_unique<FASEDMemoryTimingModel>(m,address_map(m.scenario,delta),model,args,path,memsize);
}
std::unique_ptr<mmio_t> mmio;
std::unique_ptr<FASEDMemoryTimingModel> model;
std::ofstream trace;
unsigned index=0;
bool restoring=false;
void snapshot(const std::string &name) {
  const auto calls=mmio->calls;
  auto state=model->save_checkpoint(); model->validate_checkpoint(state);
  write_bytes(name,state); check(mmio->calls==calls);
}
void init(const std::string &reference,unsigned restore,unsigned cut,unsigned scenario) {
  check(cut<=4); index=restore ? cut : 0; restoring=restore;
  mmio=std::make_unique<mmio_t>(); mmio->scenario=scenario; model=make(*mmio);
  if (restore) {
    const auto payload=read_bytes(std::filesystem::path(reference)/("cut-"+std::to_string(cut)+".owner"));
    const auto before=read_bytes("stats.csv");
    if (restore == 2) {
      auto prepared=model->prepare_checkpoint_publication(payload);
      prepared->seal(); prepared->publish();
    } else {model->validate_checkpoint(payload);model->load_checkpoint(payload);}
    check(mmio->calls==0 && read_bytes("stats.csv")==before);
    snapshot("initial.owner");
  }
  trace.open("trace"); check(bool(trace)); mmio->trace=&trace;
}
int step() {
  mmio->stage=index;
  if (!restoring) snapshot("cut-"+std::to_string(index)+".owner");
  trace<<"OP "<<index<<'\n';
  if (!index) model->init();
  else if (index<4) model->profile();
  else {
    model->finish();
    rejects([]{model->save_checkpoint();});
    rejects([]{model->validate_checkpoint({});});
    rejects([]{model->load_checkpoint({});});
    rejects([]{model->prepare_checkpoint_publication({});});
    trace.close(); model.reset(); mmio.reset(); return 1;
  }
  ++index; return 0;
}
void negatives() {
  mmio_t m; auto f=make(m); f->init(); m.stage=1; f->profile();
  auto good=f->save_checkpoint();
  const auto disk=read_bytes("stats.csv"); const auto calls=m.calls;
  auto reject_payload=[&](std::vector<uint8_t> bad) {
    rejects([&]{f->validate_checkpoint(bad);}); rejects([&]{f->load_checkpoint(bad);});
    rejects([&]{f->prepare_checkpoint_publication(bad);});
    check(f->save_checkpoint()==good && m.calls==calls && read_bytes("stats.csv")==disk);
  };
  for (size_t size=0;size<good.size();size+=137) reject_payload({good.begin(),good.begin()+size});
  auto bad=good; bad.push_back(0); reject_payload(bad);
  for (size_t i=0;i<32;++i) {bad=good;bad[i]^=0x80;reject_payload(bad);}
  // Locate state by comparing the pre-init payload's zero histogram tail.
  // Configuration length is independently encoded by the Python verifier.
  auto fresh=make(m,"fresh.csv"); auto created=fresh->save_checkpoint();
  const size_t config_size=created.size()-16-std::string("cycles,requests,\n").size()-8*1024*8-16;
  for (uint64_t value : std::vector<uint64_t>{2,3,UINT64_MAX}) {
    bad=good; for(unsigned i=0;i<8;++i) bad[config_size+i]=value>>(8*i); reject_payload(bad);
  }
  bad=good; bad[config_size+8]=0xff; reject_payload(bad);
  // Corrupt CSV header, uint32 value, newline, baseline widths and range count.
  const size_t header=config_size+16;
  bad=good;bad[header]='x';reject_payload(bad);
  bad=good;bad[header+std::string("cycles,requests,\n").size()+3]=';';reject_payload(bad);
  bad=good;bad[header+std::string("cycles,requests,\n112,116,").size()]='x';reject_payload(bad);
  const size_t hist=header+std::string("cycles,requests,\n112,116,\n").size();
  bad=good;bad[hist+7]=0x80;reject_payload(bad);
  const size_t ranges=hist+8*1024*8;
  bad=good; for(unsigned i=0;i<8;++i) bad[ranges+i]=0xff;reject_payload(bad);
  bad=good;bad[ranges+8+7]=0x80;reject_payload(bad);
  bad=created;bad[config_size+16+std::string("cycles,requests,\n").size()]=1;reject_payload(bad);
  for(unsigned change=0;change<4;++change) {
    auto other=make(m,"other.csv",change==0 ? 4 : 0,change==1 ? 2048 : 1024,
      change==2 ? 1 : 0,change==3 ? std::vector<std::string>{"+mm_latency_0=9"} : std::vector<std::string>{"+mm_latency_0=7"});
    rejects([&]{other->validate_checkpoint(good);}); rejects([&]{other->load_checkpoint(good);});
    rejects([&]{other->prepare_checkpoint_publication(good);});
  }
  for(unsigned operation=0;operation<3;++operation) for(bool interrupt:{false,true}) {
    mmio_t bus;auto owner=make(bus,"guard.csv");
    if(operation) owner->init();
    const auto payload=owner->save_checkpoint();unsigned checked=0;
    bus.hook=[&]{
      if(checked++) return;
      rejects([&]{owner->save_checkpoint();});rejects([&]{owner->validate_checkpoint(payload);});
      rejects([&]{owner->load_checkpoint(payload);});rejects([&]{owner->profile();});
      rejects([&]{owner->prepare_checkpoint_publication(payload);});
      if(interrupt) throw std::runtime_error("injected FASED MMIO interruption");
    };
    auto call=[&]{if(!operation) owner->init();else if(operation==1) owner->profile();else owner->finish();};
    if(interrupt) rejects(call);else call();
    check(checked>0);bus.hook={};
    if(interrupt || operation==2) {
      rejects([&]{owner->save_checkpoint();});rejects([&]{owner->validate_checkpoint(payload);});
      rejects([&]{owner->load_checkpoint(payload);});
      rejects([&]{owner->prepare_checkpoint_publication(payload);});
    } else owner->validate_checkpoint(owner->save_checkpoint());
  }
  // Deferred output materialization failure poisons the owner before MMIO.
  {
    if (std::filesystem::is_directory("blocked.csv"))
      std::filesystem::remove("blocked.csv");
    mmio_t bus;auto owner=make(bus,"blocked.csv");owner->load_checkpoint(good);
    std::filesystem::remove("blocked.csv");std::filesystem::create_directory("blocked.csv");
    rejects([&]{owner->profile();});check(bus.calls==0);
    rejects([&]{owner->save_checkpoint();});rejects([&]{owner->load_checkpoint(good);});
    rejects([&]{owner->prepare_checkpoint_publication(good);});
    std::filesystem::remove("blocked.csv");
  }
  std::cout<<"PASS: FASED malformed/configuration/suspension/interruption rejections "<<rejected<<'\n';
}

// Exercise the production prepared adapter with independent real driver
// destinations. Neither candidate construction nor sealing may touch MMIO or
// files, and publication must restore every byte before ordinary continuation.
void prepared_checks() {
  mmio_t bus;auto owner=make(bus,"prepared.csv");
  const auto initial=owner->save_checkpoint();
  owner->init();bus.stage=1;owner->profile();const auto active=owner->save_checkpoint();
  const auto disk=read_bytes("prepared.csv");const auto calls=bus.calls;
  auto unchanged=[&] {
    check(owner->save_checkpoint()==active && bus.calls==calls && read_bytes("prepared.csv")==disk);
  };
  {auto candidate=owner->prepare_checkpoint_publication(initial);unchanged();}
  unchanged();
  {auto candidate=owner->prepare_checkpoint_publication(initial);candidate->seal();unchanged();}
  unchanged();
  {
    auto candidate=owner->prepare_checkpoint_publication(initial);candidate->seal();
    rejects([&]{candidate->seal();});unchanged();
  }
  {
    auto candidate=owner->prepare_checkpoint_publication(initial);
    bool rejected=false;
    std::thread other([&]{try {candidate->seal();} catch(const std::runtime_error &) {rejected=true;}});
    other.join();check(rejected);unchanged();
    candidate->seal();candidate->publish();
    check(owner->save_checkpoint()==initial && bus.calls==calls && read_bytes("prepared.csv")==disk);
  }
  owner->load_checkpoint(active);
  // Same-byte legacy loads and a complete ABA must invalidate old candidates.
  for(bool aba:{false,true}) {
    auto candidate=owner->prepare_checkpoint_publication(initial);
    if(aba) owner->load_checkpoint(initial);
    owner->load_checkpoint(active);
    rejects([&]{candidate->seal();});unchanged();
  }
  {
    auto first=owner->prepare_checkpoint_publication(initial);
    auto second=owner->prepare_checkpoint_publication(initial);
    first->seal();first->publish();rejects([&]{second->seal();});
    check(owner->save_checkpoint()==initial);owner->load_checkpoint(active);
  }
  {
    auto candidate=owner->prepare_checkpoint_publication(initial);
    auto bad=active;bad.push_back(0);
    rejects([&]{owner->load_checkpoint(bad);});
    candidate->seal();candidate->publish();check(owner->save_checkpoint()==initial);
    owner->load_checkpoint(active);
  }
  // Aggregate validation failure cancels the first candidate without publishing.
  {
    auto candidate=owner->prepare_checkpoint_publication(initial);
    checkpoint_owner_t unsupported;
    rejects([&]{unsupported.prepare_checkpoint_publication({});});unchanged();
  }
  // All checks/seals finish before either of two actual owners publishes.
  {
    mmio_t other_bus;auto other=make(other_bus,"aggregate.csv");
    const auto other_disk=read_bytes("aggregate.csv");
    auto first=owner->prepare_checkpoint_publication(initial);
    auto second=other->prepare_checkpoint_publication(active);
    first->seal();second->seal();unchanged();
    check(other_bus.calls==0 && other->save_checkpoint()==initial && read_bytes("aggregate.csv")==other_disk);
    first->publish();second->publish();
    check(owner->save_checkpoint()==initial && other->save_checkpoint()==active);
    check(bus.calls==calls && other_bus.calls==0 && read_bytes("prepared.csv")==disk &&
          read_bytes("aggregate.csv")==other_disk);
    owner->load_checkpoint(active);
  }
  // Address reuse must not revive a candidate whose actual owner died.
  {
    using storage_t=std::aligned_storage_t<sizeof(FASEDMemoryTimingModel),alignof(FASEDMemoryTimingModel)>;
    storage_t storage;
    auto *old=new(&storage) FASEDMemoryTimingModel(bus,address_map(0),0,{"+mm_latency_0=7"},"lifetime.csv",1024);
    auto candidate=old->prepare_checkpoint_publication(active);old->~FASEDMemoryTimingModel();
    auto *replacement=new(&storage) FASEDMemoryTimingModel(bus,address_map(0),0,{"+mm_latency_0=7"},"lifetime.csv",1024);
    rejects([&]{candidate->seal();});check(replacement->save_checkpoint()==initial);
    replacement->~FASEDMemoryTimingModel();
  }
  // Ordinary calls invalidate even if their work is later interrupted. During
  // the call, sealing must reject the suspended owner before any assignment.
  for(unsigned operation=0;operation<3;++operation) for(bool interrupt:{false,true}) {
    mmio_t current_bus;auto current=make(current_bus,"current.csv");
    if(operation) current->init();
    auto candidate=current->prepare_checkpoint_publication(initial);unsigned invoked=0;
    current_bus.hook=[&]{
      if(invoked++) return;
      rejects([&]{candidate->seal();});
      if(interrupt) throw std::runtime_error("prepared FASED operation interruption");
    };
    auto call=[&]{if(!operation) current->init();else if(operation==1) current->profile();else current->finish();};
    if(interrupt) rejects(call);else call();
    current_bus.hook={};check(invoked>0);rejects([&]{candidate->seal();});
  }
  {
    mmio_t current_bus;auto current=make(current_bus,"prepared-blocked.csv");current->load_checkpoint(active);
    auto candidate=current->prepare_checkpoint_publication(initial);
    std::filesystem::remove("prepared-blocked.csv");std::filesystem::create_directory("prepared-blocked.csv");
    rejects([&]{current->profile();});check(current_bus.calls==0);
    rejects([&]{candidate->seal();});std::filesystem::remove("prepared-blocked.csv");
  }
  unsigned failures[2]{};
  for(unsigned phase=0;phase<2;++phase) for(long n=0;;++n) {
    check(n<2000);
    std::unique_ptr<prepared_checkpoint_t> candidate;
    if(phase) candidate=owner->prepare_checkpoint_publication(initial);
    allocation_failed=false;fail_after=n;bool failed=false;
    try {
      if(phase) candidate->seal();else candidate=owner->prepare_checkpoint_publication(initial);
    } catch(const std::bad_alloc &) {failed=true;}
    fail_after=-1;unchanged();
    if(!failed) {check(!allocation_failed);break;}
    check(allocation_failed);++failures[phase];
  }
  check(failures[0]>0 && failures[1]>0);
  {
    auto candidate=owner->prepare_checkpoint_publication(initial);candidate->seal();
    allocation_failed=false;fail_after=0;candidate->publish();
    const bool no_allocation=fail_after==0 && !allocation_failed;
    fail_after=-1;check(no_allocation && owner->save_checkpoint()==initial && bus.calls==calls &&
                        read_bytes("prepared.csv")==disk);
  }
  std::cout<<"FASED_PREPARED_ALLOCATIONS prepare_failures="<<failures[0]<<" seal_failures="<<failures[1]
           <<" publication_allocations=0 unchanged=1 mmio=0 files=0\n";
  std::cout<<"PASS: FASED prepared cancellation/ABA/lifetime/thread/aggregate/interruption checks\n";
}

#ifndef FASED_CHECKPOINT_DPI
FASEDMemoryTimingModel *death_owner=nullptr;
mmio_t *death_bus=nullptr;
std::vector<uint8_t> death_expected,death_disk;
uint64_t death_calls=0;
void terminated_publication() noexcept {
  fail_after=-1;
  try {
    if((death_owner && death_owner->save_checkpoint()!=death_expected) ||
       death_bus->calls!=death_calls || read_bytes("death.csv")!=death_disk) std::_Exit(87);
    std::cerr<<"FASED_PUBLISH_REJECTED unchanged=1 mmio=0 files=0\n";
  } catch(...) {std::_Exit(88);}
  std::_Exit(86);
}
void publish_misuse(unsigned which) {
  // A private process makes fail-stop behavior observable without forking VCS.
  mmio_t bus;auto owner=make(bus,"death.csv");const auto payload=owner->save_checkpoint();
  owner->init();bus.stage=1;owner->profile();
  auto candidate=owner->prepare_checkpoint_publication(payload);
  if(which!=0) candidate->seal();
  if(which==1) candidate->publish();
  if(which==2) owner->load_checkpoint(owner->save_checkpoint());
  death_owner=owner.get();death_bus=&bus;death_expected=owner->save_checkpoint();
  death_calls=bus.calls;death_disk=read_bytes("death.csv");
  std::set_terminate(terminated_publication);
  if(which==3) {std::thread other([&]{candidate->publish();});other.join();}
  if(which==4) {owner.reset();death_owner=nullptr;}
  candidate->publish();
  throw std::runtime_error("invalid prepared publication returned");
}
#endif
}
#ifdef FASED_CHECKPOINT_DPI
extern "C" int fased_init(const char *reference,int restore,int cut,int scenario) {
  try {init(reference,restore,cut,scenario);return 0;} catch(const std::exception &e){std::cerr<<e.what()<<'\n';std::_Exit(1);}
}
extern "C" int fased_step() {
  try{return step();}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int fased_negative() {
  try{negatives();prepared_checks();return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
#else
int main(int argc,char **argv) {
  try {check(argc==5);if(std::string(argv[1])=="negative") {negatives();prepared_checks();}
    else if(std::string(argv[1])=="death") publish_misuse(std::stoul(argv[3]));
    else {init(argv[1],std::stoul(argv[2]),std::stoul(argv[3]),std::stoul(argv[4]));while(!step()) {}}
    return 0;
  } catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
#endif
