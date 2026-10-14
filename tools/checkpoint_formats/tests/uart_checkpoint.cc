// Actual UART host driver, deterministic MMIO component fixture. These labels
// are not Rocket target cycles and this test grants no complete CPU support.
#include "bridges/uart.h"
#include "core/config.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <queue>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a,d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }

namespace {
constexpr unsigned operations = 8, config_bytes = 88, handler_offset = 144;
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "uart-component"};
const UARTBRIDGEMODULE_struct addresses{1056,1060,1064,1068,1072,1076};
const std::vector<uint8_t> input{0,128,255,65};
void check(bool b, const std::string &s = "UART assertion") {
  if (!b) throw std::runtime_error(s);
}
std::vector<uint8_t> read_file(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f),"missing file "+p.string());
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
void write_file(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()),b.size());check(bool(f));
}
std::vector<std::string> arguments(const std::filesystem::path &p) {
  return {"+uart-checkpoint-file0", "+uart-in0="+(p/"input.bin").string(),
          "+uart-out0="+(p/"output.bin").string()};
}
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  unsigned op=0,budget=0; uint64_t calls=0;
  std::queue<uint8_t> output;
  std::function<void()> hook;
  std::ofstream trace;
  std::vector<std::string> expected;
  size_t comparison=0;
  void line(const std::string &s,const std::string &signal="fixture") {
    trace << s << std::endl;
    if (!expected.empty()) {
      if (comparison>=expected.size() || expected[comparison]!=s)
        throw std::runtime_error("FIRST_MISMATCH fixture_cycle="+std::to_string(100+7*op)+
          " signal="+signal+" op="+std::to_string(op)+" observed="+s);
      ++comparison;
    }
  }
  void write(size_t a,uint32_t d) override {
    ++calls;if(hook)hook();
    line("W "+std::to_string(a)+" "+std::to_string(d),a==1068?"uart_in_bits":"uart_mmio");
    if(a==1072){check(d==1 && budget);--budget;}
    else if(a==1064){check(d==1 && !output.empty());output.pop();}
    else check(a==1068);
  }
  uint32_t read(size_t a) override {
    ++calls;if(hook)hook();
    uint32_t v=0;
    if(a==1076)v=bool(budget);
    else if(a==1060)v=!output.empty();
    else if(a==1056){check(!output.empty());v=output.front();}
    else throw std::runtime_error("unexpected UART address");
    line("R "+std::to_string(a)+" "+std::to_string(v));return v;
  }
};
std::unique_ptr<mmio_t> mmio;
std::unique_ptr<uart_t> driver;
std::filesystem::path directory;
unsigned index=0,rejected=0,selected_cut=0;bool restoring=false;
void rejects(const std::function<void()> &fn) {
  try {fn();}catch(const std::runtime_error &){++rejected;return;}
  throw std::runtime_error("expected UART rejection");
}
void init(const std::filesystem::path &p,bool restore,unsigned cut,bool compare) {
  driver.reset();mmio=std::make_unique<mmio_t>();directory=p;index=cut;restoring=restore;
  check(cut<=operations);write_file(p/"input.bin",input);
  // Construction and restore must leave this unrelated existing destination
  // untouched. Only successful finish publishes owned output bytes.
  const std::vector<uint8_t> sentinel{83,65,70,69};write_file(p/"output.bin",sentinel);
  driver=std::make_unique<uart_t>(*mmio,addresses,0,arguments(p));
  mmio->trace.open(p/(restore?"restore-"+std::to_string(cut)+".trace":"reference.trace"));
  if(restore) {
    auto b=read_file(p/("cut-"+std::to_string(cut)+".owner"));
    driver->validate_checkpoint(b);driver->load_checkpoint(b);
    write_file(p/("restore-"+std::to_string(cut)+".initial.owner"),driver->save_checkpoint());
    check(mmio->calls==0 && read_file(p/"output.bin")==sentinel,"restore side effect before first edge");
    if(compare && cut<operations) {
      std::ifstream f(p/"reference.trace");std::string s;bool selected=false;
      while(std::getline(f,s)) {
        if(s=="OP "+std::to_string(cut)+" C "+std::to_string(100+7*cut))selected=true;
        if(selected)mmio->expected.push_back(s);
      }
      check(!mmio->expected.empty());
    }
  }
}
int step() {
  if(index==operations) {
    const auto b=driver->save_checkpoint();
    write_file(directory/(restoring?"restore-"+std::to_string(selected_cut)+".final.owner":"cut-8.owner"),b);
    if(restoring) {
      check(mmio->comparison==mmio->expected.size(),"short UART continuation");
    }
    driver->finish();
    std::cout << "PASS: UART component continuation\n";return 1;
  }
  if(!restoring)write_file(directory/("cut-"+std::to_string(index)+".owner"),driver->save_checkpoint());
  mmio->op=index;mmio->budget=0;
  mmio->line("OP "+std::to_string(index)+" C "+std::to_string(100+7*index));
  auto out=[&](std::initializer_list<uint8_t> bytes){for(auto b:bytes)mmio->output.push(b);};
  switch(index) {
  case 1:mmio->budget=1;out({0});break;
  case 2:out({128,255});break;
  case 3:mmio->budget=2;out({65});break;
  case 4:mmio->budget=10;out({0,129});break;
  case 5:mmio->budget=1;break;
  case 6:out({165,66});break;
  }
  driver->tick();check(mmio->output.empty());++index;return 0;
}
void negative(const std::filesystem::path &p) {
  const auto n=p/"negative-validation";std::filesystem::create_directories(n);
  write_file(n/"cut-4.owner",read_file(p/"cut-4.owner"));
  init(n,true,4,false);
  const auto good=driver->save_checkpoint();const auto calls=mmio->calls;
  auto bad_case=[&](std::vector<uint8_t> b) {
    rejects([&]{driver->validate_checkpoint(b);});rejects([&]{driver->load_checkpoint(b);});
    check(driver->save_checkpoint()==good && mmio->calls==calls &&
      read_file(n/"output.bin")==std::vector<uint8_t>({83,65,70,69}),"partial UART restore");
  };
  for(size_t i=0;i<good.size();++i)bad_case({good.begin(),good.begin()+i});
  for(size_t i=0;i<config_bytes;++i){auto b=good;b[i]^=1;bad_case(b);}
  for(size_t i=handler_offset;i<handler_offset+44;++i){auto b=good;b[i]^=1;bad_case(b);}
  auto alter=[&](size_t offset,uint64_t value) {
    auto b=good;for(unsigned i=0;i<8;++i)b[offset+i]=value>>(8*i);bad_case(b);
  };
  for(auto offset:{88,112})alter(offset,256);
  for(auto offset:{96,104,120,128})alter(offset,2);
  alter(96,1);alter(120,1); // suspended valid input/output
  alter(136,0);alter(136,UINT64_MAX);
  alter(handler_offset+44,5);alter(handler_offset+52,UINT64_MAX);
  auto trailing=good;trailing.push_back(0);bad_case(trailing);
  auto changed_map=addresses;++changed_map.in_ready;
  uart_t other(*mmio,changed_map,0,arguments(n));rejects([&]{other.load_checkpoint(good);});
  auto args=arguments(n);args.erase(args.begin());
  uart_t external(*mmio,addresses,0,args);
  rejects([&]{external.save_checkpoint();});rejects([&]{external.load_checkpoint(good);});
  write_file(n/"input.bin",{0,128,254,65});
  uart_t changed(*mmio,addresses,0,arguments(n));rejects([&]{changed.load_checkpoint(good);});
  rejects([&]{uart_t invalid(*mmio,addresses,0,{"+uart-checkpoint-file0"});});
  rejects([&]{uart_t device(*mmio,addresses,0,{"+uart-checkpoint-file0","+uart-in0=/dev/null","+uart-out0=unused"});});
  mmio->hook=[&]{
    rejects([&]{driver->save_checkpoint();});rejects([&]{driver->validate_checkpoint(good);});
    rejects([&]{driver->load_checkpoint(good);});
  };
  driver->tick();mmio->hook=nullptr;
  const auto completed=driver->save_checkpoint();
  driver->finish();driver->finish();rejects([&]{driver->save_checkpoint();});
  rejects([&]{driver->load_checkpoint(completed);});
  init(n,true,4,false);
  mmio->hook=[] {throw std::runtime_error("interrupted UART MMIO");};
  rejects([&]{driver->tick();});mmio->hook=nullptr;
  rejects([&]{driver->save_checkpoint();});rejects([&]{driver->load_checkpoint(good);});
  std::cout << "PASS: UART atomic payload/configuration/suspension checks " << rejected << '\n';
}
}

extern "C" int uart_init(const char *p,int restore,int cut) {
  try{selected_cut=cut;init(p,restore,cut,true);return 0;}
  catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int uart_step() {
  try{return step();}
  catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int uart_negative(const char *p) {
  try{negative(p);return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" void uart_failure(){std::exit(1);}
#ifndef UART_CHECKPOINT_DPI
int main(int argc,char **argv) {
  if(argc!=4)return 2;
  const std::string mode=argv[1];
  if(mode=="negative")return uart_negative(argv[2])?1:0;
  if(uart_init(argv[2],mode=="restore",std::stoi(argv[3])))return 1;
  int result;do{result=uart_step();}while(!result);return result<0?1:0;
}
#endif
