// Production metasim DMA calls with an independent AXI peer, not target RTL.
#include "emul/simif_emul.h"
#include "core/simulation.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <limits>

namespace fs = std::filesystem;
static uint64_t now=1000000;
midas_time_t timestamp() { return now+=100; }
double diff_secs(midas_time_t a,midas_time_t b) { return double(a-b)/1000000; }
static void check(bool b) { if(!b) throw std::runtime_error("CPU-managed IO assertion"); }
static unsigned rejects=0;
static void reject(const std::function<void()> &fn) {
  try { fn(); } catch(const std::runtime_error &) { ++rejects; return; }
  throw std::runtime_error("CPU-managed IO accepted unsupported state");
}
static void save(const fs::path &p,const std::vector<uint8_t> &v) {
  std::ofstream f(p,std::ios::binary); f.write(reinterpret_cast<const char *>(v.data()),v.size()); check(bool(f));
}
static std::vector<uint8_t> load(const fs::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
static const unsigned lengths[]={0,1,255,256,257,513};
static constexpr unsigned operations=14;
static const TargetConfig &configuration(unsigned beat) {
  // simif_t retains this reference for the complete platform lifetime.
  static const TargetConfig configs[]={
    {{12,32,32},{16,34,64},1,AXI4Config{16,64,64},{},{0,0},"cpu-io-fixture"},
    {{12,32,32},{16,34,64},1,AXI4Config{16,64,128},{},{0,0},"cpu-io-fixture"},
    {{12,32,32},{16,34,64},1,AXI4Config{16,64,512},{},{0,0},"cpu-io-fixture"}};
  check(beat==8 || beat==16 || beat==64);
  return configs[beat==8 ? 0 : beat==16 ? 1 : 2];
}
struct platform_t : simif_emul_t {
  bool fail_mmio=false, active_mmio=false;
  explicit platform_t(unsigned beat) : simif_emul_t(configuration(beat),{"+memsize=4096"}) {}
  void write(size_t,uint32_t) override {}
  uint32_t read(size_t addr) override {
    if(addr==100) {
      if(fail_mmio) throw std::runtime_error("injected MMIO failure");
      active_mmio=true; do_tick(); active_mmio=false; return 0x1234;
    }
    return addr==0 ? 1 : addr==4 ? 0x46697265 : 23;
  }
  checkpoint_owner_t &owner() {
    auto owners=checkpoint_stream_io_owners();
    check(owners.size()==1 && owners[0].first=="runtime/cpu-managed-stream-io" && owners[0].second);
    return *owners[0].second;
  }
};
struct driver_t : simulation_t {
  platform_t &p;
  fs::path out;
  std::ofstream trace;
  unsigned index,beat;
  driver_t(widget_registry_t &r,platform_t &p,const fs::path &out,unsigned cut,unsigned beat)
    : simulation_t(r,{}),p(p),out(out),trace(out/"trace"),index(cut),beat(beat) { check(bool(trace)); }
  int simulation_run() override {
    auto &io=p.get_cpu_managed_stream_io();
    for(;index<operations;++index) {
      save(out/("cut-"+std::to_string(index)+".io"),p.owner().save_checkpoint());
      save(out/("cut-"+std::to_string(index)+".axi"),p.get_cpu_managed_axi4()->save_checkpoint());
      trace<<"OP "<<index<<'\n';
      if(index==0) check(io.mmio_read(100)==0x1234);
      else if(index==1) {
        check(!io.cpu_managed_axi4_read(4096,nullptr,0));
        check(!io.cpu_managed_axi4_write(4096,nullptr,0));
      } else {
        const unsigned count=lengths[(index-2)/2];
        const size_t addr=4096+index*65536;
        std::vector<char> bytes(size_t(count)*beat);
        for(size_t i=0;i<bytes.size();++i) bytes[i]=char(index*17+i);
        if(index%2==0) check(io.cpu_managed_axi4_write(addr,bytes.data(),bytes.size())==bytes.size());
        else {
          check(io.cpu_managed_axi4_read(addr,bytes.data(),bytes.size())==bytes.size());
          for(size_t i=0;i<bytes.size();++i) check(uint8_t(bytes[i])==uint8_t((addr+i)*13+7));
        }
      }
      trace<<"RETURN "<<index<<'\n';
    }
    save(out/"final.io",p.owner().save_checkpoint());
    save(out/"final.axi",p.get_cpu_managed_axi4()->save_checkpoint());
    return 0;
  }
};
static int execute(const char *mode,const char *source,const char *dest,unsigned cut,unsigned beat) {
  try {
    platform_t p(beat); auto &owner=p.owner(); auto &io=p.get_cpu_managed_stream_io();
    auto good=owner.save_checkpoint(), axi=p.get_cpu_managed_axi4()->save_checkpoint();
    check(owner.checkpoint_schema()=="firesim.emul.cpu-managed-stream-io.returned.v1");
    const fs::path out(dest); fs::create_directories(out);
    if(std::string(mode)=="negative") {
      for(size_t n=0;n<good.size();++n) reject([&] { owner.load_checkpoint({good.begin(),good.begin()+n}); });
      for(size_t n=0;n<good.size();++n) {
        auto bad=good; bad[n]^=1; reject([&] { owner.validate_checkpoint(bad); });
        reject([&] { owner.load_checkpoint(bad); });
      }
      auto bad=good; bad.push_back(0); reject([&] { owner.load_checkpoint(bad); });
      check(owner.save_checkpoint()==good && p.get_cpu_managed_axi4()->save_checkpoint()==axi);
      platform_t other(beat==64 ? 8 : 64); reject([&] { other.owner().load_checkpoint(good); });
      // An interrupted callback permanently poisons the same owner; loading an
      // earlier idle image may not make its missing continuation disappear.
      p.fail_mmio=true; reject([&] { io.mmio_read(100); });
      reject([&] { owner.save_checkpoint(); }); reject([&] { owner.validate_checkpoint(good); });
      reject([&] { owner.load_checkpoint(good); }); reject([&] { io.cpu_managed_axi4_read(0,nullptr,0); });
      check(p.get_cpu_managed_axi4()->save_checkpoint()==axi);
      for(bool write : {false,true}) {
        platform_t broken(beat); auto image=broken.owner().save_checkpoint();
        auto before=broken.get_cpu_managed_axi4()->save_checkpoint(); char data[64]={};
        reject([&] { if(write) broken.get_cpu_managed_stream_io().cpu_managed_axi4_write(0,data,beat-1);
                    else broken.get_cpu_managed_stream_io().cpu_managed_axi4_read(0,data,beat-1); });
        reject([&] { broken.owner().load_checkpoint(image); });
        reject([&] { broken.owner().save_checkpoint(); });
        check(broken.get_cpu_managed_axi4()->save_checkpoint()==before);
      }
      std::cout<<"CPU_IO_NEGATIVE rejected="<<rejects<<" partial_publication=0 target_edges=0\n"; return 0;
    }
    if(std::string(mode)=="restore") {
      auto image=load(fs::path(source)/("cut-"+std::to_string(cut)+".io"));
      auto transport=load(fs::path(source)/("cut-"+std::to_string(cut)+".axi"));
      owner.validate_checkpoint(image); p.get_cpu_managed_axi4()->validate_checkpoint(transport);
      owner.load_checkpoint(image); p.get_cpu_managed_axi4()->load_checkpoint(transport);
      save(out/"readback.io",owner.save_checkpoint()); save(out/"readback.axi",p.get_cpu_managed_axi4()->save_checkpoint());
      check(owner.save_checkpoint()==image && p.get_cpu_managed_axi4()->save_checkpoint()==transport);
      std::cout<<"CPU_IO_PREEDGE_READBACK owners=2 target_edges=0\n";
    }
    // CPU aggregate admission remains disabled even with an audited IO owner.
    widget_registry_t registry;
    registry.add_widget(new master_t(p,{0,4,8},0,{}));
    registry.add_widget(new clockmodule_t(p,{16,20,24,28,32,36},0,{}));
    driver_t driver(registry,p,out,cut,beat);
    reject([&] { p.begin_restored_load(driver); });
    p.start_driver(driver);
    auto &m=*p.get_cpu_managed_axi4();
    uint64_t read_addr=0, write_addr=0; unsigned read_left=0,write_left=0;
    unsigned active_boundaries=0, ticks=0;
    bool write_response=false,done=false;
    while(!done) {
      check(++ticks<100000);
      // Every DMA wait and MMIO yield owns a stack continuation. Controller
      // cannot capture/load it or enter another call while the driver is parked.
      if(m.ar_valid() || m.aw_valid() || m.r_ready() || m.b_ready() || p.active_mmio) {
        auto before=m.save_checkpoint();
        reject([&] { owner.save_checkpoint(); }); reject([&] { owner.validate_checkpoint(good); });
        reject([&] { owner.load_checkpoint(good); });
        reject([&] { io.cpu_managed_axi4_read(0,nullptr,0); });
        reject([&] { io.cpu_managed_axi4_write(0,nullptr,0); });
        reject([&] { io.mmio_read(100); });
        check(m.save_checkpoint()==before); ++active_boundaries;
      }
      const bool ar=m.ar_valid(),aw=m.aw_valid(),w=m.w_valid();
      const bool r=m.r_ready() && read_left, b=m.b_ready() && write_response;
      std::vector<uint32_t> data(beat/4,0);
      if(r) for(unsigned i=0;i<beat;++i) reinterpret_cast<uint8_t *>(data.data())[i]=uint8_t((read_addr+i)*13+7);
      if(ar) {
        check(!read_left); read_addr=m.ar_addr(); read_left=m.ar_len()+1;
        driver.trace<<"AR "<<driver.index<<' '<<read_addr<<' '<<read_left<<'\n';
      }
      if(aw) {
        check(!write_left && !write_response); write_addr=m.aw_addr(); write_left=m.aw_len()+1;
        driver.trace<<"AW "<<driver.index<<' '<<write_addr<<' '<<write_left<<'\n';
      }
      if(w) {
        check(write_left && m.w_last()==(write_left==1));
        const auto *bytes=static_cast<const uint8_t *>(m.w_data());
        const size_t base=4096+driver.index*65536;
        for(unsigned i=0;i<beat;++i) check(bytes[i]==uint8_t(driver.index*17+write_addr-base+i));
        check(m.w_strb()==(beat==64 ? ~size_t(0) : (size_t(1)<<beat)-1));
        driver.trace<<"W "<<driver.index<<' '<<write_addr<<'\n';
        write_addr+=beat; if(!--write_left) write_response=true;
      }
      const bool last=r && read_left==1;
      m.tick(false,true,true,true,0,data,last,r,0,b);
      if(r) { read_addr+=beat; --read_left; }
      if(b) write_response=false;
      done=p.to_sim();
    }
    check(p.end()==0 && !read_left && !write_left && !write_response);
    check(owner.save_checkpoint()==good);
    driver.trace.close();
    std::cout<<"CPU_IO_PASS operations="<<operations-cut<<" active_boundaries="<<active_boundaries
             <<" rejections="<<rejects<<" target_edges=0\n";
    return 0;
  } catch(const std::exception &e) { std::cerr<<"CPU_IO_FAIL "<<e.what()<<'\n'; return 2; }
}
#ifdef CPU_IO_DPI
extern "C" int cpu_io_test(const char *m,const char *s,const char *d,unsigned c,unsigned b) { return execute(m,s,d,c,b); }
#else
int main(int argc,char **argv) { return argc==6 ? execute(argv[1],argv[2],argv[3],std::stoul(argv[4]),std::stoul(argv[5])) : 2; }
#endif
