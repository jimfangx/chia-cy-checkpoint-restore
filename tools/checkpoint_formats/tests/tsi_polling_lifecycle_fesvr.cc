// Atomic fourteen-owner publication, with the real installed HTIF provider.
#define main polling_unused_main
#include "tsi_polling_prepare_fesvr.cc"
#undef main
#include "fesvr/tsi_polling_lifecycle.h"
#include <csignal>
#include <pthread.h>
using group_t = firesim_tsi_polling_lifecycle_t;
static constexpr const char *extra_names[]{"exit","lifecycle"};
static images_t load_group(const fs::path &prefix) {
  auto result=load(prefix);
  for(auto name:extra_names)result.emplace_back(name,bytes(prefix.string()+"."+name));
  return result;
}
static auto destination_peers(const firesim_tsi_t &tsi) {
  auto result=peers(tsi);result.emplace_back("exit",tsi.save_htif_exit_component());return result;
}
static void no_caller(const firesim_tsi_t &tsi) {
  bool absent=false;try{tsi.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}
  require(absent,"aggregate published a caller/context");
}
static void step(firesim_tsi_t &tsi,const std::string &line,bool fresh) {
  std::istringstream in(line);std::string op;uint64_t n=0;in>>op;
  if(op=="TICK") {if(fresh)tsi.advance_prepared_polling_components();else tsi.tick();}
  else if(op=="SEND"){in>>n;tsi.send_word(n);}
  else if(op=="PACKET")while(in>>n)require(tsi.data_available() && tsi.recv_word()==n,"aggregate packet mismatch");
  else throw std::runtime_error("unknown aggregate operation");
}
static void startup(firesim_tsi_t &tsi) {
  tsi.tick();tsi.tick();firesim_loadmem_t request;std::array<uint8_t,16> data{};
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"startup write");
  tsi.recv_loadmem_data(data.data(),16);tsi.tick();
  require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"startup read");
  tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"startup merge");
  tsi.recv_loadmem_data(data.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
}
static void atomic_cases(firesim_tsi_t &tsi,const images_t &good,const fs::path &out) {
  group_t group(tsi);const auto before=destination_peers(tsi);
  const auto lifecycle=firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint();
  auto unchanged=[&] {
    require(destination_peers(tsi)==before && firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint()==lifecycle,
            "aggregate rejection partially published");no_caller(tsi);
  };
  size_t rejected=0;
  auto reject=[&](const images_t &bad){bool failed=false;try{auto next=group.prepare(bad);}
    catch(const std::runtime_error &){failed=true;}require(failed,"invalid aggregate accepted");unchanged();++rejected;};
  // Every truncated prefix, configuration-byte mutation and trailing byte of
  // each of the fourteen complete images. Parse all peers before publication.
  for(size_t i=0;i<good.size();++i) {
    for(size_t n=0;n<good[i].second.size();++n){auto bad=good;bad[i].second.resize(n);reject(bad);}
    {auto bad=good;bad[i].second.push_back(0);reject(bad);}
    {auto bad=good;bad[i].second[0]^=1;reject(bad);}
    {auto bad=good;bad.erase(bad.begin()+i);reject(bad);}
    {auto bad=good;bad[i].first="unknown";reject(bad);}
  }
  {auto bad=good;bad.push_back(good.back());reject(bad);}
  {auto bad=good;std::swap(bad[12],bad[13]);reject(bad);}
  // Optional zero and the raw low bit must not collapse into exit_code().
  for(auto fields:std::vector<std::array<uint64_t,3>>{{1,0,0},{1,2,0},{0,0,1},{1,3,1}}) {
    auto bad=good;widget_checkpoint_config_t image{32,{1,32,0}};
    for(auto n:fields)image.word(n);bad[13].second=image.bytes;reject(bad);
  }
  {auto bad=good;widget_checkpoint_config_t image{31,{1,32,0}};image.word(1);image.word(3);
    bad[12].second=image.bytes;reject(bad);}
  {auto abandoned=group.prepare(good);unchanged();}unchanged();
  size_t late=0;
  for(unsigned which=0;which<3;++which) {
    auto next=group.prepare(good);
    if(which==0)tsi.send_word(0x12345678);
    else if(which==1)tsi.set_loaded_in_target(true);
    else {auto b=tsi.terminal_owner().save_checkpoint();b.at(59)=1;
      const_cast<checkpoint_owner_t &>(tsi.terminal_owner()).load_checkpoint(b);}
    const auto changed=destination_peers(tsi);require(changed!=before,"ineffective late-peer fault");
    bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}
    require(failed && destination_peers(tsi)==changed &&
      firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint()==lifecycle,"late peer partially published");no_caller(tsi);++late;
    const auto &owner=which==0?tsi.serial_queue_owner():which==1?tsi.host_control_owner():tsi.terminal_owner();
    for(const auto &[name,b]:before)if(name==(which==0?"serial":which==1?"host":"terminal"))
      const_cast<checkpoint_owner_t &>(owner).load_checkpoint(b);
    unchanged();
  }
  long prepare_failures=0;
  for(;;++prepare_failures) {
    bool exhausted=false;tsi_terminal_fail_allocation_after(prepare_failures);
    try{auto next=group.prepare(good);}catch(const std::bad_alloc &){exhausted=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);unchanged();if(!exhausted)break;
  }
  auto owned=good;auto next=group.prepare(owned);auto competing=group.prepare(owned);owned.clear();
  long commit_failures=0;
  for(;;++commit_failures) {
    bool exhausted=false;tsi_terminal_fail_allocation_after(commit_failures);
    try{next.commit();}catch(const std::bad_alloc &){exhausted=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);if(!exhausted)break;unchanged();
  }
  require(prepare_failures>30 && commit_failures>0 && group.inspect()==good,"incomplete aggregate after allocation sweep");
  for(unsigned i=0;i<2;++i){bool failed=false;try{if(i)competing.commit();else next.commit();}
    catch(const std::runtime_error &){failed=true;}require(failed && group.inspect()==good,"aggregate candidate reused");}
  save(out/"preedge",group.inspect());
  std::cout<<"AGGREGATE_ATOMIC malformed_membership_cross="<<rejected<<" late_peers="<<late
           <<" prepare_allocations="<<prepare_failures<<" commit_allocations="<<commit_failures
           <<" abandoned=1 consumed_competing=2 owners=14 target_edges=0 context_entries=0\n";
}
static void late_guard(firesim_tsi_t &tsi,const images_t &good,const std::string &which,const fs::path &out) {
  group_t group(tsi);auto next=group.prepare(good);
  auto before=peers(tsi);save(out/"before",before);
  sigset_t set;sigemptyset(&set);sigaddset(&set,SIGTERM);
  struct sigaction old{},changed{};
  if(which=="pending" || which=="delivered") {
    require(std::raise(SIGTERM)==0,"late signal");
    if(which=="delivered") {pthread_sigmask(SIG_UNBLOCK,&set,nullptr);pthread_sigmask(SIG_BLOCK,&set,nullptr);}
  }else if(which=="mask")pthread_sigmask(SIG_UNBLOCK,&set,nullptr);
  else if(which=="handler"){changed.sa_handler=SIG_IGN;sigemptyset(&changed.sa_mask);require(!sigaction(SIGTERM,&changed,&old),"handler");}
  else if(which=="occupied-exit")tsi.htif_exit(0);
  else if(which=="occupied-stop")tsi.stop();
  else throw std::runtime_error("unknown late guard");
  bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}
  require(failed && peers(tsi)==before,"late provider guard published protocol owners");no_caller(tsi);
  require(tsi.done()==(which=="occupied-stop") && tsi.exit_code()==0,"late provider fields changed");
  save(out/"after",peers(tsi));
  if(which=="handler")sigaction(SIGTERM,&old,nullptr);
  if(which=="mask")pthread_sigmask(SIG_BLOCK,&set,nullptr);
  std::cout<<"AGGREGATE_LATE_GUARD "<<which<<" rejected=1 peers_unchanged=1 context_entries=0 target_edges=0\n";
}
static int aggregate_run(const char *mode,const char *elf,const char *input,const char *metadata,
                         const char *source,const char *plan,const char *destination) {
  try {
    sigset_t set;sigemptyset(&set);for(int sig:{SIGINT,SIGTERM,SIGABRT})sigaddset(&set,sig);
    require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"block lifecycle signals");
    fs::path out(destination);fs::create_directories(out);std::string action(mode);
    std::vector<std::string> args{"polling-prepare","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-terminal-input="+std::string(input),"+permissive-off",elf};
    std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());firesim_tsi_t tsi(argv.size(),argv.data(),true);
    group_t group(tsi);
    if(action=="capture") {
      startup(tsi);save(out/"startup.metadata",tsi.save_startup_metadata());
      save(out/"cut-0",group.inspect());size_t cut=0;std::string line;std::ifstream steps(plan);
      require(bool(steps),"capture plan missing");
      while(std::getline(steps,line)){step(tsi,line,false);++cut;
        if(tsi.done()){bool failed=false;try{group.inspect();}catch(const std::runtime_error &){failed=true;}
          require(failed,"unowned stopped parent accepted");std::ofstream(out/("cut-"+std::to_string(cut)+".stopped"))<<"rejected\n";}
        else save(out/("cut-"+std::to_string(cut)),group.inspect());}
      if(!tsi.done()){tsi.send_word(1);tsi.send_word(0);tsi.tick();require(tsi.done(),"source did not finish");}
      std::cout<<"AGGREGATE_CAPTURE operations="<<cut<<" owners=14 source_finished=1 target_edges=0\n";return 0;
    }
    tsi.prepare_startup_metadata(bytes(metadata));auto good=load_group(source);
    if(action=="atomic"){atomic_cases(tsi,good,out);return 0;}
    if(action.rfind("guard-",0)==0){late_guard(tsi,good,action.substr(6),out);return 0;}
    auto next=group.prepare(good);next.commit();save(out/"preedge",group.inspect());
    require(group.inspect()==good,"incomplete zero-edge aggregate");
    bool rejected=false;try{tsi.tick();}catch(const std::runtime_error &){rejected=true;}
    require(rejected,"aggregate enabled outer context");
    if(good[12].second.at(56)==1) {
      const auto before=group.inspect();rejected=false;
      try{tsi.advance_prepared_polling_components();}catch(const std::runtime_error &){rejected=true;}
      require(rejected && group.inspect()==before,"unowned exit parent continued");
      std::cout<<"AGGREGATE_READBACK owners=14 requested_exit=1 target_edges=0 target_services=0 context_entries=0\n";
      return 0;
    }
    require(action=="restore" || action=="continue","unknown aggregate mode");
    if(action=="continue") {
      const auto cut=std::stoul(fs::path(source).filename().string().substr(4));
      std::ifstream steps(plan);std::ofstream continued(out/"continuation.bin",std::ios::binary);std::string line;size_t op=0,count=0;
      while(std::getline(steps,line)) {if(++op<=cut)continue;step(tsi,line,true);auto actual=group.inspect();
        require(actual==load_group(fs::path(source).parent_path()/("cut-"+std::to_string(op))),"aggregate continuation mismatch");
        for(const auto &[n,b]:actual)continued.write(reinterpret_cast<const char *>(b.data()),b.size());++count;}
      require(bool(continued),"continuation readback failed");
      std::cout<<"AGGREGATE_CONTINUATION operations="<<count<<" owners=14 target_edges=0 context_entries=0\n";
    }
    std::cout<<"AGGREGATE_READBACK owners=14 requested_exit=0 target_edges=0 target_services=0 context_entries=0\n";
    return 0;
  }catch(const std::exception &e){tsi_terminal_fail_allocation_after(-1);std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_AGGREGATE_DPI
extern "C" int tsi_polling_prepare(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return aggregate_run(m,e,i,b,s,p,d);}
extern "C" void tsi_polling_prepare_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return aggregate_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
