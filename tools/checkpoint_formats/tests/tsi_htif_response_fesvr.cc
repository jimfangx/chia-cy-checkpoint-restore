// Actual BCD callback and fromhost queue in the production HTIF dispatcher.
// No CPU execution or complete HTIF checkpoint is implied.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include "tsi_polling_cut_checks.h"
namespace fs=std::filesystem;
static void require(bool b,const char *s) { if (!b) throw std::runtime_error(s); }
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"save failed");
}
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p,std::ios::binary);require(bool(f),"missing image");
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
static void snapshot(firesim_tsi_t &tsi,const fs::path &out,const std::string &name) {
  polling_cut_check(tsi,out,name,name!="complete");
  save(out/(name+".poll"),tsi.htif_poll_owner().save_checkpoint());
  save(out/(name+".serial"),tsi.serial_queue_owner().save_checkpoint());
  save(out/(name+".read"),tsi.serial_read_owner().save_checkpoint());
  save(out/(name+".host"),tsi.host_control_owner().save_checkpoint());
}
static void packet(firesim_tsi_t &tsi,std::initializer_list<uint32_t> words) {
  for (auto word:words) require(tsi.data_available() && tsi.recv_word()==word,"production serial packet differs");
  require(!tsi.data_available(),"extra production serial word");
}
static int run(const char *mode,const char *source,const char *destination) {
  try {
    fs::path out(destination);fs::create_directories(out);
    if (std::string(mode)=="readback") {
      firesim_tsi_htif_poll_t owner(0x80002000,0x80002008);
      owner.load_checkpoint(read(source));save(out/"preedge.poll",owner.save_checkpoint());
      std::cout<<"COMPLETE_ACTUAL_RESPONSE_READBACK target_edges=0 context_entries=0 services=0\n";return 0;
    }
    require(std::string(mode)=="capture","bad response mode");
    // BCD uses canonical_terminal_t on fd 0. Bind deterministic input before
    // any command is dispatched and verify that it is consumed exactly once.
    save(out/"input.bin",{'A'});
    int input=::open((out/"input.bin").c_str(),O_RDONLY);require(input>=0,"cannot open BCD input");
    require(::dup2(input,0)==0,"cannot bind BCD input");::close(input);
    std::string name="response-fesvr",permissive="+permissive",no_msip="+no_hart0_msip",off="+permissive-off",elf=source;
    char *argv[]={name.data(),permissive.data(),no_msip.data(),off.data(),elf.data()};
    firesim_tsi_t tsi(5,argv,true);tsi.tick();tsi.tick();
    firesim_loadmem_t request;std::array<uint8_t,16> initial{};
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
    tsi.recv_loadmem_data(initial.data(),initial.size());
    for (size_t i=0;i<16;++i) require(initial[i]==i,"ELF bytes differ");
    tsi.tick();require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF partial read differs");
    tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
    std::array<uint32_t,2> merged{};tsi.recv_loadmem_data(merged.data(),8);
    require(merged[0]==0xaabbccdd && merged[1]==0x77665544,"ELF merged bytes differ");
    tsi.set_loaded_in_target(true);tsi.tick();packet(tsi,{0,0x80002000,0,1,0});
    snapshot(tsi,out,"tohost-read");
    // Device 1 / command 0: BCD read. Its installed tick() calls the actual
    // retained command callback with 0x100|'A', then removes that command.
    tsi.send_word(0);tsi.send_word(0x01000000);tsi.tick();
    packet(tsi,{1,0x80002000,0,1,0,0,0, 0,0x80002008,0,1,0});
    snapshot(tsi,out,"fromhost-pending");
    require(::lseek(0,0,SEEK_CUR)==1,"BCD input was not consumed once");
    tsi.send_word(0);tsi.tick();snapshot(tsi,out,"fromhost-half");
    tsi.send_word(0);tsi.tick();
    packet(tsi,{1,0x80002008,0,1,0,0x141,0x01000000, 0,0x80002000,0,1,0});
    snapshot(tsi,out,"next-poll");
    // The installed syscall pass/fail handler still runs after the callback.
    tsi.send_word(1);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002000,0,1,0,0,0});
    require(tsi.done() && tsi.exit_code()==0,"installed pass command did not terminate");
    snapshot(tsi,out,"complete");
    require(::lseek(0,0,SEEK_CUR)==1,"BCD input consumed twice");
    std::cout<<"REAL_FESVR_HTIF_RESPONSE bcd_input_bytes=1 callback=72057594037928257 fromhost_writes=1 terminal_exit=0 cuts=5\n";
    return 0;
  } catch (const std::exception &e) { std::cerr<<"FAIL "<<e.what()<<'\n';return 2; }
}
#ifdef TSI_HTIF_RESPONSE_DPI
extern "C" int tsi_htif_response(const char *m,const char *s,const char *o) {return run(m,s,o);}
extern "C" void tsi_htif_response_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=4)return 2;return run(argv[1],argv[2],argv[3]);}
#endif
