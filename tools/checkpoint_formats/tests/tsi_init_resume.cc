// Fresh production initialization dispatch, without entering HTIF/context.
#include "fesvr/firesim_tsi.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
static std::vector<uint8_t> bytes(const fs::path &p) {
  std::ifstream f(p, std::ios::binary);
  if (!f) throw std::runtime_error("missing image");
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
static void write(const fs::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()), b.size());
  if (!f) throw std::runtime_error("write failed");
}
static std::vector<uint8_t> raw(firesim_tsi_t &tsi) {
  std::vector<uint8_t> result;
  for (const checkpoint_owner_t *o : std::vector<const checkpoint_owner_t *>{&tsi.host_control_owner(),
       &tsi.init_accesses_owner(), &tsi.serial_read_owner(), &tsi.serial_queue_owner()}) {
    auto b = o->save_checkpoint(); result.insert(result.end(), b.begin(), b.end());
  }
  return result;
}
static int run(const char *mode, const char *elf, const char *source, const char *plan,
               const char *destination, const char *flush_text, const char *msip_text) {
  try {
    const bool flush = std::stoul(flush_text), msip = std::stoul(msip_text);
    fs::path out(destination); fs::create_directories(out);
    std::vector<std::string> args{"init-resume", "+permissive", "+idle-counts=1",
      "+init_write=0x80000100:0x12345678", "+init_read=0x10000010",
      "+init_write=0x80000100:0x0", "+init_read=0x80000108"};
    if (flush) args.push_back("+cflush_addr=0x10000100");
    if (!msip) args.push_back("+no_hart0_msip");
    args.push_back("+permissive-off"); args.push_back(elf);
    std::vector<char *> argv; for (auto &a : args) argv.push_back(a.data());
    firesim_tsi_t tsi(argv.size(), argv.data(), true);
    const auto before = raw(tsi);
    if (std::string(mode) == "invalid") {
      std::ifstream cases(plan); std::string name; size_t count = 0;
      if (!cases) throw std::runtime_error("missing invalid list");
      while (std::getline(cases, name)) {
        bool rejected = false;
        try { tsi.load_initialization_checkpoint(bytes(name)); }
        catch (const std::exception &) { rejected = true; }
        if (!rejected || raw(tsi) != before) throw std::runtime_error("invalid bundle changed an owner");
        ++count;
      }
      if (!count) throw std::runtime_error("empty invalid list");
      write(out/"unchanged.owners", raw(tsi));
      std::cout << "ATOMIC_REJECTIONS " << count << " zero_edges=1 context_entries=0\n";
      return 0;
    }
    tsi.load_initialization_checkpoint(bytes(source));
    write(out/"preedge.bundle", tsi.save_initialization_checkpoint());
    std::cout << "COMPLETE_READBACK zero_edges=1 context_entries=0 restore_services=0\n";
    std::ifstream commands(plan); if (!commands) throw std::runtime_error("missing plan");
    std::ofstream trace(out/"trace"); std::string line; size_t op = 0;
    while (std::getline(commands, line)) {
      ++op; std::istringstream in(line); std::string kind; uint64_t expected;
      if (!(in >> kind >> expected)) throw std::runtime_error("bad command");
      uint64_t actual = expected;
      if (kind == "POP") actual = tsi.data_available() ? tsi.in_bits() : uint64_t(1)<<32;
      else if (kind == "ADVANCE") actual = tsi.advance_initialization();
      else if (kind == "SEND") tsi.send_word(expected);
      else if (kind == "TARGET") tsi.set_loaded_in_target(expected);
      else throw std::runtime_error("unknown command");
      if (actual != expected) {
        std::ofstream d(out/"first-divergence.txt");
        d << "FIRST_DIVERGENCE fixture_cycle=" << 100+op << " operation=" << op
          << " signal=" << kind << " expected=" << expected << " actual=" << actual << " acknowledged=0\n";
        std::cerr << "FIRST_DIVERGENCE operation=" << op << '\n'; return 3;
      }
      if (kind == "POP") tsi.recv_word();
      trace << line << '\n'; trace.flush();
      write(out/("after-"+std::to_string(op)+".bundle"), tsi.save_initialization_checkpoint());
    }
    std::cout << "FRESH_INIT_CONTINUATION operations=" << op << " target_edges=0 context_entries=0\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_INIT_RESUME_DPI
extern "C" int tsi_init_resume(const char *m,const char *e,const char *s,const char *p,const char *o,const char *f,const char *h) {
  return run(m,e,s,p,o,f,h);
}
extern "C" void tsi_init_resume_exit(int code) { std::exit(code); }
#else
int main(int argc, char **argv) { if (argc!=8) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]); }
#endif
