// Production blocking MMIO transport; synthetic AXI peer, not a CPU checkpoint.
#include "emul/simif_emul.h"
#include "core/simulation.h"
#include "bridges/master.h"
#include "bridges/clock.h"
#include <filesystem>
#include <fstream>
#include <functional>

namespace fs = std::filesystem;
static uint64_t now=1000000;
midas_time_t timestamp() { return now+=100; }
double diff_secs(midas_time_t a,midas_time_t b) { return double(a-b)/1000000; }
static void check(bool b) { if(!b) throw std::runtime_error("MMIO IO assertion"); }
static unsigned rejects=0;
static void reject(const std::function<void()> &fn) {
  try { fn(); } catch(const std::runtime_error &) { ++rejects; return; }
  throw std::runtime_error("MMIO IO accepted unsupported state");
}
static void save(const fs::path &p,const std::vector<uint8_t> &v) {
  std::ofstream f(p,std::ios::binary); f.write(reinterpret_cast<const char *>(v.data()),v.size()); check(bool(f));
}
static std::vector<uint8_t> load(const fs::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
static const TargetConfig configs[]={
  {{12,32,32},{16,34,64},1,AXI4Config{16,64,512},{},{0,0},"mmio-io-fixture"},
  {{4,32,32},{16,34,64},1,AXI4Config{16,64,512},{},{0,0},"mmio-io-fixture"}};
static constexpr unsigned operations=12;
static uint64_t address(unsigned op) { return op==11 ? 0xfffffffc : 0x100+op*4; }
static uint32_t response(uint64_t addr) { return uint32_t(addr*0x10203+0xfedcba98); }
static uint32_t write_data(unsigned op) { return 0xf0000000u+op*0x10203; }
struct platform_t : simif_emul_t {
  uint64_t ticks=0;
  explicit platform_t(unsigned delay,unsigned geometry=0)
    : simif_emul_t(configs[geometry],{"+memsize=4096","+fuzz-host-timing="+std::to_string(delay),"+fuzz-seed=165"}) {}
  // Fixture initialization and clock sampling only. Workload accesses below
  // explicitly use the production read/write, including its AXI queues.
  uint32_t read(size_t addr) override {
    if(addr<100) return addr==0 ? 1 : addr==4 ? 0x46697265 : 23;
    return simif_emul_t::read(addr);
  }
  void write(size_t addr,uint32_t data) override { if(addr>=100) simif_emul_t::write(addr,data); }
  checkpoint_owner_t &owner() { auto p=checkpoint_mmio_io_owner(); check(p.first=="runtime/mmio-io"); return *p.second; }
  std::vector<std::pair<std::string,checkpoint_owner_t *>> owners() {
    return {{"io",&owner()},{"axi",master.get()},{"timing",checkpoint_host_timing_owner().second},
            {"stream",checkpoint_stream_io_owners().at(0).second},{"dma",get_cpu_managed_axi4()}};
  }
  void snapshot(const fs::path &out,const std::string &prefix) {
    for(auto &[name,p] : owners()) save(out/(prefix+"."+name),p->save_checkpoint());
    std::ofstream(out/(prefix+".ticks"))<<ticks<<'\n';
  }
};
struct driver_t : simulation_t {
  platform_t &p; fs::path out; std::ofstream trace; unsigned index;
  driver_t(widget_registry_t &r,platform_t &p,const fs::path &out,unsigned cut)
    : simulation_t(r,{}),p(p),out(out),trace(out/"trace"),index(cut) { check(bool(trace)); }
  int simulation_run() override {
    for(;index<operations;++index) {
      p.snapshot(out,"cut-"+std::to_string(index));
      trace<<"OP "<<index<<' '<<p.ticks<<'\n';
      if(index%2==0) p.simif_emul_t::write(address(index),write_data(index));
      else {
        uint32_t data=index%3==0 ? p.get_cpu_managed_stream_io().mmio_read(address(index)) : p.simif_emul_t::read(address(index));
        check(data==response(address(index)));
      }
      trace<<"RETURN "<<index<<' '<<p.ticks<<'\n';
    }
    p.snapshot(out,"final"); return 0;
  }
};
static int execute(const char *mode,const char *source,const char *dest,unsigned cut,unsigned delay) {
  try {
    platform_t p(delay); auto &owner=p.owner();
    check(owner.checkpoint_schema()=="firesim.emul.mmio-io.returned.v1");
    const auto good=owner.save_checkpoint(),axi=p.master->save_checkpoint();
    const auto good_group=p.save_checkpoint_io();
    auto pending_group=p.prepare_checkpoint_io(good_group);
    const fs::path out(dest); fs::create_directories(out);
    if(std::string(mode)=="negative") {
      for(size_t n=0;n<good.size();++n) reject([&] { owner.load_checkpoint({good.begin(),good.begin()+n}); });
      for(size_t n=0;n<good.size();++n) {
        auto bad=good; bad[n]^=1; reject([&] { owner.validate_checkpoint(bad); }); reject([&] { owner.load_checkpoint(bad); });
      }
      auto bad=good; bad.push_back(0); reject([&] { owner.load_checkpoint(bad); });
      platform_t other(delay,1); reject([&] { other.owner().load_checkpoint(good); });
      check(owner.save_checkpoint()==good && p.master->save_checkpoint()==axi);
      for(bool write : {false,true}) {
        platform_t broken(delay); auto before=broken.master->save_checkpoint();
        reject([&] { if(write) broken.simif_emul_t::write(0x100000000,0x1234); else broken.simif_emul_t::read(0x100000000); });
        reject([&] { broken.owner().save_checkpoint(); }); reject([&] { broken.owner().validate_checkpoint(good); });
        reject([&] { broken.owner().load_checkpoint(good); });
        reject([&] { broken.simif_emul_t::read(0x100); }); reject([&] { broken.simif_emul_t::write(0x100,0); });
        check(broken.master->save_checkpoint()==before);
      }
      std::cout<<"MMIO_IO_NEGATIVE rejected="<<rejects<<" partial_publication=0 target_edges=0\n"; return 0;
    }
    if(std::string(mode)=="restore") {
      auto image=p.save_checkpoint_io();
      // The production transaction owns all five runtime I/O components.
      const std::vector<std::string> names{"io","axi","stream","dma","timing"};
      check(image.owners.size()==names.size());
      for(size_t i=0;i<names.size();++i)
        image.owners[i].payload=load(fs::path(source)/("cut-"+std::to_string(cut)+"."+names[i]));
      auto prepared=p.prepare_checkpoint_io(image);
      p.publish_checkpoint_io(*prepared);
      std::ifstream(fs::path(source)/("cut-"+std::to_string(cut)+".ticks"))>>p.ticks;
      p.snapshot(out,"readback");
      for(auto &[name,pointer] : p.owners()) check(pointer->save_checkpoint()==load(fs::path(source)/("cut-"+std::to_string(cut)+"."+name)));
      check(p.ticks>0); --p.ticks; // Fixture startup's single do_tick, no AXI or PRNG use.
      std::cout<<"MMIO_IO_PREEDGE_READBACK owners=5 target_edges=0\n";
    }
    // Use the current generation so suspended-call denial cannot be satisfied
    // merely by an already invalidated candidate from before the restore.
    pending_group=p.prepare_checkpoint_io(p.save_checkpoint_io());
    widget_registry_t registry;
    registry.add_widget(new master_t(p,{0,4,8},0,{}));
    registry.add_widget(new clockmodule_t(p,{16,20,24,28,32,36},0,{}));
    driver_t driver(registry,p,out,cut); p.start_driver(driver);
    auto &m=*p.master;
    bool read_pending=false,aw_seen=false,w_seen=false;
    uint64_t read_addr=0,write_addr=0,read_due=0,write_due=0;
    unsigned active=0,stream_active=0,queued=0,inflight=0;
    bool done=false;
    while(!done) {
      check(++p.ticks<10000);
      // Both contexts are parked at the dispatcher handoff. Try all owner
      // hooks and reentry before submitting another synthetic peer tick.
      if(m.ar_valid() || m.aw_valid() || m.r_ready() || m.b_ready()) {
        const auto before=m.save_checkpoint();
        reject([&] { owner.save_checkpoint(); }); reject([&] { owner.validate_checkpoint(good); });
        reject([&] { owner.load_checkpoint(good); });
        reject([&] { p.save_checkpoint_io(); });
        reject([&] { p.prepare_checkpoint_io(good_group); });
        reject([&] { p.publish_checkpoint_io(*pending_group); });
        reject([&] { p.seal_checkpoint_io(*pending_group); });
        reject([&] { p.simif_emul_t::read(0x100); }); reject([&] { p.simif_emul_t::write(0x100,0); });
        check(m.save_checkpoint()==before); ++active;
        if(m.ar_valid() || m.aw_valid()) ++queued;
        if(m.r_ready() || m.b_ready()) ++inflight;
        if(driver.index%2 && driver.index%3==0) {
          auto *stream=p.owners().at(3).second;
          const auto image=load(out/("cut-"+std::to_string(driver.index)+".stream"));
          reject([&] { stream->save_checkpoint(); }); reject([&] { stream->validate_checkpoint(image); });
          reject([&] { stream->load_checkpoint(image); }); ++stream_active;
        }
      }
      const bool ar=m.ar_valid() && p.ticks%3==2, aw=m.aw_valid() && p.ticks%4==1;
      const bool w=m.w_valid() && p.ticks%5==3;
      const bool r=m.r_ready() && read_pending && p.ticks>=read_due && p.ticks%2==0;
      const bool b=m.b_ready() && aw_seen && w_seen && p.ticks>=write_due && p.ticks%2;
      if(ar) { check(!read_pending); read_pending=true; read_addr=m.ar_addr(); read_due=p.ticks+3;
        check(m.ar_id()==0 && m.ar_size()==2 && m.ar_len()==0);
        driver.trace<<"AR "<<p.ticks<<' '<<read_addr<<'\n'; }
      if(aw) { check(!aw_seen); aw_seen=true; write_addr=m.aw_addr(); write_due=p.ticks+4;
        check(m.aw_id()==0 && m.aw_size()==2 && m.aw_len()==0);
        driver.trace<<"AW "<<p.ticks<<' '<<write_addr<<'\n'; }
      if(w) { check(!w_seen && m.w_strb()==15 && m.w_last()); w_seen=true;
        uint32_t data; memcpy(&data,m.w_data(),4); check(data==write_data(driver.index));
        driver.trace<<"W "<<p.ticks<<' '<<data<<'\n'; }
      if(r) driver.trace<<"R "<<p.ticks<<' '<<response(read_addr)<<'\n';
      if(b) driver.trace<<"B "<<p.ticks<<'\n';
      m.tick(false,ar,aw,w,0,{response(read_addr)},true,r,0,b);
      if(r) read_pending=false;
      if(b) aw_seen=w_seen=false;
      done=p.to_sim();
    }
    check(p.end()==0 && !read_pending && !aw_seen && !w_seen);
    check(owner.save_checkpoint()==good); driver.trace.close();
    std::cout<<"MMIO_IO_PASS operations="<<operations-cut<<" active="<<active<<" stream_active="<<stream_active
             <<" queued="<<queued<<" inflight="<<inflight<<" rejections="<<rejects<<" target_edges=0\n";
    return 0;
  } catch(const std::exception &e) { std::cerr<<"MMIO_IO_FAIL "<<e.what()<<'\n'; return 2; }
}
#ifdef MMIO_IO_DPI
extern "C" int mmio_io_test(const char *m,const char *s,const char *d,unsigned c,unsigned b) { return execute(m,s,d,c,b); }
#else
int main(int argc,char **argv) { return argc==6 ? execute(argv[1],argv[2],argv[3],std::stoul(argv[4]),std::stoul(argv[5])) : 2; }
#endif
