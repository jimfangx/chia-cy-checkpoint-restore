// Actual blockdev driver; the scripted MMIO service is a component fixture,
// not a substitute for an atomic whole-Rocket checkpoint or semantic replay.
#include "bridges/blockdev.h"
#include "core/config.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>
#include <sstream>
#include <thread>
#include <type_traits>
#include <cerrno>

#ifdef BLOCKDEV_PREPARED_PUBLICATION
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
static unsigned libc_calls = 0, stream_opens = 0, stream_closes = 0;
static bool fail_open = false, fail_seek = false;
extern "C" FILE *__real_fmemopen(void *, size_t, const char *);
extern "C" int __real_fseeko(FILE *, off_t, int);
extern "C" int __real_fclose(FILE *);
extern "C" int __real_fflush(FILE *);
extern "C" off_t __real_ftello(FILE *);
extern "C" FILE *__wrap_fmemopen(void *p, size_t n, const char *mode) {
  ++libc_calls;
  if (fail_open) { errno = ENOMEM; return nullptr; }
  auto *f = __real_fmemopen(p,n,mode); if(f)++stream_opens; return f;
}
extern "C" int __wrap_fseeko(FILE *f, off_t p, int mode) {
  ++libc_calls;
  if(fail_seek) { errno=EIO; return -1; }
  return __real_fseeko(f,p,mode);
}
extern "C" int __wrap_fclose(FILE *f) { ++libc_calls; ++stream_closes; return __real_fclose(f); }
extern "C" int __wrap_fflush(FILE *f) { ++libc_calls; return __real_fflush(f); }
extern "C" off_t __wrap_ftello(FILE *f) { ++libc_calls; return __real_ftello(f); }
#endif

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a, d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }

namespace {
constexpr unsigned operations = 14;
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "blockdev-component"};
// This matches the actual exact Rocket generated constructor. Python binds
// every address/geometry word independently against its current header.
const BLOCKDEVBRIDGEMODULE_struct addresses{
  512,516,520,524,528,532,536,540,544,548,552,556,560,
  564,568,572,576,580,584,588,592,596,600,604,608,612};
