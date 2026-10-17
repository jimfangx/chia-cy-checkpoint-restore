// Joint production runtime I/O candidate; synthetic AXI traffic, no CPU claim.
#include "emul/simif_emul.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <new>

// Exhaust every allocation boundary in preparation and publication separately.
static thread_local long fail_after=-1;
static thread_local bool allocation_failed=false;
void *operator new(std::size_t n) {
  if(fail_after>=0 && fail_after--==0) { fail_after=-1; allocation_failed=true; throw std::bad_alloc(); }
  if(void *p=std::malloc(n ? n : 1)) return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p,std::size_t) noexcept { std::free(p); }
void operator delete[](void *p,std::size_t) noexcept { std::free(p); }

midas_time_t timestamp() { return 0; }
double diff_secs(midas_time_t,midas_time_t) { return 0; }
static void check(bool b) { if(!b) throw std::runtime_error("runtime IO assertion"); }
static unsigned rejections=0;
template<class F> static void reject(F fn) {
  try { fn(); } catch(const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("runtime IO accepted invalid candidate");
}
static const TargetConfig configs[]={
  {{12,32,32},{16,34,64},1,AXI4Config{16,64,512},{},{0,0},"runtime-io-fixture"},
  {{12,32,32},{16,34,64},1,{},{},{0,0},"runtime-io-fixture"},
  {{11,32,32},{16,34,64},1,AXI4Config{16,64,512},{},{0,0},"runtime-io-fixture"},
  {{12,32,32},{16,34,64},1,AXI4Config{16,64,256},{},{0,0},"runtime-io-fixture"}};
struct platform_t : simif_emul_t {
  explicit platform_t(unsigned config=0,unsigned delay=7)
    : simif_emul_t(configs[config],{"+memsize=4096","+fuzz-host-timing="+std::to_string(delay),"+fuzz-seed=166"}) {}
  void timing() { host_timing.begin_delay(); }
};
using image_t=simif_emul_t::io_checkpoint_t;
static void save(const std::filesystem::path &out,const std::string &prefix,const image_t &image) {
  std::filesystem::create_directories(out);
  std::ofstream manifest(out/(prefix+".owners"));
  for(size_t i=0;i<image.owners.size();++i) {
    const auto &entry=image.owners[i]; manifest<<entry.name<<' '<<entry.schema<<'\n';
    std::ofstream f(out/(prefix+"."+std::to_string(i)),std::ios::binary);
    f.write(reinterpret_cast<const char *>(entry.payload.data()),entry.payload.size());check(bool(f));
  }
}
static image_t load(const std::filesystem::path &out,const std::string &prefix) {
  image_t image; std::ifstream manifest(out/(prefix+".owners"));check(bool(manifest));
  std::string name,schema;
  while(manifest>>name>>schema) {
    std::ifstream f(out/(prefix+"."+std::to_string(image.owners.size())),std::ios::binary);check(bool(f));
    image.owners.push_back({name,schema,{std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()}});
  }
  return image;
}
static void traffic(mmio_t &m,unsigned stage) {
  const auto beat=m.get_config().beat_bytes();
  std::vector<char> data(beat*3);for(size_t i=0;i<data.size();++i)data[i]=char(i*13+7);
  size_t strb[]={0x5,0xa,0xf};
  m.read_req(0x120,2,2);m.write_req(0x240,2,2,data.data(),strb);
  const std::vector<uint32_t> reply(beat/4,0x12345678);
  if(stage>=1) m.tick(false,true,true,true,0,reply,false,false,0,false);
  if(stage>=2) {
    m.tick(false,false,false,true,0,reply,false,true,0,false);
    m.tick(false,false,false,true,0,reply,false,true,0,false);
    m.tick(false,false,false,false,0,reply,true,true,0,true);
  }
}
static void finish(mmio_t &m,unsigned stage) {
  const auto beat=m.get_config().beat_bytes();
  const std::vector<uint32_t> reply(beat/4,0x12345678);
  if(stage==0) m.tick(false,true,true,true,0,reply,false,false,0,false);
  if(stage<2) {
    m.tick(false,false,false,true,0,reply,false,true,0,false);
    m.tick(false,false,false,true,0,reply,false,true,0,false);
    m.tick(false,false,false,false,0,reply,true,true,0,true);
  }
  uint32_t data[3]={};check(m.read_resp(data));check(m.write_resp());
  for(auto value:data)check(value==0x12345678);
}
static int execute(const char *mode,const char *source,const char *destination,unsigned stage,unsigned no_dma) {
 try {
  check(stage<3 && no_dma<2); platform_t p(no_dma); const auto initial=p.save_checkpoint_io();
  auto unchanged=[&] { check(p.save_checkpoint_io()==initial); };
  if(std::string(mode)=="negative") {
    platform_t incoming(no_dma);traffic(*incoming.master,stage);
    if(!no_dma)traffic(*incoming.get_cpu_managed_axi4(),stage);
    incoming.timing();const auto image=incoming.save_checkpoint_io();
    for(size_t i=0;i<image.owners.size();++i) {
      auto bad=image;bad.owners.erase(bad.owners.begin()+i);reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners.push_back(image.owners[i]);reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners[i].name+="/unknown";reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners[i].schema+="/unknown";reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners[i].payload.push_back(0);reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners[i].payload.clear();reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
      bad=image;bad.owners[i].payload[0]^=1;reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
    }
    auto bad=image;std::swap(bad.owners.front(),bad.owners.back());reject([&]{p.prepare_checkpoint_io(bad);});unchanged();
    for(unsigned config : {1-no_dma,2u,3u}) {
      platform_t other(config);auto before=other.save_checkpoint_io();
      reject([&]{other.prepare_checkpoint_io(image);});check(other.save_checkpoint_io()==before);
    }
    platform_t other_delay(no_dma,1);auto before=other_delay.save_checkpoint_io();
    reject([&]{other_delay.prepare_checkpoint_io(image);});check(other_delay.save_checkpoint_io()==before);
    auto candidate=p.prepare_checkpoint_io(image);
    platform_t other(no_dma);before=other.save_checkpoint_io();
    reject([&]{other.publish_checkpoint_io(*candidate);});check(other.save_checkpoint_io()==before);unchanged();
    std::thread foreign([&]{reject([&]{p.publish_checkpoint_io(*candidate);});});foreign.join();unchanged();
    alignas(platform_t) unsigned char storage[sizeof(platform_t)];
    auto *retired=new(storage) platform_t(no_dma);
    auto old=retired->prepare_checkpoint_io(image);retired->~platform_t();
    auto *replacement=new(storage) platform_t(no_dma);
    reject([&]{replacement->publish_checkpoint_io(*old);});
    check(replacement->save_checkpoint_io()==initial);replacement->~platform_t();
    // Every stateful member invalidates a prepared destination. No member may
    // be swapped before the complete destination recheck succeeds.
    for(unsigned owner=0;owner<(no_dma?2u:3u);++owner) {
      platform_t stale(no_dma);auto c=stale.prepare_checkpoint_io(image);
      if(owner==0)stale.master->read_req(0x300,2,0);
      if(owner==1)stale.timing();
      if(owner==2)stale.get_cpu_managed_axi4()->read_req(0x400,2,0);
      auto changed=stale.save_checkpoint_io();reject([&]{stale.publish_checkpoint_io(*c);});check(stale.save_checkpoint_io()==changed);
    }
    unsigned preparation_failures=0,publication_failures=0;
    for(long limit=0;;++limit) {
      check(limit<20000);allocation_failed=false;fail_after=limit;
      try { auto c=p.prepare_checkpoint_io(image);fail_after=-1;check(!allocation_failed);unchanged();break; }
      catch(const std::exception &) {fail_after=-1;check(allocation_failed);++preparation_failures;unchanged();}
    }
    for(long limit=0;;++limit) {
      check(limit<20000);allocation_failed=false;fail_after=limit;
      try {p.publish_checkpoint_io(*candidate);fail_after=-1;check(!allocation_failed);break;}
      catch(const std::exception &) {fail_after=-1;check(allocation_failed);++publication_failures;unchanged();}
    }
    // Sweep to the first uninjected success, irrespective of the number of
    // owners. A three-owner group naturally allocates less than a DMA group.
    check(preparation_failures>0 && publication_failures>0);
    check(p.save_checkpoint_io()==image);reject([&]{p.publish_checkpoint_io(*candidate);});check(p.save_checkpoint_io()==image);
    save(destination,"published",p.save_checkpoint_io());
    std::cout<<"RUNTIME_IO_NEGATIVE rejected="<<rejections<<" preparation_failures="<<preparation_failures
             <<" publication_failures="<<publication_failures<<" partial_publication=0 target_edges=0\n";return 0;
  }
  if(std::string(mode)=="reference") {
    traffic(*p.master,stage);if(!no_dma)traffic(*p.get_cpu_managed_axi4(),stage);p.timing();
    save(destination,"cut",p.save_checkpoint_io());
  } else {
    const auto image=load(source,"cut");auto candidate=p.prepare_checkpoint_io(image);unchanged();
    p.publish_checkpoint_io(*candidate);check(p.save_checkpoint_io()==image);save(destination,"readback",p.save_checkpoint_io());
  }
  finish(*p.master,stage);if(!no_dma)finish(*p.get_cpu_managed_axi4(),stage);
  save(destination,"final",p.save_checkpoint_io());
  std::cout<<"RUNTIME_IO_PASS owners="<<initial.owners.size()<<" stage="<<stage<<" target_edges=0\n";return 0;
 }catch(const std::exception &e){fail_after=-1;std::cerr<<"RUNTIME_IO_FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef RUNTIME_IO_DPI
extern "C" int runtime_io_test(const char *m,const char *s,const char *d,unsigned c,unsigned b) {return execute(m,s,d,c,b);}
#else
int main(int argc,char **argv){return argc==6?execute(argv[1],argv[2],argv[3],std::stoul(argv[4]),std::stoul(argv[5])):2;}
#endif
