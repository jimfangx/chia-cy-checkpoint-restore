// Complete write-child/FIFO state, independently checked against installed memif.
#include "fesvr/tsi_memif_write.h"
#include <fesvr/memif.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
#include <map>
namespace fs = std::filesystem;
using writer_t = firesim_tsi_memif_write_t;
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static auto bytes(const fs::path &path) {
  std::ifstream f(path, std::ios::binary); require(bool(f), "missing image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static void save(const fs::path &path, const std::vector<uint8_t> &b) {
  std::ofstream f(path, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); require(bool(f), "save failed");
}
static auto lines(const char *path) {
  std::ifstream f(path); require(bool(f), "missing plan");
  std::vector<std::string> result; std::string line;
  while (std::getline(f,line)) result.push_back(line);
  return result;
}
static auto unhex(const std::string &s) {
  std::vector<uint8_t> result;
  if (s == "-") return result;
  require(s.size()%2 == 0, "bad hex length");
  for (size_t i=0; i<s.size(); i+=2) result.push_back(std::stoul(s.substr(i,2),nullptr,16));
  return result;
}
static std::string hex(const uint8_t *bytes, size_t size) {
  std::string result; const char *digits="0123456789abcdef";
  for (size_t i=0;i<size;++i) { result+=digits[bytes[i]>>4]; result+=digits[bytes[i]&15]; }
  return result;
}
static uint8_t initial(uint64_t address) { return uint8_t((address*37) ^ (address>>8) ^ 0xa5); }
struct services_t final : writer_t::services_t {
  firesim_tsi_serial_state_t &q;
  size_t calls = 0;
  explicit services_t(firesim_tsi_serial_state_t &q) : q(q) {}
  void issue(uint64_t a, uint64_t n) override { ++calls; q.issue_read(a,n); }
  bool receive(uint32_t &w) override {
    ++calls; if (!q.response_available()) return false; w=q.pop_response(); return true;
  }
  void write(uint64_t a, size_t n, const uint32_t *w) override { ++calls; q.issue_write(a,n,w); }
};
// This invokes the installed libfesvr memif implementation, not the new owner.
static void installed(const char *plan, const fs::path &out) {
  struct memory_t final : chunked_memif_t {
    std::ofstream events;
    std::map<uint64_t,uint8_t> memory;
    explicit memory_t(const fs::path &out) : events(out/"installed-events.txt") {}
    void read_chunk(addr_t a, size_t n, void *p) override {
      auto b=static_cast<uint8_t *>(p);
      for(size_t i=0;i<n;++i) b[i]=memory.count(a+i)?memory.at(a+i):initial(a+i);
      events<<"READ "<<a<<' '<<n<<' '<<hex(b,n)<<'\n';
    }
    void write_chunk(addr_t a, size_t n, const void *p) override {
      auto b=static_cast<const uint8_t *>(p);
      events<<"WRITE "<<a<<' '<<n<<' '<<hex(b,n)<<'\n';
      for(size_t i=0;i<n;++i) memory[a+i]=b[i];
    }
    void clear_chunk(addr_t a, size_t n) override {
      std::array<uint8_t,1024> zeros{};
      for(size_t i=0;i<n;i+=1024) write_chunk(a+i,std::min(size_t(1024),n-i),zeros.data());
    }
    size_t chunk_align() override { return 8; }
    size_t chunk_max_size() override { return 1024; }
  } memory(out);
  memif_t memif(&memory);
  for(const auto &line:lines(plan)) {
    std::istringstream in(line);std::string op,encoded;uint64_t address;in>>op;
    if(op!="BEGIN")continue;
    in>>address>>encoded;auto data=unhex(encoded);memif.write(address,data.size(),data.data());
    // Check all preserved neighboring bytes as well as the entire written range.
    const auto first=address&~uint64_t(7),end=(address+data.size()+7)&~uint64_t(7);
    for(auto a=first;a<end;++a) {
      const auto actual=memory.memory.count(a)?memory.memory.at(a):initial(a);
      require(actual==(a>=address && a-address<data.size()?data[a-address]:initial(a)),
              "installed write changed sentinel/payload");
    }
  }
  std::cout<<"INSTALLED_MEMIF sentinel_and_payload=passed\n";
}
static size_t checks() {
  writer_t w; firesim_tsi_serial_state_t q; services_t s(q); size_t count=0;
  auto reject=[&](auto f) { bool bad=false;try{f();}catch(const std::exception &){bad=true;}require(bad,"missing rejection");++count; };
  auto atomic=[&](auto f) { const auto a=w.save_checkpoint(),b=q.save_checkpoint();reject(f);
    require(w.save_checkpoint()==a && q.save_checkpoint()==b,"partial invalid restore"); };
  atomic([&]{w.begin(~uint64_t(0),{1,2});});
  atomic([&]{w.begin(0,std::vector<uint8_t>(writer_t::maximum+1));});
  atomic([&]{w.finish();});
  w.begin(0x1280003009,{1,2,3,4,5,6,7,8,9});w.advance(s);q.push_response(0xaabbccdd);w.advance(s);
  auto image=w.save_checkpoint();
  atomic([&]{w.begin(0,{});});atomic([&]{w.finish();});
  for(size_t i=0;i<image.size();++i) {
    atomic([&]{w.validate_checkpoint({image.begin(),image.begin()+i});});
    atomic([&]{w.load_checkpoint({image.begin(),image.begin()+i});});
  }
  for(size_t i=0;i<64;++i) {auto bad=image;bad[i]^=1;atomic([&]{w.load_checkpoint(bad);});}
  auto change=[&](size_t at,uint64_t v){auto bad=image;for(unsigned i=0;i<8;++i)bad[at+i]=v>>(8*i);return bad;};
  for(auto at:{64u,72u,80u,88u,105u,177u,185u,193u,201u,209u})
    atomic([&]{w.load_checkpoint(change(at,~uint64_t(0)));});
  auto extra=image;extra.push_back(0);atomic([&]{w.load_checkpoint(extra);});
  struct hostile_t final : writer_t::services_t {
    writer_t &w; decltype(reject) &reject_call;
    hostile_t(writer_t &w,decltype(reject) &r):w(w),reject_call(r){}
    void call() {
      reject_call([&]{w.save_checkpoint();});reject_call([&]{w.load_checkpoint({});});
      reject_call([&]{w.validate_checkpoint({});});reject_call([&]{w.begin(0,{});});
      reject_call([&]{w.advance(*this);});reject_call([&]{w.finish();});reject_call([&]{w.idle();});
      throw std::runtime_error("escaping service");
    }
    void issue(uint64_t,uint64_t) override {call();}
    bool receive(uint32_t &) override {call();return false;}
    void write(uint64_t,size_t,const uint32_t *) override {call();}
  };
  for(unsigned phase=0;phase<3;++phase) {
    writer_t broken;firesim_tsi_serial_state_t queue;services_t io(queue);
    broken.begin(phase==2?0:1,std::vector<uint8_t>(8));
    if(phase==1)broken.advance(io);
    if(phase==2)broken.advance(io); // tail selection -> aligned body write
    hostile_t h(broken,reject);reject([&]{broken.advance(h);});
    reject([&]{broken.save_checkpoint();});reject([&]{broken.load_checkpoint(image);});
    reject([&]{broken.validate_checkpoint(image);});reject([&]{broken.advance(io);});
  }
  writer_t interrupted;interrupted.interrupt();reject([&]{interrupted.save_checkpoint();});
  reject([&]{interrupted.begin(0,{});});reject([&]{interrupted.load_checkpoint(image);});
  // The maximum copied payload must complete, including 1024-byte chunking.
  writer_t large;firesim_tsi_serial_state_t queue;services_t io(queue);
  large.begin(0,std::vector<uint8_t>(writer_t::maximum,0xff));
  while(large.advance(io)!=writer_t::result_t::complete){}
  writer_t fresh;fresh.load_checkpoint(large.save_checkpoint());require(fresh.save_checkpoint()==large.save_checkpoint(),"maximum readback");
  fresh.finish();require(fresh.idle(),"maximum write incomplete");++count;
  return count;
}
static int run(const char *mode,const char *destination,const char *plan,const char *expected,
               const char *image,const char *queue,const char *cut) {
  try {
    fs::path out(destination);fs::create_directories(out);
    if(std::string(mode)=="installed"){installed(plan,out);return 0;}
    if(std::string(mode)=="check"){std::cout<<"ATOMIC_CHECKS "<<checks()<<'\n';return 0;}
    writer_t w;firesim_tsi_serial_state_t q;services_t s(q);
    if(std::string(mode)=="invalid") {
      w.begin(7,{1,2,3});w.advance(s);q.push_response(42);w.advance(s);
      const auto before=w.save_checkpoint(),peer=q.save_checkpoint();bool failed=false;
      try {auto a=bytes(image),b=bytes(queue);w.validate_checkpoint(a);q.validate_checkpoint(b);w.load_checkpoint(a);q.load_checkpoint(b);}
      catch(const std::exception &){failed=true;}
      require(failed && w.save_checkpoint()==before && q.save_checkpoint()==peer,"partial invalid publication");
      save(out/"unchanged.write",before);save(out/"unchanged.serial",peer);
      std::cout<<"REJECTED_BEFORE_MUTATION zero_edges=1\n";return 0;
    }
    const bool source=std::string(mode)=="capture";
    if(!source){auto a=bytes(image),b=bytes(queue);w.validate_checkpoint(a);q.validate_checkpoint(b);w.load_checkpoint(a);q.load_checkpoint(b);}
    require(s.calls==0,"restore invoked target service");
    save(out/"preedge.write",w.save_checkpoint());save(out/"preedge.serial",q.save_checkpoint());
    const auto ops=lines(plan),wanted=lines(expected);require(ops.size()==wanted.size(),"wrong oracle size");
    const size_t first=source?0:std::stoull(cut);
    std::ofstream readbacks(out/"continuation.bin",std::ios::binary),trace(out/"trace");
    auto snapshot=[&](size_t op){for(const auto &pair:std::vector<std::pair<std::string,std::vector<uint8_t>>>{
        {"write",w.save_checkpoint()},{"serial",q.save_checkpoint()}}) {
      if(source)save(out/("cut-"+std::to_string(op)+"."+pair.first),pair.second);
      else readbacks.write(reinterpret_cast<const char *>(pair.second.data()),pair.second.size());
    }};
    snapshot(first);
    for(size_t i=first;i<ops.size();++i) {
      std::istringstream in(ops[i]);std::string op,encoded,actual;uint64_t a,n;in>>op;actual=ops[i];
      if(op=="BEGIN"){in>>a>>encoded;w.begin(a,unhex(encoded));}
      else if(op=="ADVANCE") {auto r=w.advance(s);actual="ADVANCE "+std::string(r==writer_t::result_t::blocked?"BLOCKED":r==writer_t::result_t::complete?"COMPLETE":"PROGRESS");}
      else if(op=="SEND"){in>>n;q.push_response(n);}
      else if(op=="PACKET") {
        size_t index=0;
        while(in>>n) {
          require(q.request_available(),"missing request");
          if(q.request_front()!=n) {
            std::ofstream f(out/"first-divergence.txt");
            f<<"operation="<<i+1<<" word="<<index<<" expected="<<n<<" actual="<<q.request_front()<<" acknowledged=0\n";
            require(q.request_front()!=n,"divergent word consumed");
            throw std::runtime_error("FIRST_DIVERGENCE unconsumed request");
          }
          q.pop_request();++index;
        }
      } else if(op=="FINISH")w.finish();
      else throw std::runtime_error("unknown operation");
      require(actual==wanted[i],"wrong service boundary");trace<<i+1<<' '<<actual<<'\n';snapshot(i+1);
    }
    std::cout<<"WRITE_CONTINUATION operations="<<ops.size()-first<<" complete_readbacks="<<2*(ops.size()-first+1)
             <<" target_edges=0 restore_services=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_MEMIF_WRITE_DPI
extern "C" int tsi_memif_write_checkpoint(const char *m,const char *o,const char *p,const char *e,const char *i,const char *q,const char *c){return run(m,o,p,e,i,q,c);}
extern "C" void tsi_memif_write_exit(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
