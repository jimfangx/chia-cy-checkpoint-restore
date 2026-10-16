// Explicit memif read caller/FIFO continuation and installed-provider oracle.
#include "fesvr/tsi_memif_read.h"
#include <fesvr/memif.h>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
using reader_t = firesim_tsi_memif_read_t;
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static auto bytes(const fs::path &p) {
  std::ifstream f(p,std::ios::binary); require(bool(f),"missing image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
}
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"save failed");
}
static auto lines(const char *p) {
  std::ifstream f(p);require(bool(f),"missing plan");std::vector<std::string> result;std::string line;
  while(std::getline(f,line))result.push_back(line);
  return result;
}
static std::string hex(const uint8_t *p,size_t n) {
  std::string result;const char *digits="0123456789abcdef";
  for(size_t i=0;i<n;++i){result+=digits[p[i]>>4];result+=digits[p[i]&15];}return result;
}
static uint8_t initial(uint64_t a) {return uint8_t((a*37)^(a>>8)^0xa5);}
struct services_t final : reader_t::services_t {
  firesim_tsi_serial_read_services_t production;size_t calls=0;
  explicit services_t(firesim_tsi_serial_state_t &q):production(q){}
  void issue(uint64_t a,uint64_t n) override {++calls;production.issue(a,n);}
  bool receive(uint32_t &w) override {++calls;return production.receive(w);}
};
// Both candidates allocate and validate before either destination publishes.
static void restore(reader_t &r,firesim_tsi_serial_state_t &q,
                    const std::vector<uint8_t> &a,const std::vector<uint8_t> &b) {
  r.load_serial_checkpoint(q,a,b);
}
static void installed(const char *plan,const fs::path &out) {
  struct memory_t final : chunked_memif_t {
    std::ofstream events;
    explicit memory_t(const fs::path &p):events(p/"installed-events.txt"){}
    void read_chunk(addr_t a,size_t n,void *p) override {
      auto b=static_cast<uint8_t *>(p);for(size_t i=0;i<n;++i)b[i]=initial(a+i);
      events<<"READ "<<a<<' '<<n<<' '<<hex(b,n)<<'\n';
    }
    void write_chunk(addr_t,size_t,const void *) override {throw std::runtime_error("unexpected write");}
    void clear_chunk(addr_t,size_t) override {throw std::runtime_error("unexpected clear");}
    size_t chunk_align() override {return 8;}
    size_t chunk_max_size() override {return 1024;}
  } memory(out);
  memif_t memif(&memory);size_t count=0;
  for(const auto &line:lines(plan)) {
    std::istringstream in(line);std::string op;uint64_t a,n;in>>op;if(op!="BEGIN")continue;
    in>>a>>n;std::vector<uint8_t> data(n+2,0x5a);memif.read(a,n,data.data()+1);
    require(data.front()==0x5a && data.back()==0x5a,"installed read changed sentinel");
    for(size_t i=0;i<n;++i)require(data[i+1]==initial(a+i),"installed read result differs");
    ++count;
  }
  std::cout<<"INSTALLED_MEMIF reads="<<count<<" sentinel_and_payload=passed\n";
}
extern void tsi_terminal_fail_allocation_after(long);
static size_t checks() {
  reader_t r;firesim_tsi_serial_state_t q;services_t s(q);size_t count=0;
  auto reject=[&](auto f){bool bad=false;try{f();}catch(const std::exception &){bad=true;}require(bad,"missing rejection");++count;};
  auto atomic=[&](auto f){const auto a=r.save_checkpoint(),b=q.save_checkpoint();reject(f);
    require(r.save_checkpoint()==a && q.save_checkpoint()==b,"partial invalid restore");};
  atomic([&]{r.begin(~uint64_t(0),2);});atomic([&]{r.begin(0,reader_t::maximum+1);});
  atomic([&]{r.finish();});atomic([&]{r.result();});
  r.begin(0x1280003009,9);r.advance(s);q.push_response(0xaabbccdd);r.advance(s);auto image=r.save_checkpoint();
  atomic([&]{r.begin(0,0);});atomic([&]{r.finish();});atomic([&]{r.result();});
  for(size_t i=0;i<image.size();++i) {
    atomic([&]{r.validate_checkpoint({image.begin(),image.begin()+i});});
    atomic([&]{r.load_checkpoint({image.begin(),image.begin()+i});});
  }
  for(size_t i=0;i<64;++i){auto bad=image;bad[i]^=1;atomic([&]{r.load_checkpoint(bad);});}
  auto change=[&](size_t at,uint64_t v){auto bad=image;for(unsigned i=0;i<8;++i)bad.at(at+i)=v>>(8*i);return bad;};
  for(auto at:{64u,72u,80u,88u,105u,177u,185u,193u,201u,209u})
    atomic([&]{r.load_checkpoint(change(at,~uint64_t(0)));});
  auto bad=image;bad.at(96)=1;atomic([&]{r.load_checkpoint(bad);});
  bad=image;bad.push_back(0);atomic([&]{r.load_checkpoint(bad);});
  const auto queues=q.save_checkpoint();size_t failures=0;
  for(;failures<10000;++failures) {
    reader_t fresh;firesim_tsi_serial_state_t peer;
    const auto before=fresh.save_checkpoint(),other=peer.save_checkpoint();bool failed=false;
    tsi_terminal_fail_allocation_after(failures);
    try{restore(fresh,peer,image,queues);}catch(const std::bad_alloc &){failed=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);
    if(!failed) {
      require(fresh.save_checkpoint()==image && peer.save_checkpoint()==queues,"allocation success lost state");break;
    }
    require(fresh.save_checkpoint()==before && peer.save_checkpoint()==other,"allocation failure published a peer");++count;
  }
  require(failures>=6 && failures<10000,"incomplete allocation fault coverage");
  std::cout<<"ALLOCATION_FAILURES "<<failures<<'\n';
  struct hostile_t final : reader_t::services_t {
    reader_t &r;decltype(reject) &failure;
    hostile_t(reader_t &r,decltype(reject) &f):r(r),failure(f){}
    void call() {
      failure([&]{r.save_checkpoint();});failure([&]{r.load_checkpoint({});});failure([&]{r.validate_checkpoint({});});
      failure([&]{r.begin(0,0);});failure([&]{r.advance(*this);});failure([&]{r.result();});
      failure([&]{r.finish();});failure([&]{r.idle();});throw std::runtime_error("escaping service");
    }
    void issue(uint64_t,uint64_t) override {call();}
    bool receive(uint32_t &) override {call();return false;}
  };
  for(bool receive:{false,true}) {
    reader_t broken;firesim_tsi_serial_state_t queue;services_t io(queue);broken.begin(1,8);
    if(receive)broken.advance(io);
    hostile_t h(broken,reject);reject([&]{broken.advance(h);});
    reject([&]{broken.save_checkpoint();});reject([&]{broken.load_checkpoint(image);});
    reject([&]{broken.validate_checkpoint(image);});reject([&]{broken.advance(io);});
  }
  reader_t interrupted;interrupted.interrupt();reject([&]{interrupted.save_checkpoint();});
  reject([&]{interrupted.begin(0,0);});reject([&]{interrupted.load_checkpoint(image);});
  // Full supported length, maximum address and zero-byte operations.
  for(auto spec:std::vector<std::pair<uint64_t,uint64_t>>{{0,reader_t::maximum},{~uint64_t(0)-6,7},{~uint64_t(0),0}}) {
    reader_t large;firesim_tsi_serial_state_t queue;services_t io(queue);large.begin(spec.first,spec.second);
    while(large.advance(io)!=reader_t::result_t::complete) {
      if(queue.request_available()) {
        std::array<uint32_t,5> packet{};for(auto &v:packet)v=queue.pop_request();
        for(size_t i=0;i<=packet[3];++i)queue.push_response(0xffffffff);
      }
    }
    reader_t fresh;fresh.load_checkpoint(large.save_checkpoint());
    require(fresh.save_checkpoint()==large.save_checkpoint() && fresh.result().size()==spec.second,"maximum readback");
    for(auto byte:fresh.result())require(byte==255,"maximum data differs");
    queue.push_response(42);require(fresh.advance(io)==reader_t::result_t::complete && queue.pop_response()==42,"complete consumed extra word");
    fresh.finish();require(fresh.idle(),"maximum incomplete");++count;
  }
  return count;
}
static int run(const char *mode,const char *destination,const char *plan,const char *expected,
               const char *image,const char *queue,const char *cut) {
  try {
    fs::path out(destination);fs::create_directories(out);
    if(std::string(mode)=="installed"){installed(plan,out);return 0;}
    if(std::string(mode)=="check"){const auto count=checks();std::cout<<"ATOMIC_CHECKS "<<count<<'\n';return 0;}
    reader_t r;firesim_tsi_serial_state_t q;services_t s(q);
    if(std::string(mode)=="invalid") {
      r.begin(7,3);r.advance(s);q.push_response(42);r.advance(s);
      const auto before=r.save_checkpoint(),peer=q.save_checkpoint();bool failed=false;
      try{restore(r,q,bytes(image),bytes(queue));}catch(const std::exception &){failed=true;}
      require(failed && r.save_checkpoint()==before && q.save_checkpoint()==peer,"partial invalid publication");
      save(out/"unchanged.read",before);save(out/"unchanged.serial",peer);
      std::cout<<"REJECTED_BEFORE_MUTATION zero_edges=1\n";return 0;
    }
    const bool source=std::string(mode)=="capture";
    if(!source)restore(r,q,bytes(image),bytes(queue));
    require(s.calls==0,"restore invoked target service");
    save(out/"preedge.read",r.save_checkpoint());save(out/"preedge.serial",q.save_checkpoint());
    const auto ops=lines(plan),wanted=lines(expected);require(ops.size()==wanted.size(),"wrong oracle size");
    const size_t first=source?0:std::stoull(cut);
    std::ofstream readbacks(out/"continuation.bin",std::ios::binary),trace(out/"trace");
    auto snapshot=[&](size_t op){for(const auto &pair:std::vector<std::pair<std::string,std::vector<uint8_t>>>{
        {"read",r.save_checkpoint()},{"serial",q.save_checkpoint()}}) {
      if(source)save(out/("cut-"+std::to_string(op)+"."+pair.first),pair.second);
      else readbacks.write(reinterpret_cast<const char *>(pair.second.data()),pair.second.size());
    }};
    snapshot(first);
    for(size_t i=first;i<ops.size();++i) {
      std::istringstream in(ops[i]);std::string op,actual;uint64_t a,n;in>>op;actual=ops[i];
      if(op=="BEGIN"){in>>a>>n;r.begin(a,n);}
      else if(op=="ADVANCE"){auto p=r.advance(s);actual="ADVANCE "+std::string(p==reader_t::result_t::blocked?"BLOCKED":p==reader_t::result_t::complete?"COMPLETE":"PROGRESS");}
      else if(op=="SEND"){while(in>>n)q.push_response(n);}
      else if(op=="PACKET") {
        size_t index=0;while(in>>n) {
          require(q.request_available(),"missing request");
          if(q.request_front()!=n) {
            std::ofstream f(out/"first-divergence.txt");f<<"operation="<<i+1<<" request_word="<<index
              <<" expected="<<n<<" actual="<<q.request_front()<<" acknowledged=0\n";
            throw std::runtime_error("FIRST_DIVERGENCE unconsumed request");
          }
          q.pop_request();++index;
        }
      } else if(op=="RESULT") {
        const auto &data=r.result();std::istringstream oracle(wanted[i]);std::string tag,encoded;oracle>>tag>>encoded;
        const auto actual_hex=hex(data.data(),data.size());actual="RESULT "+(actual_hex.empty()?"-":actual_hex);
        if(actual!=wanted[i]) {
          size_t at=0;while(at<data.size() && encoded.substr(2*at,2)==actual_hex.substr(2*at,2))++at;
          require(at<data.size(),"wrong result length");std::ofstream f(out/"first-divergence.txt");
          f<<"operation="<<i+1<<" result_byte="<<at<<" expected="<<std::stoul(encoded.substr(2*at,2),nullptr,16)
            <<" actual="<<unsigned(data[at])<<" acknowledged=0\n";
          throw std::runtime_error("FIRST_DIVERGENCE unacknowledged result");
        }
      } else if(op=="FINISH")r.finish();else throw std::runtime_error("unknown operation");
      require(actual==wanted[i],"wrong service boundary");trace<<i+1<<' '<<actual<<'\n';snapshot(i+1);
    }
    std::cout<<"READ_CONTINUATION operations="<<ops.size()-first<<" complete_readbacks="<<2*(ops.size()-first+1)
             <<" target_edges=0 restore_services=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_MEMIF_READ_DPI
extern "C" int tsi_memif_read_checkpoint(const char *m,const char *o,const char *p,const char *e,const char *i,const char *q,const char *c){return run(m,o,p,e,i,q,c);}
extern "C" void tsi_memif_read_exit(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
