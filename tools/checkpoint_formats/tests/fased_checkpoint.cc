// Actual FASED host adapter with deterministic MMIO, not a full runtime restore.
#include "bridges/fased_memory_timing_model.h"
#include "core/config.h"
#include <filesystem>
#include <functional>
#include <iostream>
#include <memory>

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
void init(const std::string &reference,bool restore,unsigned cut,unsigned scenario) {
  check(cut<=4); index=restore ? cut : 0; restoring=restore;
  mmio=std::make_unique<mmio_t>(); mmio->scenario=scenario; model=make(*mmio);
  if (restore) {
    const auto payload=read_bytes(std::filesystem::path(reference)/("cut-"+std::to_string(cut)+".owner"));
    const auto before=read_bytes("stats.csv");
    model->validate_checkpoint(payload); model->load_checkpoint(payload);
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
  }
  for(unsigned operation=0;operation<3;++operation) for(bool interrupt:{false,true}) {
    mmio_t bus;auto owner=make(bus,"guard.csv");
    if(operation) owner->init();
    const auto payload=owner->save_checkpoint();unsigned checked=0;
    bus.hook=[&]{
      if(checked++) return;
      rejects([&]{owner->save_checkpoint();});rejects([&]{owner->validate_checkpoint(payload);});
      rejects([&]{owner->load_checkpoint(payload);});rejects([&]{owner->profile();});
      if(interrupt) throw std::runtime_error("injected FASED MMIO interruption");
    };
    auto call=[&]{if(!operation) owner->init();else if(operation==1) owner->profile();else owner->finish();};
    if(interrupt) rejects(call);else call();
    check(checked>0);bus.hook={};
    if(interrupt || operation==2) {
      rejects([&]{owner->save_checkpoint();});rejects([&]{owner->validate_checkpoint(payload);});
      rejects([&]{owner->load_checkpoint(payload);});
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
    std::filesystem::remove("blocked.csv");
  }
  std::cout<<"PASS: FASED malformed/configuration/suspension/interruption rejections "<<rejected<<'\n';
}
}
#ifdef FASED_CHECKPOINT_DPI
extern "C" int fased_init(const char *reference,int restore,int cut,int scenario) {
  try {init(reference,restore,cut,scenario);return 0;} catch(const std::exception &e){std::cerr<<e.what()<<'\n';std::_Exit(1);}
}
extern "C" int fased_step() {
  try{return step();}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int fased_negative() {
  try{negatives();return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
#else
int main(int argc,char **argv) {
  try {check(argc==5);if(std::string(argv[1])=="negative") negatives();
    else {init(argv[1],std::stoul(argv[2]),std::stoul(argv[3]),std::stoul(argv[4]));while(!step()) {}}
    return 0;
  } catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
#endif
