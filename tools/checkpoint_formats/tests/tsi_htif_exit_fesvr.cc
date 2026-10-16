// Installed direct-exit handler, production TSI integration and exit component
// projections. These are host cuts, not complete HTIF or CPU continuations.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <csignal>
#include <pthread.h>
namespace fs = std::filesystem;
using owner_t = firesim_tsi_htif_exit_t;
static void require(bool b, const char *s) { if (!b) throw std::runtime_error(s); }
static auto bytes(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static void save(const fs::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()), b.size());
  require(bool(f), "save failed");
}
// Ordinary installed HTIF/syscall reference. An odd command must never touch
// target memory or respond. Its no-signature stop performs no target service.
class reference_t final : public htif_t {
public:
  reference_t() : htif_t(std::vector<std::string>{"none"}), syscall(this) {}
  void request(uint64_t raw) {
    command_t command(memif(), raw, [](uint64_t) { throw std::runtime_error("direct exit responded"); });
    syscall.handle_command(command);
  }
  bool exiting() const { return should_exit(); }
private:
  syscall_t syscall;
  void reset() override { throw std::runtime_error("reference reset"); }
  void read_chunk(addr_t, size_t, void *) override { throw std::runtime_error("reference read"); }
  void write_chunk(addr_t, size_t, const void *) override { throw std::runtime_error("reference write"); }
  size_t chunk_align() override { return 8; }
  size_t chunk_max_size() override { return 1024; }
};
static void observed(reference_t &r, const fs::path &path) {
  std::ofstream f(path); f << r.exiting() << ' ' << r.done() << ' ' << r.exit_code() << '\n';
}
static void capture(const char *elf, const fs::path &out, uint64_t raw, uint64_t flush) {
  save(out/"input.bin", {65});
  std::ostringstream address; address << std::hex << flush;
  std::vector<std::string> args{"htif-exit", "+permissive", "+no_hart0_msip", "+idle-counts=3",
    "+cflush_addr=0x"+address.str(), "+checkpoint-terminal-input="+(out/"input.bin").string(),
    "+permissive-off", elf};
  std::vector<char *> argv; for (auto &a : args) argv.push_back(a.data());
  firesim_tsi_t tsi(argv.size(), argv.data(), true);
  tsi.tick(); tsi.tick(); firesim_loadmem_t req; std::array<uint8_t,16> data{};
  require(tsi.recv_loadmem_write_req(req) && req.addr==0x80000000 && req.size==16, "startup write");
  tsi.recv_loadmem_data(data.data(),16); tsi.tick();
  require(tsi.recv_loadmem_read_req(req) && req.addr==0x80001000 && req.size==8, "startup read");
  tsi.send_loadmem_word(0xaabbccdd); tsi.send_loadmem_word(0x11223344); tsi.tick();
  require(tsi.recv_loadmem_write_req(req) && req.addr==0x80001000 && req.size==8, "startup merge");
  tsi.recv_loadmem_data(data.data(),8); tsi.set_loaded_in_target(true); tsi.tick();
  size_t cut=0, tick=0, exit_rejections=0; std::ofstream cuts(out/"cuts.txt"), events(out/"events.txt");
  auto snapshot = [&] {
    const auto prefix=out/("cut-"+std::to_string(cut));
    const auto image=tsi.save_htif_exit_component();
    if(image.at(56)==1) {
      bool rejected=false;try{tsi.inspect_polling_cut();}catch(const std::runtime_error &){rejected=true;}
      require(rejected,"polling aggregate silently omitted active exit component");++exit_rejections;
    }
    save(prefix.string()+".exit", image);
    save(prefix.string()+".poll", tsi.htif_poll_owner().save_checkpoint());
    save(prefix.string()+".read", tsi.serial_read_owner().save_checkpoint());
    save(prefix.string()+".serial", tsi.serial_queue_owner().save_checkpoint());
    save(prefix.string()+".terminal", tsi.terminal_owner().save_checkpoint());
    cuts << cut++ << ' ' << tick << ' ' << tsi.done() << ' ' << tsi.exit_code() << '\n';
  };
  auto service = [&] { tsi.tick(); ++tick; snapshot(); };
  auto drain = [&](uint64_t expected_read) {
    bool found=false;
    while (tsi.data_available()) {
      std::array<uint32_t,5> h{};
      for (unsigned i=0;i<5;++i) { require(tsi.data_available(), "short header"); h[i]=tsi.recv_word(); if(i==1)snapshot(); }
      const uint64_t a=uint64_t(h[1]) | uint64_t(h[2])<<32; const size_t n=(h[3]+1)*4;
      require(h[0]<=1 && h[4]==0 && n==8, "unexpected serial request");
      uint64_t value=0;
      if(h[0])for(unsigned i=0;i<2;++i){require(tsi.data_available(),"short write");value|=uint64_t(tsi.recv_word())<<(32*i);}
      snapshot(); events << tick << ' ' << (h[0]?"W":"R") << ' ' << a << ' ' << value << '\n';
      if(!h[0]){require(!found && a==expected_read,"wrong read order");found=true;}
    }
    require(found==(expected_read!=0), "missing read");
  };
  auto reply = [&](uint64_t value) {
    tsi.send_word(uint32_t(value)); snapshot(); service();
    tsi.send_word(uint32_t(value>>32)); snapshot(); service();
  };
  snapshot(); drain(0x80002000);
  // BCD response remains queued because the peer's fromhost is occupied.
  reply(0x0100000000000000ULL); drain(0x80002008);
  reply(7); drain(0x80002000);
  reply(raw); drain(0x80002008);
  require(!tsi.done(), "exit failed to retain queued response before stop");
  reply(0); drain(0);
  require(tsi.done(), "installed stop not reached");
  reference_t reference; reference.request(raw); reference.stop();
  require(tsi.exit_code()==reference.exit_code(), "production exit differs from installed reference");
  observed(reference, out/"reference.txt");
  std::ofstream(out/"aggregate-rejections.txt")<<exit_rejections<<'\n';
}
static void projection(const char *source, const fs::path &out, uint64_t raw, const std::string &mode) {
  owner_t owner; const auto before=owner.save_checkpoint(); const auto image=bytes(source);
  if(mode=="reject") {
    bool rejected=false; try{owner.load_checkpoint(image);}catch(const std::runtime_error &){rejected=true;}
    require(rejected && owner.save_checkpoint()==before,"invalid image changed exit owner");
    save(out/"unchanged.exit",owner.save_checkpoint()); return;
  }
  owner.load_checkpoint(image);
  save(out/"pre-service.exit",owner.save_checkpoint()); // before any reference service
  reference_t reference;
  if(owner.phase()!=owner_t::phase_t::running)reference.request(owner.raw_exit());
  if(owner.phase()==owner_t::phase_t::stopped)reference.stop();
  owner.validate_observed(reference.exiting(), reference.done(), reference.exit_code());
  observed(reference,out/"bound.txt");
  const uint32_t expected_raw=uint32_t(raw);
  reference_t expected;
  if(owner.phase()!=owner_t::phase_t::running)expected.request(raw);
  if(owner.phase()==owner_t::phase_t::stopped)expected.stop();
  if(reference.exit_code()!=expected.exit_code()) {
    require(mode=="corrupt", "unexpected exit component divergence");
    std::ofstream f(out/"first-divergence.txt");
    f<<"FIRST_DIVERGENCE boundary=0 signal=exit_code expected="<<expected.exit_code()
      <<" actual="<<reference.exit_code()<<" acknowledged=0 stop_services=0\n";
    return;
  }
  require(mode!="corrupt", "corruption was not detected");
  if(owner.phase()==owner_t::phase_t::running)
    owner.request(raw,[&]{reference.request(raw);});
  if(owner.phase()==owner_t::phase_t::requested)
    owner.stop([&]{reference.stop();});
  require(owner.raw_exit()==expected_raw,"raw status lost");
  owner.validate_observed(reference.exiting(),reference.done(),reference.exit_code());
  save(out/"final.exit",owner.save_checkpoint()); observed(reference,out/"final.txt");
}
static void internal(const fs::path &out) {
  size_t checks=0;
  auto reject=[&](auto call){bool bad=false;try{call();}catch(const std::runtime_error &){bad=true;}require(bad,"missing boundary rejection");++checks;};
  owner_t o; const auto initial=o.save_checkpoint();
  for(auto payload:{0ULL,2ULL,0x1000000000001ULL}){owner_t bad;reject([&]{bad.request(payload,[]{throw std::logic_error("service entered");});});}
  reject([&]{o.validate_observed(true,false,0);}); // signal-only exit
  reject([&]{o.validate_observed(false,true,0);});
  reject([&]{o.validate_observed(false,false,7);});
  require(o.save_checkpoint()==initial,"observation mutated state");
  o.request(1,[&]{reject([&]{o.save_checkpoint();});reject([&]{o.load_checkpoint(initial);});});
  reject([&]{o.validate_observed(false,false,0);});
  reject([&]{o.validate_observed(true,true,0);});
  o.stop([&]{reject([&]{o.save_checkpoint();});});
  reject([&]{o.validate_observed(true,false,0);});
  owner_t interrupted;try{interrupted.request(1,[]{throw std::runtime_error("callback failed");});}catch(const std::runtime_error &){}
  reject([&]{interrupted.save_checkpoint();});reject([&]{interrupted.load_checkpoint(initial);});
  std::ofstream(out/"internal.txt")<<"checks="<<checks<<" cpu_edges=0\n";
}
// raise() queues a blocked signal; it does not guarantee handler delivery.
// The loop controller can pass a blocked mask through exec. Exercise the real
// installed handler after proving the signal was queued, without replacing it
// or changing production signal policy. Each case runs in its own process.
// A pristine installed HTIF reference observes the same process-global latch;
// production admission is checked separately on the actual final TSI class.
static void deliver_signal(reference_t &reference, const fs::path &out, int sig) {
  sigset_t selected, original, pending, restored;
  require(sigemptyset(&selected)==0 && sigaddset(&selected,sig)==0,"signal set failed");
  require(pthread_sigmask(SIG_BLOCK,&selected,&original)==0,"signal block failed");
  const int initially_blocked=sigismember(&original,sig);
  require(initially_blocked>=0 && !reference.exiting(),"signal lifecycle was not pristine");
  require(sigpending(&pending)==0 && sigismember(&pending,sig)==0,"signal already pending");
  struct sigaction action{};
  require(sigaction(sig,nullptr,&action)==0 && action.sa_handler!=SIG_DFL &&
          action.sa_handler!=SIG_IGN,"installed signal handler missing");
  require(std::raise(sig)==0,"signal raise failed");
  require(sigpending(&pending)==0 && sigismember(&pending,sig)==1 && !reference.exiting(),
          "blocked signal did not remain queued before delivery");
  require(pthread_sigmask(SIG_UNBLOCK,&selected,nullptr)==0,"signal unblock failed");
  require(reference.exiting() && sigpending(&pending)==0 && sigismember(&pending,sig)==0,
          "installed signal handler did not observe delivery");
  require(pthread_sigmask(SIG_SETMASK,&original,nullptr)==0 &&
          pthread_sigmask(SIG_BLOCK,nullptr,&restored)==0 &&
          sigismember(&restored,sig)==initially_blocked,"signal mask restore failed");
  std::ofstream(out/"signal-delivery.txt")
    <<"signal="<<sig<<" initially_blocked="<<initially_blocked
    <<" before_exiting=0 pending_queued=1 after_exiting=1 pending_after=0 mask_restored=1\n";
}
static void unowned(const char *elf,const fs::path &out,const std::string &which) {
  const int sig=which.rfind("signal-int",0)==0?SIGINT:which.rfind("signal-term",0)==0?SIGTERM:0;
  if(sig && (which.find("-blocked")!=std::string::npos || which.find("-unblocked")!=std::string::npos)) {
    sigset_t selected;
    require(sigemptyset(&selected)==0 && sigaddset(&selected,sig)==0 &&
            pthread_sigmask(which.find("-unblocked")!=std::string::npos?SIG_UNBLOCK:SIG_BLOCK,
                            &selected,nullptr)==0,"initial signal mask setup failed");
  }
  std::vector<std::string> args{"htif-exit", "+permissive", "+signature="+(out/"unused-signature").string(),
    "+permissive-off", elf};
  if(which!="signature")args.erase(args.begin()+2);
  std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());
  std::unique_ptr<reference_t> signal_reference;
  if(sig)signal_reference=std::make_unique<reference_t>();
  firesim_tsi_t tsi(argv.size(),argv.data(),true);
  const auto serial=tsi.serial_queue_owner().save_checkpoint();
  if(sig)deliver_signal(*signal_reference,out,sig);
  else if(which=="exit")tsi.htif_exit(1);
  else if(which=="stop")tsi.stop();
  else require(which=="signature","unknown unsupported case");
  bool rejected=false;try{tsi.save_htif_exit_component();}catch(const std::runtime_error &){rejected=true;}
  require(rejected && tsi.serial_queue_owner().save_checkpoint()==serial,"unowned lifecycle admitted or target mutated");
  std::ofstream(out/"unowned.txt")<<which<<" rejected=1 serial_unchanged=1 context_entries=0\n";
}
static int run(const char *mode,const char *source,const char *destination,const char *raw,const char *flush) {
  try {
    fs::path out(destination); fs::create_directories(out); const std::string operation(mode);
    if(operation=="capture")capture(source,out,std::stoull(raw),std::stoull(flush));
    else if(operation=="internal")internal(out);
    else if(operation=="unowned")unowned(source,out,raw);
    else projection(source,out,std::stoull(raw),operation);
    std::cout<<"HTIF_EXIT_COMPONENT operation="<<mode<<" cpu_edges=0 complete_htif_restore=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HTIF_EXIT_DPI
extern "C" int tsi_htif_exit(const char *m,const char *s,const char *o,const char *r,const char *f){return run(m,s,o,r,f);}
extern "C" void tsi_htif_exit_status(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=6)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5]);}
#endif
