// Production polling/syscall dispatch with fresh, atomic component restoration.
#define main polling_prepare_unused_main
#include "tsi_polling_prepare_fesvr.cc"
#undef main
#include "fesvr/tsi_polling_syscall.h"
#include <csignal>
#include <pthread.h>
#include <dirent.h>
#include <iomanip>
#include <sys/stat.h>
using syscall_group_t = firesim_tsi_polling_syscall_t;
static images_t load_syscall(const fs::path &p) {
  auto result = load(p);
  for (auto name : {"syscall", "lifecycle"}) result.emplace_back(name, bytes(p.string()+"."+name));
  return result;
}
static void syscall_startup(firesim_tsi_t &tsi) {
  tsi.tick(); tsi.tick(); firesim_loadmem_t request; std::array<uint8_t,16> data{};
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"startup write");
  tsi.recv_loadmem_data(data.data(),16); tsi.tick();
  require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"startup read");
  tsi.send_loadmem_word(0xaabbccdd); tsi.send_loadmem_word(0x11223344); tsi.tick();
  require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"startup merge");
  tsi.recv_loadmem_data(data.data(),8); tsi.set_loaded_in_target(true); tsi.tick();
}
// Audit the actual process descriptor table, including the installed HTIF's
// embedded syscall_proxy. A missing optional second session does not remove
// that inherited owner. Never infer descriptor ownership from object names.
using descriptors_t = std::map<int, std::string>;
static descriptors_t descriptors() {
  DIR *directory=opendir("/proc/self/fd");require(directory,"cannot inspect descriptors");
  struct close_dir_t {DIR *p;~close_dir_t(){closedir(p);}} close{directory};
  descriptors_t result;
  while(auto entry=readdir(directory)) {
    char *end=nullptr;const auto fd=strtol(entry->d_name,&end,10);
    if(!*entry->d_name || *end || fd==dirfd(directory))continue;
    struct stat info{};require(!fstat(fd,&info),"descriptor changed during audit");
    std::array<char,4096> target{};const auto path="/proc/self/fd/"+std::to_string(fd);
    const auto n=readlink(path.c_str(),target.data(),target.size());
    require(n>=0 && size_t(n)<target.size(),"cannot inspect descriptor target");
    const auto status=fcntl(fd,F_GETFL),flags=fcntl(fd,F_GETFD);
    require(status>=0 && flags>=0,"cannot inspect descriptor flags");
    std::ostringstream row;row<<info.st_dev<<' '<<info.st_ino<<' '<<info.st_mode<<' '
      <<info.st_rdev<<' '<<status<<' '<<flags<<' '<<std::quoted(std::string(target.data(),n));
    require(result.emplace(fd,row.str()).second,"duplicate descriptor");
  }
  return result;
}
static void save_descriptors(const fs::path &p,const descriptors_t &fds) {
  std::ofstream f(p);for(const auto &[fd,value]:fds)f<<fd<<' '<<value<<'\n';
  require(bool(f),"cannot save descriptors");
}
static void require_additions(const descriptors_t &before,const descriptors_t &after,size_t count) {
  require(after.size()==before.size()+count,"unexpected session descriptor count");
  for(const auto &[fd,value]:before)
    require(after.count(fd) && after.at(fd)==value,"session changed an existing descriptor");
  std::vector<std::string> added;
  for(const auto &[fd,value]:after)if(!before.count(fd))added.push_back(value);
  std::vector<std::string> expected;
  for(size_t i=0;i<count/3;++i)
    expected.insert(expected.end(),{before.at(0),before.at(1),before.at(1)});
  std::sort(added.begin(),added.end());std::sort(expected.begin(),expected.end());
  require(added==expected,"session descriptor identities differ from installed duplicates");
}
static void descriptor_lifetime(std::vector<char *> &argv,bool ordinary,const fs::path &out) {
  const auto before=descriptors();save_descriptors(out/"before.fds",before);
  {
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    const auto constructed=descriptors();require_additions(before,constructed,ordinary?3:0);
    save_descriptors(out/"constructed.fds",constructed);
    const auto &proxy=firesim_htif_require_dormant_proxy_api();
    bool rejected=false;
    if(ordinary) {
      try{proxy.validate(tsi);}catch(const std::runtime_error &){rejected=true;}
      require(rejected,"ordinary live proxy admitted as retired");
    } else {
      proxy.validate(tsi);
      try{proxy.retire(tsi);}catch(const std::runtime_error &){rejected=true;}
      require(rejected,"proxy retirement repeated");
      proxy.validate(tsi);
    }
    require(descriptors()==constructed,"proxy guard changed descriptor table");
    syscall_startup(tsi);
    const auto polling=descriptors();require_additions(constructed,polling,ordinary?3:0);
    save_descriptors(out/"polling.fds",polling);
    // Complete a zero mailbox read and each actual idle yield, then issue
    // the next mailbox read. Every suspension has the same descriptor set.
    while(tsi.data_available())tsi.recv_word();
    tsi.send_word(0);tsi.tick();tsi.send_word(0);tsi.tick();
    for(unsigned i=0;i<4;++i) {
      require(descriptors()==polling,"idle changed descriptors");
      save_descriptors(out/("idle-"+std::to_string(i)+".fds"),descriptors());
      if(i<3)tsi.tick();
    }
    require(tsi.data_available() && !tsi.done(),"idle did not return to mailbox read");
    if(!ordinary)syscall_group_t(tsi).inspect();
  } // Destruction must release the inherited and optional suspended session.
  const auto destroyed=descriptors();require(destroyed==before,"suspended teardown leaked/closed descriptors");
  save_descriptors(out/"destroyed.fds",destroyed);
  std::cout<<"DESCRIPTOR_LIFETIME inherited="<<(ordinary?3:0)<<" polling_added="<<(ordinary?3:0)
    <<" idle_cuts=4 teardown_equal=1 ordinary="<<ordinary<<" target_edges=0\n";
  std::cout<<"PROXY_GUARD retired="<<!ordinary<<" rejection=1 descriptors_unchanged=1\n";
}
static auto unprepared(const firesim_tsi_t &tsi) {
  auto result=peers(tsi);
  result.emplace_back("lifecycle",firesim_tsi_htif_lifecycle_t(const_cast<firesim_tsi_t &>(tsi)).save_checkpoint());
  return result;
}
static void atomic_syscall(firesim_tsi_t &tsi,syscall_group_t &group,const images_t &good,const fs::path &out) {
  const auto before=unprepared(tsi); size_t malformed=0,membership=0,cross=0;
  auto unchanged=[&] {
    require(unprepared(tsi)==before,"invalid syscall partially published peers");
    bool absent=false;try{tsi.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}
    require(absent,"invalid syscall published polling caller");
  };
  auto reject=[&](const images_t &bad) {
    bool failed=false;try{group.load(bad);}catch(const std::runtime_error &){failed=true;}
    require(failed,"invalid syscall aggregate accepted");unchanged();
  };
  for(size_t i=0;i<good.size();++i) {
    for(size_t n=0;n<good[i].second.size();++n){auto bad=good;bad[i].second.resize(n);reject(bad);++malformed;}
    for(unsigned n=0;n<2;++n){auto bad=good;if(n)bad[i].second.push_back(0);else bad[i].second[16]^=1;reject(bad);++malformed;}
    for(unsigned n=0;n<4;++n){auto bad=good;
      if(n==0)bad.erase(bad.begin()+i);if(n==1)bad.push_back(good[i]);
      if(n==2)bad[i].first="unknown";if(n==3)std::swap(bad[i],bad[(i+1)%good.size()]);
      reject(bad);++membership;}
  }
  auto put=[](auto &b,size_t at,uint64_t v){for(unsigned i=0;i<8;++i)b.at(at+i)=uint8_t(v>>(8*i));};
  // Individually valid fields/images with incompatible parent/child/provider.
  for(unsigned n=0;n<7;++n){auto bad=good;
    if(n==0)put(bad[0].second,64,0x2000); // command disagrees with syscall
    if(n==1){bad[0].second.resize(88);put(bad[0].second,72,1);put(bad[0].second,80,1);}
    if(n==2)bad[12].second[112]^=2; // raw exit argument vs provider
    if(n==3){put(bad[13].second,56,0);put(bad[13].second,64,0);}
    if(n==4)put(bad[13].second,72,1); // unowned stop
    if(n==5){put(bad[8].second,48,1);bad[8].second.resize(64);put(bad[8].second,56,1ULL<<56);}
    if(n==6){put(bad[9].second,bad[9].second.size()-8,1);bad[9].second.push_back('X');}
    reject(bad);++cross;}
  long allocations=0;
  for(;;++allocations){bool exhausted=false;tsi_terminal_fail_allocation_after(allocations);
    try{group.load(good);}catch(const std::bad_alloc &){exhausted=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}
    tsi_terminal_fail_allocation_after(-1);if(!exhausted)break;unchanged();}
  require(allocations>40 && group.inspect()==good,"allocation coverage incomplete");
  std::ofstream(out/"atomic.txt")<<"malformed="<<malformed<<" membership="<<membership<<" cross="<<cross
    <<" allocation_failures="<<allocations<<" unchanged_on_failure=1\n";
}
static int syscall_run(const char *mode,const char *elf,const char *input,const char *metadata,
                       const char *source,const char *plan,const char *destination) {
  try {
    sigset_t set;sigemptyset(&set);for(int sig:{SIGINT,SIGTERM,SIGABRT})sigaddset(&set,sig);
    require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"block signals");
    fs::path out(destination);fs::create_directories(out);std::string action(mode);
    std::vector<std::string> args{"syscall-polling","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-syscall-exit","+checkpoint-terminal-input="+std::string(input)};
    // The input basename selects only immutable test configuration, also bound
    // into startup metadata. No state is inferred from a saved host pointer.
    const bool flush=fs::path(input).filename().string().find("flush")!=std::string::npos;
    if(flush)args.push_back("+cflush_addr=0x20004000");
    if(action=="entry-duplicate")args.push_back("+checkpoint-syscall-exit");
    if(action=="entry-signature")args.push_back("+signature=unsupported");
    if(action=="entry-unsealed")args.erase(args.begin()+5);
    if(action=="descriptors-ordinary")args.erase(args.begin()+4);
    args.insert(args.end(),{"+permissive-off",elf});
    std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());
    if(action.rfind("entry-",0)==0) {
      bool failed=false;try{firesim_tsi_t candidate(argv.size(),argv.data(),true);}catch(const std::runtime_error &){failed=true;}
      require(failed,"unsupported entry admitted");std::cout<<"ENTRY_REJECTED "<<action<<" startup=0 target_edges=0\n";return 0;
    }
    if(action.rfind("descriptors-",0)==0) {
      descriptor_lifetime(argv,action=="descriptors-ordinary",out);return 0;
    }
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    syscall_group_t group(tsi);
    if(action=="capture") {
      syscall_startup(tsi);save(out/"startup.metadata",tsi.save_startup_metadata());
      save(out/"cut-0",group.inspect());
    } else {
      tsi.prepare_startup_metadata(bytes(metadata));const auto good=load_syscall(source);
      if(action=="atomic"){atomic_syscall(tsi,group,good,out);return 0;}
      if(action=="invalid") {
        const auto before=unprepared(tsi);bool failed=false;try{group.load(good);}catch(const std::runtime_error &){failed=true;}
        require(failed && unprepared(tsi)==before,"invalid group partially restored");
        std::cout<<"REJECTED owners=14 unpublished=1 target_edges=0 context_entries=0\n";return 0;
      }
      if(action.rfind("guard-",0)==0) {
        const auto before=unprepared(tsi);auto next=group.prepare(good);
        if(action=="guard-pending")require(!std::raise(SIGTERM),"raise pending");
        else if(action=="guard-mask")require(!pthread_sigmask(SIG_UNBLOCK,&set,nullptr),"unblock signals");
        else if(action=="guard-exit")tsi.htif_exit(0);
        else if(action=="guard-stop")tsi.stop();
        else if(action=="guard-peer")tsi.send_word(0xface);
        else throw std::runtime_error("unknown late guard");
        const auto changed=peers(tsi);bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}
        require(failed && peers(tsi)==changed,"late guard published peers");
        if(action=="guard-mask")pthread_sigmask(SIG_BLOCK,&set,nullptr);
        if(action=="guard-pending"){sigset_t term;sigemptyset(&term);sigaddset(&term,SIGTERM);timespec timeout{};
          require(sigtimedwait(&term,nullptr,&timeout)==SIGTERM,"drain pending");}
        if(action=="guard-mask" || action=="guard-pending"){
          require(unprepared(tsi)==before,"repair changed peers");next.commit();require(group.inspect()==good,"retry incomplete");}
        std::cout<<"LATE_GUARD "<<action<<" unpublished=1 target_edges=0 context_entries=0\n";return 0;
      }
      auto owned=good;auto next=group.prepare(owned);owned.clear();next.commit();
      require(group.inspect()==good,"incomplete zero-service readback");save(out/"preedge",group.inspect());
      bool failed=false;try{next.commit();}catch(const std::runtime_error &){failed=true;}require(failed,"candidate repeated");
      failed=false;try{tsi.tick();}catch(const std::runtime_error &){failed=true;}require(failed && group.inspect()==good,"context admitted");
      failed=false;try{tsi.advance_prepared_polling_components();}catch(const std::runtime_error &){failed=true;}
      require(failed && group.inspect()==good,"narrow polling omitted caller");
      if(action=="terminal-corrupt") {
        auto image=tsi.terminal_owner().save_checkpoint();require(image.size()==72,"nonempty terminal fixture");
        image.at(image.size()-8)=1;image.push_back('X');
        const_cast<checkpoint_owner_t &>(tsi.terminal_owner()).load_checkpoint(image);
        const auto before=peers(tsi);
        for(unsigned which=0;which<2;++which){failed=false;
          try{if(which)group.advance();else group.inspect();}catch(const std::runtime_error &){failed=true;}
          require(failed && peers(tsi)==before,"terminal corruption admitted or serviced");}
        std::cout<<"TERMINAL_CORRUPTION rejected=1 services=0 startup_binding=1\n";return 0;
      }
      if(action.rfind("unsupported-",0)==0 && action!="unsupported-selector") {
        while(tsi.data_available())tsi.recv_word();
        uint64_t command=action=="unsupported-odd"?1:1ULL<<56;
        tsi.send_word(command);tsi.send_word(command>>32);
        failed=false;try{group.advance();}catch(const std::runtime_error &){failed=true;}
        require(failed && !tsi.data_available() && !firesim_htif_lifecycle_read(tsi).has_exit,"unowned command cleared/dispatched");
        std::cout<<"UNSUPPORTED_COMMAND rejected=1 clear_packets=0 exit_services=0\n";return 0;
      }
      if(action=="corrupt") {
        const auto image=bytes(std::string(source)+".fault");
        const_cast<checkpoint_owner_t &>(tsi.syscall_exit_owner()).load_checkpoint(image);
      }
    }
    const size_t cut=action=="capture"?0:std::stoul(fs::path(source).filename().string().substr(4));
    std::ifstream steps(plan);require(bool(steps),"missing plan");std::string line;size_t op=0,count=0;
    std::ofstream continued(out/"continuation.bin",std::ios::binary);
    while(std::getline(steps,line)) {
      if(++op<=cut)continue;std::istringstream in(line);std::string kind;uint64_t n=0;in>>kind;
      if(kind=="TICK"){
        try{if(action=="capture")tsi.tick();else group.advance();}
        catch(const std::runtime_error &){
          if(action!="unsupported-selector")throw;
          require(!firesim_htif_lifecycle_read(tsi).has_exit && !tsi.data_available(),"unowned selector issued exit/writeback/response");
          std::cout<<"UNSUPPORTED_SELECTOR rejected=1 exit_services=0 writeback=0 response=0\n";return 0;
        }
      }
      else if(kind=="SEND"){in>>n;if(action=="unsupported-selector" && n==93)n=64;tsi.send_word(n);}
      else if(kind=="PACKET") {
        size_t word=0;while(in>>n){require(tsi.data_available(),"missing packet");const auto actual=tsi.in_bits();
          if(actual!=n){require(action=="corrupt" && tsi.in_bits()==actual,"unexpected first divergence");
            std::cout<<"FIRST_DIVERGENCE operation="<<op<<" word="<<word<<" expected="<<n<<" actual="<<actual
              <<" acknowledged=0 context_entries=0\n";return 0;}
          require(tsi.recv_word()==n,"packet changed");++word;}
      } else throw std::runtime_error("unknown plan operation");
      const auto actual=group.inspect();
      if(action=="capture")save(out/("cut-"+std::to_string(op)),actual);
      else {
        if(action!="corrupt" && action!="unsupported-selector")
          require(actual==load_syscall(fs::path(source).parent_path()/("cut-"+std::to_string(op))),"continuation mismatch");
        for(const auto &[name,b]:actual)continued.write(reinterpret_cast<const char *>(b.data()),b.size());
      }
      ++count;
    }
    require(action!="corrupt","semantic corruption undetected");
    require(action!="unsupported-selector","unsupported selector admitted");
    // Complete fromhost read, publish its pending response, then reach the
    // polling exit boundary. Fresh restoration intentionally does not stop.
    if(action=="capture")tsi.tick();else group.advance();
    std::vector<uint32_t> final_packet;
    if(flush)final_packet={1,0x20004000,0,1,0,0x80002000,0};
    final_packet.insert(final_packet.end(),{1,0x80002008,0,1,0,1,0});
    for(auto word:final_packet)require(tsi.data_available() && tsi.recv_word()==word,"final response/flush order");
    require(!tsi.data_available(),"extra final packet");
    const auto state=firesim_htif_lifecycle_read(tsi);
    require(state.has_exit && state.stopped==(action=="capture"),"stop ordering/provider mismatch");
    if(action!="capture"){
      save(out/"final",group.inspect());
      bool failed=false;try{group.advance();}catch(const std::runtime_error &){failed=true;}require(failed,"complete caller resumed");
    }
    std::ofstream(out/"completion.txt")<<"raw_exit="<<state.raw_exit<<" stopped="<<state.stopped
      <<" response=1 context_entries="<<(action=="capture"?"source":"0")<<"\n";
    std::cout<<"SYSCALL_POLLING operations="<<count<<" owners=14 restore_services=0 target_edges=0 fresh="
      <<(action!="capture")<<" complete=1\n";return 0;
  }catch(const std::exception &e){tsi_terminal_fail_allocation_after(-1);std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_POLLING_SYSCALL_DPI
extern "C" int tsi_polling_prepare(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return syscall_run(m,e,i,b,s,p,d);}
extern "C" void tsi_polling_prepare_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return syscall_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
