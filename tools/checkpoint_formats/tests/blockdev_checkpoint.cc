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
void snapshot(const std::string &name) {
  const auto calls = mmio->calls;
  auto b = driver->save_checkpoint(); driver->validate_checkpoint(b);
  write_file(directory / (name + ".owner"), b);
  check(mmio->calls == calls, "checkpoint issued MMIO");
}
void init(const std::filesystem::path &out, bool restore, unsigned cut, bool compare) {
  directory = out; restoring = restore; index = restore ? cut : 0;
  check(index <= operations);
  mmio = std::make_unique<mmio_t>();
  driver = std::make_unique<blockdev_t>(*mmio, addresses, 0, args, 1, 24);
  prefix = restore ? "restore-" + std::to_string(cut) : "reference";
  if (restore) {
    const auto b = read_file(directory / ("cut-" + std::to_string(cut) + ".owner"));
    driver->validate_checkpoint(b); driver->load_checkpoint(b);
    check(mmio->calls == 0, "restore issued MMIO before first edge");
    snapshot(prefix + ".initial");
    check(driver->save_checkpoint() == b, "incomplete zero-edge host readback");
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
} // namespace

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
    if (std::string(argv[1])=="negative") negative(argv[2]);
    else { init(argv[2],std::string(argv[1])=="restore",std::stoul(argv[3]),true); while (!step()) {} }
    return 0;
  } catch (const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
#endif
