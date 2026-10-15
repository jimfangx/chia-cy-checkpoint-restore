// Sealed terminal and real BCD continuations; not a CPU restore harness.
#include "fesvr/firesim_tsi.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <fcntl.h>
#include <unistd.h>
namespace fs = std::filesystem;
static void require(bool b, const char *s) { if (!b) throw std::runtime_error(s); }
static void save(const fs::path &p, const std::vector<uint8_t> &bytes) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(bytes.data()), bytes.size()); require(bool(f), "save failed");
}
static std::vector<uint8_t> read_file(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing owner image");
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
static void put(std::vector<uint8_t> &v, size_t at, uint64_t n) {
  for (unsigned i=0;i<8;++i) v.at(at+i)=n>>(8*i);
}
static constexpr uint64_t READ = 0x0100000000000000ULL;
static const std::vector<uint8_t> INPUT{65,0,255};
class memory_t final : public memif_t {
public:
  memory_t() : memif_t(nullptr) {}
  void read(addr_t, size_t, void *) override { throw std::runtime_error("unexpected memory read"); }
  void write(addr_t, size_t, const void *) override { throw std::runtime_error("unexpected memory write"); }
};
static void execute(const std::string &op, const fs::path &images, const fs::path &out, int cut) {
  std::ostringstream log; std::vector<uint8_t> emitted;
  firesim_tsi_terminal_t terminal(INPUT,[&](uint8_t ch){emitted.push_back(ch);log<<"OUTPUT "<<unsigned(ch)<<'\n';});
  firesim_tsi_bcd_t bcd([&](uint64_t v){log<<"RESPONSE "<<v<<'\n';},1048576,&terminal);
  memory_t mem;
  if (cut>=0) {
    const auto t=read_file(images/("cut-"+std::to_string(cut)+".terminal"));
    const auto b=read_file(images/("cut-"+std::to_string(cut)+".bcd"));
    // Component coordinator prevalidates both before changing either owner.
    terminal.validate_checkpoint(t); bcd.validate_checkpoint(b);
    terminal.load_checkpoint(t); bcd.load_checkpoint(b);
    save(out/"preedge.terminal",terminal.save_checkpoint()); save(out/"preedge.bcd",bcd.save_checkpoint());
    require(terminal.save_checkpoint()==t && bcd.save_checkpoint()==b && emitted.empty(),"incomplete/active readback");
  }
  auto capture=[&](int n) {
    save(out/("cut-"+std::to_string(n)+".terminal"),terminal.save_checkpoint());
    save(out/("cut-"+std::to_string(n)+".bcd"),bcd.save_checkpoint());
  };
  if(cut<0) capture(0);
  for(int event=cut<0?1:cut+1;event<=12;++event) {
    log<<"EVENT "<<event<<'\n';
    auto command=[&](uint64_t raw){bcd.handle_command(command_t(mem,raw,[](uint64_t){throw std::runtime_error("stale callback");}));};
    switch(event) {
      case 1: case 3: case 11: command(READ); break;
      case 2: case 5: case 6: case 8: case 10: bcd.tick(); break;
      case 4: command(READ|(1ULL<<48)|'Z'); break;
      case 7: command(READ); command(READ); break;
      case 9: command(READ|(1ULL<<48)); break;
      case 12: command(READ|(1ULL<<48)|255); break;
    }
    if(cut<0) capture(event);
  }
  save(out/"final.terminal",terminal.save_checkpoint()); save(out/"final.bcd",bcd.save_checkpoint());
  const auto text=log.str();save(out/"events.log",{text.begin(),text.end()});save(out/"emitted.bin",emitted);
  std::cout<<"SEALED_CONTINUATION mode="<<op<<" cut="<<cut<<" target_edges=0 context_entries=0\n";
}
static void invalid(const fs::path &images, const fs::path &out) {
  size_t services=0, count=0;
  firesim_tsi_terminal_t terminal(INPUT,[&](uint8_t){++services;});
  firesim_tsi_bcd_t bcd([&](uint64_t){++services;},1048576,&terminal);
  const auto before=terminal.save_checkpoint(), peer=bcd.save_checkpoint();
  const auto good=read_file(images/"cut-4.terminal");
  auto reject=[&](const std::vector<uint8_t> &candidate) {
    bool rejected=false;try{terminal.load_checkpoint(candidate);}catch(const std::runtime_error &){rejected=true;}
    require(rejected && terminal.save_checkpoint()==before && bcd.save_checkpoint()==peer && !services,"non-atomic terminal rejection");++count;
  };
  for(size_t n=0;n<good.size();++n) reject({good.begin(),good.begin()+n});
  for(size_t at=0;at<59;++at) {auto v=good;v[at]^=1;reject(v);}
  auto v=good;v.push_back(0);reject(v);
  for(auto value:{uint64_t(4),UINT64_MAX}){v=good;put(v,59,value);reject(v);}
  for(auto value:{uint64_t(0),uint64_t(2),uint64_t(1048577),UINT64_MAX}){v=good;put(v,67,value);reject(v);}
  firesim_tsi_terminal_t other({65,0,254},[&](uint8_t){++services;});
  bool failed=false;try{other.load_checkpoint(good);}catch(const std::runtime_error &){failed=true;}
  require(failed && !services,"incompatible input accepted");
  // Missing/invalid second owner is rejected before a valid first-owner load.
  for(bool missing:{false,true}) {
    auto t=good;auto b=missing?std::vector<uint8_t>{}:peer;if(!missing)b[0]^=1;
    failed=false;try{terminal.validate_checkpoint(t);bcd.validate_checkpoint(b);terminal.load_checkpoint(t);bcd.load_checkpoint(b);}
    catch(const std::runtime_error &){failed=true;}
    require(failed && terminal.save_checkpoint()==before && bcd.save_checkpoint()==peer && !services,"incomplete pair partially restored");
  }
  terminal.load_checkpoint(good);save(out/"preedge.terminal",terminal.save_checkpoint());
  std::cout<<"TERMINAL_ATOMIC_REJECTIONS malformed="<<count<<" incompatible=1 missing_or_invalid_peer=2 services=0\n";
}
static void guards() {
  firesim_tsi_terminal_t live;
  for(int op=0;op<3;++op) {
    bool failed=false;try{if(op==0)live.save_checkpoint();else if(op==1)live.validate_checkpoint({});else live.load_checkpoint({});}
    catch(const std::runtime_error &){failed=true;}require(failed,"live terminal accepted");
  }
  firesim_tsi_terminal_t *active=nullptr;size_t rejected=0;
  auto check=[&] {
    for(int op=0;op<5;++op) {
      bool failed=false;try{if(op==0)active->save_checkpoint();else if(op==1)active->validate_checkpoint({});
        else if(op==2)active->load_checkpoint({});else if(op==3)active->read();else active->write(0);}
      catch(const std::runtime_error &){failed=true;}require(failed,"active terminal accepted");++rejected;
    }
  };
  firesim_tsi_terminal_t terminal(INPUT,[&](uint8_t){check();});active=&terminal;terminal.write(42);
  require(rejected==5,"incomplete active guards");
  firesim_tsi_terminal_t interrupted(INPUT,[](uint8_t){throw std::runtime_error("service failure");});
  try{interrupted.write(0);}catch(const std::runtime_error &){}
  active=&interrupted;check();
  // Validate the hard output bound before any extra external output.
  size_t writes=0;firesim_tsi_terminal_t bounded({},[&](uint8_t){++writes;});
  for(uint64_t n=0;n<firesim_tsi_terminal_t::maximum;++n)bounded.write(n);
  bool failed=false;try{bounded.write(0);}catch(const std::runtime_error &){failed=true;}
  require(failed && writes==firesim_tsi_terminal_t::maximum,"output limit emitted an extra byte");
  std::cout<<"TERMINAL_GUARDS live=3 active=5 interrupted=5 output_limit=1\n";
}
static void packet(firesim_tsi_t &tsi, std::initializer_list<uint32_t> expected) {
  for(auto word:expected) require(tsi.data_available() && tsi.recv_word()==word,"production packet differs");
  require(!tsi.data_available(),"extra production packet");
}
static void integration(const fs::path &elf, const fs::path &out) {
  const auto input=out/"input.bin";save(input,INPUT);
  std::vector<std::string> args{"terminal","+permissive","+no_hart0_msip",
    "+checkpoint-terminal-input="+input.string(),"+permissive-off",elf};
  std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
  firesim_tsi_t tsi(argv.size(),argv.data(),true);
  save(out/"pristine.terminal",tsi.terminal_owner().save_checkpoint());
  // Prove the original file is no longer an input service after construction.
  save(input,{});
  tsi.tick();tsi.tick();firesim_loadmem_t request;std::array<uint8_t,16> bytes{};
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
  tsi.recv_loadmem_data(bytes.data(),16);tsi.tick();
  require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF read differs");
  tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
  tsi.recv_loadmem_data(bytes.data(),8);tsi.set_loaded_in_target(true);tsi.tick();packet(tsi,{0,0x80002000,0,1,0});
  for(auto ch:INPUT) {
    tsi.send_word(0);tsi.send_word(0x01000000);tsi.tick();
    packet(tsi,{1,0x80002000,0,1,0,0,0,0,0x80002008,0,1,0});
    tsi.send_word(0);tsi.send_word(0);tsi.tick();
    packet(tsi,{1,0x80002008,0,1,0,0x100|uint32_t(ch),0x01000000,0,0x80002000,0,1,0});
  }
  save(out/"consumed.terminal",tsi.terminal_owner().save_checkpoint());
  // BCD write routes through the same owned transcript, including binary 0.
  const int original=dup(1),fd=open((out/"output.bin").c_str(),O_CREAT|O_TRUNC|O_WRONLY,0600);
  require(original>=0 && fd>=0 && dup2(fd,1)==1,"cannot redirect terminal output");close(fd);
  tsi.send_word('Z');tsi.send_word(0x01010000);tsi.tick();
  packet(tsi,{1,0x80002000,0,1,0,0,0,0,0x80002000,0,1,0});
  require(dup2(original,1)==1,"cannot restore stdout");close(original);
  save(out/"written.terminal",tsi.terminal_owner().save_checkpoint());
  bool failed=false;try{tsi.save_startup_metadata();}catch(const std::runtime_error &){failed=true;}
  require(failed,"unbound aggregate metadata admitted terminal peer");
  tsi.send_word(1);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002000,0,1,0,0,0});
  require(tsi.done() && tsi.exit_code()==0,"production exit differs");
  std::cout<<"ACTUAL_TSI_TERMINAL input_bytes=3 output_bytes=1 source_file_replaced=1 metadata_rejected=1 exit=0\n";
}
static int run(const char *mode,const char *source,const char *images,const char *destination,int cut) {
  try {
    const std::string op(mode);fs::path out(destination);fs::create_directories(out);
    if(op=="guards")guards();else if(op=="integration")integration(source,out);
    else if(op=="invalid")invalid(images,out);
    else {require(op=="capture" || op=="restore" || op=="corrupt","unknown terminal mode");execute(op,images,out,cut);}
    return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_TERMINAL_DPI
extern "C" int tsi_terminal(const char *m,const char *s,const char *i,const char *o,int c){return run(m,s,i,o,c);}
extern "C" void tsi_terminal_exit(int code){std::exit(code);}
#else
int main(int argc,char **argv){if(argc!=6)return 2;return run(argv[1],argv[2],argv[3],argv[4],std::stoi(argv[5]));}
#endif
