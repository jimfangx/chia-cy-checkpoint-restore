// Actual linked FESVR/TestChip/FireSim program-loading coroutine. This verifies
// the new operation owner at real suspended calls; it does not restore HTIF.
#include "fesvr/firesim_tsi.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <array>

static void require(bool test,const char *message) {
  if(!test) throw std::runtime_error(message);
}
static void queue_snapshot(const firesim_tsi_t &tsi,const std::filesystem::path &out,const std::string &name) {
  auto bytes=tsi.loadmem_queue_owner().save_checkpoint();
  std::ofstream file(out/(name+".queues"),std::ios::binary);
  file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
  require(bool(file),"cannot save real queue owner");
}
static void snapshot(const firesim_tsi_t &tsi,const std::filesystem::path &out,int index) {
  auto bytes=tsi.loadmem_read_owner().save_checkpoint();
  std::ofstream file(out/ ("suspended-"+std::to_string(index)+".owner"),std::ios::binary);
  file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
  require(bool(file),"cannot save real suspended owner");
  queue_snapshot(tsi,out,"suspended-"+std::to_string(index));
  auto control=tsi.host_control_owner().save_checkpoint();
  std::ofstream host(out/("suspended-"+std::to_string(index)+".host"),std::ios::binary);
  host.write(reinterpret_cast<const char *>(control.data()),control.size());
  require(bool(host),"cannot save real host control");
  auto loader=tsi.program_loader_owner().save_checkpoint();
  std::ofstream program(out/("suspended-"+std::to_string(index)+".program"),std::ios::binary);
  program.write(reinterpret_cast<const char *>(loader.data()),loader.size());
  require(bool(program),"cannot save real program loader");
}
static int run(const char *elf,const char *destination) {
  try {
    std::filesystem::path out(destination); std::filesystem::create_directories(out);
    std::string name="integration", payload=elf;
    char *argv[]={name.data(),payload.data()};
    firesim_tsi_t tsi(2,argv,true);
    snapshot(tsi,out,0);
    tsi.tick(); // original program-load yield
    snapshot(tsi,out,1);
    require(!tsi.has_loadmem_reqs() && !tsi.loaded_in_host(),"load advanced before original yield");
    tsi.tick(); // writes queued; read is waiting for their drain
    snapshot(tsi,out,2);
    firesim_loadmem_t request;
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,
            "changed first ELF write");
    queue_snapshot(tsi,out,"write0-popped");
    std::array<unsigned char,16> initial{};
    tsi.recv_loadmem_data(initial.data(),1);
    queue_snapshot(tsi,out,"write0-partial");
    tsi.recv_loadmem_data(initial.data()+1,initial.size()-1);
    for(size_t i=0;i<initial.size();++i) require(initial[i]==i,"changed aligned ELF payload");
    require(!tsi.recv_loadmem_read_req(request),"read overtook pending writes");
    tsi.tick();
    snapshot(tsi,out,3);
    require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,
            "changed unaligned ELF read");
    tsi.send_loadmem_word(0xaabbccdd);
    queue_snapshot(tsi,out,"response-queued");
    tsi.tick();
    snapshot(tsi,out,4);
    require(!tsi.loaded_in_host() && !tsi.has_loadmem_reqs(),"partial read completed loading");
    tsi.send_loadmem_word(0x11223344);
    tsi.tick();
    snapshot(tsi,out,5);
    require(tsi.loaded_in_host(),"complete read did not resume original loader");
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,
            "changed merged ELF write");
    queue_snapshot(tsi,out,"write1-popped");
    std::array<uint32_t,2> merged{};
    tsi.recv_loadmem_data(merged.data(),sizeof(merged));
    require(merged[0]==0xaabbccdd && merged[1]==0x77665544,"lost partial read/ELF merge bytes");
    require(!tsi.has_loadmem_reqs() && !tsi.data_available(),"duplicate request before reset drain");
    for(int i=0;i<2;++i) {
      tsi.tick();
      auto bytes=tsi.host_control_owner().save_checkpoint();
      std::ofstream file(out/("reset-wait-"+std::to_string(i)+".host"),std::ios::binary);
      file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
      require(bool(file) && tsi.loaded_in_host() && !tsi.busy(),"changed repeated reset wait");
    }
    tsi.set_loaded_in_target(true); tsi.tick();
    snapshot(tsi,out,6);
    std::array<uint32_t,6> msip{1,0x02000000,0,0,0,1};
    for(auto expected:msip) require(tsi.data_available() && tsi.recv_word()==expected,"changed reset serial word");
    require(!tsi.data_available() && !tsi.done(),"changed actual HTIF idle/reset lifecycle");
    for(int i=1;i<=25;++i) {
      tsi.tick();
      auto bytes=tsi.host_control_owner().save_checkpoint();
      std::ofstream file(out/("idle-yield-"+std::to_string(i)+".host"),std::ios::binary);
      file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
      require(bool(file) && tsi.loaded_in_host() && !tsi.busy() && !tsi.data_available() && !tsi.done(),
              "changed actual no-tohost idle loop");
    }
    std::cout<<"REAL_FESVR_HOST_CONTROL reset_waits=2 idle_yields=26 host_images=34\n";
    std::cout<<"REAL_FESVR_LOADMEM_READ partial_words=1 merged_bytes=8 reset_words=6 suspended_cuts=7\n";
    return 0;
  } catch(const std::exception &error) { std::cerr<<"FAIL "<<error.what()<<"\n"; return 2; }
}
#ifdef FIRESIM_TSI_LOADMEM_DPI
extern "C" int firesim_tsi_loadmem_integration(const char *elf,const char *out) {return run(elf,out);}
#else
int main(int argc,char **argv) {require(argc==3,"elf/out required");return run(argv[1],argv[2]);}
#endif
