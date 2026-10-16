// Exercise actual ordinary HTIF/BCD dispatch; component images do not resume HTIF.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
static void require(bool b,const char *s){if(!b)throw std::runtime_error(s);}
static auto bytes(const fs::path &p){std::ifstream f(p,std::ios::binary);require(bool(f),"missing image");return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});}
static void save(const fs::path &p,const std::vector<uint8_t> &b){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"save failed");}
static int run(const char *mode,const char *elf,const char *input,const char *plan,
               const char *destination,const char *flush,const char *source) {
  try {
    const fs::path out(destination);fs::create_directories(out);
    if(std::string(mode)=="readback") {
      firesim_tsi_memif_write_t w;firesim_tsi_serial_state_t q;
      firesim_tsi_bcd_identity_t caller(w,q);
      const auto a=bytes(std::string(source)+".write"),b=bytes(std::string(source)+".serial");
      caller.load_components({{"identity",bytes(std::string(source)+".identity")},{"write",a},{"serial",b}});
      save(out/"preedge.identity",caller.save_checkpoint());
      save(out/"preedge.write",w.save_checkpoint());save(out/"preedge.serial",q.save_checkpoint());
      firesim_tsi_htif_poll_t poll(0x80002000,0x80002008);
      poll.load_checkpoint(bytes(std::string(source)+".poll"));
      save(out/"preedge.poll",poll.save_checkpoint());
      std::cout<<"COMPLETE_CHILD_READBACK context_entries=0 target_services=0 target_edges=0\n";return 0;
    }
    std::vector<std::string> args{"memif-identity","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-terminal-input="+std::string(input),"+cflush_addr=0x"+std::string(flush),"+permissive-off",elf};
    std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    tsi.tick();tsi.tick();firesim_loadmem_t request;std::array<uint8_t,16> data{};
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
    tsi.recv_loadmem_data(data.data(),16);tsi.tick();
    require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF read differs");
    tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
    tsi.recv_loadmem_data(data.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
    firesim_tsi_memif_write_t idle;
    const auto idle_image=idle.save_checkpoint();size_t cut=0,active=0,guards=0;
    auto snapshot=[&] {
      const auto image=tsi.memif_write_owner().save_checkpoint();
      const bool busy=image!=idle_image;
      bool rejected=false;try{tsi.inspect_polling_cut();}catch(const std::runtime_error &){rejected=true;}
      require(rejected==busy,"active memif caller passed as an ordinary polling cut");
      if(busy){++active;require(!tsi.done(),"active identity exited");++guards;}
      save(out/("cut-"+std::to_string(cut)+".write"),image);
      save(out/("cut-"+std::to_string(cut)+".identity"),tsi.bcd_identity_owner().save_checkpoint());
      save(out/("cut-"+std::to_string(cut)+".serial"),tsi.serial_queue_owner().save_checkpoint());
      // This read must now succeed even while the identity child is blocked:
      // dispatch returned through both guards before the host context yielded.
      save(out/("cut-"+std::to_string(cut)+".poll"),tsi.htif_poll_owner().save_checkpoint());
    };
    snapshot();std::ifstream steps(plan);require(bool(steps),"missing plan");std::string line;
    while(std::getline(steps,line)) {
      std::istringstream in(line);std::string op;uint64_t n;in>>op;
      if(op=="TICK")tsi.tick();
      else if(op=="SEND"){in>>n;tsi.send_word(n);}
      else if(op=="PACKET") {
        while(in>>n)require(tsi.data_available() && tsi.in_bits()==n && tsi.recv_word()==n,"production identity packet differs");
      } else throw std::runtime_error("unknown operation");
      ++cut;snapshot();
    }
    // Finish the ordinary installed HTIF; do not discard a suspended caller.
    while(tsi.data_available())tsi.recv_word();
    tsi.send_word(1);tsi.send_word(0);tsi.tick();
    require(tsi.done() && tsi.exit_code()==0,"ordinary source did not exit");
    std::cout<<"ACTUAL_IDENTITY cuts="<<cut+1<<" active_child_cuts="<<active<<" polling_guards="<<guards
             <<" source_exit=0 cpu_edges=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_MEMIF_IDENTITY_DPI
extern "C" int tsi_memif_identity(const char *m,const char *e,const char *i,const char *p,const char *o,const char *f,const char *s){return run(m,e,i,p,o,f,s);}
extern "C" void tsi_memif_identity_exit(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
