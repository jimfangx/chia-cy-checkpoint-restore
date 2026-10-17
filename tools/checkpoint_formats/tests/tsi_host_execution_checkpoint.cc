// Explicit outer caller tests; operation labels are not CPU target cycles.
#include "fesvr/tsi_host_execution.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>
using owner_t = firesim_tsi_host_execution_t;
static void require(bool ok) { if (!ok) throw std::runtime_error("outer caller assertion failed"); }
static void rejects(const std::function<void()> &f) {
  bool failed=false; try { f(); } catch(const std::runtime_error &) { failed=true; } require(failed);
}
static auto bytes(const std::string &p) {
  std::ifstream f(p,std::ios::binary); require(bool(f));
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
}
static void save(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()),b.size()); require(bool(f));
}
struct divergence_t : std::runtime_error { using std::runtime_error::runtime_error; };
struct services_t : owner_t::services_t {
  owner_t &owner; std::string expected,actual; int code=0; bool fail=false;
  services_t(owner_t &owner,const std::string &line) : owner(owner) {
    std::istringstream in(line); in>>expected>>code;
  }
  void service(const std::string &name) {
    actual=name;
    // A nested call/snapshot/load may neither inspect nor replace stack state.
    rejects([&]{owner.save_checkpoint();});
    rejects([&]{owner.phase();});
    rejects([&]{owner.validate_checkpoint({});});
    rejects([&]{owner.load_checkpoint({});});
    rejects([&]{owner.advance(*this);});
    if(fail)throw std::runtime_error("injected service failure");
    if(expected!=name)throw divergence_t("signal=service expected="+expected+" actual="+name);
  }
  void start() override { service("START"); }
  owner_t::result_t poll() override {
    service("POLL");
    return code==0?owner_t::result_t::progress:code==1?owner_t::result_t::blocked:owner_t::result_t::complete;
  }
  void stop() override { service("STOP"); }
  int exit_code() override { service("EXIT");return code; }
  void finish() {
    if(actual.empty() && expected!="NONE")throw divergence_t("signal=service expected="+expected+" actual=none");
  }
};
static int run(const char *source,const char *plan,const char *destination) {
  try {
    const std::filesystem::path out(destination);std::filesystem::create_directories(out);
    owner_t owner;
    if(std::string(source)!="new")owner.load_checkpoint(bytes(source));
    save(out/"preedge.owner",owner.save_checkpoint());
    std::cout<<"COMPLETE_OUTER_READBACK target_edges=0 context_entries=0 services=0\n";
    const auto before=owner.save_checkpoint();size_t invalids=0;
    auto invalid=[&](const std::vector<uint8_t> &bad){
      rejects([&]{owner.validate_checkpoint(bad);});rejects([&]{owner.load_checkpoint(bad);});
      require(owner.save_checkpoint()==before);++invalids;
    };
    for(size_t n=0;n<before.size();++n)invalid({before.begin(),before.begin()+n});
    for(size_t n=0;n<48;++n)for(unsigned bit=0;bit<8;++bit){auto b=before;b[n]^=1<<bit;invalid(b);}
    auto b=before;b.push_back(0);invalid(b);
    b=before;b[48]=5;invalid(b);
    b=before;b[60]=1;invalid(b); // result must fit the installed int ABI
    if(owner.phase()!=owner_t::phase_t::returned){b=before;b[56]=1;invalid(b);rejects([&]{owner.exit_code();});}
    std::ifstream f(plan);require(bool(f));std::string line;size_t op=0;
    while(std::getline(f,line)) {
      services_t service(owner,line);
      try { owner.advance(service);service.finish(); }
      catch(const divergence_t &e){
        std::cout<<"FIRST_DIVERGENCE operation="<<op<<' '<<e.what()<<" acknowledged=0\n";return 3;
      }
      save(out/("after-"+std::to_string(op)+".owner"),owner.save_checkpoint());++op;
    }
    require(owner.phase()==owner_t::phase_t::returned);
    // Every service site must poison after an exception and reject recovery.
    for(unsigned target=0;target<4;++target) {
      owner_t failed;
      std::vector<std::string> steps{"START","POLL 2","STOP","EXIT -1"};
      for(unsigned i=0;i<target;++i){services_t s(failed,steps[i]);failed.advance(s);}
      services_t s(failed,steps[target]);s.fail=true;
      rejects([&]{failed.advance(s);});rejects([&]{failed.save_checkpoint();});
      rejects([&]{failed.load_checkpoint(before);});rejects([&]{failed.phase();});
    }
    std::cout<<"OUTER_CHECKS atomic_invalids="<<invalids<<" continued_operations="<<op
      <<" poisoned_services=4 return="<<owner.exit_code()<<'\n';return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HOST_EXECUTION_DPI
extern "C" int tsi_host_execution(const char *s,const char *p,const char *d){return run(s,p,d);}
extern "C" void tsi_host_execution_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){return argc==4?run(argv[1],argv[2],argv[3]):2;}
#endif
