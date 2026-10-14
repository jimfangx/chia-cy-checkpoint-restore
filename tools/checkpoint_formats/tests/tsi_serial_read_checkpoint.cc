// Fresh pointer-free serial read/FIFO component continuations, not HTIF/CPU.
#include "fesvr/tsi_serial_read.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
using reader_t = firesim_tsi_serial_read_t;
static void require(bool b,const std::string &s) { if (!b) throw std::runtime_error(s); }
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p,std::ios::binary); require(bool(f),"missing image");
  return {std::istreambuf_iterator<char>(f),{}};
}
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()),b.size()); require(bool(f),"save failed");
}
static std::vector<std::string> lines(const char *p) {
  std::ifstream f(p); require(bool(f),"missing oracle"); std::vector<std::string> r; std::string s;
  while (std::getline(f,s)) r.push_back(s);
  return r;
}
struct services_t final : reader_t::services_t {
  firesim_tsi_serial_read_services_t production;
  std::string record;
  size_t calls = 0;
  explicit services_t(firesim_tsi_serial_state_t &serial) : production(serial) {}
  void issue(uint64_t a,uint64_t n) override {
    ++calls; record="ISSUE "+std::to_string(a)+" "+std::to_string(n); production.issue(a,n);
  }
  bool receive(uint32_t &w) override {
    ++calls; bool ok=production.receive(w); record=ok?"WORD "+std::to_string(w):"EMPTY"; return ok;
  }
};
static std::string operation(reader_t &r,firesim_tsi_serial_state_t &q,services_t &io,const std::string &s) {
  std::istringstream in(s); std::string op; in>>op; uint64_t a,n; uint32_t w;
  if (op=="BEGIN") { in>>a>>n; r.begin(a,n); }
  else if (op=="ADVANCE") {
    io.record="NO_SERVICE"; auto p=r.advance(io);
    return op+" "+io.record+" "+(p==reader_t::result_t::blocked?"BLOCKED":p==reader_t::result_t::complete?"COMPLETE":"PROGRESS");
  } else if (op=="SEND") { in>>w; q.push_response(w); }
  else if (op=="REQUEST") return op+" "+std::to_string(q.pop_request());
  else if (op=="RESULT") { std::string result=op; for (auto v:r.result()) result+=" "+std::to_string(v); return result; }
  else if (op=="FINISH") r.finish();
  else if (op=="QUERY") return op+" REQUEST="+std::to_string(q.request_available())+" RESPONSE="+std::to_string(q.response_available());
  else throw std::runtime_error("unknown operation");
  return s;
}
static size_t checks() {
  reader_t r; firesim_tsi_serial_state_t q; services_t io(q); size_t n=0;
  auto reject=[&](auto f) { bool bad=false; try {f();} catch(const std::exception &) {bad=true;} require(bad,"missing rejection"); ++n; };
  auto atomic=[&](auto f) { auto before=r.save_checkpoint(),queue=q.save_checkpoint(); reject(f); require(before==r.save_checkpoint() && queue==q.save_checkpoint(),"partial mutation"); };
  for (auto bytes:{0ULL,1ULL,3ULL,1028ULL,~0ULL}) atomic([&]{r.begin(0,bytes);});
  atomic([&]{r.finish();}); atomic([&]{r.result();});
  r.begin(0xfffffffffffffff8ULL,8); auto issue=r.save_checkpoint();
  atomic([&]{r.begin(0,4);});
  r.advance(io); q.push_response(0xffffffff); r.advance(io);
  auto image=r.save_checkpoint();
  for (size_t i=0;i<image.size();++i) {
    atomic([&]{r.validate_checkpoint({image.begin(),image.begin()+i});});
    atomic([&]{r.load_checkpoint({image.begin(),image.begin()+i});});
  }
  for (size_t i=0;i<64;++i) { auto bad=image; bad[i]^=1; atomic([&]{r.load_checkpoint(bad);}); }
  auto extra=image; extra.push_back(0); atomic([&]{r.load_checkpoint(extra);});
  // Reentrant callbacks and escaping issue/receive exceptions invalidate cuts.
  struct hostile_t final : reader_t::services_t {
    reader_t &r; decltype(reject) &check_failure; bool fail;
    hostile_t(reader_t &r,decltype(reject) &f,bool fail) : r(r),check_failure(f),fail(fail) {}
    void callback() {
      check_failure([&]{r.save_checkpoint();}); check_failure([&]{r.validate_checkpoint({});});
      check_failure([&]{r.load_checkpoint({});}); check_failure([&]{r.begin(0,4);});
      check_failure([&]{r.result();}); check_failure([&]{r.finish();}); check_failure([&]{r.advance(*this);});
      if (fail) throw std::runtime_error("escaping service");
    }
    void issue(uint64_t,uint64_t) override {callback();}
    bool receive(uint32_t &) override {callback(); return false;}
  };
  for (bool response:{false,true}) {
    reader_t broken; broken.begin(0,4); hostile_t h(broken,reject,false);
    if (response) broken.advance(h);
    h.fail=true; reject([&]{broken.advance(h);});
    reject([&]{broken.save_checkpoint();}); reject([&]{broken.load_checkpoint(issue);});
    reject([&]{broken.validate_checkpoint(issue);}); reject([&]{broken.advance(h);});
  }
  reader_t interrupted; interrupted.interrupt();
  reject([&]{interrupted.save_checkpoint();}); reject([&]{interrupted.load_checkpoint(issue);});
  reject([&]{interrupted.validate_checkpoint(issue);}); reject([&]{interrupted.begin(0,4);});
  reject([&]{interrupted.advance(io);}); reject([&]{interrupted.result();}); reject([&]{interrupted.finish();});
  // Restoring partial responses preserves the reserved capacity through the
  // maximum chunk and does not consume an extra queued word after completion.
  for (unsigned size:{4u,8u,1024u}) {
    reader_t source; firesim_tsi_serial_state_t queues; services_t services(queues);
    source.begin(~0ULL,size); source.advance(services);
    for (unsigned i=0;i<size/4;++i) {
      queues.push_response(i); reader_t fresh; fresh.load_checkpoint(source.save_checkpoint());
      require(fresh.save_checkpoint()==source.save_checkpoint(),"partial readback differs");
      fresh.advance(services); source.load_checkpoint(fresh.save_checkpoint()); ++n;
    }
    queues.push_response(42); require(source.advance(services)==reader_t::result_t::complete && queues.pop_response()==42,"complete consumed extra response");
    require(source.result().size()==size/4,"maximum result differs"); source.finish(); ++n;
  }
  return n;
}
static int run(const char *mode,const char *destination,const char *commands,const char *expected,const char *image,const char *queue,const char *cut) {
  try {
    fs::path out(destination); fs::create_directories(out); reader_t r; firesim_tsi_serial_state_t q; services_t io(q);
    require(r.checkpoint_schema()=="firesim.tsi.serial-read.v1","wrong schema");
    if (std::string(mode)=="check") {std::cout<<"ATOMIC_CHECKS "<<checks()<<'\n'; return 0;}
    if (std::string(mode)=="invalid") {
      r.begin(0x123456789abcdef0ULL,8); r.advance(io); q.push_response(42); r.advance(io);
      auto before=r.save_checkpoint(),serial=q.save_checkpoint(); bool bad=false;
      try { auto a=read(image),b=read(queue); r.validate_checkpoint(a); q.validate_checkpoint(b); r.load_checkpoint(a); q.load_checkpoint(b); }
      catch(const std::exception &) {bad=true;}
      require(bad && r.save_checkpoint()==before && q.save_checkpoint()==serial,"invalid partial restore");
      save(out/"unchanged.read",before); save(out/"unchanged.serial",serial);
      std::cout<<"REJECTED_BEFORE_MUTATION zero_edges=1\n"; return 0;
    }
    bool reference=std::string(mode)=="reference";
    if (!reference) {
      auto a=read(image),b=read(queue); r.validate_checkpoint(a); q.validate_checkpoint(b); r.load_checkpoint(a); q.load_checkpoint(b);
    }
    require(io.calls==0,"restore called services");
    save(out/"preedge.read",r.save_checkpoint()); save(out/"preedge.serial",q.save_checkpoint());
    if (std::string(mode)=="readback") {std::cout<<"COMPLETE_READBACK zero_edges=1 restore_services=0\n"; return 0;}
    auto ops=lines(commands),wanted=lines(expected); require(ops.size()==wanted.size(),"wrong oracle size");
    size_t first=reference?0:std::stoull(cut),acknowledged=0; require(first<=ops.size(),"wrong cut");
    auto snapshot=[&](size_t i) {save(out/("cut-"+std::to_string(i)+".read"),r.save_checkpoint());save(out/("cut-"+std::to_string(i)+".serial"),q.save_checkpoint());};
    snapshot(first); std::ofstream trace(out/"trace");
    for (size_t i=first;i<ops.size();++i) {
      auto actual="OP "+std::to_string(i+1)+" C "+std::to_string(101+i)+" "+operation(r,q,io,ops[i]);
      if (actual!=wanted[i]) {
        std::ofstream f(out/"first-divergence.json");
        f<<"{\"operation\":"<<i+1<<",\"fixture_cycle\":"<<101+i<<",\"acknowledged\":"<<acknowledged
         <<",\"expected\":\""<<wanted[i]<<"\",\"actual\":\""<<actual<<"\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE "+actual);
      }
      trace<<actual<<'\n'; ++acknowledged; snapshot(i+1);
    }
    std::cout<<"COMPLETE_READBACK zero_edges=1 restore_services=0 acknowledged="<<acknowledged<<'\n'; return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_SERIAL_READ_DPI
extern "C" int tsi_serial_read_checkpoint(const char *m,const char *o,const char *c,const char *e,const char *i,const char *q,const char *s) {return run(m,o,c,e,i,q,s);}
extern "C" void tsi_serial_read_exit(int status) {std::exit(status);}
#else
int main(int argc,char **argv) {if (argc!=8) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
