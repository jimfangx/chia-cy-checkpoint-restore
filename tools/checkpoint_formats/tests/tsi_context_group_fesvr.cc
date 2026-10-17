// Real source and fresh restricted wrapper contexts; host-operation boundaries.
#define TSI_HOST_GROUP_DPI
#include "tsi_host_group_fesvr.cc"
#include "fesvr/tsi_context_group.h"
#include <thread>
using context_group_t = firesim_tsi_context_group_t;
void tsi_terminal_fail_allocation_size(std::size_t);
static images_t load_context(const fs::path &p) {
  auto result=load_host(p);result.emplace_back("wrapper",bytes(p.string()+".wrapper"));return result;
}
static auto context_unprepared(const firesim_tsi_t &tsi) {
  auto result=host_unprepared(tsi);result.emplace_back("wrapper",tsi.host_wrapper_owner().save_checkpoint());return result;
}
static int context_run(const char *mode,const char *elf,const char *input,const char *metadata,
                       const char *source,const char *plan,const char *destination) {
  try {
    sigset_t set;sigemptyset(&set);for(int sig:{SIGINT,SIGTERM,SIGABRT})sigaddset(&set,sig);
    require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"block context signals");
    const fs::path out(destination);fs::create_directories(out);const std::string action(mode);
    std::vector<std::string> args{"syscall-polling","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-syscall-exit","+checkpoint-terminal-input="+std::string(input)};
    if(fs::path(input).filename().string().find("flush")!=std::string::npos)args.push_back("+cflush_addr=0x20004000");
    args.insert(args.end(),{"+permissive-off",elf});
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);context_group_t group(tsi);
    if(action=="capture"){
      syscall_startup(tsi);save(out/"startup.metadata",tsi.save_startup_metadata());save(out/"cut-0",group.inspect());
    }else{
      tsi.prepare_startup_metadata(bytes(metadata));const auto good=load_context(source);
      const auto before=context_unprepared(tsi);
      auto unchanged=[&]{require(context_unprepared(tsi)==before && !group.native_context_initialized(),"context partially published/entered");
        bool absent=false;try{tsi.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}require(absent,"context child published");};
      if(action=="invalid"){
        bool rejected=false;try{group.load(good);}catch(const std::runtime_error &){rejected=true;}
        require(rejected,"invalid context admitted");unchanged();
        std::cout<<"REJECTED owners=16 unpublished=1 context_entries=0 target_edges=0\n";return 0;
      }
      if(action=="atomic"){
        size_t malformed=0,membership=0,cross=0;
        auto reject=[&](const images_t &bad){bool failed=false;try{group.load(bad);}catch(const std::runtime_error &){failed=true;}
          require(failed,"bad context admitted");unchanged();};
        for(size_t i=0;i<good.size();++i){
          for(size_t n=0;n<good[i].second.size();++n){auto bad=good;bad[i].second.resize(n);reject(bad);++malformed;}
          for(unsigned n=0;n<2;++n){auto bad=good;if(n)bad[i].second.push_back(0);else bad[i].second[16]^=1;reject(bad);++malformed;}
          for(unsigned n=0;n<4;++n){auto bad=good;if(n==0)bad.erase(bad.begin()+i);if(n==1)bad.push_back(good[i]);
            if(n==2)bad[i].first="unknown";if(n==3)std::swap(bad[i],bad[(i+1)%good.size()]);reject(bad);++membership;}
        }
        for(unsigned phase:{0,2}){auto bad=good;bad[15].second.at(40)=phase;reject(bad);++cross;}
        long allocations=0;
        for(;;++allocations){bool failed=false;tsi_terminal_fail_allocation_after(allocations);
          try{group.load(good);}catch(const std::bad_alloc &){failed=true;}
          catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
          tsi_terminal_fail_allocation_after(-1);if(!failed)break;unchanged();}
        require(group.inspect()==good && !group.native_context_initialized(),"context atomic publication differs");
        std::ofstream(out/"atomic.txt")<<"malformed="<<malformed<<" membership="<<membership<<" cross="<<cross
          <<" allocation_failures="<<allocations<<" unchanged_on_failure=1 context_entries=0\n";return 0;
      }
      auto next=group.prepare(good);auto competitor=group.prepare(good);
      if(action.rfind("guard-",0)==0){
        if(action=="guard-wrapper"){auto b=tsi.host_wrapper_owner().save_checkpoint();b.at(40)=1;
          const_cast<checkpoint_owner_t &>(tsi.host_wrapper_owner()).load_checkpoint(b);
        }else if(action=="guard-peer")tsi.send_word(0xface);
        else if(action=="guard-exit")tsi.htif_exit(0);
        else if(action=="guard-stop")tsi.stop();
        else if(action=="guard-mask")require(!pthread_sigmask(SIG_UNBLOCK,&set,nullptr),"unblock");
        else if(action=="guard-pending")require(!std::raise(SIGTERM),"raise pending");
        else throw std::runtime_error("unknown context guard");
        auto observed=[&]{auto b=peers(tsi);b.emplace_back("outer",tsi.host_execution_owner().save_checkpoint());
          b.emplace_back("wrapper",tsi.host_wrapper_owner().save_checkpoint());return b;};
        const auto changed=observed();bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}
        require(failed && observed()==changed && !group.native_context_initialized(),"context late guard published");
        if(action=="guard-mask")pthread_sigmask(SIG_BLOCK,&set,nullptr);
        if(action=="guard-pending"){sigset_t term;sigemptyset(&term);sigaddset(&term,SIGTERM);timespec timeout{};
          require(sigtimedwait(&term,nullptr,&timeout)==SIGTERM,"drain pending");}
        if(action=="guard-mask" || action=="guard-pending"){next.commit();require(group.inspect()==good,"retry changed context");}
        std::cout<<"CONTEXT_LATE_GUARD "<<action<<" unpublished=1 services=0 target_edges=0 context_entries=0\n";return 0;
      }
      next.commit();require(group.inspect()==good && !group.native_context_initialized(),"zero-entry context readback differs");
      save(out/"preedge",group.inspect());
      for(unsigned which=0;which<4;++which){bool failed=false;
        try{if(which==0)next.commit();else if(which==1)competitor.commit();else if(which==2)tsi.tick();else tsi.switch_to_host();}
        catch(const std::runtime_error &){failed=true;}
        require(failed && group.inspect()==good && !group.native_context_initialized(),"context admission guard failed");}
      if(action=="thread"){
        bool rejected=false;std::thread worker([&]{try{group.resume();}catch(const std::runtime_error &){rejected=true;}});worker.join();
        require(rejected && group.inspect()==good && !group.native_context_initialized(),"foreign creator entered context");
        std::cout<<"FOREIGN_CREATOR rejected=1 unpublished=1 context_entries=0 target_edges=0\n";return 0;
      }
      if(action=="allocation"){
        bool rejected=false;tsi_terminal_fail_allocation_size(1048576);
        try{group.resume();}catch(const std::bad_alloc &){rejected=true;}
        tsi_terminal_fail_allocation_size(0);
        require(rejected && group.inspect()==good && !group.native_context_initialized(),"context allocation failure changed owners");
        std::cout<<"CONTEXT_ALLOCATION stack_bytes=1048576 rejected=1 unchanged=1 retry=1\n";
      }
      if(action=="resume-mask" || action=="resume-pending"){
        for(unsigned initialized=0;initialized<2;++initialized){
          const auto state=group.inspect();
          require(group.native_context_initialized()==bool(initialized),"unexpected context initialization");
          if(action=="resume-mask")require(!pthread_sigmask(SIG_UNBLOCK,&set,nullptr),"unblock continuation");
          else require(!std::raise(SIGTERM),"raise continuation pending");
          bool failed=false;try{group.resume();}catch(const std::runtime_error &){failed=true;}
          if(action=="resume-mask")require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"reblock continuation");
          else {sigset_t term;sigemptyset(&term);sigaddset(&term,SIGTERM);timespec timeout{};
            require(sigtimedwait(&term,nullptr,&timeout)==SIGTERM,"drain continuation pending");}
          require(failed && group.inspect()==state && group.native_context_initialized()==bool(initialized),"continuation guard serviced");
          if(!initialized)group.resume();
        }
        std::cout<<"CONTEXT_RESUME_GUARD "<<action<<" boundaries=2 unchanged=1 services=0 target_edges=0\n";return 0;
      }
      if(action=="corrupt")const_cast<checkpoint_owner_t &>(tsi.syscall_exit_owner()).load_checkpoint(bytes(std::string(source)+".fault"));
      std::cout<<"COMPLETE_CONTEXT_READBACK owners=16 services=0 target_edges=0 context_entries=0\n";
    }
    const auto cut=action=="capture"?0:std::stoul(fs::path(source).filename().string().substr(4));
    std::ifstream steps(plan);require(bool(steps),"missing context plan");std::string line;size_t op=0,count=0,resumes=0;
    std::ofstream continued(out/"continuation.bin",std::ios::binary);
    while(std::getline(steps,line)){
      if(++op<=cut)continue;
      std::istringstream in(line);std::string kind;uint32_t n;in>>kind;
      if(kind=="TICK"){if(action=="capture")tsi.tick();else group.resume();++resumes;}
      else if(kind=="SEND"){in>>n;tsi.send_word(n);}
      else if(kind=="PACKET"){
        size_t word=0;while(in>>n){require(tsi.data_available(),"missing context packet");const auto actual=tsi.in_bits();
          if(actual!=n){require(action=="corrupt" && tsi.in_bits()==actual,"unexpected context divergence");
            std::cout<<"FIRST_DIVERGENCE operation="<<op<<" word="<<word<<" expected="<<n<<" actual="<<actual
              <<" acknowledged=0 fresh_context=1\n";return 0;}
          require(tsi.recv_word()==n,"context packet changed");++word;}
      }else throw std::runtime_error("unknown context operation");
      const auto actual=group.inspect();
      if(action=="capture")save(out/("cut-"+std::to_string(op)),actual);
      else for(const auto &[name,b]:actual)continued.write(reinterpret_cast<const char *>(b.data()),b.size());
      ++count;
    }
    require(action!="corrupt" && tsi.done() && tsi.host_wrapper_owner().save_checkpoint().at(40)==2,"wrapper did not reach tail");
    for(unsigned i=0;i<3;++i){const auto before=group.inspect();if(action=="capture")tsi.tick();else group.resume();
      require(group.inspect()==before,"wrapper tail serviced");}
    std::cout<<"CONTEXT_GROUP operations="<<count<<" resumes="<<resumes<<" owners=16 tail_ticks=3 startup_replays=0 target_edges=0 fresh="
      <<(action!="capture")<<" return="<<tsi.exit_code()<<"\n";return 0;
  }catch(const std::exception &e){tsi_terminal_fail_allocation_after(-1);tsi_terminal_fail_allocation_size(0);std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_CONTEXT_GROUP_DPI
extern "C" int tsi_context_group(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return context_run(m,e,i,b,s,p,d);}
extern "C" void tsi_context_group_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){return argc==8?context_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]):2;}
#endif
