// Reuse the unchanged production serial peer and direct-exit reference. The
// observer captures actual private provider fields, not the exit projection.
#define main htif_exit_unused_main
#include "tsi_htif_exit_fesvr.cc"
#undef main
#include "fesvr/tsi_htif_lifecycle.h"
#include <cstring>

class masked_t {
  sigset_t original;
public:
  masked_t() {
    sigset_t set;
    require(sigemptyset(&set)==0, "mask init");
    for(int sig:{SIGINT,SIGTERM,SIGABRT})require(sigaddset(&set,sig)==0,"mask add");
    require(pthread_sigmask(SIG_BLOCK,&set,&original)==0,"mask block");
  }
  ~masked_t(){if(pthread_sigmask(SIG_SETMASK,&original,nullptr))std::abort();}
};
static std::unique_ptr<firesim_tsi_t> destination(const char *elf) {
  std::vector<std::string> args{"lifecycle", "+permissive", "+permissive-off", elf};
  std::vector<char *> argv; for(auto &a:args)argv.push_back(a.data());
  return std::make_unique<firesim_tsi_t>(argv.size(),argv.data(),true);
}
static void fields(htif_t &htif,const fs::path &path) {
  const auto s=firesim_htif_lifecycle_read(htif);
  std::ofstream(path)<<s.has_exit<<' '<<s.raw_exit<<' '<<s.stopped<<' '
                     <<htif.done()<<' '<<htif.exit_code()<<'\n';
}
// Real FIFO peers exercise the publication primitive without claiming a
// complete HTIF aggregate. No provider/target service occurs in the callback.
static void transaction(std::vector<uint8_t> image,const fs::path &out,const std::string &which) {
  reference_t ref(which=="signature" ?
    std::vector<std::string>{"+signature="+(out/"unused-signature").string(),"none"} :
    std::vector<std::string>{"none"});
  firesim_tsi_htif_lifecycle_t owner(ref);
  firesim_tsi_serial_state_t peer,candidate;
  peer.issue_read(0x80001234,8);peer.push_response(0x11223344);
  const uint32_t payload[]{0xdeadbeef,0xfedcba98};
  candidate.issue_write(0x1234567887654320,8,payload);
  candidate.push_response(0x5678);candidate.push_response(0x99);
  const auto before=peer.save_checkpoint(),replacement=candidate.save_checkpoint();
  save(out/"before.serial",before);save(out/"candidate.serial",replacement);
  unsigned callbacks=0;
  auto publish=[&]() noexcept {peer.swap_state(candidate);++callbacks;};
  if(which=="signature") {
    bool rejected=false;try{auto next=owner.prepare_checkpoint(image);}
    catch(const std::runtime_error &){rejected=true;}
    require(rejected && !ref.done() && ref.exit_code()==0,"signature preparation changed lifecycle");
  } else {
    const auto initial=owner.save_checkpoint();
    auto next=owner.prepare_checkpoint(image);
    require(owner.save_checkpoint()==initial && peer.save_checkpoint()==before,"preparation published state");
    const auto wanted=image;image.clear(); // candidate owns parsed fields, not image storage
    if(which=="commit") {
      next.commit(publish);
      require(callbacks==1 && owner.save_checkpoint()==wanted && peer.save_checkpoint()==replacement,
              "incomplete lifecycle/peer publication");
      bool rejected=false;try{next.commit(publish);}catch(const std::runtime_error &){rejected=true;}
      require(rejected && callbacks==1 && owner.save_checkpoint()==wanted && peer.save_checkpoint()==replacement,
              "consumed lifecycle candidate published twice");
      save(out/"after.lifecycle",owner.save_checkpoint());fields(ref,out/"after.fields");
    } else if(which=="abandon" || which=="peer-invalid") {
      if(which=="peer-invalid") {
        bool rejected=false;try{candidate.load_checkpoint({});}catch(const std::runtime_error &){rejected=true;}
        require(rejected,"invalid peer candidate accepted");
      }
      require(owner.save_checkpoint()==initial,"unpublished candidate changed provider");
      save(out/"after.lifecycle",owner.save_checkpoint());fields(ref,out/"after.fields");
    } else {
      sigset_t set;sigemptyset(&set);sigaddset(&set,SIGTERM);
      struct sigaction original{},changed{};
      if(which=="pending" || which=="delivered") {
        require(std::raise(SIGTERM)==0,"queue late signal");
        if(which=="delivered") {
          require(pthread_sigmask(SIG_UNBLOCK,&set,nullptr)==0,"deliver late signal");
          require(pthread_sigmask(SIG_BLOCK,&set,nullptr)==0,"block late signal");
        }
      } else if(which=="mask")require(pthread_sigmask(SIG_UNBLOCK,&set,nullptr)==0,"late unblock");
      else if(which=="handler") {
        changed.sa_handler=SIG_IGN;sigemptyset(&changed.sa_mask);
        require(sigaction(SIGTERM,&changed,&original)==0,"late handler");
      } else if(which=="occupied-exit")ref.htif_exit(0);
      else if(which=="occupied-stop")ref.stop();
      else throw std::runtime_error("unknown lifecycle transaction");
      bool rejected=false;try{auto other=owner.prepare_checkpoint(wanted);}
      catch(const std::runtime_error &){rejected=true;}
      require(rejected,"late destination guard missing during preparation");
      rejected=false;try{next.commit(publish);}catch(const std::runtime_error &){rejected=true;}
      require(rejected && !callbacks && peer.save_checkpoint()==before,"late guard partially published peers");
      if(which=="pending") {
        int signal=0;require(sigwait(&set,&signal)==0 && signal==SIGTERM,"drain late signal");
      } else if(which=="mask")require(pthread_sigmask(SIG_BLOCK,&set,nullptr)==0,"reblock late signal");
      else if(which=="handler")require(sigaction(SIGTERM,&original,nullptr)==0,"restore late handler");
      require(ref.done()==(which=="occupied-stop") && ref.exit_code()==0,"late guard changed lifecycle fields");
      if(which!="delivered") {
        save(out/"after.lifecycle",owner.save_checkpoint());fields(ref,out/"after.fields");
        if(which!="occupied-stop" && which!="occupied-exit")
          require(owner.save_checkpoint()==initial,"late guard changed provider");
      }
    }
  }
  require(callbacks==(which=="commit"),"wrong transaction callback count");
  require(peer.save_checkpoint()==(which=="commit"?replacement:before),"transaction changed peer on rejection");
  save(out/"after.serial",peer.save_checkpoint());
  std::ofstream(out/"transaction.txt")<<which<<" callbacks="<<callbacks<<" target_services=0\n";
}
static int lifecycle_run(const char *mode,const char *source,const char *destination_path,
                         const char *raw,const char *flush) {
  try {
    fs::path out(destination_path);fs::create_directories(out);
    const std::string op(mode);
    masked_t mask;
    if(op=="transaction") {
      transaction(bytes(source),out,raw);
    } else if(op=="capture") {
      capture(source,out,std::stoull(raw),std::stoull(flush),[](htif_t &htif,const fs::path &prefix){
        firesim_tsi_htif_lifecycle_t owner(htif);
        save(prefix.string()+".lifecycle",owner.save_checkpoint());
        fields(htif,prefix.string()+".fields");
      });
    } else if(op=="raw") {
      reference_t ref;
      const uint32_t bits=std::stoull(raw);int signed_raw;std::memcpy(&signed_raw,&bits,sizeof(bits));
      if(std::string(flush)!="absent")ref.htif_exit(signed_raw);
      firesim_tsi_htif_lifecycle_t owner(ref);
      save(out/"requested.lifecycle",owner.save_checkpoint());fields(ref,out/"requested.fields");
      ref.stop();save(out/"stopped.lifecycle",owner.save_checkpoint());fields(ref,out/"stopped.fields");
    } else if(op=="guard") {
      reference_t ref(op=="guard" && std::string(raw)=="signature" ?
                      std::vector<std::string>{"+signature="+(out/"unused-signature").string(),"none"} :
                      std::vector<std::string>{"none"});
      firesim_tsi_htif_lifecycle_t owner(ref);
      const std::string which(raw);
      if(which=="pending-exit" || which=="delivered-exit")ref.htif_exit(0);
      const auto before=which=="signature" ? std::vector<uint8_t>{} : owner.save_checkpoint();
      const auto image=bytes(source);
      sigset_t set;sigemptyset(&set);sigaddset(&set,SIGTERM);
      struct sigaction original{},changed{};
      if(which=="pending" || which=="delivered" || which=="pending-exit" || which=="delivered-exit") {
        require(std::raise(SIGTERM)==0,"queue signal");
        if(which.rfind("delivered",0)==0)require(pthread_sigmask(SIG_UNBLOCK,&set,nullptr)==0,"deliver signal");
        if(which.rfind("delivered",0)==0)require(pthread_sigmask(SIG_BLOCK,&set,nullptr)==0,"block after delivery");
      } else if(which=="mask") {
        require(pthread_sigmask(SIG_UNBLOCK,&set,nullptr)==0,"unblock signal");
      } else if(which=="handler") {
        changed.sa_handler=SIG_IGN;sigemptyset(&changed.sa_mask);
        require(sigaction(SIGTERM,&changed,&original)==0,"change handler");
      } else if(which=="occupied-exit")ref.htif_exit(0);
      else if(which=="occupied-stop")ref.stop();
      else require(which=="signature","unknown guard");
      bool read_rejected=false;
      try{owner.save_checkpoint();}catch(const std::runtime_error &){read_rejected=true;}
      require(read_rejected==(which!="occupied-exit" && which!="occupied-stop"),"missing capture guard");
      bool rejected=false;try{owner.load_checkpoint(image);}catch(const std::runtime_error &){rejected=true;}
      require(rejected,"missing lifecycle restore guard");
      if(which=="pending" || which=="pending-exit") {
        int received=0;require(sigwait(&set,&received)==0 && received==SIGTERM,"drain pending signal");
      } else if(which=="mask")require(pthread_sigmask(SIG_BLOCK,&set,nullptr)==0,"reblock signal");
      else if(which=="handler")require(sigaction(SIGTERM,&original,nullptr)==0,"restore handler");
      // Delivered signals cannot be undone; inspect the actual visible fields
      // without clearing that process-global flag or invoking a target service.
      require(ref.done()==(which=="occupied-stop") && ref.exit_code()==0,"guard partially assigned provider fields");
      if(which.rfind("delivered",0)!=0 && which!="occupied-exit" && which!="occupied-stop" && which!="signature")
        require(owner.save_checkpoint()==before,"guard mutated private provider state");
      if(which=="occupied-exit" || which=="occupied-stop")fields(ref,out/"unchanged.fields");
      std::ofstream(out/"guard.txt")<<which<<" rejected=1 target_services=0\n";
    } else {
      auto tsi=destination("none");firesim_tsi_htif_lifecycle_t owner(*tsi);
      const auto before=owner.save_checkpoint(),serial=tsi->serial_queue_owner().save_checkpoint();
      const auto image=bytes(source);
      if(op=="reject") {
        bool prepare_rejected=false;
        try{auto next=owner.prepare_checkpoint(image);}catch(const std::runtime_error &){prepare_rejected=true;}
        require(prepare_rejected && owner.save_checkpoint()==before,"malformed preparation changed lifecycle");
        std::ofstream(out/"prepare-rejected.txt")<<"rejected=1 target_services=0\n";
        bool rejected=false;try{owner.load_checkpoint(image);}catch(const std::runtime_error &){rejected=true;}
        require(rejected && owner.save_checkpoint()==before,"malformed lifecycle partially restored");
        save(out/"unchanged.lifecycle",owner.save_checkpoint());
      } else {
        owner.load_checkpoint(image);
        save(out/"pre-service.lifecycle",owner.save_checkpoint());fields(*tsi,out/"pre-service.fields");
        const auto state=firesim_htif_lifecycle_read(*tsi);
        if(op=="corrupt") {
          const uint32_t expected=std::stoull(raw);
          require(state.has_exit && state.raw_exit!=expected,"missing lifecycle corruption");
          std::ofstream(out/"first-divergence.txt")<<"FIRST_DIVERGENCE boundary=0 signal=exitcode.raw expected="
            <<expected<<" actual="<<state.raw_exit<<" acknowledged=0 target_services=0\n";
        } else {
          require(op=="restore","unknown lifecycle operation");
          if(!state.stopped)tsi->stop();
          save(out/"final.lifecycle",owner.save_checkpoint());fields(*tsi,out/"final.fields");
        }
      }
      require(tsi->serial_queue_owner().save_checkpoint()==serial,"lifecycle performed target service");
      save(out/"unchanged.serial",serial);
    }
    std::cout<<"HTIF_LIFECYCLE operation="<<op<<" cpu_edges=0 complete_htif_restore=0\n";return 0;
  } catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HTIF_LIFECYCLE_DPI
extern "C" int tsi_htif_lifecycle(const char *m,const char *s,const char *o,const char *r,const char *f){return lifecycle_run(m,s,o,r,f);}
extern "C" void tsi_htif_lifecycle_status(int status){std::exit(status);}
#else
int main(int argc,char **argv){if(argc!=6)return 2;return lifecycle_run(argv[1],argv[2],argv[3],argv[4],argv[5]);}
#endif