const std::vector<std::string> args{"+blkdev-in-mem0=128"};
uint64_t data_word(unsigned sector, unsigned beat) {
  return (uint64_t(0x12340000 + sector) << 32) | (0x76540000 + beat);
}
void check(bool b, const std::string &message = "blockdev assertion") {
  if (!b) throw std::runtime_error(message);
}
unsigned rejected = 0;
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected blockdev rejection");
}
std::vector<uint8_t> read_file(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f), "missing input " + p.string());
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
void write_file(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); check(bool(f));
}
struct mmio_t : simif_t {
  mmio_t() : simif_t(cfg) {}
  std::queue<blkdev_request> reqs;
  std::queue<blkdev_data> beats;
  unsigned read_budget = 0, ack_budget = 0, op = 0;
  uint64_t calls = 0;
  std::function<void()> hook;
  std::ofstream trace;
  std::vector<std::string> expected;
  size_t comparison = 0;
  void line(const std::string &s, const std::string &signal = "fixture") {
    trace << s << std::endl;
    if (!expected.empty()) {
      if (comparison >= expected.size() || expected[comparison] != s) {
        std::ostringstream m;
        m << "FIRST_MISMATCH fixture_cycle=" << 100 + 7 * op << " signal=" << signal
          << " op=" << op << " observed=" << s;
        throw std::runtime_error(m.str());
      }
      ++comparison;
    }
  }
  void write(size_t a, uint32_t d) override {
    ++calls; if (hook) hook();
    const std::string signal = a == addresses.bdev_rresp_data_lower ? "bdev_rresp_data_lower" :
                               a == addresses.bdev_rresp_data_upper ? "bdev_rresp_data_upper" :
                               "mmio_" + std::to_string(a);
    line("W " + std::to_string(a) + " " + std::to_string(d), signal);
    if (a == addresses.bdev_req_ready) { check(!reqs.empty()); reqs.pop(); }
    if (a == addresses.bdev_data_ready) { check(!beats.empty()); beats.pop(); }
    if (a == addresses.bdev_wack_valid) { check(ack_budget); --ack_budget; }
    if (a == addresses.bdev_rresp_valid) { check(read_budget); --read_budget; }
  }
  uint32_t read(size_t a) override {
    ++calls; if (hook) hook();
    uint32_t d = 0;
    if (a == addresses.bdev_reqs_pending) d = 1;
    else if (a == addresses.bdev_req_valid) d = !reqs.empty();
    else if (a == addresses.bdev_data_valid) d = !beats.empty();
    else if (a == addresses.bdev_wack_ready) d = ack_budget > 0;
    else if (a == addresses.bdev_rresp_ready) d = read_budget > 0;
    else if (a == addresses.bdev_req_write) d = reqs.front().write;
    else if (a == addresses.bdev_req_offset) d = reqs.front().offset;
    else if (a == addresses.bdev_req_len) d = reqs.front().len;
    else if (a == addresses.bdev_req_tag) d = reqs.front().tag;
    else if (a == addresses.bdev_data_data_upper) d = beats.front().data >> 32;
    else if (a == addresses.bdev_data_data_lower) d = beats.front().data;
    else if (a == addresses.bdev_data_tag) d = beats.front().tag;
    else throw std::runtime_error("unexpected fixture MMIO");
    line("R " + std::to_string(a) + " " + std::to_string(d)); return d;
  }
};
std::unique_ptr<mmio_t> mmio;
std::unique_ptr<blockdev_t> driver;
std::filesystem::path directory;
unsigned index;
bool restoring;
std::string prefix;
#ifdef BLOCKDEV_PREPARED_PUBLICATION
static_assert(!std::is_copy_constructible_v<blockdev_t> && !std::is_move_constructible_v<blockdev_t>);
void publish(prepared_checkpoint_t &candidate) {
  static_assert(noexcept(candidate.publish()));
  const auto calls = libc_calls;
  allocation_failed=false; fail_after=0;
  candidate.publish();
  const bool clean=fail_after==0 && !allocation_failed;
  fail_after=-1; check(clean && libc_calls == calls,"publication allocated or called libc stream I/O");
}
#endif
void snapshot(const std::string &name) {
  const auto calls = mmio->calls;
  auto b = driver->save_checkpoint(); driver->validate_checkpoint(b);
  write_file(directory / (name + ".owner"), b);
  check(mmio->calls == calls, "checkpoint issued MMIO");
}
void init(const std::filesystem::path &out, bool restore, unsigned cut, bool compare) {
  directory = out; restoring = restore; index = restore ? cut : 0;
  check(index <= operations);
  driver.reset();
  mmio = std::make_unique<mmio_t>();
  driver = std::make_unique<blockdev_t>(*mmio, addresses, 0, args, 1, 24);
  prefix = restore ? "restore-" + std::to_string(cut) : "reference";
  if (restore) {
    auto b = read_file(directory / ("cut-" + std::to_string(cut) + ".owner"));
    const auto expected = b;
    driver->validate_checkpoint(b);
#ifdef BLOCKDEV_PREPARED_PUBLICATION
    auto candidate = driver->prepare_checkpoint_publication(b);
    b.clear(); b.shrink_to_fit(); // Candidate owns stream backing and all queues.
    candidate->seal(); publish(*candidate);
    candidate.reset(); // Retired stream/backing cleanup must preserve live disk.
#else
    driver->load_checkpoint(b);
#endif
    check(mmio->calls == 0, "restore issued MMIO before first edge");
    snapshot(prefix + ".initial");
    check(driver->save_checkpoint() == expected, "incomplete zero-edge host readback");
  }
  mmio->trace.open(directory / (prefix + ".trace")); check(bool(mmio->trace));
  if (compare && restore && cut < operations) {
    std::ifstream f(directory / "reference.trace"); check(bool(f));
    bool found = false;
    for (std::string s; std::getline(f, s);) {
      if (s == "OP " + std::to_string(cut) + " C " + std::to_string(100 + 7 * cut)) found = true;
      if (found) mmio->expected.push_back(s);
    }
    check(found);
  }
}
int step() {
  if (index == operations) {
    if (!restoring) snapshot("cut-" + std::to_string(index));
    snapshot(prefix + ".final");
    check(mmio->comparison == mmio->expected.size(), "incomplete component comparison");
    driver.reset(); mmio.reset(); return 1;
  }
  if (!restoring) snapshot("cut-" + std::to_string(index));
  auto &m = *mmio; m.op = index; m.ack_budget = m.read_budget = 0;
  m.line("OP " + std::to_string(index) + " C " + std::to_string(100 + 7 * index));
  auto beats = [&](unsigned sector, unsigned first, unsigned end) {
    for (unsigned b = first; b < end; ++b) m.beats.push({data_word(sector, b), 0});
  };
  switch (index) {
  case 0: driver->init(); break;
  case 1: beats(2,0,5); driver->recv(); break;
  case 2: m.reqs.push({true,2,1,0}); driver->recv(); break;
  case 3: driver->tick(); break;
  case 4: beats(2,5,21); driver->tick(); break;
  case 5: beats(2,21,64); driver->tick(); break;
  case 6: m.reqs.push({false,2,1,0}); m.read_budget=7; driver->tick(); break;
  case 7: m.ack_budget=1; driver->send(); break;
  case 8: m.read_budget=20; driver->send(); break;
  case 9: m.read_budget=1000; driver->send(); break;
  case 10: m.reqs.push({true,3,1,0}); beats(3,0,64); driver->recv(); break;
  case 11: m.ack_budget=1; driver->tick(); break;
  case 12: m.reqs.push({false,3,1,0}); m.read_budget=1000; driver->tick(); break;
  case 13: driver->tick(); break;
  }
  check(m.reqs.empty() && m.beats.empty(), "fixture input did not drain");
  ++index; return 0;
}
void negative(const std::filesystem::path &out) {
  const auto validation=out/"negative-validation";
  std::filesystem::create_directories(validation);
  write_file(validation/"cut-5.owner",read_file(out/"cut-5.owner"));
  init(validation, true, 5, false);
  auto good = driver->save_checkpoint(); const auto calls = mmio->calls;
  auto bad_case = [&](const std::vector<uint8_t> &b) {
    rejects([&] { driver->validate_checkpoint(b); });
    rejects([&] { driver->load_checkpoint(b); });
    check(driver->save_checkpoint() == good && mmio->calls == calls,
          "invalid image partially restored blockdev");
  };
  // Header/configuration truncations and all configuration bytes.
  constexpr size_t config_size = (4 + 8 + 26) * 8;
  for (size_t n=0; n<config_size+24; ++n) bad_case({good.begin(),good.begin()+n});
  for (size_t n=0; n<config_size; ++n) { auto b=good; b[n]^=1; bad_case(b); }
  for (size_t n : {config_size+48, good.size()-65536, good.size()-32768, good.size()-1})
    bad_case({good.begin(),good.begin()+n});
  auto b=good; b.push_back(0); bad_case(b);
  auto setword = [&](size_t at, uint64_t value) {
    auto b=good; for (unsigned i=0;i<8;++i) b[at+i]=value>>(8*i); bad_case(b);
  };
  setword(config_size, 2); setword(config_size+8, 2);
  setword(config_size+8, 1); setword(config_size+16, 65537);
  setword(config_size+24, UINT64_MAX); // impossible queued request count
  // At cut 5 both request/data/response/ack queues are empty.
  const size_t tracker = config_size + 24 + 4*8;
  setword(tracker, 1025); setword(tracker+8,64); setword(tracker+16,65);
  setword(tracker+16,0); setword(tracker+16,1088);
  auto alter_cut = [&](unsigned cut, size_t at, uint64_t v) {
    auto b=read_file(out/("cut-"+std::to_string(cut)+".owner"));
    check(at+8<=b.size());
    for (unsigned i=0;i<8;++i) b[at+i]=v>>(8*i);
    bad_case(b);
  };
  alter_cut(3,config_size+32,2); // invalid request write flag
  alter_cut(3,config_size+40,128); // range outside disk
  alter_cut(3,config_size+48,0); alter_cut(3,config_size+48,17);
  alter_cut(3,config_size+56,1); // request tag
  alter_cut(2,config_size+32,UINT64_MAX); // data count
  alter_cut(2,config_size+48,1); // queued data tag
  alter_cut(7,config_size+40,UINT64_MAX); // response count
  alter_cut(7,config_size+56,1); // queued response tag
  alter_cut(7,config_size+48+57*16+8,1); // ack tag
  alter_cut(7,config_size+8,0); // lost response-pending flag
  alter_cut(5,config_size,0); // lifecycle contradicts partial write
  // Exercise every backing byte with nonzero varied data, including first/
  // last bytes and a legal end-of-file position. This catches libc stream
  // reconstruction that silently changes a byte outside the workload sectors.
  auto full_disk=good;
  for (size_t i=0;i<65536;++i) full_disk[full_disk.size()-65536+i]=1+(i%255);
  for (unsigned i=0;i<8;++i) full_disk[config_size+16+i]=uint64_t(65536)>>(8*i);
  driver->validate_checkpoint(full_disk); driver->load_checkpoint(full_disk);
  check(driver->save_checkpoint()==full_disk && mmio->calls==calls,
        "complete disk/end-position zero-edge readback");
  driver->load_checkpoint(good); check(driver->save_checkpoint()==good);
  auto other_args = args; other_args.push_back("+blkdev-rlatency0=4095");
  blockdev_t changed(*mmio,addresses,0,other_args,1,24);
  rejects([&] { changed.load_checkpoint(good); });
  auto changed_map=addresses; ++changed_map.bdev_req_len;
  blockdev_t other(*mmio,changed_map,0,args,1,24);
  rejects([&] { other.load_checkpoint(good); });
  blockdev_t tags(*mmio,addresses,0,args,2,24);
  rejects([&] { tags.load_checkpoint(good); });
  blockdev_t geometry(*mmio,addresses,0,{"+blkdev-in-mem0=127"},1,24);
  rejects([&] { geometry.load_checkpoint(good); });
  blockdev_t disconnected(*mmio,addresses,0,{},1,24);
  auto empty=disconnected.save_checkpoint();
  disconnected.validate_checkpoint(empty); disconnected.load_checkpoint(empty);
  check(disconnected.save_checkpoint()==empty);
  rejects([&] { disconnected.load_checkpoint(good); });
  // Do not infer ownership of a real disk pathname or debug log. Both modes
  // fail before image parsing or MMIO, even with an otherwise valid payload.
  const auto external=out/"external.disk";
  write_file(external,std::vector<uint8_t>(65536,0xa5));
  const auto bytes=read_file(external);
  const std::vector<std::string> file_args{"+blkdev0="+external.string()};
  blockdev_t external_disk(*mmio,addresses,0,file_args,1,24);
  const std::vector<std::string> log_args{"+blkdev-in-mem0=128","+blkdev-log0="+(out/"debug.log").string()};
  blockdev_t logged(*mmio,addresses,0,log_args,1,24);
  for (auto *unsupported : {&external_disk,&logged}) {
    rejects([&] { unsupported->save_checkpoint(); });
    rejects([&] { unsupported->validate_checkpoint(good); });
    rejects([&] { unsupported->load_checkpoint(good); });
  }
  check(read_file(external)==bytes && mmio->calls==calls);
  // Each public MMIO operation rejects a suspended/reentrant cut. An
  // interrupted operation stays poisoned even after its stack unwinds.
  for (unsigned op : {0U,1U,7U,13U}) for (bool interrupt : {false,true}) {
    auto case_out=out/("suspend-"+std::to_string(op)+(interrupt?"-fault":"-return"));
    std::filesystem::create_directories(case_out);
    init(case_out,false,0,false);
    while (index<op) step();
    const auto before=driver->save_checkpoint(); unsigned seen=0;
    mmio->hook=[&] {
      ++seen;
      rejects([&] { driver->save_checkpoint(); });
      rejects([&] { driver->validate_checkpoint(before); });
      rejects([&] { driver->load_checkpoint(before); });
      rejects([&] { driver->tick(); });
      rejects([&] { driver->recv(); });
      rejects([&] { driver->send(); });
      rejects([&] { driver->init(); });
      if (interrupt) throw std::runtime_error("injected MMIO interruption");
    };
    if (interrupt) rejects([&] { step(); }); else step();
    check(seen>0); mmio->hook={};
    if (interrupt) {
      rejects([&] { driver->save_checkpoint(); });
      rejects([&] { driver->validate_checkpoint(before); });
      rejects([&] { driver->load_checkpoint(before); });
    } else driver->validate_checkpoint(driver->save_checkpoint());
  }
  driver.reset(); mmio.reset();
  std::cout << "PASS: blockdev atomic payload/configuration/suspension checks " << rejected << '\n';
}
#ifdef BLOCKDEV_PREPARED_PUBLICATION
void publication_negative(const std::filesystem::path &p) {
  const auto good=read_file(p/"cut-5.owner");
  const auto n=p/"publication-negative";std::filesystem::create_directories(n);
  init(n,false,0,false);
  const auto initial=driver->save_checkpoint();const auto before=rejected;
  auto unchanged=[&] {check(driver->save_checkpoint()==initial && mmio->calls==0,"partial blockdev publication");};
  auto malformed=[&](const std::vector<uint8_t> &bad) {
    rejects([&]{driver->prepare_checkpoint_publication(bad);});unchanged();
  };
  constexpr size_t config=(4+8+26)*8;
  for(size_t i=0;i<config+24;++i)malformed({good.begin(),good.begin()+i});
  for(size_t i=0;i<config;++i){auto bad=good;bad[i]^=1;malformed(bad);}
  for(size_t i:{config+48,good.size()-65536,good.size()-32768,good.size()-1})
    malformed({good.begin(),good.begin()+i});
  {auto bad=good;bad.push_back(0);malformed(bad);}
  for(auto offset:{config,config+8,config+16,config+24,config+56,config+64,config+72}) {
    auto bad=good;std::fill(bad.begin()+offset,bad.begin()+offset+8,255);malformed(bad);
  }
  for(unsigned phase=0;phase<2;++phase) {
    const auto live=stream_opens-stream_closes;
    auto c=driver->prepare_checkpoint_publication(good);if(phase)c->seal();c.reset();
    check(stream_opens-stream_closes==live,"cancelled candidate leaked a stream");unchanged();
  }
  {auto c=driver->prepare_checkpoint_publication(good);c->seal();rejects([&]{c->seal();});unchanged();}
  {auto c=driver->prepare_checkpoint_publication(good);
    std::thread t([&]{rejects([&]{c->seal();});});t.join();unchanged();c->seal();}
  {std::unique_ptr<prepared_checkpoint_t> c;
    {blockdev_t dead(*mmio,addresses,0,args,1,24);c=dead.prepare_checkpoint_publication(good);}
    rejects([&]{c->seal();});}
  {auto c=driver->prepare_checkpoint_publication(good);driver->load_checkpoint(initial);
    rejects([&]{c->seal();});unchanged();}
  {auto c=driver->prepare_checkpoint_publication(good);auto other=driver->prepare_checkpoint_publication(good);
    c->seal();publish(*c);check(driver->save_checkpoint()==good && mmio->calls==0);
    rejects([&]{c->seal();});rejects([&]{other->seal();});c.reset();driver->load_checkpoint(initial);unchanged();}
  // A returned init mutates configuration state without a legacy load.
  {auto c=driver->prepare_checkpoint_publication(good);driver->init();rejects([&]{c->seal();});
    driver->load_checkpoint(initial);mmio->calls=0;unchanged();}
  unsigned failures[2]{};
  for(unsigned phase=0;phase<2;++phase)for(long i=0;;++i) {
    std::unique_ptr<prepared_checkpoint_t> c;if(phase)c=driver->prepare_checkpoint_publication(good);
    const auto live=stream_opens-stream_closes;
    allocation_failed=false;fail_after=i;bool failed=false;
    try{if(phase)c->seal();else c=driver->prepare_checkpoint_publication(good);}
    catch(const std::bad_alloc &){failed=true;}
    fail_after=-1;unchanged();
    if(!failed){check(!allocation_failed);break;}
    check(stream_opens-stream_closes==live,"allocation failure leaked stream");
    ++failures[phase];if(phase)c->seal(); // Failed seal can be retried.
  }
  check(failures[0] && failures[1]);
  for(bool seek:{false,true}) {
    const auto live=stream_opens-stream_closes;
    fail_open=!seek;fail_seek=seek;
    rejects([&]{driver->prepare_checkpoint_publication(good);});fail_open=fail_seek=false;
    check(stream_opens-stream_closes==live,"libc preparation failure leaked stream");unchanged();
  }
  // All backing bytes, including a nonzero final byte and EOF cursor, survive
  // both cancelled and successful candidates and destruction of retired state.
  auto full=good;for(size_t i=0;i<65536;++i)full[full.size()-65536+i]=1+i%255;
  for(unsigned i=0;i<8;++i)full[config+16+i]=uint64_t(65536)>>(8*i);
  {auto c=driver->prepare_checkpoint_publication(full);c->seal();publish(*c);c.reset();
    check(driver->save_checkpoint()==full && mmio->calls==0);driver->load_checkpoint(initial);unchanged();}
  // Both source and replacement can be disconnected (there is no FILE).
  {blockdev_t f(*mmio,addresses,0,{},1,24);auto payload=f.save_checkpoint();
    auto c=f.prepare_checkpoint_publication(payload);c->seal();publish(*c);c.reset();check(f.save_checkpoint()==payload);
    rejects([&]{f.prepare_checkpoint_publication(good);});}
  // All public service phases exclude suspended/poisoned destination stamps.
  for(unsigned op:{0U,1U,7U,13U})for(bool interrupt:{false,true}) {
    const auto local=n/("suspended-"+std::to_string(op)+(interrupt?"-fault":"-return"));
    std::filesystem::create_directories(local);init(local,false,0,false);while(index<op)step();
    auto c=driver->prepare_checkpoint_publication(good);unsigned hooks=0;
    mmio->hook=[&]{++hooks;rejects([&]{driver->prepare_checkpoint_publication(good);});
      rejects([&]{c->seal();});if(interrupt)throw std::runtime_error("injected MMIO interruption");};
    if(interrupt)rejects([&]{step();});else step();
    mmio->hook=nullptr;check(hooks>0);
    if(interrupt){rejects([&]{driver->prepare_checkpoint_publication(good);});rejects([&]{c->seal();});}
  }
  init(n,false,0,false);
  auto other_args=args;other_args.push_back("+blkdev-rlatency0=4095");
  {blockdev_t f(*mmio,addresses,0,other_args,1,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  {auto map=addresses;++map.bdev_req_len;blockdev_t f(*mmio,map,0,args,1,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  {blockdev_t f(*mmio,addresses,0,args,2,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  {blockdev_t f(*mmio,addresses,0,{"+blkdev-in-mem0=127"},1,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  const auto external=n/"external.disk";write_file(external,std::vector<uint8_t>(65536,0xa5));
  const auto bytes=read_file(external);const std::vector<std::string> external_args{"+blkdev0="+external.string()};
  const std::vector<std::string> log_args{"+blkdev-in-mem0=128","+blkdev-log0="+(n/"debug.log").string()};
  {blockdev_t f(*mmio,addresses,0,external_args,1,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  {blockdev_t f(*mmio,addresses,0,log_args,1,24);rejects([&]{f.prepare_checkpoint_publication(good);});}
  check(read_file(external)==bytes && mmio->calls==0);
  std::cout<<"BLOCKDEV_PUBLICATION_NEGATIVE rejections="<<rejected-before<<" prepare_failures="<<failures[0]
           <<" seal_failures="<<failures[1]<<" libc_failures=2 unchanged=1\n";
}
std::vector<uint8_t> fatal_expected;
const char *fatal_mode=nullptr;
void terminated() noexcept {
  fail_after=-1;
  try {
    check(driver->save_checkpoint()==fatal_expected && mmio->calls==0);
    std::fprintf(stderr,"BLOCKDEV_PUBLICATION_FATAL mode=%s unchanged=1 mmio=0\n",fatal_mode);
    std::fflush(stderr);std::_Exit(86);
  }catch(...){std::_Exit(87);}
}
void publication_fatal(const std::filesystem::path &p,const char *mode) {
  init(p,false,0,false);fatal_expected=driver->save_checkpoint();fatal_mode=mode;
  const std::string m(mode);auto c=driver->prepare_checkpoint_publication(fatal_expected);
  if(m=="expired"){driver.reset();driver=std::make_unique<blockdev_t>(*mmio,addresses,0,args,1,24);}
  else if(m!="unsealed")c->seal();
  if(m=="consumed")publish(*c);
  if(m=="stale"){auto other=driver->prepare_checkpoint_publication(fatal_expected);other->seal();publish(*other);}
  if(m=="legacy")driver->load_checkpoint(fatal_expected);
  std::set_terminate(terminated);
  if(m=="thread"){std::thread t([&]{c->publish();});t.join();}
  else if(m!="returned")c->publish();
  std::fprintf(stderr,"BLOCKDEV_PUBLICATION_UNEXPECTED_RETURN mode=%s\n",mode);std::_Exit(88);
}
#endif
} // namespace
extern "C" int blockdev_publication_negative(const char *p) {
#ifdef BLOCKDEV_PREPARED_PUBLICATION
  try{publication_negative(p);return 0;}catch(const std::exception &e){fail_after=-1;std::cerr<<e.what()<<'\n';return 1;}
#else
  return 1;
#endif
}
extern "C" void blockdev_publication_fatal(const char *p,const char *mode) {
#ifdef BLOCKDEV_PREPARED_PUBLICATION
  publication_fatal(p,mode);
#else
  std::exit(2);
#endif
}

extern "C" void blockdev_failure() { std::exit(1); }
#ifdef BLOCKDEV_CHECKPOINT_DPI
extern "C" int blockdev_init(const char *d, int restore, int cut, int compare) {
  try { init(d,restore,cut,compare); return 0; }
  catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
extern "C" int blockdev_step() {
  try { return step(); }
  catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return -1; }
}
extern "C" int blockdev_negative(const char *d) {
  try { negative(d); return 0; }
  catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
#else
int main(int argc,char **argv) {
  try {
    check(argc==4);
    if (std::string(argv[1])=="publication-negative") return blockdev_publication_negative(argv[2]);
    if (std::string(argv[1])=="publication-fatal") {blockdev_publication_fatal(argv[2],argv[3]);return 88;}
    if (std::string(argv[1])=="negative") negative(argv[2]);
    else { init(argv[2],std::string(argv[1])=="restore",std::stoul(argv[3]),true); while (!step()) {} }
    return 0;
  } catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
#endif
