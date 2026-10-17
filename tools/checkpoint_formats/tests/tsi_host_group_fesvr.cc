// Production restricted outer/polling/provider aggregate; no context restore.
#define TSI_POLLING_SYSCALL_DPI
#include "tsi_polling_syscall_fesvr.cc"
#include "fesvr/tsi_host_group.h"
using host_group_t = firesim_tsi_host_group_t;
static images_t load_host(const fs::path &p) {
  auto result=load_syscall(p);result.emplace_back("outer",bytes(p.string()+".outer"));return result;
}
static auto host_unprepared(const firesim_tsi_t &tsi) {
  auto result=unprepared(tsi);result.emplace_back("outer",tsi.host_execution_owner().save_checkpoint());
  result.emplace_back("syscall",tsi.syscall_exit_owner().save_checkpoint());return result;
}
static void atomic_host(firesim_tsi_t &tsi,host_group_t &group,const images_t &good,const fs::path &out) {
  const auto before=host_unprepared(tsi);size_t malformed=0,membership=0,cross=0;
  auto unchanged=[&]{require(host_unprepared(tsi)==before,"host group partially published");
    bool absent=false;try{tsi.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}
    require(absent,"host group published child");};
  auto reject=[&](const images_t &bad){bool failed=false;try{group.load(bad);}catch(const std::runtime_error &){failed=true;}
    require(failed,"invalid host group admitted");unchanged();};
  for(size_t i=0;i<good.size();++i){
    for(size_t n=0;n<good[i].second.size();++n){auto bad=good;bad[i].second.resize(n);reject(bad);++malformed;}
    for(unsigned n=0;n<2;++n){auto bad=good;if(n)bad[i].second.push_back(0);else bad[i].second[16]^=1;
      reject(bad);++malformed;}
    for(unsigned n=0;n<4;++n){auto bad=good;
      if(n==0)bad.erase(bad.begin()+i);if(n==1)bad.push_back(good[i]);
      if(n==2)bad[i].first="unknown";if(n==3)std::swap(bad[i],bad[(i+1)%good.size()]);
      reject(bad);++membership;}
  }
  auto put=[](auto &b,size_t at,uint64_t v){for(unsigned i=0;i<8;++i)b.at(at+i)=uint8_t(v>>(8*i));};
  // Every outer phase is individually parseable. Parent/provider disagreement
  // must reject before any owner is published, including an occupied result.
  for(unsigned phase:{0,2,3,4}){auto bad=good;put(bad[14].second,48,phase);reject(bad);++cross;}
  auto bad=good;put(bad[13].second,72,1);reject(bad);++cross;
  long allocations=0;
  for(;;++allocations){bool failed=false;tsi_terminal_fail_allocation_after(allocations);
    try{group.load(good);}catch(const std::bad_alloc &){failed=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);if(!failed)break;unchanged();}
  require(allocations>40 && group.inspect()==good,"host allocation coverage incomplete");
  std::ofstream(out/"atomic.txt")<<"malformed="<<malformed<<" membership="<<membership<<" cross="<<cross
    <<" allocation_failures="<<allocations<<" unchanged_on_failure=1\n";
}
static int host_run(const char *mode,const char *elf,const char *input,const char *metadata,
                    const char *source,const char *plan,const char *destination) {
  try {
    sigset_t set;sigemptyset(&set);for(int sig:{SIGINT,SIGTERM,SIGABRT})sigaddset(&set,sig);
    require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"block signals");
    const fs::path out(destination);fs::create_directories(out);const std::string action(mode);
    std::vector<std::string> args{"syscall-polling","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-syscall-exit","+checkpoint-terminal-input="+std::string(input)};
    const bool flush=fs::path(input).filename().string().find("flush")!=std::string::npos;
    if(flush)args.push_back("+cflush_addr=0x20004000");
    args.insert(args.end(),{"+permissive-off",elf});
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);host_group_t group(tsi);
    if(action=="capture"){
      syscall_startup(tsi);save(out/"startup.metadata",tsi.save_startup_metadata());save(out/"cut-0",group.inspect());
    } else {
      tsi.prepare_startup_metadata(bytes(metadata));const auto good=load_host(source);
      if(action=="atomic"){atomic_host(tsi,group,good,out);return 0;}
      if(action=="invalid"){
        const auto before=host_unprepared(tsi);bool failed=false;try{group.load(good);}catch(const std::runtime_error &){failed=true;}
        require(failed && host_unprepared(tsi)==before,"invalid host group changed peers");
        bool absent=false;try{tsi.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}
        require(absent,"invalid published child");
        std::cout<<"REJECTED owners=15 unpublished=1 target_edges=0 context_entries=0\n";return 0;
      }
      if(action.rfind("guard-",0)==0){
        auto next=group.prepare(good);
        if(action=="guard-outer"){
          auto b=tsi.host_execution_owner().save_checkpoint();b.at(48)=2;
          const_cast<checkpoint_owner_t &>(tsi.host_execution_owner()).load_checkpoint(b);
        }else if(action=="guard-peer")tsi.send_word(0xface);
        else if(action=="guard-stop")tsi.stop();
        else if(action=="guard-exit")tsi.htif_exit(0);
        else if(action=="guard-pending")require(!std::raise(SIGTERM),"raise pending");
        else if(action=="guard-mask")require(!pthread_sigmask(SIG_UNBLOCK,&set,nullptr),"unblock");
        else throw std::runtime_error("unknown guard");
        const auto peers_before=peers(tsi);const auto outer=tsi.host_execution_owner().save_checkpoint();
        bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}
        require(failed && peers(tsi)==peers_before && tsi.host_execution_owner().save_checkpoint()==outer,"late host guard published");
        if(action=="guard-mask")pthread_sigmask(SIG_BLOCK,&set,nullptr);
        if(action=="guard-pending"){sigset_t term;sigemptyset(&term);sigaddset(&term,SIGTERM);timespec timeout{};
          require(sigtimedwait(&term,nullptr,&timeout)==SIGTERM,"drain pending");}
        if(action=="guard-mask" || action=="guard-pending"){next.commit();require(group.inspect()==good,"guard retry incomplete");}
        std::cout<<"HOST_LATE_GUARD "<<action<<" unpublished=1 services=0 target_edges=0 context_entries=0\n";return 0;
      }
      auto owned=good;auto next=group.prepare(owned);auto competitor=group.prepare(owned);owned.clear();next.commit();
      require(group.inspect()==good,"host zero-service readback differs");save(out/"preedge",group.inspect());
      for(unsigned which=0;which<3;++which){bool failed=false;
        try{if(which==0)next.commit();else if(which==1)competitor.commit();else tsi.tick();}
        catch(const std::runtime_error &){failed=true;}
        require(failed && group.inspect()==good,"host candidate/context guard admitted");}
      std::cout<<"COMPLETE_HOST_READBACK owners=15 services=0 target_edges=0 context_entries=0\n";
      if(action=="corrupt")const_cast<checkpoint_owner_t &>(tsi.syscall_exit_owner()).load_checkpoint(bytes(std::string(source)+".fault"));
    }
    const auto cut=action=="capture"?0:std::stoul(fs::path(source).filename().string().substr(4));
    std::ifstream steps(plan);require(bool(steps),"missing plan");std::string line;size_t op=0,count=0;
    std::ofstream continued(out/"continuation.bin",std::ios::binary);
    while(std::getline(steps,line)){
      if(++op<=cut)continue;
      std::istringstream in(line);std::string kind;uint32_t n;in>>kind;
      if(kind=="TICK"){if(action=="capture")tsi.tick();else group.advance();}
      else if(kind=="SEND"){in>>n;tsi.send_word(n);}
      else if(kind=="PACKET"){
        size_t word=0;while(in>>n){require(tsi.data_available(),"missing host packet");const auto actual=tsi.in_bits();
          if(actual!=n){require(action=="corrupt" && tsi.in_bits()==actual,"unexpected host divergence");
            std::cout<<"FIRST_DIVERGENCE operation="<<op<<" word="<<word<<" expected="<<n<<" actual="<<actual
              <<" acknowledged=0 context_entries=0\n";return 0;}
          require(tsi.recv_word()==n,"packet changed");++word;}
      }else throw std::runtime_error("unknown host operation");
      const auto actual=group.inspect();
      if(action=="capture" || action=="extend")save(out/("cut-"+std::to_string(op)),actual);
      else for(const auto &[name,b]:actual)continued.write(reinterpret_cast<const char *>(b.data()),b.size());
      ++count;
    }
    require(action!="corrupt","host corruption undetected");
    if(action=="capture"){
      // Production has no yield at stop or return-code collection. Record its
      // actual returned aggregate separately from explicit component cuts.
      tsi.tick();while(tsi.data_available())tsi.recv_word();save(out/"live-returned",group.inspect());
      for(unsigned i=0;i<3;++i){const auto before=group.inspect();tsi.tick();require(group.inspect()==before,"tail serviced");}
    }else {
      require(tsi.done() && tsi.host_execution_owner().save_checkpoint().at(48)==4,"host did not return");
      const auto before=group.inspect();bool failed=false;try{group.advance();}catch(const std::runtime_error &){failed=true;}
      require(failed && group.inspect()==before,"returned host advanced");
    }
    std::cout<<"HOST_GROUP operations="<<count<<" owners=15 complete=1 startup_replays=0 target_edges=0 fresh="
      <<(action!="capture")<<" return="<<tsi.exit_code()<<"\n";return 0;
  }catch(const std::exception &e){tsi_terminal_fail_allocation_after(-1);std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HOST_GROUP_DPI
extern "C" int tsi_host_group(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return host_run(m,e,i,b,s,p,d);}
extern "C" void tsi_host_group_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){return argc==8?host_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]):2;}
#endif
