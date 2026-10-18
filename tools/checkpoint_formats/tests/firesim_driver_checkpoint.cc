// Actual production FireSim driver, with separately owned MMIO/bridge fixtures.
// Component cuts do not certify generated RTL, TSI/FESVR or CPU continuation.
#include "firesim/firesim_top.cc"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <new>
#include <thread>
#include <type_traits>

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

static_assert(!std::is_copy_constructible_v<firesim_top_t> &&
              !std::is_move_constructible_v<firesim_top_t>);

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
midas_time_t timestamp() { return 1000000; }
double diff_secs(midas_time_t e, midas_time_t s) { return (e-s)/1000000.0; }
extern "C" time_t firesim_driver_test_time(time_t *out) noexcept {
  if (out) *out = 1000;
  return 1000;
}

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "firesim-driver-fixture"};
unsigned rejected = 0, operation = 0, acknowledged = 0, scenario = 0;
std::ofstream trace;
std::vector<std::string> expected;
size_t next_expected = 0;
void check(bool value) {
  if (!value) throw std::runtime_error("FireSim driver test assertion");
}
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected FireSim driver rejection");
}
void emit(const std::string &line) {
  if (!expected.empty()) {
    const auto want = next_expected < expected.size() ? expected[next_expected] : "<end>";
    if (line != want) {
      std::cerr << "FIRST_MISMATCH fixture_cycle=" << 100+operation
                << " operation=" << operation << " acknowledged=" << acknowledged
                << " expected=" << want << " actual=" << line << '\n';
      throw std::runtime_error("first divergent FireSim driver boundary");
    }
    ++next_expected;
  }
  if (trace) trace << line << '\n';
}
std::vector<uint8_t> words(std::initializer_list<uint64_t> values) {
  std::vector<uint8_t> out;
  for (auto value : values)
    for (unsigned i=0;i<8;++i) out.push_back(value >> (8*i));
  return out;
}
uint64_t word(const std::vector<uint8_t> &bytes, size_t offset) {
  check(offset+8<=bytes.size()); uint64_t value=0;
  for (unsigned i=0;i<8;++i) value |= uint64_t(bytes[offset+i]) << (8*i);
  return value;
}
void set_word(std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
  check(offset+8<=bytes.size());
  for (unsigned i=0;i<8;++i) bytes[offset+i]=value>>(8*i);
}
int status(unsigned s) {
  return s==0 ? 0 : s==1 ? 7 : s==2 ? -9 : std::numeric_limits<int>::min();
}
struct platform_t : simif_t, checkpoint_owner_t {
  platform_t() : simif_t(cfg) {}
  std::array<uint64_t,4> ticks{};
  uint64_t polls=0, issued=0, calls=0;
  unsigned mode=0;
  bool tracing=false;
  std::function<void()> hook;
  void write(size_t address, uint32_t data) override {
    ++calls; if (hook) hook();
    if (address==100) ++issued;
    else if (address>=200 && address<232 && (address-200)%8==0)
      ++ticks[(address-200)/8];
    if (tracing) emit("W "+std::to_string(address)+" "+std::to_string(data));
  }
  uint32_t read(size_t address) override {
    ++calls; if (hook) hook();
    uint32_t value=0;
    if (address==104) value=(++polls % 3 == 0);
    else if (address>=200 && address<232) {
      const auto i=(address-200)/8;
      value=(address-200)%8==0 ? (mode<4 && i==mode && ticks[i]==2) : uint32_t(status(mode));
    }
    if (tracing) emit("R "+std::to_string(address)+" "+std::to_string(value));
    return value;
  }
  std::string checkpoint_schema() const override { return "fixture.mmio.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    return words({mode,polls,issued,ticks[0],ticks[1],ticks[2],ticks[3]});
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override {
    check(b.size()==56 && word(b,0)==mode);
  }
  void load_checkpoint(const std::vector<uint8_t> &b) override {
    validate_checkpoint(b); polls=word(b,8); issued=word(b,16);
    for (unsigned i=0;i<4;++i) ticks[i]=word(b,24+8*i);
  }
};
struct bridge_t : bridge_driver_t {
  static char KIND;
  unsigned index;
  bridge_t(platform_t &p,unsigned index) : bridge_driver_t(p,&KIND),index(index) {}
  std::string checkpoint_schema() const override { return "fixture.bridge.v1"; }
  std::vector<uint8_t> save_checkpoint() const override { return words({index}); }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override { check(b==words({index})); }
  void load_checkpoint(const std::vector<uint8_t> &b) override { validate_checkpoint(b); }
  void tick() override { write(200+index*8,1); }
  bool terminate() override { return read(200+index*8); }
  int exit_code() override { return int(int32_t(read(204+index*8))); }
};
char bridge_t::KIND;
struct fixture_t {
  platform_t platform;
  widget_registry_t registry;
  std::unique_ptr<firesim_top_t> driver;
  fixture_t(unsigned mode=0,std::vector<std::string> extra={},unsigned count=4,bool reverse=false) {
    platform.mode=mode;
    registry.add_widget(new clockmodule_t(platform,{16,20,24,28,32,36},0,{}));
    registry.add_widget(new peek_poke_t(platform,{100,104,108},0,{}, {}, {}));
    for (unsigned i=0;i<count;++i)
      registry.add_widget(new bridge_t(platform,reverse ? count-1-i : i));
    std::vector<std::string> args{"+max-cycles="+std::string(mode==5?"0":"100"),
      "+heartbeat-checkpoint-buffered","+heartbeat-polling-interval=1000"};
    args.insert(args.end(),extra.begin(),extra.end());
    driver=std::make_unique<firesim_top_t>(platform,registry,args);
  }
  std::vector<std::pair<std::string,checkpoint_owner_t *>> owners() {
    auto out=driver->checkpoint_driver_owners();
    // This fixture exercises the concrete loop directly. Base flow ownership
    // is covered independently by the preserved simulation_t regression.
    out.erase(out.begin()+1);
    const auto widgets=registry.checkpoint_owners();
    out.insert(out.end(),widgets.begin(),widgets.end());
    out.emplace_back("fixture/mmio",&platform);
    return out;
  }
};
std::unique_ptr<fixture_t> fixture;
std::filesystem::path output;
void write(const std::filesystem::path &path,const std::vector<uint8_t> &b) {
  std::ofstream f(path,std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()),b.size()); check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &path) {
  std::ifstream f(path,std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
void snapshot(const std::string &prefix) {
  const auto calls=fixture->platform.calls;
  const auto owners=fixture->owners();
  for (size_t i=0;i<owners.size();++i) {
    auto bytes=owners[i].second->save_checkpoint();
    owners[i].second->validate_checkpoint(bytes);
    write(output/(prefix+"."+std::to_string(i)+".owner"),bytes);
  }
  check(calls==fixture->platform.calls);
}
void initialize(const char *source,const char *directory,bool restore,unsigned cut,unsigned mode) {
  output=directory; scenario=mode; operation=cut; acknowledged=cut;
  fixture=std::make_unique<fixture_t>(mode);
  if (restore) {
    auto owners=fixture->owners();
    std::vector<std::vector<uint8_t>> bytes;
    for (size_t i=0;i<owners.size();++i) {
      bytes.push_back(read(std::filesystem::path(source)/("cut-"+std::to_string(cut)+"."+std::to_string(i)+".owner")));
      owners[i].second->validate_checkpoint(bytes.back());
    }
    // Complete fixture inventory validation precedes any load/publication.
#ifdef FIRESIM_DRIVER_PREPARED_PUBLICATION
    // Only the driver adapter is under test here. Other owners retain their
    // legacy fixture loader; this is not a whole-simulator transaction.
    auto driver = owners[0].second->prepare_checkpoint_publication(bytes[0]);
    driver->seal();
    for (size_t i=1;i<owners.size();++i) owners[i].second->load_checkpoint(bytes[i]);
    allocation_failed = false; fail_after = 0;
    driver->publish();
    const bool clean = fail_after == 0 && !allocation_failed; fail_after = -1; check(clean);
#else
    for (size_t i=0;i<owners.size();++i) owners[i].second->load_checkpoint(bytes[i]);
#endif
    check(fixture->platform.calls==0);
    snapshot("initial");
    std::ifstream f(std::filesystem::path(source)/"trace"); check(bool(f));
    bool selected=false; std::string line;
    while (std::getline(f,line)) {
      if (line=="OP "+std::to_string(cut+1)+" C "+std::to_string(101+cut) || line=="FINAL") selected=true;
      if (selected) expected.push_back(line);
    }
    check(!expected.empty());
  }
  trace.open(output/"trace"); check(bool(trace));
  fixture->platform.tracing=true;
  std::cout << "FIRESIM_DRIVER_READBACK edges=0 mmio_calls=0\n";
}
bool advance() {
  auto &driver=*fixture->driver;
  // A loaded finished cut must finalize without reissuing any operation.
  auto owners=driver.checkpoint_driver_owners();
  auto loop=owners.back().second->save_checkpoint();
  if (word(loop,24)!=7) {
    ++operation;
    emit("OP "+std::to_string(operation)+" C "+std::to_string(100+operation));
    const bool done=driver.simulation_run_step();
    acknowledged=operation;
    snapshot("cut-"+std::to_string(operation));
    if (!done) return false;
  }
  emit("FINAL");
  const auto code=driver.simulation_run_finalize();
  const bool timeout=driver.simulation_timed_out();
  emit("RESULT "+std::to_string(code)+" TIMEOUT "+std::to_string(timeout));
  check(code==(scenario<4?status(scenario):0) && timeout==(scenario>=4));
  check(expected.empty() || next_expected==expected.size());
  trace.flush();
  std::cout << "PASS: fresh FireSim driver continuation operations=" << operation << "\n";
  return true;
}
struct services_t : bridge_run_loop_t::services_t {
  std::function<void()> hook;
  bool stop=false,done=false,terminal=false;
  int code=-7;
  uint64_t calls=0;
  void called() { ++calls; if (hook) hook(); }
  bool horizon_reached() override { called(); return stop; }
  void run_tasks() override { called(); }
  void issue_step() override { called(); }
  bool step_done() override { called(); return done; }
  void tick_bridge(uint64_t) override { called(); }
  bool bridge_terminated(uint64_t) override { called(); return terminal; }
  int bridge_exit_code(uint64_t) override { called(); return code; }
};
void negative() {
  bridge_run_loop_t loop(4); services_t services;
  const auto initial=loop.save_checkpoint();
  auto malformed=[&](std::vector<uint8_t> b) {
    const auto before=loop.save_checkpoint();
    const auto calls=services.calls;
    rejects([&]{loop.validate_checkpoint(b);}); rejects([&]{loop.load_checkpoint(b);});
    check(loop.save_checkpoint()==before && services.calls==calls);
  };
  for (size_t n=0;n<initial.size();++n) malformed({initial.begin(),initial.begin()+n});
  auto b=initial; b.push_back(0); malformed(b);
  for (auto pair : std::vector<std::pair<unsigned,uint64_t>>{{0,0},{8,2},{16,3},{24,8},{32,1},{40,2},{48,1},{48,UINT64_MAX}}) {
    b=initial; set_word(b,pair.first,pair.second); malformed(b);
  }
  for (unsigned phase=0;phase<8;++phase) {
    b=initial; set_word(b,24,phase);
    if (phase>=4 && phase<=6) { set_word(b,32,4); malformed(b); }
    b=initial; set_word(b,24,phase); set_word(b,40,1);
    if (phase!=7) malformed(b);
  }
  for (unsigned phase=0;phase<7;++phase) {
    bridge_run_loop_t current(1); services_t svc;
    auto starting=current.save_checkpoint(); set_word(starting,24,phase); current.load_checkpoint(starting);
    auto image=current.save_checkpoint();
    svc.hook=[&] { rejects([&]{current.save_checkpoint();}); rejects([&]{current.load_checkpoint(image);});
                    rejects([&]{current.advance(svc);}); };
    current.advance(svc);
    bridge_run_loop_t failed(1); failed.load_checkpoint(starting);
    svc.hook=[] { throw std::runtime_error("interrupted service"); };
    rejects([&]{failed.advance(svc);});
    rejects([&]{failed.save_checkpoint();}); rejects([&]{failed.load_checkpoint(image);});
  }
  bridge_run_loop_t empty(0); services_t svc;
  for (unsigned i=0;i<5;++i) empty.advance(svc);
  check(word(empty.save_checkpoint(),24)==3); svc.done=true; empty.advance(svc);
  svc.stop=true; empty.advance(svc); check(empty.finished() && !empty.terminated() && empty.exit_code()==0);
  for (int value : {0,7,-9,std::numeric_limits<int>::min(),std::numeric_limits<int>::max()}) {
    b=initial; set_word(b,24,7); set_word(b,40,1); set_word(b,48,uint32_t(value));
    loop.load_checkpoint(b); check(loop.exit_code()==value && loop.terminated());
  }
  fixture_t running; rejects([&]{running.owners()[0].second->save_checkpoint();});
  running.driver->simulation_run_step();
  auto good=running.owners()[0].second->save_checkpoint();
  rejects([&]{running.owners()[0].second->load_checkpoint(good);});
  rejects([&]{running.driver->simulation_run_finalize();});
  rejects([&]{running.owners()[0].second->save_checkpoint();}); // poisoned finalization
  fixture_t source; source.driver->simulation_run_step(); good=source.owners()[0].second->save_checkpoint();
  for (size_t n=0;n<good.size();++n) {
    fixture_t fresh; const auto calls=fresh.platform.calls;
    rejects([&]{fresh.owners()[0].second->load_checkpoint({good.begin(),good.begin()+n});});
    check(fresh.platform.calls==calls); rejects([&]{fresh.owners()[0].second->save_checkpoint();});
  }
  for (auto extra : std::vector<std::vector<std::string>>{{"+profile-interval=10"},{"+profile-interval=11"}}) {
    fixture_t fresh(0,extra);
    rejects([&]{fresh.owners()[0].second->load_checkpoint(good);});
    rejects([&]{fresh.owners()[1].second->save_checkpoint();});
  }
  fixture_t fewer(0,{},3); rejects([&]{fewer.owners()[0].second->load_checkpoint(good);});
  fixture_t changed; changed.registry.add_widget(new bridge_t(changed.platform,4));
  rejects([&]{changed.owners()[0].second->load_checkpoint(good);});
  fixture_t active;
  active.driver->simulation_run_step(); active.driver->simulation_run_step();
  auto active_image=active.owners()[0].second->save_checkpoint();
  active.platform.hook=[&] {
    rejects([&]{active.owners()[0].second->save_checkpoint();});
    rejects([&]{active.owners()[0].second->load_checkpoint(active_image);});
    rejects([&]{active.driver->simulation_run_step();});
  };
  active.driver->simulation_run_step();
  active.platform.hook=[] { throw std::runtime_error("MMIO interrupted"); };
  rejects([&]{active.driver->simulation_run_step();});
  rejects([&]{active.owners()[0].second->save_checkpoint();});
  rejects([&]{active.owners()[0].second->load_checkpoint(active_image);});
  fixture_t completed(5); check(completed.driver->simulation_run_step());
  check(completed.driver->simulation_run_finalize()==0);
  rejects([&]{completed.driver->simulation_run_finalize();});
  rejects([&]{completed.driver->simulation_run_step();});
  rejects([&]{completed.owners()[0].second->load_checkpoint(good);});
  std::cout << "PASS: FireSim driver atomic/configuration/lifecycle rejections " << rejected << '\n';
}

checkpoint_owner_t &driver_owner(fixture_t &f) {
  return *f.driver->checkpoint_driver_owners().front().second;
}
using inventory_t = std::vector<std::vector<uint8_t>>;
inventory_t observe(fixture_t &f) {
  inventory_t result;
  auto owners = f.owners();
  // A fresh driver deliberately has no source image. All other fixture owners
  // can be read back, including the separate scheduler and bridge-loop state.
  try { result.push_back(owners[0].second->save_checkpoint()); }
  catch (const std::runtime_error &) { result.emplace_back(); }
  for (size_t i=1; i<owners.size(); ++i) result.push_back(owners[i].second->save_checkpoint());
  return result;
}
void publish(prepared_checkpoint_t &candidate) {
  allocation_failed = false; fail_after = 0;
  static_assert(noexcept(candidate.publish())); candidate.publish();
  const bool clean = fail_after == 0 && !allocation_failed; fail_after = -1; check(clean);
}
void publication_negative() {
  fixture_t source; source.driver->simulation_run_step();
  const auto good = driver_owner(source).save_checkpoint();
  fixture_t dest; auto &owner = driver_owner(dest);
  const auto initial = observe(dest);
  auto unchanged = [&] {
    check(observe(dest) == initial && dest.platform.calls == 0);
    // Also prove that a failed/cancelled operation has not poisoned or started
    // the destination; source-save rejection alone cannot establish freshness.
    auto probe = owner.prepare_checkpoint_publication(good);
    probe->seal();
  };
  auto malformed = [&](const std::vector<uint8_t> &bad) {
    rejects([&] { owner.prepare_checkpoint_publication(bad); }); unchanged();
  };
  for (size_t n=0; n<good.size(); ++n) malformed({good.begin(), good.begin()+n});
  for (size_t n=0; n<good.size(); ++n) { auto bad=good; bad[n]^=1; malformed(bad); }
  for (unsigned bit=0; bit<64; ++bit) {
    auto bad=good; bad[good.size()-8+bit/8]^=uint8_t(1U<<(bit%8)); malformed(bad);
  }
  { auto bad=good; bad.push_back(0); malformed(bad); }
  // A payload from a different owner is not a compatible running driver.
  malformed(source.owners()[1].second->save_checkpoint());
  for (unsigned phase=0; phase<2; ++phase) {
    auto c=owner.prepare_checkpoint_publication(good); if (phase) c->seal();
    c.reset(); unchanged();
  }
  { auto c=owner.prepare_checkpoint_publication(good); c->seal(); rejects([&] { c->seal(); }); unchanged(); }
  { auto c=owner.prepare_checkpoint_publication(good);
    std::thread t([&] { rejects([&] { c->seal(); }); }); t.join(); unchanged(); }
  { std::unique_ptr<prepared_checkpoint_t> c;
    { fixture_t dead; c=driver_owner(dead).prepare_checkpoint_publication(good); }
    rejects([&] { c->seal(); }); unchanged(); }
  { fixture_t f; auto &o=driver_owner(f);
    auto c=o.prepare_checkpoint_publication(good), other=o.prepare_checkpoint_publication(good);
    c->seal(); publish(*c);
    check(o.save_checkpoint()==good && f.platform.calls==0);
    rejects([&] { c->seal(); }); rejects([&] { other->seal(); });
    rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=driver_owner(f); auto c=o.prepare_checkpoint_publication(good);
    o.load_checkpoint(good); rejects([&] { c->seal(); });
    rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=driver_owner(f); auto c=o.prepare_checkpoint_publication(good);
    f.driver->simulation_run_step(); rejects([&] { c->seal(); });
    rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=driver_owner(f); auto c=o.prepare_checkpoint_publication(good);
    // Premature finalization poisons a still-unstarted driver's call state.
    rejects([&] { f.driver->simulation_run_finalize(); });
    rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); }); }
  { fixture_t f(5); auto &o=driver_owner(f);
    check(f.driver->simulation_run_step()); f.driver->simulation_run_finalize();
    rejects([&] { o.prepare_checkpoint_publication(good); }); }
  for (const auto &extra : std::vector<std::vector<std::string>>{
         {"+profile-interval=10"}, {"+profile-interval=11"}}) {
    fixture_t f(0,extra); rejects([&] { driver_owner(f).prepare_checkpoint_publication(good); });
    check(f.platform.calls==0);
  }
  { fixture_t f(0,{},3); rejects([&] { driver_owner(f).prepare_checkpoint_publication(good); }); }
  { fixture_t f; auto &o=driver_owner(f); auto c=o.prepare_checkpoint_publication(good);
    f.registry.add_widget(new bridge_t(f.platform,4));
    rejects([&] { c->seal(); }); rejects([&] { o.prepare_checkpoint_publication(good); });
    check(f.platform.calls==0); }
  // Preparation retains no caller-owned image bytes.
  { fixture_t f; auto &o=driver_owner(f); auto before=observe(f); auto input=good;
    auto c=o.prepare_checkpoint_publication(input); input.assign(1,0); c->seal(); publish(*c);
    before[0]=good; check(observe(f)==before && f.platform.calls==0); }
  unsigned failures[2]{};
  for (unsigned phase=0; phase<2; ++phase) for (long n=0; ; ++n) {
    std::unique_ptr<prepared_checkpoint_t> c;
    if (phase) c=owner.prepare_checkpoint_publication(good);
    allocation_failed=false; fail_after=n; bool failed=false;
    try { if (phase) c->seal(); else c=owner.prepare_checkpoint_publication(good); }
    catch (const std::bad_alloc &) { failed=true; }
    fail_after=-1; unchanged();
    if (!failed) { check(!allocation_failed); break; }
    ++failures[phase];
    // A partially failed seal can be retried on the same candidate.
    if (phase) c->seal();
  }
  check(failures[0] && failures[1]);
  std::cout << "DRIVER_PUBLICATION_NEGATIVE rejections=" << rejected
            << " prepare_failures=" << failures[0] << " seal_failures=" << failures[1]
            << " unchanged=1 mmio=0\n";
}
fixture_t *fatal_fixture;
inventory_t fatal_expected;
std::vector<uint8_t> fatal_source;
const char *fatal_mode;
void terminated() noexcept {
  fail_after=-1;
  try {
    check(observe(*fatal_fixture)==fatal_expected && fatal_fixture->platform.calls==0);
    if (fatal_expected[0].empty()) {
      auto probe=driver_owner(*fatal_fixture).prepare_checkpoint_publication(fatal_source); probe->seal();
    }
    std::fprintf(stderr,"DRIVER_PUBLICATION_FATAL mode=%s unchanged=1 mmio=0\n",fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
void publication_fatal(const char *mode) {
  std::set_terminate(terminated);
  fixture_t source; source.driver->simulation_run_step(); fatal_source=driver_owner(source).save_checkpoint();
  fixture_t f; fatal_fixture=&f; fatal_mode=mode;
  auto &o=driver_owner(f); auto c=o.prepare_checkpoint_publication(fatal_source);
  const std::string m(mode);
  if (m=="expired") {
    auto dead=std::make_unique<fixture_t>(); c=driver_owner(*dead).prepare_checkpoint_publication(fatal_source);
    c->seal(); dead.reset();
  } else if (m!="unsealed") c->seal();
  if (m=="consumed") publish(*c);
  else if (m=="stale") { auto other=o.prepare_checkpoint_publication(fatal_source); other->seal(); publish(*other); }
  else if (m=="legacy") o.load_checkpoint(fatal_source);
  fatal_expected=observe(f);
  if (m=="thread") { std::thread t([&] { c->publish(); }); t.join(); }
  else c->publish();
  // An unexpected return must never enter the successful terminate handler.
  std::fprintf(stderr, "DRIVER_PUBLICATION_UNEXPECTED_RETURN mode=%s\n", mode);
  std::fflush(stderr);
  std::_Exit(88);
}
} // namespace

extern "C" int firesim_driver_init(const char *source,const char *out,int restore,int cut,int mode) {
  try { initialize(source,out,restore,cut,mode); return 0; }
  catch (const std::exception &e) { std::cerr << "REJECTED_BEFORE_FIRST_EDGE " << e.what() << '\n'; return 1; }
}
extern "C" int firesim_driver_step() {
  try { return advance()?1:0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return -1; }
}
extern "C" int firesim_driver_negative() {
  try { negative(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
extern "C" int firesim_driver_publication_negative() {
  try { publication_negative(); return 0; }
  catch (const std::exception &e) { fail_after=-1; std::cerr << e.what() << '\n'; return 1; }
}
extern "C" void firesim_driver_publication_fatal(const char *mode) { publication_fatal(mode); }
extern "C" void firesim_driver_failure() { std::exit(1); }
#ifndef FIRESIM_DRIVER_CHECKPOINT_DPI
int main(int argc,char **argv) {
  if (argc==2 && std::string(argv[1])=="negative") return firesim_driver_negative();
  if (argc==2 && std::string(argv[1])=="publication-negative") return firesim_driver_publication_negative();
  if (argc==3 && std::string(argv[1])=="publication-fatal") { publication_fatal(argv[2]); return 1; }
  if (argc!=6) return 1;
  if (firesim_driver_init(argv[1],argv[2],std::stoi(argv[3]),std::stoi(argv[4]),std::stoi(argv[5]))) return 1;
  int result;
  do { result=firesim_driver_step(); } while (!result);
  return result<0?1:0;
}
#endif
