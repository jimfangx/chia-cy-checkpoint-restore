// Explicit identity caller/write/FIFO continuations, not an HTIF or CPU restore.
#include "fesvr/tsi_bcd_identity.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
#include <functional>
namespace fs = std::filesystem;
using caller_t = firesim_tsi_bcd_identity_t;
using images_t = caller_t::images_t;
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static auto bytes(const fs::path &path) {
  std::ifstream f(path,std::ios::binary);require(bool(f),"missing owner image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
}
static void save(const fs::path &path,const std::vector<uint8_t> &b) {
  std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());
  require(bool(f),"save failed");
}
static auto load(const fs::path &path) {
  images_t result;
  for(auto name:{"identity","write","serial"})result.emplace_back(name,bytes(path.string()+"."+name));
  return result;
}
struct owners_t {
  firesim_tsi_memif_write_t writer;
  firesim_tsi_serial_state_t serial;
  caller_t caller{writer,serial};
  images_t snapshot() const {
    return {{"identity",caller.save_checkpoint()},{"write",writer.save_checkpoint()},
            {"serial",serial.save_checkpoint()}};
  }
};
struct services_t final : caller_t::services_t {
  firesim_tsi_serial_state_t &serial;
  std::string response;
  size_t calls=0;
  explicit services_t(firesim_tsi_serial_state_t &serial):serial(serial){}
  void issue(uint64_t a,uint64_t n) override {++calls;serial.issue_read(a,n);}
  bool receive(uint32_t &w) override {
    ++calls;if(!serial.response_available())return false;w=serial.pop_response();return true;
  }
  void write(uint64_t a,size_t n,const uint32_t *w) override {++calls;serial.issue_write(a,n,w);}
  void respond(uint64_t value) override {
    ++calls;require(response.empty(),"duplicate response within one service");response=std::to_string(value);
  }
};
extern void tsi_terminal_fail_allocation_after(long);
static void checks() {
  owners_t source,dest;
  services_t io(source.serial),other(dest.serial);
  source.caller.begin(0x01ff128000300100ULL);source.caller.advance(io);
  source.serial.push_response(0x12345678);source.caller.advance(io);
  const auto good=source.snapshot();
  dest.caller.begin(0x01ff128000400701ULL);dest.caller.advance(other);
  const auto before=dest.snapshot();
  size_t malformed=0,membership=0,cross=0;
  auto reject=[&](const images_t &image) {
    bool rejected=false;try{dest.caller.load_components(image);}catch(const std::runtime_error &){rejected=true;}
    require(rejected && dest.snapshot()==before,"invalid image partially published");
  };
  for(size_t owner=0;owner<3;++owner) {
    for(size_t length=0;length<good[owner].second.size();++length) {
      auto bad=good;bad[owner].second.resize(length);reject(bad);++malformed;
    }
    auto bad=good;bad[owner].second.push_back(0);reject(bad);++malformed;
    bad=good;bad[owner].second[16]^=1;reject(bad);++malformed;
    bad=good;bad.erase(bad.begin()+owner);reject(bad);++membership;
    bad=good;bad.push_back(good[owner]);reject(bad);++membership;
    bad=good;bad[owner].first="unknown";reject(bad);++membership;
    bad=good;std::swap(bad[owner],bad[(owner+1)%3]);reject(bad);++membership;
  }
  auto put=[](std::vector<uint8_t> &b,size_t at,uint64_t value) {
    for(unsigned i=0;i<8;++i)b.at(at+i)=value>>(8*i);
  };
  for(unsigned which=0;which<7;++which) {
    auto bad=good;
    if(which==0)put(bad[0].second,72,0); // idle caller with active child
    if(which==1)put(bad[0].second,72,2); // response before write completes
    if(which==2)bad[0].second[81]^=8; // wrong destination, individually valid command
    if(which==3)bad[0].second[80]=1; // wrong identity payload
    if(which==4)bad[1].second[96]^=1; // copied payload disagrees with command
    if(which==5)bad[1].second=firesim_tsi_memif_write_t{}.save_checkpoint();
    if(which==6)put(bad[0].second,72,4);
    reject(bad);++cross;
  }
  long failures=0;
  for(;;++failures) {
    bool exhausted=false;tsi_terminal_fail_allocation_after(failures);
    try{dest.caller.load_components(good);}catch(const std::bad_alloc &){exhausted=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);
    if(!exhausted)break;
    require(dest.snapshot()==before,"allocation failure partially published identity components");
  }
  require(failures>=10 && dest.snapshot()==good,"allocation injection missed preparation");
  // Any escaping service poisons the caller. Reentrant publication is rejected
  // before its child, transport or response destination can be mutated.
  size_t hostile=0;
  auto rejected=[&](auto action) {
    bool failed=false;try{action();}catch(const std::runtime_error &){failed=true;}
    require(failed,"hostile service admitted");++hostile;
  };
  struct hostile_t final : caller_t::services_t {
    owners_t &o;const images_t &good;std::function<void(std::function<void()>)> reject;
    hostile_t(owners_t &o,const images_t &good,decltype(reject) reject):o(o),good(good),reject(reject){}
    void attack() {
      reject([&]{o.caller.save_checkpoint();});reject([&]{o.caller.load_components(good);});
      reject([&]{o.caller.load_checkpoint(good[0].second);});reject([&]{o.caller.begin(0x01ff000000000000ULL);});
      reject([&]{o.caller.finish();});throw std::runtime_error("escaping identity service");
    }
    void issue(uint64_t,uint64_t) override {attack();}
    bool receive(uint32_t &) override {attack();return false;}
    void write(uint64_t,size_t,const uint32_t *) override {attack();}
    void respond(uint64_t) override {attack();}
  };
  for(unsigned phase=0;phase<4;++phase) {
    owners_t broken;services_t service(broken.serial);
    broken.caller.begin(phase<2?0x01ff128000300100ULL:0x01ff128000300000ULL);
    if(phase==1)broken.caller.advance(service); // receive callback, request already issued
    if(phase>=2)broken.caller.advance(service); // aligned body selection
    if(phase==3)broken.caller.advance(service); // response callback
    hostile_t h(broken,good,rejected);rejected([&]{broken.caller.advance(h);});
    rejected([&]{broken.caller.save_checkpoint();});rejected([&]{broken.caller.load_components(good);});
    rejected([&]{broken.caller.advance(service);});
  }
  std::cout<<"ATOMIC malformed="<<malformed<<" membership="<<membership<<" cross="<<cross
           <<" allocation_failures="<<failures<<" hostile="<<hostile<<" unchanged_on_failure=1\n";
}
static int run(const char *mode,const char *directory,const char *plan,const char *expected,
               const char *source,const char *cut) {
  try {
    fs::path out(directory);fs::create_directories(out);
    if(std::string(mode)=="check"){checks();return 0;}
    owners_t owners;services_t service(owners.serial);
    if(std::string(mode)=="invalid") {
      owners.caller.begin(0x01ff128000400701ULL);owners.caller.advance(service);
      const auto before=owners.snapshot();bool rejected=false;
      try{owners.caller.load_components(load(source));}catch(const std::runtime_error &){rejected=true;}
      require(rejected && owners.snapshot()==before,"invalid process partially restored");
      for(const auto &[name,b]:before)save(out/("unchanged."+name),b);
      std::cout<<"REJECTED_BEFORE_MUTATION owners=3 target_edges=0\n";return 0;
    }
    const bool capture=std::string(mode)=="capture";
    if(!capture)owners.caller.load_components(load(source));
    require(service.calls==0,"restore invoked services");
    for(const auto &[name,b]:owners.snapshot())save(out/("preedge."+name),b);
    const size_t first=capture?0:std::stoull(cut);
    std::ifstream steps(plan),oracle(expected);require(bool(steps)&&bool(oracle),"missing oracle");
    std::ofstream readbacks(out/"continuation.bin",std::ios::binary),trace(out/"trace");
    auto snapshot=[&](size_t index) {
      for(const auto &[name,b]:owners.snapshot()) {
        if(capture)save(out/("cut-"+std::to_string(index)+"."+name),b);
        else readbacks.write(reinterpret_cast<const char *>(b.data()),b.size());
      }
    };
    snapshot(first);std::string line,wanted;size_t index=0;
    while(std::getline(steps,line)) {
      require(bool(std::getline(oracle,wanted)),"short oracle");if(index++<first)continue;
      std::istringstream in(line);std::string op,actual=line;uint64_t value;in>>op;
      if(op=="BEGIN"){in>>value;owners.caller.begin(value);}
      else if(op=="ADVANCE") {
        service.response.clear();const auto result=owners.caller.advance(service);
        actual="ADVANCE "+std::string(result==caller_t::result_t::blocked?"BLOCKED":
                  result==caller_t::result_t::complete?"COMPLETE":"PROGRESS");
        if(!service.response.empty())actual+=" RESPOND "+service.response;
      } else if(op=="SEND"){in>>value;owners.serial.push_response(value);}
      else if(op=="FINISH")owners.caller.finish();
      else if(op=="PACKET") {
        size_t word=0;
        while(in>>value) {
          require(owners.serial.request_available(),"missing request");
          const auto actual_word=owners.serial.request_front();
          if(actual_word!=value) {
            std::ofstream f(out/"first-divergence.txt");
            f<<"operation="<<index<<" word="<<word<<" expected="<<value<<" actual="<<actual_word<<" acknowledged=0\n";
            require(owners.serial.request_front()==actual_word,"divergent word consumed");
            throw std::runtime_error("FIRST_DIVERGENCE unconsumed request");
          }
          owners.serial.pop_request();++word;
        }
      } else throw std::runtime_error("unknown identity operation");
      require(actual==wanted,"wrong identity service/response boundary");trace<<index<<' '<<actual<<'\n';snapshot(index);
    }
    std::cout<<"IDENTITY_CONTINUATION operations="<<index-first<<" complete_readbacks="<<3*(index-first+1)
             <<" restore_services=0 target_edges=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_BCD_IDENTITY_DPI
extern "C" int tsi_bcd_identity_checkpoint(const char *m,const char *o,const char *p,const char *e,const char *s,const char *c){return run(m,o,p,e,s,c);}
extern "C" void tsi_bcd_identity_exit(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=7)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6]);}
#endif
