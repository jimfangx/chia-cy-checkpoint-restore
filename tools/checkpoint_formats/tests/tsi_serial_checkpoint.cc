// Complete two-FIFO component restores; no coroutine or CPU restore claim.
#include "fesvr/tsi_serial_state.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs=std::filesystem;
static void require(bool b,const std::string &s) {if(!b) throw std::runtime_error(s);}
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p,std::ios::binary);require(bool(f),"missing image");
  return {std::istreambuf_iterator<char>(f),{}};
}
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"save failed");
}
static std::vector<std::string> lines(const char *p) {
  std::ifstream f(p);require(bool(f),"missing oracle");std::vector<std::string> r;std::string s;
  while(std::getline(f,s)) r.push_back(s);
  return r;
}
static std::string operation(firesim_tsi_serial_state_t &o,const std::string &s) {
  std::istringstream in(s);std::string op;in>>op;uint64_t address;unsigned bytes;uint32_t word;
  if(op=="READ") {in>>address>>bytes;o.issue_read(address,bytes);}
  else if(op=="WRITE") {
    in>>address;std::vector<uint32_t> data;
    while(in>>word) data.push_back(word);
    o.issue_write(address,data.size()*4,data.data());
  } else if(op=="SEND") {in>>word;o.push_response(word);}
  else if(op=="REQUEST") {
    require(o.request_available(),"missing request");word=o.request_front();require(o.pop_request()==word,"front differs");
    return op+" "+std::to_string(word);
  } else if(op=="RESPONSE") return op+" "+std::to_string(o.pop_response());
  else if(op=="TICK") {bool valid,ready;in>>valid>>word>>ready;o.tick(valid,word,ready);}
  else if(op=="QUERY") return op+" REQUEST="+std::to_string(o.request_available())+" RESPONSE="+std::to_string(o.response_available());
  else throw std::runtime_error("unknown operation");
  return s;
}
static size_t checks() {
  firesim_tsi_serial_state_t o;size_t n=0;
  auto reject=[&](auto f) {bool bad=false;try {f();}catch(const std::exception &) {bad=true;}require(bad,"missing rejection");++n;};
  auto atomic=[&](auto f) {auto before=o.save_checkpoint();reject(f);require(before==o.save_checkpoint(),"partial mutation");};
  uint32_t data=42;
  for(auto bytes:{size_t(0),size_t(1),size_t(3),size_t(1028),size_t(-1)}) {
    atomic([&]{o.issue_read(0,bytes);});atomic([&]{o.issue_write(0,bytes,&data);});
  }
  atomic([&]{o.issue_write(0,4,nullptr);});
  o.issue_read(0xfffffffffffffff8ULL,8);o.push_response(0xffffffff);
  auto image=o.save_checkpoint();
  for(size_t i=0;i<image.size();++i) {
    atomic([&]{o.validate_checkpoint({image.begin(),image.begin()+i});});
    atomic([&]{o.load_checkpoint({image.begin(),image.begin()+i});});
  }
  for(size_t i=0;i<64;++i) {auto bad=image;bad[i]^=1;atomic([&]{o.load_checkpoint(bad);});}
  auto extra=image;extra.push_back(0);atomic([&]{o.load_checkpoint(extra);});
  // Full maximum-size chunks, both 64-bit address halves and simultaneous
  // request/response FIFOs. Audit every restored word, not only the header.
  for(unsigned count:{1u,2u,256u}) {
    firesim_tsi_serial_state_t source,restored;std::vector<uint32_t> data(count);
    for(unsigned i=0;i<count;++i) data[i]=0x81234567u+i*0x10203u;
    source.issue_write(0xfffffffffffffff8ULL,count*4,data.data());
    source.issue_read(0x8000000100000000ULL,count*4);
    for(auto word:data) source.push_response(word);
    auto full=source.save_checkpoint();restored.load_checkpoint(full);
    require(restored.save_checkpoint()==full,"maximum chunk readback differs");++n;
    while(source.request_available()) {require(source.pop_request()==restored.pop_request(),"maximum request differs");++n;}
    while(source.response_available()) {require(source.pop_response()==restored.pop_response(),"maximum response differs");++n;}
    require(source.save_checkpoint()==restored.save_checkpoint(),"maximum empty state differs");++n;
  }
  // A callback-free FIFO API completes before a capture can occur. An escaping
  // failed queue transaction invalidates access rather than inventing a cut.
  for(bool response:{false,true}) {
    firesim_tsi_serial_state_t broken;
    reject([&]{if(response) broken.pop_response();else broken.pop_request();});
    reject([&]{broken.save_checkpoint();});reject([&]{broken.validate_checkpoint(image);});
    reject([&]{broken.load_checkpoint(image);});reject([&]{broken.push_response(1);});
    reject([&]{broken.request_available();});reject([&]{broken.response_available();});
    reject([&]{broken.issue_read(0,4);});reject([&]{broken.tick(false,0,false);});
  }
  return n;
}
static int run(const char *mode,const char *destination,const char *commands,const char *expected,const char *image,const char *cut) {
  try {
    fs::path out(destination);fs::create_directories(out);firesim_tsi_serial_state_t owner;
    require(owner.checkpoint_schema()=="firesim.tsi.serial-queues.v1","wrong schema");
    if(std::string(mode)=="check") {std::cout<<"ATOMIC_CHECKS "<<checks()<<'\n';return 0;}
    if(std::string(mode)=="invalid") {
      owner.issue_read(0x123456789abcdef0ULL,8);owner.push_response(42);
      auto before=owner.save_checkpoint();bool bad=false;
      try {owner.load_checkpoint(read(image));}catch(const std::exception &) {bad=true;}
      require(bad && owner.save_checkpoint()==before,"invalid partial restore");save(out/"unchanged.owner",before);
      std::cout<<"REJECTED_BEFORE_MUTATION zero_edges=1\n";return 0;
    }
    bool reference=std::string(mode)=="reference";
    if(!reference) owner.load_checkpoint(read(image));
    save(out/"preedge.owner",owner.save_checkpoint());
    if(std::string(mode)=="readback") {std::cout<<"COMPLETE_READBACK zero_edges=1 restore_services=0\n";return 0;}
    auto ops=lines(commands),wanted=lines(expected);require(ops.size()==wanted.size(),"wrong oracle size");
    size_t first=reference?0:std::stoull(cut),acknowledged=0;require(first<=ops.size(),"wrong cut");
    save(out/("cut-"+std::to_string(first)+".owner"),owner.save_checkpoint());std::ofstream trace(out/"trace");
    for(size_t i=first;i<ops.size();++i) {
      auto actual="OP "+std::to_string(i+1)+" C "+std::to_string(101+i)+" "+operation(owner,ops[i]);
      if(actual!=wanted[i]) {
        std::ofstream f(out/"first-divergence.json");
        f<<"{\"operation\":"<<i+1<<",\"fixture_cycle\":"<<101+i<<",\"acknowledged\":"<<acknowledged
          <<",\"expected\":\""<<wanted[i]<<"\",\"actual\":\""<<actual<<"\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE "+actual);
      }
      trace<<actual<<'\n';++acknowledged;save(out/("cut-"+std::to_string(i+1)+".owner"),owner.save_checkpoint());
    }
    std::cout<<"COMPLETE_READBACK zero_edges=1 restore_services=0 acknowledged="<<acknowledged<<'\n';return 0;
  }catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_SERIAL_DPI
extern "C" int tsi_serial_checkpoint(const char *m,const char *o,const char *c,const char *e,const char *i,const char *s) {return run(m,o,c,e,i,s);}
extern "C" void tsi_serial_exit(int status) {std::exit(status);}
#else
int main(int argc,char **argv) {if(argc!=7) return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6]);}
#endif
