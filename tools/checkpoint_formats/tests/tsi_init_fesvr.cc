// Actual installed-HTIF/TestChip init ordering, routing and cache-flush calls.
// Component captures only; no HTIF/context or CPU continuation is claimed.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>
namespace fs = std::filesystem;
static void require(bool b, const char *s) { if (!b) throw std::runtime_error(s); }
static void snapshot(firesim_tsi_t &tsi, const fs::path &out, const std::string &name) {
  for (const auto &owner : std::vector<std::pair<std::string, const checkpoint_owner_t *>>{
         {"init", &tsi.init_accesses_owner()}, {"read", &tsi.serial_read_owner()},
         {"serial", &tsi.serial_queue_owner()}, {"host", &tsi.host_control_owner()}}) {
    const auto bytes = owner.second->save_checkpoint();
    std::ofstream f(out/(name+"."+owner.first), std::ios::binary);
    f.write(reinterpret_cast<const char *>(bytes.data()), bytes.size()); require(bool(f), "snapshot failed");
  }
}
static void packet(std::vector<uint32_t> &result, bool write, uint64_t address, std::vector<uint32_t> data) {
  result.insert(result.end(), {uint32_t(write), uint32_t(address), uint32_t(address >> 32), uint32_t(data.size()-1), 0});
  if (write) result.insert(result.end(), data.begin(), data.end());
}
static void access(std::vector<uint32_t> &result, bool flush, bool write, uint64_t address, std::vector<uint32_t> data) {
  if (flush) {
    const uint64_t base = address & ~uint64_t(63);
    packet(result, true, 0x10000100, {uint32_t(base), uint32_t(base >> 32)});
  }
  packet(result, write, address, data);
}
static void drain(firesim_tsi_t &tsi, const fs::path &out, const std::string &name, const std::vector<uint32_t> &expected) {
  snapshot(tsi, out, name+"-queued");
  for (size_t i=0; i<expected.size(); ++i) {
    require(tsi.data_available() && tsi.in_valid() && tsi.in_bits()==expected[i] && tsi.recv_word()==expected[i],
            "actual ordered init/cache-flush/MSIP word differs");
    if (i==0 || i==expected.size()/2 || i+1==expected.size())
      snapshot(tsi, out, name+"-pop-"+std::to_string(i));
  }
  require(!tsi.data_available(), "extra init serial request");
}
static int run(const char *elf, const char *destination, const char *flush_text, const char *msip_text) {
  try {
    const bool flush = std::stoul(flush_text), msip = std::stoul(msip_text);
    fs::path out(destination); fs::create_directories(out);
    std::vector<std::string> args{"init-integration", "+permissive", "+idle-counts=1",
      "+init_write=0x80000100:0x12345678", "+init_read=0x10000010",
      "+init_write=0x80000100:0x0", "+init_read=0x80000108"};
    if (flush) args.push_back("+cflush_addr=0x10000100");
    if (!msip) args.push_back("+no_hart0_msip");
    args.push_back("+permissive-off"); args.push_back(elf);
    std::vector<char *> argv; for (auto &a : args) argv.push_back(a.data());
    firesim_tsi_t tsi(argv.size(), argv.data(), true); snapshot(tsi, out, "constructed");
    // Service the real installed FESVR ELF loader, including its unaligned
    // segment merge. These original bytes are independently checked.
    tsi.tick(); tsi.tick(); firesim_loadmem_t request;
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16, "ELF write differs");
    std::array<uint8_t,16> initial{}; tsi.recv_loadmem_data(initial.data(),16);
    for (size_t i=0; i<16; ++i) require(initial[i]==i, "ELF data differs");
    tsi.tick(); require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8, "ELF read differs");
    tsi.send_loadmem_word(0xaabbccdd); tsi.send_loadmem_word(0x11223344); tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8, "ELF merge differs");
    std::array<uint32_t,2> merged{}; tsi.recv_loadmem_data(merged.data(),8);
    require(merged[0]==0xaabbccdd && merged[1]==0x77665544, "ELF merge data differs");
    snapshot(tsi, out, "reset-wait"); tsi.set_loaded_in_target(true); tsi.tick();
    std::vector<uint32_t> first;
    access(first, flush, true, 0x80000100, {0x12345678}); access(first, flush, false, 0x10000010, {0});
    drain(tsi, out, "first", first);
    for (unsigned i=0; i<2; ++i) { tsi.tick(); snapshot(tsi, out, "first-wait-"+std::to_string(i)); }
    tsi.send_word(0x89abcdef); snapshot(tsi, out, "first-response"); tsi.tick();
    std::vector<uint32_t> second;
    access(second, flush, true, 0x80000100, {0}); access(second, flush, false, 0x80000108, {0});
    drain(tsi, out, "second", second);
    for (unsigned i=0; i<2; ++i) { tsi.tick(); snapshot(tsi, out, "second-wait-"+std::to_string(i)); }
    tsi.send_word(0xfedcba98); snapshot(tsi, out, "second-response"); tsi.tick();
    std::vector<uint32_t> last;
    if (msip) access(last, flush, true, 0x2000000, {1});
    access(last, flush, false, 0x80002000, {0,0}); drain(tsi, out, "poll", last);
    require(tsi.loaded_in_host() && !tsi.done(), "actual HTIF did not enter poll");
    std::cout << "REAL_TESTCHIP_INIT flush=" << flush << " msip=" << msip
              << " accesses=4 read_results=89abcdef,fedcba98 serial_words=" << first.size()+second.size()+last.size() << '\n';
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_INIT_FESVR_DPI
extern "C" int tsi_init_fesvr(const char *e,const char *o,const char *f,const char *m) { return run(e,o,f,m); }
extern "C" void tsi_init_fesvr_exit(int code) { std::exit(code); }
#else
int main(int argc,char **argv) { if(argc!=5) return 2; return run(argv[1],argv[2],argv[3],argv[4]); }
#endif
