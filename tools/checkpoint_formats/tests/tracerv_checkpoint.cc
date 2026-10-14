// Actual TracerV/StreamEngine host calls, with separately owned fixture queues.
// These cuts are not CPU checkpoints or generated transport validation.
#include "bridges/tracerv.h"
#include "core/config.h"
#include "core/bridge_driver.h"
#include "tracerv-recipe.h"
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>
#include <sstream>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "tracerv-component"};
const std::vector<uint8_t> sentinel{83,65,70,69};
constexpr unsigned operations = 8;
unsigned rejected = 0, index = 0, selected_cut = 0, scenario = 0, hart = 0;
bool restoring = false;
std::filesystem::path directory;
std::ofstream trace;
std::vector<std::string> expected;
size_t compared = 0;
void check(bool b, const std::string &s="TracerV assertion") { if (!b) throw std::runtime_error(s); }
void write(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary);check(bool(f),"missing file "+p.string());
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
std::string hex(const std::vector<uint8_t> &b) {
  const char *digits="0123456789abcdef";std::string s;
  for(auto v:b){s+=digits[v>>4];s+=digits[v&15];}return s;
}
void line(const std::string &s,const std::string &signal) {
  trace<<s<<std::endl;
  if(!expected.empty()) {
    if(compared>=expected.size() || s!=expected[compared])
      throw std::runtime_error("FIRST_MISMATCH fixture_cycle="+std::to_string(100+7*index)+" signal="+signal);
    ++compared;
  }
}
void rejects(const std::function<void()> &fn) {
  try{fn();}catch(const std::runtime_error &){++rejected;return;}
  throw std::runtime_error("expected TracerV rejection");
}
struct io_t : simif_t {
  io_t():simif_t(cfg){}
  unsigned calls=0;std::function<void()> hook;
  void called(){++calls;if(hook)hook();}
  void write(size_t a,uint32_t d) override {
    called();line("W "+std::to_string(a)+" "+std::to_string(d),"tracerv_mmio");
  }
  uint32_t read(size_t) override { std::abort(); }
};
struct queue_t : FPGAToCPUStreamDriver {
  std::deque<uint8_t> bytes;
  unsigned calls=0;std::function<void()> hook;
  void init() override {}
  size_t pull(void *dest,size_t n,size_t minimum) override {
    ++calls;if(hook)hook();
    auto count=std::min(n,bytes.size());if(count<minimum)count=0;
    std::vector<uint8_t> data;
    for(size_t i=0;i<count;++i){data.push_back(bytes.front());bytes.pop_front();}
    if(count)std::memcpy(dest,data.data(),count);
    line("P "+std::to_string(n)+" "+std::to_string(minimum)+" "+std::to_string(count)+" "+hex(data),"tracerv_pull");
    return count;
  }
  void flush() override {++calls;if(hook)hook();line("F","tracerv_flush");}
};
struct engine_t : StreamEngine {
  queue_t *queue;
  explicit engine_t(unsigned stream){
    for(unsigned i=0;i<=stream;++i)fpga_to_cpu_streams.push_back(std::make_unique<queue_t>());
    queue=static_cast<queue_t *>(fpga_to_cpu_streams[stream].get());
  }
};
std::unique_ptr<io_t> io;
std::unique_ptr<engine_t> engine;
std::unique_ptr<tracerv_t> driver;
std::vector<std::string> arguments(const std::filesystem::path &p,unsigned mode) {
  std::vector<std::string> a={"+tracerv-checkpoint-buffered","+trace-select="+std::to_string(mode),
    "+trace-start=12345678", "+trace-end=abcdef01", "+trace-output-format="+std::to_string(mode==1?1:0)};
  if(mode!=3)a.push_back("+tracefile="+(p/"TRACEFILE").string());
  if(mode==2)a.push_back("+trace-test-output");
  return a;
}
std::filesystem::path output(){return directory/("TRACEFILE-C"+std::to_string(hart));}
void snapshot(const std::string &name) {
  const auto calls=io->calls+engine->queue->calls;
  auto payload=driver->save_checkpoint();driver->validate_checkpoint(payload);
  write(directory/(name+".owner"),payload);
  write(directory/(name+".queue"),{engine->queue->bytes.begin(),engine->queue->bytes.end()});
  check(calls==io->calls+engine->queue->calls && read(output())==sentinel,"capture side effect");
}
void add(unsigned count) {
  for(unsigned t=0;t<count;++t) {
    const uint64_t data[]={uint64_t(100+7*index),tracerv_t::valid_mask|uint64_t(0x80000000+4096*hart+4*t),0,0,0,0,0,0};
    const auto *b=reinterpret_cast<const uint8_t *>(data);
    engine->queue->bytes.insert(engine->queue->bytes.end(),b,b+64);
  }
}
void init(const std::filesystem::path &p,bool restore,unsigned cut,unsigned mode,unsigned h,bool compare=true) {
  driver.reset();engine.reset();io=std::make_unique<io_t>();engine=std::make_unique<engine_t>(h);
  directory=p;restoring=restore;selected_cut=cut;index=cut;scenario=mode;hart=h;compared=0;expected.clear();
  check(h<4 && mode<4 && cut<operations);
  write(output(),sentinel);
  driver=std::make_unique<tracerv_t>(*io,*engine,recipe_mmio[h],h,arguments(p,mode),h,recipe_depth,recipe_ipc,recipe_clock);
  check(driver->checkpoint_schema()=="firesim.bridge.tracerv.v1");
  if(restore){
    auto payload=read(p/("cut-"+std::to_string(cut)+".owner"));
    driver->validate_checkpoint(payload);driver->load_checkpoint(payload);
    auto queue=read(p/("cut-"+std::to_string(cut)+".queue"));
    engine->queue->bytes={queue.begin(),queue.end()};
    check(io->calls+engine->queue->calls==0 && read(output())==sentinel,"restore side effect");
    snapshot("restore-"+std::to_string(cut)+".initial");
    if(compare){
      std::ifstream f(p/"reference.trace");std::string s;bool selected=false;
      while(std::getline(f,s)){if(s=="OP "+std::to_string(cut)+" C "+std::to_string(100+7*cut))selected=true;
        if(selected)expected.push_back(s);}
      check(!expected.empty());
    }
  }
  trace.close();trace.open(p/(restore?"restore-"+std::to_string(cut)+".trace":"reference.trace"));
}
int step() {
  if(!restoring)snapshot("cut-"+std::to_string(index));
  line("OP "+std::to_string(index)+" C "+std::to_string(100+7*index),"operation");
  if(index==0)driver->init();
  else if(index==7){
    // Preserve the last complete owner before publication; no finished cut supported.
    snapshot(restoring?"restore-"+std::to_string(selected_cut)+".final":"final");
    driver->finish();line("OUTPUT "+hex(read(output())),"tracerv_output");
    check(expected.empty() || compared==expected.size(),"short TracerV continuation");
    std::cout<<"PASS: TracerV component continuation\n";return 1;
  } else if(index==4)driver->flush();
  else {
    if(index==1)add(recipe_depth-1);
    if(index==2 || index==5)add(1);
    if(index==3)add(2);
    driver->tick();
  }
  ++index;return 0;
}
void negative(const std::filesystem::path &p) {
  const auto n=p/"negative-validation";std::filesystem::create_directories(n);
  write(n/"cut-3.owner",read(p/"cut-3.owner"));write(n/"cut-3.queue",read(p/"cut-3.queue"));
  init(n,true,3,0,0,false);const auto good=driver->save_checkpoint();const auto calls=io->calls+engine->queue->calls;
  const size_t config=32+32*8+8+std::strlen(recipe_clock.domain_name);
  auto bad_case=[&](const std::vector<uint8_t> &b){
    rejects([&]{driver->validate_checkpoint(b);});rejects([&]{driver->load_checkpoint(b);});
    check(driver->save_checkpoint()==good && io->calls+engine->queue->calls==calls && read(output())==sentinel,"partial TracerV restore");
  };
  for(size_t i=0;i<config+24;++i)bad_case({good.begin(),good.begin()+i});
  bad_case({good.begin(),good.end()-1});
  for(size_t i=0;i<config;++i){auto b=good;b[i]^=1;bad_case(b);}
  auto alter=[&](size_t offset,uint64_t v){auto b=good;for(unsigned i=0;i<8;++i)b[offset+i]=v>>(8*i);bad_case(b);};
  alter(config,2);alter(config,0);alter(config+16,UINT64_MAX);alter(config+16,0);
  auto b=good;b.push_back(0);bad_case(b);b=good;b[config+24]^=1;bad_case(b);
  for(unsigned h=1;h<4;++h){tracerv_t other(*io,*engine,recipe_mmio[h],h,arguments(n,0),h,recipe_depth,recipe_ipc,recipe_clock);
    rejects([&]{other.load_checkpoint(good);});}
  auto different_clock=ClockInfo{"other-clock",1,1};
  tracerv_t other(*io,*engine,recipe_mmio[0],0,arguments(n,0),0,recipe_depth,recipe_ipc,different_clock);
  rejects([&]{other.load_checkpoint(good);});
  for(unsigned mode=1;mode<4;++mode){tracerv_t other_mode(*io,*engine,recipe_mmio[0],0,arguments(n,mode),0,recipe_depth,recipe_ipc,recipe_clock);
    rejects([&]{other_mode.load_checkpoint(good);});}
  auto args=arguments(n,0);args.erase(args.begin());
  tracerv_t live(*io,*engine,recipe_mmio[0],0,args,0,recipe_depth,recipe_ipc,recipe_clock);
  rejects([&]{live.save_checkpoint();});rejects([&]{live.load_checkpoint(good);});
  args=arguments(n,0);args.push_back("+trace-output-format=2");
  rejects([&]{tracerv_t perf(*io,*engine,recipe_mmio[0],0,args,0,recipe_depth,recipe_ipc,recipe_clock);});
  auto callback=[&]{rejects([&]{driver->save_checkpoint();});rejects([&]{driver->validate_checkpoint(good);});
    rejects([&]{driver->load_checkpoint(good);});rejects([&]{driver->init();});rejects([&]{driver->tick();});
    rejects([&]{driver->flush();});rejects([&]{driver->finish();});};
  engine->queue->hook=callback;driver->tick();driver->flush();engine->queue->hook=nullptr;
  driver->validate_checkpoint(driver->save_checkpoint());
  rejects([&]{driver->init();}); // Failed lifecycle call poisons this owner.
  rejects([&]{driver->save_checkpoint();});
  init(n,true,3,0,0,false);engine->queue->hook=[] {throw std::runtime_error("injected suspended pull failure");};
  rejects([&]{driver->tick();});engine->queue->hook=nullptr;
  rejects([&]{driver->save_checkpoint();});rejects([&]{driver->load_checkpoint(good);});
  rejects([&]{driver->finish();});
  init(n,true,3,0,0,false);driver->finish();
  rejects([&]{driver->save_checkpoint();});rejects([&]{driver->load_checkpoint(good);});
  rejects([&]{driver->tick();});rejects([&]{driver->flush();});rejects([&]{driver->finish();});
  // Guard every MMIO inside init, too.
  init(n,false,0,0,0,false);io->hook=callback;driver->init();io->hook=nullptr;
  driver->validate_checkpoint(driver->save_checkpoint());
  std::cout<<"PASS: TracerV atomic payload/configuration/lifecycle checks "<<rejected<<'\n';
}
}
extern "C" int tracerv_init(const char *p,int restore,int cut,int mode,int h){
  try{init(p,restore,cut,mode,h);return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}}
extern "C" int tracerv_step(){try{return step();}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}}
extern "C" int tracerv_negative(const char *p){try{negative(p);return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}}
extern "C" void tracerv_failure(){std::exit(1);}
#ifndef TRACERV_CHECKPOINT_DPI
int main(int argc,char **argv){
  if(argc!=6)return 2;
  const std::string mode=argv[1];
  if(mode=="negative")return tracerv_negative(argv[2])?1:0;
  if(tracerv_init(argv[2],mode=="restore",std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5])))return 1;
  int result;do{result=tracerv_step();}while(!result);return result<0?1:0;
}
#endif
