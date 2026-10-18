// Actual heartbeat + clock drivers, independent MMIO service. These are
// fixture boundaries, not CPU cuts. Wall time is replaced only in this test.
#include "bridges/heartbeat.h"
#include "bridges/clock.h"
#include "core/config.h"
#include <filesystem>
#include <functional>
#include <iostream>
#include <memory>
#include <thread>
#include <type_traits>

#ifdef HEARTBEAT_PREPARED_PUBLICATION
static thread_local long fail_after = -1;
static thread_local bool allocation_failed = false;
void *operator new(std::size_t n) {
  if (fail_after >= 0 && fail_after-- == 0) {
    fail_after = -1; allocation_failed = true; throw std::bad_alloc();
  }
  if (auto p = std::malloc(n ? n : 1)) return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
#endif

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
static time_t fixture_time = 1700000000;
static unsigned time_calls = 0;
extern "C" time_t __wrap_time(time_t *p) {
  ++time_calls;
  if (p) *p = fixture_time;
  return fixture_time;
}

namespace {
constexpr unsigned operations = 15, config_bytes = 144;
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "heartbeat-component"};
const CLOCKBRIDGEMODULE_struct addresses{1088,1092,1096,1100,1104,1108};
const std::vector<uint8_t> sentinel{83,65,70,69};
void check(bool b, const std::string &s = "heartbeat assertion") {
  if (!b) throw std::runtime_error(s);
}
std::vector<uint8_t> read_file(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary); check(bool(f),"missing file "+p.string());
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
void write_file(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()),b.size());check(bool(f));
}
std::vector<std::string> arguments(const std::filesystem::path &p,unsigned scenario) {
  return {"+heartbeat-checkpoint-buffered", "+heartbeat-output="+(p/"heartbeat.csv").string(),
          "+heartbeat-polling-interval="+std::to_string(scenario==2?0:2),
          "+partitioned="+std::to_string(scenario==1)};
}
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  unsigned op=0; uint64_t calls=0,cycle=0;
  std::function<void()> hook;
  std::ofstream trace;
  std::vector<std::string> expected;
  size_t comparison=0;
  void line(const std::string &s,const std::string &signal="fixture") {
    trace << s << std::endl;
    if (!expected.empty()) {
      if (comparison>=expected.size() || expected[comparison]!=s)
        throw std::runtime_error("FIRST_MISMATCH fixture_cycle="+std::to_string(100+7*op)+
          " signal="+signal+" op="+std::to_string(op)+" observed="+s);
      ++comparison;
    }
  }
  void write(size_t a,uint32_t d) override {
    ++calls;if(hook)hook();check(a==1108 && d==1);
    line("W "+std::to_string(a)+" "+std::to_string(d),"heartbeat_poll");
  }
  uint32_t read(size_t a) override {
    ++calls;if(hook)hook();check(a==1100 || a==1104);
    auto v=uint32_t(a==1100?cycle:cycle>>32);
    line("R "+std::to_string(a)+" "+std::to_string(v),"heartbeat_cycle");return v;
  }
};
std::unique_ptr<mmio_t> mmio;
std::unique_ptr<clockmodule_t> clock_driver;
std::unique_ptr<heartbeat_t> driver;
std::filesystem::path directory;
unsigned index=0,rejected=0,selected_cut=0,scenario=0;bool restoring=false;
#ifdef HEARTBEAT_PREPARED_PUBLICATION
static_assert(!std::is_copy_constructible_v<heartbeat_t> && !std::is_move_constructible_v<heartbeat_t>);
void publish(prepared_checkpoint_t &candidate) {
  static_assert(noexcept(candidate.publish()));
  allocation_failed=false; fail_after=0;
  candidate.publish();
  const bool clean=fail_after==0 && !allocation_failed;
  fail_after=-1; check(clean,"publication allocated");
}
#endif
void rejects(const std::function<void()> &fn) {
  try {fn();}catch(const std::runtime_error &){++rejected;return;}
  throw std::runtime_error("expected heartbeat rejection");
}
void init(const std::filesystem::path &p,bool restore,unsigned cut,unsigned mode,bool compare) {
  driver.reset();clock_driver.reset();mmio=std::make_unique<mmio_t>();
  directory=p;index=cut;restoring=restore;scenario=mode;selected_cut=cut;
  check(cut<=operations && mode<3);
  write_file(p/"heartbeat.csv",sentinel);
  fixture_time=restore?1900000000:1700000000; // Restore must replace this epoch.
  clock_driver=std::make_unique<clockmodule_t>(*mmio,addresses,0,std::vector<std::string>{});
  driver=std::make_unique<heartbeat_t>(*mmio,*clock_driver,arguments(p,mode));
  mmio->trace.open(p/(restore?"restore-"+std::to_string(cut)+".trace":"reference.trace"));
  check(driver->checkpoint_schema()=="firesim.widget.heartbeat.v1");
  if(restore) {
    auto b=read_file(p/("cut-"+std::to_string(cut)+".owner"));
    driver->validate_checkpoint(b);
    const auto times=time_calls;
#ifdef HEARTBEAT_PREPARED_PUBLICATION
    auto candidate=driver->prepare_checkpoint_publication(b);
    b.clear(); b.shrink_to_fit(); // Candidate must own all decoded sample bytes.
    candidate->seal();publish(*candidate);
#else
    driver->load_checkpoint(b);
#endif
    check(time_calls==times,"restore sampled wall clock");
    write_file(p/("restore-"+std::to_string(cut)+".initial.owner"),driver->save_checkpoint());
    check(mmio->calls==0 && read_file(p/"heartbeat.csv")==sentinel,"restore side effect before first edge");
    if(compare && cut<operations) {
      std::ifstream f(p/"reference.trace");std::string s;bool selected=false;
      while(std::getline(f,s)) {
        if(s=="OP "+std::to_string(cut)+" C "+std::to_string(100+7*cut))selected=true;
        if(selected)mmio->expected.push_back(s);
      }
      check(!mmio->expected.empty());
    }
  }
}
int step() {
  if(index==operations) {
    write_file(directory/(restoring?"restore-"+std::to_string(selected_cut)+".final.owner":"cut-15.owner"),driver->save_checkpoint());
    if(restoring)check(mmio->comparison==mmio->expected.size(),"short heartbeat continuation");
    driver->finish();
    std::cout << "PASS: heartbeat component continuation\n";return 1;
  }
  if(!restoring)write_file(directory/("cut-"+std::to_string(index)+".owner"),driver->save_checkpoint());
  mmio->op=index;
  const uint64_t cycles[]={0,0,0x100000009ULL,0x100000009ULL,0x100000009ULL,
    0x100000011ULL,0x100000011ULL,0x100000011ULL,0x100000011ULL,0x100000011ULL,
    0x100000011ULL,0x100000021ULL,0x100000021ULL,0x100000021ULL,0x100000031ULL};
  mmio->cycle=cycles[index];fixture_time=index==7?1699999998:1700000000+4*index;
  mmio->line("OP "+std::to_string(index)+" C "+std::to_string(100+7*index));
  driver->tick();
  mmio->line("RESULT "+std::to_string(driver->terminate())+" "+std::to_string(driver->exit_code()),"heartbeat_termination");
  ++index;return 0;
}
void negative(const std::filesystem::path &p) {
  const auto n=p/"negative-validation";std::filesystem::create_directories(n);
  write_file(n/"cut-7.owner",read_file(p/"cut-7.owner"));init(n,true,7,0,false);
  const auto good=driver->save_checkpoint();const auto calls=mmio->calls;
  auto bad_case=[&](const std::vector<uint8_t> &b) {
    rejects([&]{driver->validate_checkpoint(b);});rejects([&]{driver->load_checkpoint(b);});
    check(driver->save_checkpoint()==good && mmio->calls==calls &&
      read_file(n/"heartbeat.csv")==sentinel,"partial heartbeat restore");
  };
  for(size_t i=0;i<good.size();++i)bad_case({good.begin(),good.begin()+i});
  for(size_t i=0;i<config_bytes;++i){auto b=good;b[i]^=1;bad_case(b);}
  auto alter=[&](size_t offset,uint64_t value) {
    auto b=good;for(unsigned i=0;i<8;++i)b[offset+i]=value>>(8*i);bad_case(b);
  };
  alter(config_bytes,UINT64_MAX); // unsupported time_t epoch
  alter(config_bytes+8,2);alter(config_bytes+8,1); // invalid/unearned timeout
  alter(config_bytes+16,3);alter(config_bytes+16,UINT64_MAX); // invalid trip count
  alter(config_bytes+24,0); // last sample/cycle disagreement
  alter(config_bytes+32,0);alter(config_bytes+32,UINT64_MAX); // missing/extra rows
  alter(config_bytes+40,0x100000011ULL); // repeated cycle needs timeout flag
  auto trailing=good;trailing.push_back(0);bad_case(trailing);
  auto changed_map=addresses;++changed_map.tCycle_latch;
  clockmodule_t other_clock(*mmio,changed_map,0,{});
  heartbeat_t other(*mmio,other_clock,arguments(n,0));rejects([&]{other.load_checkpoint(good);});
  for(unsigned mode:{1,2}) {
    heartbeat_t other_config(*mmio,*clock_driver,arguments(n,mode));
    rejects([&]{other_config.load_checkpoint(good);});
  }
  auto args=arguments(n,0);args.erase(args.begin());
  args[0]="+heartbeat-output="+(n/"external.csv").string();
  heartbeat_t external(*mmio,*clock_driver,args);
  rejects([&]{external.save_checkpoint();});rejects([&]{external.load_checkpoint(good);});
  // MMIO has a suspended clock call and a suspended heartbeat call. Neither
  // owner's payload may be captured or restored; callbacks must not re-enter.
  index=8;mmio->op=8;
  mmio->hook=[&]{
    rejects([&]{driver->save_checkpoint();});rejects([&]{driver->validate_checkpoint(good);});
    rejects([&]{driver->load_checkpoint(good);});rejects([&]{driver->tick();});
    rejects([&]{driver->finish();});rejects([&]{clock_driver->save_checkpoint();});
  };
  driver->tick(); // count 1 -> 2, no poll yet
  driver->tick(); // poll, hook runs once per MMIO operation
  mmio->hook=nullptr;
  driver->validate_checkpoint(driver->save_checkpoint());
  // A thrown MMIO operation poisons the owner rather than silently exposing
  // its partially updated count/last_cycle or a suspended stack.
  mmio->hook=[] { throw std::runtime_error("injected MMIO failure"); };
  driver->tick();driver->tick();rejects([&]{driver->tick();});mmio->hook=nullptr;
  rejects([&]{driver->save_checkpoint();});rejects([&]{driver->validate_checkpoint(good);});
  rejects([&]{driver->load_checkpoint(good);});rejects([&]{driver->finish();});
  fixture_time=1700000000;
  clockmodule_t fresh_clock(*mmio,addresses,0,{});
  heartbeat_t completed(*mmio,fresh_clock,arguments(n,0));completed.finish();
  rejects([&]{completed.save_checkpoint();});rejects([&]{completed.load_checkpoint(good);});
  rejects([&]{completed.tick();});rejects([&]{completed.finish();});
  std::cout << "PASS: heartbeat atomic payload/configuration/suspension checks " << rejected << '\n';
}
#ifdef HEARTBEAT_PREPARED_PUBLICATION
void publication_negative(const std::filesystem::path &p) {
  const auto good=read_file(p/"cut-7.owner");
  const auto n=p/"publication-negative";std::filesystem::create_directories(n);
  init(n,false,0,0,false);
  const auto initial=driver->save_checkpoint();
  const auto before=rejected;
  auto unchanged=[&] {
    check(driver->save_checkpoint()==initial && mmio->calls==0 &&
          read_file(n/"heartbeat.csv")==sentinel,"partial prepared heartbeat mutation");
  };
  auto malformed=[&](const std::vector<uint8_t> &bad) {
    rejects([&]{driver->prepare_checkpoint_publication(bad);});unchanged();
  };
  for(size_t i=0;i<good.size();++i)malformed({good.begin(),good.begin()+i});
  for(size_t i=0;i<config_bytes;++i){auto bad=good;bad[i]^=1;malformed(bad);}
  for(unsigned bit=1;bit<64;++bit) {
    auto bad=good;bad[config_bytes+8+bit/8]^=uint8_t(1U<<(bit%8));malformed(bad);
  }
  {auto bad=good;bad.push_back(0);malformed(bad);}
  for(size_t offset:{size_t(144),size_t(160),size_t(168),size_t(176)}) {
    auto bad=good;std::fill(bad.begin()+offset,bad.begin()+offset+8,255);malformed(bad);
  }
  for(unsigned phase=0;phase<2;++phase) {
    auto c=driver->prepare_checkpoint_publication(good);if(phase)c->seal();c.reset();unchanged();
  }
  {auto c=driver->prepare_checkpoint_publication(good);c->seal();rejects([&]{c->seal();});unchanged();}
  {auto c=driver->prepare_checkpoint_publication(good);
    std::thread t([&]{rejects([&]{c->seal();});});t.join();unchanged();c->seal();}
  {std::unique_ptr<prepared_checkpoint_t> c;
    {heartbeat_t dead(*mmio,*clock_driver,arguments(n,0));c=dead.prepare_checkpoint_publication(good);}
    rejects([&]{c->seal();});}
  // Identical legacy loads invalidate outstanding candidates, including ABA.
  {auto c=driver->prepare_checkpoint_publication(good);driver->load_checkpoint(initial);
    rejects([&]{c->seal();});unchanged();}
  {auto c=driver->prepare_checkpoint_publication(good);auto other=driver->prepare_checkpoint_publication(good);
    c->seal();publish(*c);check(driver->save_checkpoint()==good && mmio->calls==0);
    rejects([&]{c->seal();});rejects([&]{other->seal();});driver->load_checkpoint(initial);unchanged();}
  // Detect destination changes made by returned services, not only legacy load.
  {auto c=driver->prepare_checkpoint_publication(good);driver->tick();rejects([&]{c->seal();});
    driver->load_checkpoint(initial);unchanged();}
  for(unsigned mode:{1,2}) {
    heartbeat_t other(*mmio,*clock_driver,arguments(n,mode));
    rejects([&]{other.prepare_checkpoint_publication(good);});
  }
  {auto changed=addresses;++changed.tCycle_latch;clockmodule_t other_clock(*mmio,changed,0,{});
    heartbeat_t other(*mmio,other_clock,arguments(n,0));
    rejects([&]{other.prepare_checkpoint_publication(good);});}
  unsigned failures[2]{};
  for(unsigned phase=0;phase<2;++phase)for(long i=0;;++i) {
    std::unique_ptr<prepared_checkpoint_t> c;if(phase)c=driver->prepare_checkpoint_publication(good);
    allocation_failed=false;fail_after=i;bool failed=false;
    try{if(phase)c->seal();else c=driver->prepare_checkpoint_publication(good);}
    catch(const std::bad_alloc &){failed=true;}
    fail_after=-1;unchanged();
    if(!failed){check(!allocation_failed);break;}
    ++failures[phase];if(phase)c->seal(); // Retry a failed seal with the same candidate.
  }
  check(failures[0] && failures[1]);
  // Suspended clock/heartbeat calls and interrupted polling reject both APIs.
  for(bool interrupt:{false,true}) {
    clockmodule_t local_clock(*mmio,addresses,0,{});
    heartbeat_t f(*mmio,local_clock,arguments(n,0));f.load_checkpoint(good);
    auto c=f.prepare_checkpoint_publication(good);unsigned hooks=0;
    mmio->hook=[&]{++hooks;rejects([&]{f.prepare_checkpoint_publication(good);});
      rejects([&]{c->seal();});if(interrupt)throw std::runtime_error("poll interruption");};
    f.tick(); // cut 7 has trip count 1; first call advances to 2.
    if(interrupt)rejects([&]{f.tick();});else f.tick();
    mmio->hook=nullptr;check(hooks>0);
    if(interrupt){rejects([&]{f.prepare_checkpoint_publication(good);});rejects([&]{c->seal();});}
  }
  {heartbeat_t finished(*mmio,*clock_driver,arguments(n,0));auto c=finished.prepare_checkpoint_publication(good);
    finished.finish();rejects([&]{c->seal();});rejects([&]{finished.prepare_checkpoint_publication(good);});}
  {auto args=arguments(n,0);args.erase(args.begin());heartbeat_t live(*mmio,*clock_driver,args);
    rejects([&]{live.prepare_checkpoint_publication(good);});}
  std::cout<<"HEARTBEAT_PUBLICATION_NEGATIVE rejections="<<rejected-before<<" prepare_failures="<<failures[0]
           <<" seal_failures="<<failures[1]<<" unchanged=1\n";
}
std::vector<uint8_t> fatal_expected;
const char *fatal_mode=nullptr;
void terminated() noexcept {
  fail_after=-1;
  try {
    check(driver->save_checkpoint()==fatal_expected && mmio->calls==0 &&
          read_file(directory/"heartbeat.csv")==sentinel);
    std::fprintf(stderr,"HEARTBEAT_PUBLICATION_FATAL mode=%s unchanged=1 mmio=0\n",fatal_mode);
    std::fflush(stderr);std::_Exit(86);
  }catch(...){std::_Exit(87);}
}
void publication_fatal(const std::filesystem::path &p,const char *mode) {
  init(p,false,0,0,false);fatal_expected=driver->save_checkpoint();fatal_mode=mode;
  const std::string m(mode);auto c=driver->prepare_checkpoint_publication(fatal_expected);
  if(m=="expired"){driver.reset();driver=std::make_unique<heartbeat_t>(*mmio,*clock_driver,arguments(p,0));}
  else if(m!="unsealed")c->seal();
  if(m=="consumed")publish(*c);
  if(m=="stale"){auto other=driver->prepare_checkpoint_publication(fatal_expected);other->seal();publish(*other);}
  if(m=="legacy")driver->load_checkpoint(fatal_expected);
  std::set_terminate(terminated);
  if(m=="thread"){std::thread t([&]{c->publish();});t.join();}
  else if(m!="returned")c->publish();
  std::fprintf(stderr,"HEARTBEAT_PUBLICATION_UNEXPECTED_RETURN mode=%s\n",mode);
  std::_Exit(88); // A returning publish must never become a passing fatal case.
}
#endif
} // namespace
extern "C" int heartbeat_publication_negative(const char *p) {
#ifdef HEARTBEAT_PREPARED_PUBLICATION
  try{publication_negative(p);return 0;}catch(const std::exception &e){fail_after=-1;std::cerr<<e.what()<<'\n';return -1;}
#else
  return -1;
#endif
}
extern "C" void heartbeat_publication_fatal(const char *p,const char *mode) {
#ifdef HEARTBEAT_PREPARED_PUBLICATION
  publication_fatal(p,mode);
#else
  std::exit(2);
#endif
}
extern "C" int heartbeat_init(const char *p,int restore,int cut,int mode) {
  try {init(p,restore,cut,mode,true);return 0;}
  catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int heartbeat_step() {
  try{return step();}
  catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" int heartbeat_negative(const char *p) {
  try{negative(p);return 0;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return -1;}
}
extern "C" void heartbeat_failure(){std::exit(1);}
#ifndef HEARTBEAT_CHECKPOINT_DPI
int main(int argc,char **argv) {
  if(argc!=5)return 2;
  const std::string mode=argv[1];
  if(mode=="publication-negative")return heartbeat_publication_negative(argv[2])?1:0;
  if(mode=="publication-fatal"){heartbeat_publication_fatal(argv[2],argv[3]);return 88;}
  if(mode=="negative")return heartbeat_negative(argv[2])?1:0;
  if(heartbeat_init(argv[2],mode=="restore",std::stoi(argv[3]),std::stoi(argv[4])))return 1;
  int result;do{result=heartbeat_step();}while(!result);return result<0?1:0;
}
#endif
