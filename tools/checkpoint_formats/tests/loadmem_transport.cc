// Production TSI bridge + loadmem widget; only platform MMIO is a fixture.
#include "core/config.h"
#include "core/simif.h"
#include "bridges/tsibridge.h"
#include "fesvr/loadmem_read_transport.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a,d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }

static void check(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(message);
}
static const TargetConfig cfg{{4,64,32},{4,64,64},1,{},{},{0,0},"transport-component"};
static const LOADMEMWIDGET_struct lm{960,964,968,972,976,980,984,988,992};
static const TSIBRIDGEMODULE_struct ts{1024,1028,1032,1036,1040,1044,1048,1052,1056};
static uint32_t pattern(uint64_t address, unsigned mode) {
  if (mode==0) return 0;
  if (mode==2) return UINT32_MAX;
  const auto index=address/4;
  return index%3==0 ? 0 : uint32_t(0x81234567ULL+index*0x10203ULL);
}
struct mmio_t final : simif_t {
  unsigned chunk, mode=1, lane=0;
  uint64_t high=0, read_address=0, write_high=0, write_address=0, write_cursor=0;
  size_t calls=0, writes_left=0;
  bool bridge_mode=false, fail_mmio=false;
  std::ostream &trace;
  std::map<uint64_t,uint32_t> contents;
  std::vector<uint32_t> serial;
  mmio_t(unsigned chunk, std::ostream &trace) : simif_t(cfg),chunk(chunk),trace(trace) {}
  uint32_t word(uint64_t address) {
    auto it=contents.find(address);
    return it==contents.end()?pattern(address,mode):it->second;
  }
  void write(size_t address, uint32_t value) override {
    if (fail_mmio) throw std::runtime_error("platform callback fault");
    ++calls; trace<<"MMIO W "<<address<<' '<<value<<'\n';
    if(address==lm.R_ADDRESS_H) high=uint64_t(value)<<32;
    else if(address==lm.R_ADDRESS_L) {read_address=high|value;lane=0;}
    else if(address==lm.W_ADDRESS_H) write_high=uint64_t(value)<<32;
    else if(address==lm.W_ADDRESS_L) write_address=write_high|value;
    else if(address==lm.W_LENGTH) {writes_left=size_t(value)*chunk;write_cursor=write_address;}
    else if(address==lm.W_DATA) {
      check(writes_left>0,"write without request");
      contents[write_cursor]=value;write_cursor+=4;--writes_left;
    } else if(address==ts.in_bits) serial.push_back(value);
  }
  uint32_t read(size_t address) override {
    if (fail_mmio) throw std::runtime_error("platform callback fault");
    ++calls;
    uint32_t value=0;
    if(address==lm.R_DATA) {
      check(lane<chunk,"read beyond beat");value=word(read_address+4*lane++);
    } else if(bridge_mode && (address==ts.done||address==ts.in_ready)) value=1;
    else check(bridge_mode && address==ts.out_valid,"unexpected MMIO read");
    trace<<"MMIO R "<<address<<' '<<value<<'\n';return value;
  }
};
static void direct_cases(const std::filesystem::path &out) {
  std::ofstream trace(out/"direct.trace");check(bool(trace),"cannot open trace");
  unsigned cases=0,rejections=0;
  for(unsigned chunk:{1,2,4,16})
    for(unsigned mode:{0,1,2})
      for(size_t bytes:{4,8,12,64,128,1024,4096})
        for(unsigned lane:{0U,chunk-1})
          for(int64_t offset:{int64_t(0),int64_t(0x100004),int64_t(-0x80000000LL)}) {
            const uint64_t host=0x100000000ULL-16+lane*4;
            const uint64_t address=offset<0?host+uint64_t(-offset):host-uint64_t(offset);
            trace<<"CASE "<<chunk<<' '<<mode<<' '<<bytes<<' '<<address<<' '<<offset<<'\n';
            mmio_t io(chunk,trace);io.mode=mode;
            loadmem_t memory(io,lm,0,{},cfg.mem,chunk);
            size_t sent=0;
            firesim_read_loadmem(memory,address,bytes,offset,[&](uint32_t value) {
              const uint32_t expected=pattern(host+4*sent,mode);
              if(value!=expected) {
                trace<<"FIRST_DIVERGENCE response_word="<<sent<<" host_address="<<(host+4*sent)
                     <<" expected="<<expected<<" actual="<<value<<" acknowledged_words="<<sent<<'\n';
                trace.flush();throw std::runtime_error("incorrect response lane/order");
              }
              trace<<"SEND "<<value<<'\n';++sent;
            });
            check(sent==bytes/4,"incorrect response count");
            trace<<"END\n";++cases;
          }
  // Exact unsigned boundary and INT64_MIN translation without signed overflow.
  for(auto example:std::vector<std::pair<uint64_t,int64_t>>{
          {UINT64_MAX-7,0},{uint64_t(1)<<63,INT64_MIN}}) {
    trace<<"CASE 2 1 8 "<<example.first<<' '<<example.second<<'\n';
    mmio_t io(2,trace);loadmem_t memory(io,lm,0,{},cfg.mem,2);
    firesim_read_loadmem(memory,example.first,8,example.second,[&](uint32_t v){trace<<"SEND "<<v<<'\n';});
    trace<<"END\n";++cases;
  }
  auto reject=[&](unsigned chunk,uint64_t address,size_t bytes,int64_t offset) {
    std::ostringstream discarded;mmio_t io(chunk,discarded);
    loadmem_t memory(io,lm,0,{},cfg.mem,chunk);size_t sent=0;
    bool rejected=false;
    try {firesim_read_loadmem(memory,address,bytes,offset,[&](uint32_t){++sent;});}
    catch(const std::runtime_error &) {rejected=true;}
    check(rejected && io.calls==0 && sent==0,"invalid request performed IO");++rejections;
  };
  for(auto bytes:{0U,1U,3U,4097U,4100U}) reject(2,0x80000000,bytes,0);
  for(auto chunk:{0U,3U,1025U,2048U}) reject(chunk,0x80000000,8,0);
  reject(2,0x80000001,8,0);reject(2,UINT64_MAX-3,8,0);
  reject(2,4,8,-8);reject(2,4,8,INT64_MIN);
  reject(2,UINT64_MAX-7,8,8);reject(2,UINT64_MAX-11,8,8);
  reject(2,0x80000000,8,1);
  // Unwinding both MMIO and response callback failures must release GMP state.
  for(unsigned stage:{0,1}) {
    std::ostringstream discarded;mmio_t io(2,discarded);
    loadmem_t memory(io,lm,0,{},cfg.mem,2);
    bool failed=false;
    try {firesim_read_loadmem(memory,0x1000,4096,0,[&](uint32_t) {
      if(stage==0) throw std::runtime_error("response callback fault");
      io.fail_mmio=true; // next beat throws inside the platform callback
    });} catch(const std::runtime_error &) {failed=true;}
    check(failed,"injected callback did not fail");
  }
  trace.close();
  std::ofstream(out/"direct-result.txt")<<"CASES "<<cases<<" REJECTIONS "<<rejections<<" CALLBACK_FAILURES 2\n";
}
static void actual_bridge(const std::filesystem::path &out,const char *elf,unsigned chunk) {
  std::ofstream trace(out/("bridge-"+std::to_string(chunk)+".trace"));
  check(bool(trace),"cannot open bridge trace");
  mmio_t io(chunk,trace);io.bridge_mode=true;
  io.contents[0x1000]=0xaabbccdd;io.contents[0x1004]=0x11223344;
  loadmem_t memory(io,lm,0,{},cfg.mem,chunk);
  tsibridge_t bridge(io,memory,ts,0,{"+permissive","+fesvr-wait-ticks=0","+fesvr-step-size=128",
                                   "+permissive-off",elf},true,-0x80000000LL);
  check(bridge.checkpoint_schema().empty(),"incomplete TSI checkpoint enabled");
  const auto stem="bridge-"+std::to_string(chunk);
  auto snapshot=[&](unsigned cut) {
    const auto before=io.calls;
    auto image=bridge.control_owner().save_checkpoint();
    bridge.control_owner().validate_checkpoint(image);
    check(before==io.calls,"control capture/validation executed MMIO");
    std::ofstream owner(out/(stem+"-control-"+std::to_string(cut)+".owner"),std::ios::binary);
    owner.write(reinterpret_cast<const char *>(image.data()),image.size());
    check(bool(owner),"cannot write actual bridge owner");
  };
  snapshot(0);
  bridge.init();
  snapshot(1);
  for(unsigned tick=0;tick<4;++tick) {
    trace<<"TICK "<<tick<<'\n';bridge.tick();
    snapshot(tick+2);
  }
  for(unsigned i=0;i<4;++i) {
    const uint32_t value=(4*i)|((4*i+1)<<8)|((4*i+2)<<16)|((4*i+3)<<24);
    check(io.contents[4*i]==value,"changed ELF initial write");
  }
  check(io.contents[0x1000]==0xaabbccdd && io.contents[0x1004]==0x77665544,"lost ELF merged write");
  check(io.serial==std::vector<uint32_t>({1,0x02000000,0,0,0,1}),"changed reset serial request");
  check(!bridge.terminate(),"changed HTIF lifecycle");
  std::ofstream(out/("bridge-"+std::to_string(chunk)+"-result.txt"))
    <<"REAL_BRIDGE chunk="<<chunk<<" merged_bytes=8 reset_words=6 ticks=4 unsupported_checkpoint=1\n";
}
static int run(const char *elf,const char *destination) {
  try {
    std::filesystem::path out(destination);std::filesystem::create_directories(out);
    direct_cases(out);actual_bridge(out,elf,1);actual_bridge(out,elf,2);
    std::cout<<"PASS production loadmem transport\n";return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef LOADMEM_TRANSPORT_DPI
extern "C" int loadmem_transport(const char *elf,const char *out) {
  const auto status=run(elf,out);
  // VCS may return success for $fatal. Preserve a nonzero process exit for
  // transport faults, after C++ stack/buffer cleanup has completed.
  if(status) std::exit(status);
  return status;
}
#else
int main(int argc,char **argv) {check(argc==3,"elf/out required");return run(argv[1],argv[2]);}
#endif
