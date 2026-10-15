// Pending default-device reads, with the installed BCD as an independent oracle.
#include "fesvr/firesim_tsi.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <fcntl.h>
#include <unistd.h>
namespace fs = std::filesystem;
static void require(bool b, const char *s) { if (!b) throw std::runtime_error(s); }
static std::vector<uint8_t> read_file(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing image");
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
static void save(const fs::path &p, const std::vector<uint8_t> &bytes) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(f), "cannot save image");
}
static void put(std::vector<uint8_t> &b, size_t at, uint64_t value) {
  for (unsigned i=0;i<8;++i) b.at(at+i)=value>>(8*i);
}
class terminal_t {
public:
  terminal_t() {
    original=::dup(0); require(original>=0 && ::pipe(fds)==0, "cannot create terminal pipe");
    require(::dup2(fds[0],0)==0, "cannot bind terminal pipe"); ::close(fds[0]);
  }
  ~terminal_t() { ::dup2(original,0); ::close(original); ::close(fds[1]); }
  void send(uint8_t ch) { require(::write(fds[1],&ch,1)==1, "cannot supply terminal input"); }
private:
  int fds[2], original;
};
class memory_t final : public memif_t {
public:
  explicit memory_t(std::ostringstream &log) : memif_t(nullptr), log(log) {}
  void read(addr_t, size_t, void *) override { throw std::runtime_error("unexpected device memory read"); }
  void write(addr_t a, size_t n, const void *p) override {
    if (hook) hook();
    log << "MEM " << a << " " << n << " ";
    for (size_t i=0;i<n;++i) log << unsigned(static_cast<const uint8_t *>(p)[i]) << ",";
    log << "\n";
  }
  std::function<void()> hook;
private:
  std::ostringstream &log;
};
static void send(device_t &device, memory_t &mem, uint64_t value, std::function<void(uint64_t)> sink) {
  device.handle_command(command_t(mem,value,std::move(sink)));
}
static constexpr uint64_t READ = 0x0100000000000000ULL;
static std::string execute(const fs::path &out, bool reference, int cut, const std::vector<uint8_t> &image,
                           bool corrupt=false) {
  terminal_t terminal;
  std::ostringstream log; memory_t mem(log);
  auto sink = [&](uint64_t value) { log << "RESPONSE " << value << "\n"; };
  firesim_tsi_bcd_t owned(sink); bcd_t installed;
  device_t &device = reference ? static_cast<device_t &>(installed) : owned;
  if (cut>=0) {
    owned.load_checkpoint(image); require(owned.save_checkpoint()==image,"incomplete preedge BCD readback");
    save(out/"preedge.bcd",owned.save_checkpoint());
  } else if (!reference) save(out/"cut-0.bcd",owned.save_checkpoint());
  // Each cut follows a completed call; supplied input is consumed in that
  // same call. Terminal state is empty at every captured boundary.
  for (int event=cut<0 ? 1 : cut+1;event<=12;++event) {
    log << "EVENT " << event << "\n";
    switch(event) {
    case 1: send(device,mem,READ|0x123,sink); break;
    case 2: case 4: case 6: case 12: device.tick(); break;
    case 3: send(device,mem,READ|0xbeef,sink); break;
    case 5: terminal.send('A'); device.tick(); break;
    case 7: send(device,mem,READ|0x987,sink); break;
    case 8: terminal.send(0); device.tick(); break;
    case 9:
      for (auto what : {0,1,2,255}) send(device,mem,0x01ff000000000000ULL | (0x80003000ULL*256+what),sink);
      break;
    case 10: // Real installed canonical terminal writes, captured separately.
      send(device,mem,0x010100000000005aULL,sink); break;
    case 11: terminal.send(255); device.tick(); break;
    }
    if (!reference && cut<0) save(out/("cut-"+std::to_string(event)+".bcd"),owned.save_checkpoint());
  }
  if (!reference && !corrupt) {
    const auto empty=firesim_tsi_bcd_t(sink).save_checkpoint();
    require(owned.save_checkpoint()==empty,"continuation retained pending reads");
  }
  return log.str();
}
static std::string with_output(const fs::path &out, bool reference, int cut,
                               const std::vector<uint8_t> &image, bool corrupt=false) {
  int original=::dup(1),fd=::open((out/"terminal-output.bin").c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
  require(original>=0 && fd>=0 && ::dup2(fd,1)==1,"cannot capture terminal output"); ::close(fd);
  try {
    auto result=execute(out,reference,cut,image,corrupt);
    ::dup2(original,1); ::close(original); return result;
  } catch (...) { ::dup2(original,1); ::close(original); throw; }
}
static void guards() {
  std::ostringstream log; memory_t mem(log); terminal_t terminal;
  firesim_tsi_bcd_t *active=nullptr; size_t rejected=0;
  std::vector<uint8_t> idle;
  auto check=[&] {
    for (int op=0;op<3;++op) {
      bool failed=false;
      try { if(op==0)active->save_checkpoint();else if(op==1)active->validate_checkpoint(idle);else active->load_checkpoint(idle); }
      catch(const std::runtime_error &) { failed=true; }
      require(failed,"BCD active service was checkpointable"); ++rejected;
    }
  };
  firesim_tsi_bcd_t owner([&](uint64_t){check();}); active=&owner; idle=owner.save_checkpoint();
  send(owner,mem,READ,[](uint64_t){throw std::runtime_error("retained callback used");});
  terminal.send('A');owner.tick();require(owner.save_checkpoint()==idle,"callback guard changed queue");
  mem.hook=check;
  send(owner,mem,0x01ff0000800030ffULL,[](uint64_t){});
  require(owner.save_checkpoint()==idle,"identity guard changed queue");
  firesim_tsi_bcd_t interrupted([](uint64_t){throw std::runtime_error("response service failure");});
  send(interrupted,mem,READ,[](uint64_t){});terminal.send('B');
  try { interrupted.tick(); } catch(const std::runtime_error &) {}
  for(int op=0;op<5;++op) {
    bool failed=false;
    try {
      if(op==0)interrupted.save_checkpoint();else if(op==1)interrupted.validate_checkpoint(idle);
      else if(op==2)interrupted.load_checkpoint(idle);else if(op==3)interrupted.tick();
      else send(interrupted,mem,READ,[](uint64_t){});
    } catch(const std::runtime_error &) {failed=true;}
    require(failed,"interrupted BCD operation was reusable");++rejected;
  }
  std::cout<<"BCD_SERVICE_GUARDS active=6 interrupted=5 total="<<rejected<<"\n";
}
static void packet(firesim_tsi_t &tsi, std::initializer_list<uint32_t> expected) {
  for(auto word:expected) require(tsi.data_available() && tsi.recv_word()==word,"actual TSI packet differs");
  require(!tsi.data_available(),"extra actual TSI word");
}
static void integration(const fs::path &elf, const fs::path &out) {
  terminal_t terminal;
  std::vector<std::string> args{"bcd","+permissive","+no_hart0_msip","+permissive-off",elf};
  std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
  firesim_tsi_t tsi(argv.size(),argv.data(),true);
  bool absent=false;try{tsi.bcd_owner();}catch(const std::runtime_error &){absent=true;}
  require(absent,"BCD existed before startup");
  tsi.tick();tsi.tick();firesim_loadmem_t request;std::array<uint8_t,16> bytes{};
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
  tsi.recv_loadmem_data(bytes.data(),16);tsi.tick();
  require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF read differs");
  tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
  tsi.recv_loadmem_data(bytes.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
  packet(tsi,{0,0x80002000,0,1,0});
  for(int pending=0;pending<=2;++pending) {
    require(tsi.inspect_polling_cut().size()==8,"production caller cut unavailable");
    save(out/("pending-"+std::to_string(pending)+".bcd"),tsi.bcd_owner().save_checkpoint());
    save(out/("pending-"+std::to_string(pending)+".poll"),tsi.htif_poll_owner().save_checkpoint());
    if(pending==2)break;
    tsi.send_word(pending==0 ? 0x123 : 0xbeef);tsi.send_word(0x01000000);tsi.tick();
    packet(tsi,{1,0x80002000,0,1,0,0,0,0,0x80002000,0,1,0});
  }
  for(auto ch:{uint32_t('A'),uint32_t(255)}) {
    terminal.send(ch);tsi.send_word(0);tsi.send_word(0);tsi.tick();
    for(int i=0;!tsi.data_available() && i<20;++i)tsi.tick();
    packet(tsi,{0,0x80002008,0,1,0});
    tsi.send_word(0);tsi.send_word(0);tsi.tick();
    packet(tsi,{1,0x80002008,0,1,0,0x100|ch,0x01000000,0,0x80002000,0,1,0});
  }
  require(tsi.bcd_owner().save_checkpoint()==read_file(out/"pending-0.bcd"),"actual BCD did not drain");
  tsi.send_word(1);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002000,0,1,0,0,0});
  require(tsi.done() && tsi.exit_code()==0,"actual loader/BCD source did not pass");
  std::cout<<"ACTUAL_TSI_BCD pending_cuts=3 fromhost_writes=2 source_exit=0\n";
}
static int run(const char *mode,const char *source,const char *image,const char *destination,int cut) {
  try {
    fs::path out(destination);fs::create_directories(out);const std::string op(mode);
    if(op=="guards") {guards();return 0;}
    if(op=="integration") {integration(source,out);return 0;}
    if(op=="capture" || op=="reference" || op=="restore" || op=="corrupt") {
      auto bytes=op=="restore" || op=="corrupt" ? read_file(image) : std::vector<uint8_t>{};
      auto log=with_output(out,op=="reference",op=="restore" || op=="corrupt" ? cut : -1,bytes,op=="corrupt");
      save(out/"events.log",{log.begin(),log.end()});
      std::cout<<"BCD_CONTINUATION mode="<<op<<" cut="<<cut<<" target_edges=0 context_entries=0\n";return 0;
    }
    auto bytes=read_file(image);size_t replies=0;
    firesim_tsi_bcd_t owner([&](uint64_t){++replies;});const auto before=owner.save_checkpoint();
    auto reject=[&](const std::vector<uint8_t> &candidate) {
      bool failed=false;try{owner.load_checkpoint(candidate);}catch(const std::runtime_error &){failed=true;}
      require(failed && owner.save_checkpoint()==before && !replies,"BCD invalid image changed state");
    };
    if(op=="invalid") {
      size_t count=0;
      for(size_t i=0;i<48;++i){auto b=bytes;b[i]^=1;reject(b);++count;}
      for(size_t n=0;n<bytes.size();++n){reject({bytes.begin(),bytes.begin()+n});++count;}
      auto b=bytes;b.push_back(0);reject(b);++count;
      for(auto value:{uint64_t(0),uint64_t(1),uint64_t(3),uint64_t(1048577),UINT64_MAX}) {
        b=bytes;put(b,48,value);reject(b);++count;
      }
      for(size_t at=56;at<bytes.size();at+=8)for(auto tag:{uint64_t(0),uint64_t(0x101),uint64_t(0x200)}) {
        b=bytes;put(b,at,tag<<48);reject(b);++count;
      }
      firesim_tsi_bcd_t other([](uint64_t){},1);bool failed=false;
      try{other.load_checkpoint(bytes);}catch(const std::runtime_error &){failed=true;}
      require(failed,"incompatible BCD configuration admitted");
      std::cout<<"BCD_ATOMIC_REJECTIONS malformed="<<count<<" incompatible=1 replies=0\n";
    } else require(op=="readback","unknown mode");
    owner.load_checkpoint(bytes);save(out/"preedge.bcd",owner.save_checkpoint());
    require(owner.save_checkpoint()==bytes && !replies,"complete BCD readback failed");
    std::cout<<"COMPLETE_BCD_READBACK target_edges=0 context_entries=0 services=0\n";return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}
}
#ifdef TSI_BCD_DPI
extern "C" int tsi_bcd(const char *m,const char *s,const char *i,const char *o,int c) {return run(m,s,i,o,c);}
extern "C" void tsi_bcd_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=6)return 2;return run(argv[1],argv[2],argv[3],argv[4],std::stoi(argv[5]));}
#endif
