// Fresh TestChip initialization caller components; not complete HTIF/CPU.
#include "fesvr/tsi_init_accesses.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
using owner_t = firesim_tsi_init_accesses_t;
static void require(bool b, const std::string &s) { if (!b) throw std::runtime_error(s); }
static owner_t make_owner(unsigned variant) {
  if (variant == 0 || variant == 1) return owner_t({}, variant == 1);
  if (variant == 2) return owner_t({{0x10000010, 0, false}}, false);
  if (variant == 5 || variant == 6)
    return owner_t({{0x80000100, 0x12345678, true}, {0x10000010, 0, false},
                    {0x80000100, 0, true}, {0x80000108, 0, false}}, variant == 6);
  require(variant == 3 || variant == 4, "unknown configuration");
  return owner_t({{0x10000010, 0, false}, {0x80000000, 0xffffffff, true},
                  {~uint64_t(0), 0, false}, {0x10000010, 0, true},
                  {0x80000000, 0, false}}, variant == 3);
}
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing image");
  return {std::istreambuf_iterator<char>(f), {}};
}
static void save(const fs::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); require(bool(f), "save failed");
}
static std::vector<std::string> lines(const char *p) {
  std::ifstream f(p); require(bool(f), "missing oracle");
  std::vector<std::string> r; std::string s;
  while (std::getline(f, s)) r.push_back(s);
  return r;
}
static std::string operation(owner_t &r, const std::string &s) {
  std::istringstream in(s); std::string op; in >> op;
  if (op == "BEGIN") r.begin();
  else if (op == "SELECT") {
    const auto p = r.select();
    if (p == owner_t::phase_t::complete) return "SELECT COMPLETE";
    return "SELECT " + std::to_string(static_cast<uint64_t>(p)) + " ADDRESS=" + std::to_string(r.address());
  } else if (op == "SET_READ") {
    uint64_t value; in >> value; require(value <= 0xffffffff, "bad read value");
    *r.read_destination() = value;
  } else if (op == "WRITE_SOURCE") return op + " " + std::to_string(*r.write_source());
  else if (op == "READ_RESULT") return op + " " + std::to_string(r.read_result());
  else if (op == "WRITE_RESULT") return op + " " + std::to_string(r.write_result());
  else if (op == "CHILD_RETURN") r.child_returned();
  else if (op == "RETIRE") r.retire();
  else throw std::runtime_error("unknown operation");
  return s;
}
static size_t checks() {
  size_t count = 0;
  auto reject = [&](auto f) {
    bool bad = false; try { f(); } catch (const std::exception &) { bad = true; }
    require(bad, "missing rejection"); ++count;
  };
  for (unsigned variant = 0; variant < 5; ++variant) {
    auto r = make_owner(variant);
    auto atomic = [&](auto f) {
      auto before = r.save_checkpoint(); reject(f);
      require(before == r.save_checkpoint(), "partial mutation");
    };
    atomic([&] { r.select(); }); atomic([&] { r.child_returned(); });
    atomic([&] { r.retire(); }); atomic([&] { r.address(); });
    atomic([&] { r.read_destination(); }); atomic([&] { r.write_source(); });
    atomic([&] { r.read_result(); }); atomic([&] { r.write_result(); });
    r.begin(); atomic([&] { r.begin(); });
    for (;;) {
      auto image = r.save_checkpoint();
      for (size_t i = 0; i < image.size(); ++i) {
        atomic([&] { r.validate_checkpoint({image.begin(), image.begin()+i}); });
        atomic([&] { r.load_checkpoint({image.begin(), image.begin()+i}); });
      }
      for (size_t i = 0; i < image.size()-24; ++i) {
        auto bad = image; bad[i] ^= 1; atomic([&] { r.load_checkpoint(bad); });
      }
      auto fresh = make_owner(variant); fresh.load_checkpoint(image);
      require(fresh.save_checkpoint() == image, "complete readback differs"); ++count;
      const auto p = r.select();
      if (p == owner_t::phase_t::complete) break;
      atomic([&] { r.select(); }); atomic([&] { r.begin(); }); atomic([&] { r.retire(); });
      if (p == owner_t::phase_t::read_child) {
        atomic([&] { r.write_source(); }); atomic([&] { r.read_result(); });
        *r.read_destination() = 0xfedcba98;
      } else {
        atomic([&] { r.read_destination(); }); atomic([&] { r.write_result(); });
      }
      auto child = r.save_checkpoint(); fresh.load_checkpoint(child);
      require(fresh.save_checkpoint() == child && fresh.address() == r.address(), "child buffer differs"); ++count;
      r.child_returned(); atomic([&] { r.child_returned(); });
      auto returned = r.save_checkpoint(); fresh.load_checkpoint(returned);
      require(fresh.save_checkpoint() == returned, "returned buffer differs"); ++count;
      if (p == owner_t::phase_t::read_child) require(fresh.read_result() == 0xfedcba98, "read destination not reconstructed");
      r.retire();
      if (p == owner_t::phase_t::msip_child) break;
    }
    // Reset may legitimately be called again; it must restart exactly once.
    r.begin(); require(r.save_checkpoint() == [&] { auto f=make_owner(variant); f.begin(); return f.save_checkpoint(); }(), "repeated reset differs"); ++count;
    const auto valid = r.save_checkpoint(); r.interrupt();
    reject([&] { r.save_checkpoint(); }); reject([&] { r.validate_checkpoint(valid); });
    reject([&] { r.load_checkpoint(valid); }); reject([&] { r.begin(); });
    reject([&] { r.select(); }); reject([&] { r.child_returned(); }); reject([&] { r.retire(); });
    reject([&] { r.address(); }); reject([&] { r.read_destination(); }); reject([&] { r.write_source(); });
    reject([&] { r.read_result(); }); reject([&] { r.write_result(); });
  }
  return count;
}
static int run(const char *mode, const char *destination, const char *commands,
               const char *expected, const char *image, const char *cut, const char *variant) {
  try {
    fs::path out(destination); fs::create_directories(out);
    auto r = make_owner(std::stoul(variant));
    require(r.checkpoint_schema() == "firesim.tsi.init-accesses.v1", "wrong schema");
    if (std::string(mode) == "check") { std::cout << "ATOMIC_CHECKS " << checks() << '\n'; return 0; }
    if (std::string(mode) == "invalid") {
      r.begin(); const auto before = r.save_checkpoint(); bool bad = false;
      try { const auto b=read(image); r.validate_checkpoint(b); r.load_checkpoint(b); }
      catch (const std::exception &) { bad = true; }
      require(bad && r.save_checkpoint() == before, "invalid partial restore");
      save(out/"unchanged.owner", before);
      std::cout << "REJECTED_BEFORE_MUTATION zero_edges=1\n"; return 0;
    }
    const bool reference = std::string(mode) == "reference";
    if (!reference) { const auto b=read(image); r.validate_checkpoint(b); r.load_checkpoint(b); }
    save(out/"preedge.owner", r.save_checkpoint());
    if (std::string(mode) == "readback") {
      std::cout << "COMPLETE_READBACK zero_edges=1 restore_services=0\n"; return 0;
    }
    const auto ops=lines(commands), wanted=lines(expected); require(ops.size()==wanted.size(), "wrong oracle size");
    const size_t first=reference ? 0 : std::stoull(cut); require(first<=ops.size(), "wrong cut");
    size_t acknowledged=0;
    auto snapshot=[&](size_t i) { save(out/("cut-"+std::to_string(i)+".owner"),r.save_checkpoint()); };
    snapshot(first); std::ofstream trace(out/"trace");
    for (size_t i=first; i<ops.size(); ++i) {
      const auto actual="OP "+std::to_string(i+1)+" C "+std::to_string(101+i)+" "+operation(r,ops[i]);
      if (actual != wanted[i]) {
        std::ofstream f(out/"first-divergence.json");
        f << "{\"operation\":" << i+1 << ",\"fixture_cycle\":" << 101+i << ",\"acknowledged\":" << acknowledged
          << ",\"expected\":\"" << wanted[i] << "\",\"actual\":\"" << actual << "\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE "+actual);
      }
      trace << actual << '\n'; ++acknowledged; snapshot(i+1);
    }
    std::cout << "COMPLETE_READBACK zero_edges=1 restore_services=0 acknowledged=" << acknowledged << '\n'; return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_INIT_DPI
extern "C" int tsi_init_checkpoint(const char *m,const char *o,const char *c,const char *e,const char *i,const char *s,const char *v) { return run(m,o,c,e,i,s,v); }
extern "C" void tsi_init_exit(int code) { std::exit(code); }
#else
int main(int argc,char **argv) { if(argc!=8) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]); }
#endif
