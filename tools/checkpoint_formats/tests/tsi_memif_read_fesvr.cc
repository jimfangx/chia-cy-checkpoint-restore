// Production virtual memif binding through actual installed syscall_t::sys_write.
// Only reader/FIFO components are restored; syscall/fd/context remain unowned.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <tuple>
#include <cstdlib>
#include <fcntl.h>
#include <unistd.h>
namespace fs = std::filesystem;
static void require(bool b,const char *s){if(!b)throw std::runtime_error(s);}
static auto bytes(const fs::path &p){std::ifstream f(p,std::ios::binary);require(bool(f),"missing image");return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});}
static void save(const fs::path &p,const std::vector<uint8_t> &b){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"save failed");}
static uint8_t initial(uint64_t a){return uint8_t((a*37)^(a>>8)^0xa5);}
static constexpr uint64_t mailbox=0x80002000, magic=0x80004000;
static void capture(const char *elf,const fs::path &out,uint64_t flush) {
  std::vector<std::string> args{"memif-read-fesvr","+permissive","+no_hart0_msip","+idle-counts=3",
    "+cflush_addr=0x"+[] (uint64_t v){std::ostringstream s;s<<std::hex<<v;return s.str();}(flush),
    "+permissive-off",elf};
  std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());
  firesim_tsi_t tsi(argv.size(),argv.data(),true);
  firesim_tsi_memif_read_t empty;const auto idle=empty.save_checkpoint();
  tsi.tick();tsi.tick();firesim_loadmem_t req;std::array<uint8_t,16> data{};
  require(tsi.recv_loadmem_write_req(req) && req.addr==0x80000000 && req.size==16,"startup write differs");
  tsi.recv_loadmem_data(data.data(),16);tsi.tick();
  require(tsi.recv_loadmem_read_req(req) && req.addr==0x80001000 && req.size==8,"startup read differs");
  require(tsi.memif_read_owner().save_checkpoint()==idle && !tsi.data_available(),"startup entered serial reader");
  tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
  require(tsi.recv_loadmem_write_req(req) && req.addr==0x80001000 && req.size==8,"startup merge differs");
  tsi.recv_loadmem_data(data.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
  require(tsi.memif_read_owner().save_checkpoint()==idle,"startup retained runtime reader");
  size_t cut=0,active=0,ticks=0;std::ofstream events(out/"events.txt"),cuts(out/"cuts.txt");
  auto snapshot=[&] {
    const auto reader=tsi.memif_read_owner().save_checkpoint();const bool pending=reader!=idle;
    if(pending) {
      bool rejected=false;try{tsi.inspect_polling_cut();}catch(const std::runtime_error &){rejected=true;}
      require(rejected,"unowned syscall parent admitted as polling checkpoint");++active;
    }
    const auto prefix=out/("cut-"+std::to_string(cut));
    save(prefix.string()+".read",reader);save(prefix.string()+".serial",tsi.serial_queue_owner().save_checkpoint());
    cuts<<cut++<<' '<<ticks<<' '<<pending<<'\n';
  };
  auto tick=[&]{tsi.tick();++ticks;snapshot();};
  auto respond=[&](const std::vector<uint8_t> &b) {
    require(b.size()>=8 && b.size()%4==0,"invalid peer response");
    auto word=[&](size_t at){return uint32_t(b[at])|uint32_t(b[at+1])<<8|uint32_t(b[at+2])<<16|uint32_t(b[at+3])<<24;};
    tsi.send_word(word(0));snapshot();tick();
    for(size_t i=4;i<b.size();i+=4)tsi.send_word(word(i));
    snapshot();tick();
  };
  auto packet=[&] {
    std::array<uint32_t,5> h{};
    for(size_t i=0;i<5;++i){require(tsi.data_available(),"short request");h[i]=tsi.recv_word();if(i==1)snapshot();}
    require(h[0]<=1 && h[4]==0 && h[3]<256,"unsupported request");
    const uint64_t a=uint64_t(h[1])|uint64_t(h[2])<<32;const size_t n=(h[3]+1)*4;
    std::vector<uint8_t> b;
    if(h[0])for(size_t i=0;i<n/4;++i){require(tsi.data_available(),"short write");const auto w=tsi.recv_word();for(unsigned j=0;j<4;++j)b.push_back(w>>(8*j));}
    snapshot();events<<ticks<<' '<<(h[0]?"WRITE":"READ")<<' '<<a<<' '<<n;
    if(h[0]){const char *digits="0123456789abcdef";events<<' ';for(auto v:b)events<<digits[v>>4]<<digits[v&15];}
    events<<'\n';return std::make_tuple(h[0],a,n);
  };
  // First poll is already issued. Drain any flush packet before its read.
  while(tsi.data_available()){const auto [write,a,n]=packet();if(!write)require(a==mailbox && n==8,"initial poll differs");}
  const std::vector<std::pair<uint64_t,uint64_t>> specs{{0,0},{0,8},{7,1},{1,7},{7,9},{0,1023},{0,1024},{3,1025},{7,2057},
    {0,64},{1,64},{2,64},{3,64},{4,64},{5,64},{6,64},{7,64}};
  size_t index=0;
  for(auto [residue,length]:specs) {
    const uint64_t buffer=0x1280003000+index*0x10000+residue;
    std::array<uint64_t,8> request{64,1,buffer,length,0,0,0,0};
    std::vector<uint8_t> command(8);for(unsigned i=0;i<8;++i)command[i]=magic>>(8*i);
    respond(command);bool next=false;
    while(!next) {
      require(tsi.data_available(),"syscall stalled without request");
      const auto [write,a,n]=packet();
      if(write)continue;
      if(a==mailbox){require(n==8,"next mailbox size differs");next=true;continue;}
      std::vector<uint8_t> reply(n);
      for(size_t i=0;i<n;++i) {
        if(a==magic)reply[i]=request.at(i/8)>>(8*(i%8));
        else if(a==mailbox+8)reply[i]=0;
        else reply[i]=initial(a+i);
      }
      respond(reply);
    }
    require(tsi.memif_read_owner().save_checkpoint()==idle,"completed syscall retained reader");++index;
  }
  // Exit through the installed pass handler after the final fromhost response.
  std::vector<uint8_t> exit(8);exit[0]=1;respond(exit);
  while(tsi.data_available()){const auto [write,a,n]=packet();require(write && (a==flush || (a==mailbox && n==8)),"unexpected exit packet");}
  require(tsi.done() && tsi.exit_code()==0,"ordinary syscall source failed to exit");
  std::ofstream result(out/"result.txt");result<<"reads="<<index*2<<" syscalls="<<index<<" cuts="<<cut<<" active="<<active
    <<" host_ticks="<<ticks<<" startup_loadmem=1 syscall_parent_owned=0 cpu_edges=0\n";
}
static int run(const char *mode,const char *source,const char *destination,const char *flush) {
  try {
    const fs::path out(destination);fs::create_directories(out);
    if(std::string(mode)=="readback") {
      firesim_tsi_memif_read_t r;firesim_tsi_serial_state_t q;
      r.load_serial_checkpoint(q,bytes(std::string(source)+".read"),bytes(std::string(source)+".serial"));
      save(out/"preedge.read",r.save_checkpoint());save(out/"preedge.serial",q.save_checkpoint());
      std::cout<<"PRODUCTION_READER_READBACK context_entries=0 target_services=0 target_edges=0\n";return 0;
    }
    // Actual installed sys_write uses its own duplicated stdout. Bind it to a
    // retained regular file and release the entire source session before audit.
    const int original=::dup(1),output=::open((out/"actual-syswrite.bin").c_str(),O_WRONLY|O_CREAT|O_TRUNC,0600);
    require(original>=0 && output>=0 && ::dup2(output,1)==1,"cannot bind syscall output");::close(output);
    capture(source,out,std::stoull(flush));
    require(::dup2(original,1)==1,"cannot restore stdout");::close(original);
    std::cout<<"PRODUCTION_MEMIF_READ source_exit=0 target_edges=0 complete_cpu_restore=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_MEMIF_READ_FESVR_DPI
extern "C" int tsi_memif_read_fesvr(const char *m,const char *s,const char *o,const char *f){return run(m,s,o,f);}
extern "C" void tsi_memif_read_fesvr_exit(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=5)return 2;return run(argv[1],argv[2],argv[3],argv[4]);}
#endif
