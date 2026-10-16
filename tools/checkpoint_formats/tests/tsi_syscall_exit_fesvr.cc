// Actual installed syscall differential and explicit parent continuation.
#include "fesvr/tsi_syscall_exit.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <csignal>
#include <pthread.h>
#include <functional>
namespace fs = std::filesystem;
using caller_t = firesim_tsi_syscall_exit_t;
using images_t = caller_t::images_t;
__attribute__((constructor)) static void mask_signals() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
  if (pthread_sigmask(SIG_BLOCK, &set, nullptr)) std::abort();
}
static void require(bool ok, const char *why) { if (!ok) throw std::runtime_error(why); }
static auto bytes(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static void save(const fs::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()), b.size());
  require(bool(f), "save failed");
}
static auto load(const fs::path &p) {
  images_t result;
  for (auto name : {"syscall", "serial", "lifecycle"}) result.emplace_back(name, bytes(p.string()+"."+name));
  return result;
}
class reference_t final : public htif_t {
public:
  unsigned calls = 0;
  bool big_endian = false;
  endianness_t get_target_endianness() const override { return big_endian ? endianness_big : endianness_little; }
  std::vector<uint8_t> memory;
  uint64_t base = 0, response = 0;
  std::ostringstream events;
  reference_t() : htif_t(std::vector<std::string>{"none"}) {}
  void dispatch(uint64_t command) {
    syscall_t syscall(this);
    command_t cmd(memif(), command, [&](uint64_t value) { ++calls; response = value; events << "RESPOND " << value << '\n'; });
    syscall.handle_command(cmd);
  }
  void read_chunk(addr_t a, size_t n, void *d) override {
    ++calls; require(a >= base && n <= memory.size() && a-base <= memory.size()-n, "reference range");
    std::memcpy(d, memory.data()+a-base, n); event("READ", a, n, static_cast<uint8_t *>(d));
  }
  void write_chunk(addr_t a, size_t n, const void *d) override {
    ++calls; require(a >= base && n <= memory.size() && a-base <= memory.size()-n, "reference range");
    std::memcpy(memory.data()+a-base, d, n); event("WRITE", a, n, static_cast<const uint8_t *>(d));
  }
  void reset() override { throw std::runtime_error("unexpected reset"); }
  size_t chunk_align() override { return 8; }
  size_t chunk_max_size() override { return 1024; }
private:
  void event(const char *kind, uint64_t a, size_t n, const uint8_t *d) {
    static const char hex[] = "0123456789abcdef";
    events << kind << ' ' << a << ' ' << n << ' ';
    for (size_t i=0; i<n; ++i) events << hex[d[i] >> 4] << hex[d[i] & 15];
    events << '\n';
  }
};
struct owners_t {
  reference_t htif;
  firesim_tsi_serial_state_t serial;
  caller_t caller{htif, serial};
  auto snapshot() const { return caller.save_components(); }
};
struct services_t : caller_t::services_t {
  owners_t &o; size_t calls = 0; std::string response;
  explicit services_t(owners_t &o) : o(o) {}
  void issue(uint64_t a, uint64_t n) override { ++calls; o.serial.issue_read(a,n); }
  bool receive(uint32_t &w) override {
    ++calls; if (!o.serial.response_available()) return false;
    w=o.serial.pop_response(); return true;
  }
  void write(uint64_t a, size_t n, const uint32_t *w) override { ++calls; o.serial.issue_write(a,n,w); }
  void respond(uint64_t v) override { ++calls; require(response.empty(), "duplicate response"); response=std::to_string(v); }
};
extern void tsi_terminal_fail_allocation_after(long);
static void atomic_checks(const images_t &good, const fs::path &out) {
  owners_t dest; const auto before=dest.snapshot(); size_t malformed=0, membership=0, cross=0;
  auto reject=[&](const images_t &bad) {
    bool rejected=false; try { dest.caller.load_components(bad); } catch (const std::runtime_error &) { rejected=true; }
    require(rejected && dest.snapshot()==before, "invalid group partially published");
  };
  for (unsigned owner=0; owner<3; ++owner) {
    for (size_t n=0; n<good[owner].second.size(); ++n) {
      auto bad=good; bad[owner].second.resize(n); reject(bad); ++malformed;
    }
    auto bad=good; bad[owner].second.push_back(0); reject(bad); ++malformed;
    bad=good; bad[owner].second[16]^=1; reject(bad); ++malformed;
    bad=good; bad.erase(bad.begin()+owner); reject(bad); ++membership;
    bad=good; bad.push_back(good[owner]); reject(bad); ++membership;
    bad=good; bad[owner].first="unknown"; reject(bad); ++membership;
    bad=good; std::swap(bad[owner],bad[(owner+1)%3]); reject(bad); ++membership;
  }
  auto put=[](std::vector<uint8_t> &b,size_t at,uint64_t v) { for(unsigned i=0;i<8;++i)b.at(at+i)=uint8_t(v>>(8*i)); };
  // This candidate is captured with writeback pending and actual optional exit.
  for (unsigned n=0; n<8; ++n) {
    auto bad=good;
    if(n==0)put(bad[0].second,88,6);  // invalid phase
    if(n==1)put(bad[0].second,96,1);  // odd command
    if(n==2)put(bad[0].second,104,64); // unsupported syscall selector
    if(n==3)bad[0].second[112]^=2;    // exit code disagrees with provider and child
    if(n==4)put(bad[2].second,56,0);  // absent provider with nonzero raw status
    if(n==5)put(bad[2].second,72,1);  // stop before writeback
    if(n==6)put(bad[0].second,88,4);  // response while write child is active
    if(n==7)bad[2].second[64]^=2;    // semantic provider mismatch
    reject(bad); ++cross;
  }
  long failures=0;
  for (;; ++failures) {
    bool exhausted=false; tsi_terminal_fail_allocation_after(failures);
    try { dest.caller.load_components(good); } catch (const std::bad_alloc &) { exhausted=true; }
    catch (...) { tsi_terminal_fail_allocation_after(-1); throw; }
    tsi_terminal_fail_allocation_after(-1);
    if (!exhausted) break;
    require(dest.snapshot()==before, "allocation failure partially restored");
  }
  require(failures>=10 && dest.snapshot()==good, "allocation injection incomplete");
  // An occupied provider fails before publishing either caller or FIFO peer.
  const auto occupied=dest.snapshot(); bool rejected=false;
  try { dest.caller.load_components(good); } catch(const std::runtime_error &) { rejected=true; }
  require(rejected && dest.snapshot()==occupied, "occupied destination partially published");
  std::ofstream(out/"atomic.txt") << "malformed=" << malformed << " membership=" << membership << " cross=" << cross
    << " allocation_failures=" << failures << " occupied=1 unchanged_on_failure=1\n";
}
static void guards(const fs::path &out) {
  unsigned rejected=0;
  auto reject=[&](auto action) {
    bool no=false; try{action();}catch(const std::runtime_error &){no=true;}
    require(no,"guard admitted unsupported operation"); ++rejected;
  };
  for(uint64_t command : {uint64_t(1),uint64_t(0x1000000000000ULL),uint64_t(0xfffffffffffeULL)}) {
    owners_t o;const auto before=o.snapshot(); reject([&]{o.caller.begin(command);});
    require(o.snapshot()==before,"invalid command changed caller");
  }
  {
    owners_t o;const auto before=o.snapshot();o.htif.big_endian=true;
    reject([&]{o.caller.begin(0x8000);}); reject([&]{o.caller.save_components();});
    o.htif.big_endian=false;require(o.snapshot()==before,"unsupported endian changed state");
  }
  {
    owners_t o;services_t io(o);o.caller.begin(0x8000);o.caller.advance(io);
    for(unsigned i=0;i<16;++i)o.serial.push_response(i==0?64:0);
    reject([&]{o.caller.advance(io);});
    require(!firesim_htif_lifecycle_read(o.htif).has_exit && io.response.empty() && o.htif.calls==0,
            "unsupported selector issued exit/response");
    // Only the read packet may have been issued, never a host writeback.
    std::vector<uint32_t> packet;
    while(o.serial.request_available()){packet.push_back(o.serial.request_front());o.serial.pop_request();}
    require(packet==std::vector<uint32_t>({0,0x8000,0,15,0}),"unsupported selector issued write");
    reject([&]{o.caller.save_components();});
  }
  {
    owners_t o;services_t ordinary(o);o.caller.begin(0x8000);o.caller.advance(ordinary);
    struct hostile_t : services_t {
      std::function<void(std::function<void()>)> reject;
      hostile_t(owners_t &o,decltype(reject) r):services_t(o),reject(r){}
      void issue(uint64_t,uint64_t) override {
        reject([&]{o.caller.save_components();});
        reject([&]{o.caller.begin(0x9000);});
        reject([&]{o.caller.load_components({});});
        reject([&]{o.caller.advance(*this);});
        throw std::runtime_error("escaping service");
      }
    } hostile(o,reject);
    reject([&]{o.caller.advance(hostile);});
    reject([&]{o.caller.save_components();});reject([&]{o.caller.load_components({});});
    reject([&]{o.caller.advance(ordinary);});
    require(!firesim_htif_lifecycle_read(o.htif).has_exit,"hostile service issued exit");
  }
  std::ofstream(out/"guards.txt")<<"rejections="<<rejected<<" command=3 endian=2 selector=2 hostile=8 provider_unchanged=1\n";
}
static int run(const char *mode_arg,const char *directory,const char *plan,const char *expected,
               const char *source,const char *cut_arg) {
  try {
    const std::string mode(mode_arg); fs::path out(directory); fs::create_directories(out);
    if (mode=="reference") {
      std::ifstream spec(plan); uint64_t command, code; spec>>command>>code;
      reference_t ref; ref.base=command & ~uint64_t(7); ref.memory=bytes(expected);
      ref.dispatch(command);
      require(ref.response==1,"installed syscall missed response");
      save(out/"memory.bin",ref.memory); std::ofstream(out/"events.txt")<<ref.events.str();
      firesim_tsi_htif_lifecycle_t lifecycle(ref); save(out/"lifecycle.bin",lifecycle.save_checkpoint());
      std::cout<<"INSTALLED_SYSCALL selector=93 response=1 provider_raw="<<uint32_t((code<<1)|1)<<"\n"; return 0;
    }
    if (mode=="check") { atomic_checks(load(source),out); return 0; }
    if (mode=="guard") { guards(out); return 0; }
    owners_t o; services_t service(o);
    if (mode=="invalid") {
      const auto before=o.snapshot(); bool rejected=false;
      try{o.caller.load_components(load(source));}catch(const std::runtime_error &){rejected=true;}
      require(rejected && o.snapshot()==before && service.calls==0 && o.htif.calls==0,"invalid restore mutation");
      for(const auto &[name,b]:o.snapshot())save(out/("unchanged."+name),b);
      std::cout<<"REJECTED owners=3 restore_services=0 target_edges=0\n"; return 0;
    }
    const bool capture=mode=="capture"; const size_t first=capture?0:std::stoull(cut_arg);
    if(!capture)o.caller.load_components(load(source));
    if(mode=="corrupt")o.caller.load_checkpoint(bytes(std::string(source)+".fault"));
    require(service.calls==0 && o.htif.calls==0,"restore replayed a service");
    for(const auto &[name,b]:o.snapshot())save(out/("preedge."+name),b);
    std::ifstream steps(plan), oracle(expected); require(bool(steps)&&bool(oracle),"missing plan");
    std::ofstream readbacks(out/"continuation.bin",std::ios::binary), trace(out/"trace");
    auto snapshot=[&](size_t index) {
      for(const auto &[name,b]:o.snapshot()) {
        if(capture)save(out/("cut-"+std::to_string(index)+"."+name),b);
        else readbacks.write(reinterpret_cast<const char *>(b.data()),b.size());
      }
    };
    snapshot(first); std::string line,wanted; size_t index=0;
    while(std::getline(steps,line)) {
      require(bool(std::getline(oracle,wanted)),"short oracle"); if(index++<first)continue;
      std::istringstream in(line); std::string op,actual=line; uint64_t value; in>>op;
      if(op=="BEGIN"){in>>value;o.caller.begin(value);}
      else if(op=="ADVANCE") {
        service.response.clear(); const auto r=o.caller.advance(service);
        actual="ADVANCE "+std::string(r==caller_t::result_t::blocked?"BLOCKED":r==caller_t::result_t::complete?"COMPLETE":"PROGRESS");
        if(!service.response.empty())actual+=" RESPOND "+service.response;
      } else if(op=="SEND"){in>>value;o.serial.push_response(value);}
      else if(op=="PACKET") {
        size_t word=0; while(in>>value) {
          require(o.serial.request_available(),"missing packet"); const auto got=o.serial.request_front();
          if(got!=value) {
            std::ofstream(out/"first-divergence.txt")<<"operation="<<index<<" word="<<word<<" expected="<<value<<" actual="<<got<<" acknowledged=0\n";
            require(o.serial.request_front()==got,"divergent word consumed"); throw std::runtime_error("FIRST_DIVERGENCE");
          }
          o.serial.pop_request(); ++word;
        }
      } else throw std::runtime_error("unknown operation");
      require(actual==wanted,"wrong syscall service boundary"); trace<<index<<' '<<actual<<'\n'; snapshot(index);
    }
    std::cout<<"SYSCALL_CONTINUATION operations="<<index-first<<" complete_readbacks="<<3*(index-first+1)
             <<" restore_services=0 target_edges=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_SYSCALL_EXIT_DPI
extern "C" int tsi_syscall_exit_fesvr(const char *m,const char *o,const char *p,const char *e,const char *s,const char *c){return run(m,o,p,e,s,c);}
extern "C" void tsi_syscall_exit_status(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=7)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6]);}
#endif
