// An actual installed syscall/memif child yields inside HTIF dispatch.
#include "tsi_polling_cut_checks.h"
#include <array>
static void require(bool value,const char *message) { if (!value) throw std::runtime_error(message); }
static void packet(firesim_tsi_t &tsi,const std::vector<uint32_t> &expected) {
  for (auto word:expected) require(tsi.data_available() && tsi.recv_word()==word,"active syscall packet differs");
  require(!tsi.data_available(),"extra active syscall serial word");
}
static int run(const char *source,const char *destination) {
  try {
    std::filesystem::path out(destination);std::filesystem::create_directories(out);
    std::vector<std::string> args{"active-service","+permissive","+no_hart0_msip","+permissive-off",source};
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    polling_cut_check(tsi,out,"unstarted",false);
    tsi.tick();polling_cut_check(tsi,out,"loader-entry",false);tsi.tick();
    firesim_loadmem_t request;std::array<uint8_t,16> bytes{};
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"wrong ELF write");
    tsi.recv_loadmem_data(bytes.data(),16);tsi.tick();
    require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"wrong ELF merge read");
    polling_cut_check(tsi,out,"loader-memif",false);
    tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"wrong ELF merge write");
    tsi.recv_loadmem_data(bytes.data(),8);
    polling_cut_check(tsi,out,"reset-wait",false);
    tsi.set_loaded_in_target(true);tsi.tick();packet(tsi,{0,0x80002000,0,1,0});
    polling_cut_check(tsi,out,"first-poll",true);
    // Device 0, command 0, even payload: real proxied syscall, not PASS.
    tsi.send_word(0x80003000);tsi.send_word(0);tsi.tick();
    packet(tsi,{1,0x80002000,0,1,0,0,0, 0,0x80003000,0,15,0});
    polling_cut_check(tsi,out,"active-syscall-pending",false);
    tsi.send_word(93);tsi.tick();
    polling_cut_check(tsi,out,"active-syscall-partial",false);
    for (unsigned i=1;i<16;++i) tsi.send_word(0);
    tsi.tick();
    std::vector<uint32_t> expected{1,0x80003000,0,15,0};expected.resize(21,0);
    expected.insert(expected.end(),{0,0x80002008,0,1,0});packet(tsi,expected);
    polling_cut_check(tsi,out,"syscall-returned",true);
    tsi.send_word(0);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002008,0,1,0,1,0});
    polling_cut_check(tsi,out,"complete",false);
    require(tsi.done() && tsi.exit_code()==0,"installed sys_exit did not complete");
    std::cout << "ACTUAL_ACTIVE_SYSCALL_REJECTIONS count=2 returned_components=8 terminal_exit=0 cpu_edges=0\n";
    return 0;
  } catch(const std::exception &error) {std::cerr<<"FAIL "<<error.what()<<'\n';return 2;}
}
#ifdef TSI_ACTIVE_SERVICE_DPI
extern "C" int tsi_active_service(const char *s,const char *o) {return run(s,o);}
extern "C" void tsi_active_service_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=3)return 2;return run(argv[1],argv[2]);}
#endif
