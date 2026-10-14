// Production bridge control component; services are independently scheduled.
// Restoring this fixture does not reconstruct HTIF or any Rocket state.
#include "bridges/tsi_bridge_state.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <functional>
#include <cstdlib>
namespace fs=std::filesystem;
static void require(bool b,const std::string &s) {if(!b) throw std::runtime_error(s);}
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p,std::ios::binary);require(bool(f),"missing image/input");
  return {std::istreambuf_iterator<char>(f),{}};
}
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());
  require(bool(f),"cannot save owner");
}
static std::vector<std::string> lines(const char *p) {
  std::ifstream f(p);require(bool(f),"missing commands/oracle");
  std::vector<std::string> result;std::string s;while(std::getline(f,s)) result.push_back(s);return result;
}
static tsi_bridge_state_t make_owner(bool fast,uint32_t wait) {
  widget_checkpoint_config_t config(17,{4,0x1040,2, uint64_t(-0x80000000LL)});
  config.text("four-hart-program");config.text("+fesvr-step-size=128");
  return {std::move(config),128,2004765,wait,fast};
}
struct service_t final:tsi_bridge_state_t::services_t {
  bool completed=true, before=false, after=false, pending=false, stop=false, loaded=false, sent=false;
  std::vector<std::string> trace;
  std::function<void()> hook;
  void record(std::string s) {trace.push_back(std::move(s));if(hook) hook();}
  void create() override {record("CREATE");}
  void write_step(uint32_t n) override {record("STEP="+std::to_string(n));}
  void loaded_in_target() override {record("LOADED_TARGET");}
  void go() override {record("GO");}
  bool done() override {record("DONE="+std::to_string(completed));return completed;}
  void receive() override {record("RECEIVE");}
  bool data_available() override {record("AVAILABLE="+std::to_string(before));return before;}
  void advance() override {record("ADVANCE");before=after;}
  bool requests_pending() override {record("REQUESTS="+std::to_string(pending));return pending;}
  void bypass() override {record("BYPASS");}
  bool terminated() override {record("TERMINATED="+std::to_string(stop));return stop;}
  void send() override {record("SEND");before=sent;}
  bool loaded_in_host() override {record("LOADED_HOST="+std::to_string(loaded));return loaded;}
};
static std::string operation(tsi_bridge_state_t &owner,const std::string &line,service_t &io) {
  std::istringstream in(line);std::string op;in>>op;io.trace.clear();
  if(op=="INIT") owner.initialize(io);
  else if(op=="TICK") {
    in>>io.completed>>io.before>>io.after>>io.pending>>io.stop>>io.loaded>>io.sent;
    owner.tick(io);
  } else if(op=="QUERY") {
    bool value;in>>value;
    const auto result=owner.query([&] {io.record("QUERY="+std::to_string(value));return value;});
    require(result==value,"changed query result");
  } else throw std::runtime_error("unknown operation");
  std::string result=op;
  for(const auto &s:io.trace) result+=" "+s;
  return result;
}
static size_t checks(bool fast,uint32_t wait) {
  auto owner=make_owner(fast,wait);service_t io;size_t count=0;
  auto rejected=[&](auto callback) {bool failed=false;try {callback();} catch(const std::runtime_error &) {failed=true;}
    require(failed,"missing rejection");++count;};
  const auto initial=owner.save_checkpoint();
  rejected([&]{owner.tick(io);});rejected([&]{owner.query([]{return 0;});});
  require(initial==owner.save_checkpoint() && io.trace.empty(),"uninitialized operation mutated state/services");
  owner.initialize(io);auto valid=owner.save_checkpoint();
  const auto calls=io.trace.size();rejected([&]{owner.initialize(io);});
  require(valid==owner.save_checkpoint() && io.trace.size()==calls,"reinitialization mutated state/services");
  for(size_t i=0;i<valid.size();++i) {
    rejected([&]{owner.validate_checkpoint({valid.begin(),valid.begin()+i});});
    rejected([&]{owner.load_checkpoint({valid.begin(),valid.begin()+i});});
    require(valid==owner.save_checkpoint(),"truncated image partially restored");
  }
  auto extra=valid;extra.push_back(0);rejected([&]{owner.load_checkpoint(extra);});
  auto other=make_owner(!fast,wait);rejected([&]{other.load_checkpoint(valid);});
  require(valid==owner.save_checkpoint(),"invalid image changed owner");
  // Every service callback independently tries all checkpoint methods and a
  // reentrant tick. Caught reentrancy must leave the completed call usable.
  io.hook=[&] {
    rejected([&]{owner.save_checkpoint();});rejected([&]{owner.validate_checkpoint(valid);});
    rejected([&]{owner.load_checkpoint(valid);});rejected([&]{owner.tick(io);});
    rejected([&]{owner.query([]{return 0;});});rejected([&]{owner.initialize(io);});
  };
  for(uint32_t i=0;i<=wait;++i) owner.tick(io);
  owner.query([&]{io.record("QUERY");return 0;});
  owner.save_checkpoint();
  // Throw at each actual callback position, including after cursor decrement
  // and fast transition writes; the owner must remain explicitly poisoned.
  for(const auto &line:std::vector<std::string>{"INIT","TICK 1 0 0 1 0 1 0","QUERY 1"}) {
    auto probe=make_owner(true,0);service_t original;
    if(line!="INIT") probe.initialize(original);
    operation(probe,line,original);const auto callbacks=original.trace.size();
    for(size_t at=0;at<callbacks;++at) {
      auto fault=make_owner(true,0);service_t broken;
      if(line!="INIT") fault.initialize(broken);
      size_t cursor=0;broken.hook=[&]{if(cursor++==at) throw std::runtime_error("callback fault");};
      rejected([&]{operation(fault,line,broken);});
      rejected([&]{fault.save_checkpoint();});rejected([&]{fault.validate_checkpoint(valid);});
      rejected([&]{fault.load_checkpoint(valid);});rejected([&]{fault.tick(broken);});
    }
  }
  // Also poison a reset-delay call whose GO failed after decrementing wait.
  auto delay=make_owner(false,1);service_t broken;delay.initialize(broken);
  broken.hook=[&]{if(broken.trace.back()=="GO") throw std::runtime_error("GO fault");};
  rejected([&]{delay.tick(broken);});rejected([&]{delay.save_checkpoint();});
  return count;
}
static int run(const char *mode,const char *destination,const char *commands,
               const char *expected,const char *image,const char *cut_text,const char *variant) {
  try {
    const std::string option=variant;const auto colon=option.find(':');require(colon!=std::string::npos,"bad variant");
    const bool fast=std::stoul(option.substr(0,colon));const auto wait=std::stoul(option.substr(colon+1));
    require(wait<=8,"bad fixture wait");
    fs::path out(destination);fs::create_directories(out);auto owner=make_owner(fast,wait);service_t io;
    if(std::string(mode)=="check") {std::cout<<"ATOMIC_CHECKS "<<checks(fast,wait)<<"\n";return 0;}
    if(std::string(mode)=="invalid") {
      owner.initialize(io);const auto before=owner.save_checkpoint();const auto calls=io.trace.size();bool failed=false;
      try {owner.load_checkpoint(read(image));} catch(const std::exception &) {failed=true;}
      require(failed && before==owner.save_checkpoint() && calls==io.trace.size(),"invalid image restored or called IO");
      save(out/"unchanged.owner",before);std::cout<<"REJECTED_BEFORE_MUTATION calls=0\n";return 0;
    }
    const auto ops=lines(commands),wanted=lines(expected);require(ops.size()==wanted.size(),"bad oracle");
    const size_t cut=std::stoul(cut_text);require(cut<=ops.size(),"bad cut");
    const bool reference=std::string(mode)=="reference";
    if(!reference) owner.load_checkpoint(read(image));
    require(io.trace.empty(),"restore executed services");save(out/"preedge.owner",owner.save_checkpoint());
    size_t first=reference?0:cut,acknowledged=0;
    save(out/("cut-"+std::to_string(first)+".owner"),owner.save_checkpoint());std::ofstream trace(out/"trace");
    for(size_t i=first;i<ops.size();++i) {
      const auto actual="OP "+std::to_string(i+1)+" C "+std::to_string(101+i)+" "+operation(owner,ops[i],io);
      if(actual!=wanted[i]) {
        std::ofstream f(out/"first-divergence.json");
        f<<"{\"operation\":"<<(i+1)<<",\"fixture_cycle\":"<<(101+i)<<",\"acknowledged\":"<<acknowledged
         <<",\"expected\":\""<<wanted[i]<<"\",\"actual\":\""<<actual<<"\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE "+actual);
      }
      trace<<actual<<'\n';++acknowledged;save(out/("cut-"+std::to_string(i+1)+".owner"),owner.save_checkpoint());
    }
    std::cout<<"COMPLETE_READBACK zero_edges=1 restore_service_calls=0 acknowledged="<<acknowledged<<'\n';return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_BRIDGE_CHECKPOINT_DPI
extern "C" int tsi_bridge_checkpoint(const char *m,const char *o,const char *c,const char *e,const char *i,const char *s,const char *v) {
  return run(m,o,c,e,i,s,v);
}
extern "C" void tsi_bridge_exit(int s) {std::exit(s);}
#else
int main(int argc,char **argv) {if(argc!=8) return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
