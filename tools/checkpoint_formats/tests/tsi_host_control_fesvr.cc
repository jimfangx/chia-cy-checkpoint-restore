// Installed-FESVR caller integration: suspended child reset and real HTIF
// tohost polling. No CPU or complete HTIF checkpoint restore is claimed.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>
namespace fs=std::filesystem;
static void require(bool b,const char *s) {if(!b) throw std::runtime_error(s);}
static void serial_snapshot(firesim_tsi_t &tsi,const fs::path &out,const std::string &name) {
  auto bytes=tsi.serial_queue_owner().save_checkpoint();
  std::ofstream f(out/(name+".serial"),std::ios::binary);
  f.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());require(bool(f),"cannot save serial owner");
  auto read=tsi.serial_read_owner().save_checkpoint();
  std::ofstream r(out/(name+".read"),std::ios::binary);
  r.write(reinterpret_cast<const char *>(read.data()),read.size());require(bool(r),"cannot save serial read owner");
}
static void snapshot(firesim_tsi_t &tsi,const fs::path &out,const std::string &name) {
  auto bytes=tsi.host_control_owner().save_checkpoint();
  std::ofstream f(out/(name+".host"),std::ios::binary);
  f.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());require(bool(f),"cannot save owner");
  serial_snapshot(tsi,out,name);
}
static void serial(firesim_tsi_t &tsi,const std::vector<uint32_t> &expected,const fs::path &out,const std::string &name) {
  serial_snapshot(tsi,out,name+"-queued");
  size_t index=0;
  for(auto word:expected) {
    require(tsi.data_available() && tsi.in_valid() && tsi.in_bits()==word && tsi.recv_word()==word,"serial reset/poll word differs");
    serial_snapshot(tsi,out,name+"-pop-"+std::to_string(index++));
  }
  require(!tsi.data_available(),"extra serial word");
}
static int run(const char *elf,const char *destination,const char *count_text) {
  try {
    const unsigned count=std::stoul(count_text);require(count && count<=10,"bad count");
    fs::path out(destination);fs::create_directories(out);
    std::string name="host-integration",payload=elf,first="+idle-counts=1",
      last="+idle-counts="+std::to_string(count),init="+init_read=0x10000010",no_msip="+no_hart0_msip",
      permissive="+permissive",off="+permissive-off";
    char *argv[]={name.data(),permissive.data(),first.data(),last.data(),init.data(),no_msip.data(),off.data(),payload.data()};
    firesim_tsi_t tsi(8,argv,true);snapshot(tsi,out,"constructed");
    tsi.tick();tsi.tick();
    firesim_loadmem_t request;
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
    std::array<uint8_t,16> initial{};tsi.recv_loadmem_data(initial.data(),16);
    for(size_t i=0;i<16;++i) require(initial[i]==i,"ELF data differs");
    tsi.tick();require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF read differs");
    tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
    std::array<uint32_t,2> merged{};tsi.recv_loadmem_data(merged.data(),8);
    require(merged[0]==0xaabbccdd && merged[1]==0x77665544,"ELF merge bytes differ");
    snapshot(tsi,out,"reset-wait");tsi.set_loaded_in_target(true);tsi.tick();
    serial(tsi,{0,0x10000010,0,0,0},out,"init");snapshot(tsi,out,"reset-child");
    for(unsigned i=0;i<3;++i) {tsi.tick();snapshot(tsi,out,"child-wait-"+std::to_string(i));}
    tsi.send_word(0x89abcdef);serial_snapshot(tsi,out,"init-response");
    tsi.tick();serial(tsi,{0,0x80002000,0,1,0},out,"first");
    snapshot(tsi,out,"first-poll");
    require(!tsi.busy() && tsi.loaded_in_host(),"first poll flags differ");
    for(unsigned loop=0;loop<3;++loop) {
      // Complete both halves of the original serial read. The final half
      // resumes HTIF's real idle callback rather than a fixture invocation.
      tsi.send_word(0);serial_snapshot(tsi,out,"poll-response-"+std::to_string(loop)+"-0");
      tsi.tick();snapshot(tsi,out,"poll-half-"+std::to_string(loop));
      tsi.send_word(0);serial_snapshot(tsi,out,"poll-response-"+std::to_string(loop)+"-1");
      tsi.tick();snapshot(tsi,out,"idle-"+std::to_string(loop)+"-0");
      for(unsigned yield=1;yield<count;++yield) {
        tsi.tick();snapshot(tsi,out,"idle-"+std::to_string(loop)+"-"+std::to_string(yield));
      }
      tsi.tick();serial(tsi,{0,0x80002000,0,1,0},out,"busy-"+std::to_string(loop));snapshot(tsi,out,"busy-poll-"+std::to_string(loop));
      require(tsi.busy() && tsi.loaded_in_host() && !tsi.done(),"busy HTIF poll differs");
    }
    std::cout<<"REAL_HTIF_HOST_CONTROL idle_count="<<count<<" child_waits=3 poll_loops=3 serial_words=25\n";return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HOST_FESVR_DPI
extern "C" int tsi_host_fesvr(const char *elf,const char *out,const char *count) {return run(elf,out,count);}
extern "C" void tsi_host_fesvr_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=4) return 2;return run(argv[1],argv[2],argv[3]);}
#endif
