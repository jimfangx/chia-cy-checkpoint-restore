// HTIF caller component checks. Fixture operation labels are not CPU cycles.
#include "fesvr/tsi_htif_poll.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <filesystem>
#include <functional>
using owner_t = firesim_tsi_htif_poll_t;
static void require(bool ok) { if (!ok) throw std::runtime_error("poll assertion failed"); }
static void rejects(const std::function<void()> &f) {
  bool rejected = false; try { f(); } catch (const std::exception &) { rejected = true; }
  require(rejected);
}
static std::vector<uint8_t> bytes(const std::string &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f));
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
static void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()), b.size()); require(bool(f));
}
struct divergence_t : std::runtime_error { using std::runtime_error::runtime_error; };
class services_t final : public owner_t::services_t {
public:
  owner_t &owner;
  std::istringstream input;
  std::string expected, actual;
  bool called = false;
  services_t(owner_t &o, const std::string &line) : owner(o), input(line) { input >> expected; }
  uint64_t number() { uint64_t n; require(bool(input >> n)); return n; }
  void service(const std::string &name) {
    actual = name; called = true;
    rejects([&] { owner.save_checkpoint(); });
    if (expected != name) throw divergence_t("service expected="+expected+" actual="+name);
  }
  void equal(uint64_t expected, uint64_t actual, const char *signal) {
    if (expected != actual) throw divergence_t(std::string("signal=")+signal+" expected="+
                                               std::to_string(expected)+" actual="+std::to_string(actual));
  }
  bool exiting() override { service("X"); return number(); }
  bool read(uint64_t address, uint64_t &value) override {
    service("R"); equal(number(), address, "read_address");
    bool done = number(); uint64_t result = number(); if (done) value = result; return done;
  }
  void write(uint64_t address, uint64_t value) override {
    service("W"); equal(number(), address, "write_address"); equal(number(), value, "write_data");
  }
  void responses() { const auto n = number(); for (size_t i = 0; i < n; ++i) owner.respond(number()); }
  bool dispatch(uint64_t value) override {
    service("D"); equal(number(), value, "tohost_command"); responses(); return number();
  }
  void tick_devices() override { service("T"); responses(); }
  bool idle() override { service("I"); return number(); }
  void finish() { if (!called && expected != "N") throw divergence_t("service expected="+expected+" actual=none"); }
};
static size_t invalid_checks(owner_t &owner) {
  const auto valid = owner.save_checkpoint(); size_t count = 0;
  auto invalid = [&](std::vector<uint8_t> b) {
    rejects([&] { owner.validate_checkpoint(b); }); rejects([&] { owner.load_checkpoint(b); });
    require(owner.save_checkpoint() == valid); ++count;
  };
  for (size_t n = 0; n < valid.size(); ++n) invalid({valid.begin(), valid.begin()+n});
  for (size_t n = 0; n < 56; ++n) for (unsigned bit = 0; bit < 8; ++bit) {
    auto bad = valid; bad[n] ^= 1U<<bit; invalid(bad);
  }
  auto extra = valid; extra.push_back(0); invalid(extra);
  auto bad = valid; bad[56] = 9; invalid(bad);
  bad = valid; bad[72] = 5; invalid(bad);
  return count;
}
static int run(const char *source, const char *plan, const char *destination) {
  try {
    const std::filesystem::path out(destination); std::filesystem::create_directories(out);
    owner_t owner(4096,8192,4);
    if (std::string(source) != "new") owner.load_checkpoint(bytes(source));
    write(out/"preedge.owner", owner.save_checkpoint());
    std::cout << "COMPLETE_POLL_READBACK target_edges=0 context_entries=0 services=0\n";
    const auto invalids = invalid_checks(owner);
    std::ifstream f(plan); require(bool(f)); std::string line; size_t operation = 0;
    while (std::getline(f,line)) {
      services_t service(owner, line);
      try { owner.advance(service); service.finish(); }
      catch (const divergence_t &e) {
        std::cerr << "FIRST_DIVERGENCE fixture_operation=" << operation << ' ' << e.what() << " acknowledged=0\n";
        return 3;
      }
      write(out/("after-"+std::to_string(operation)+".owner"), owner.save_checkpoint()); ++operation;
    }
    // Service exceptions poison the caller, so it cannot be rehabilitated.
    owner_t poisoned(4096,8192,4); services_t wrong(poisoned,"D 0 0");
    rejects([&] { poisoned.advance(wrong); });
    rejects([&] { poisoned.save_checkpoint(); });
    rejects([&] { poisoned.load_checkpoint(owner.save_checkpoint()); });
    rejects([&] { poisoned.respond(1); });
    // Limit exhaustion and unsupported configurations reject explicitly.
    owner_t full(4096,8192,1); full.respond(1); rejects([&] { full.respond(2); });
    rejects([] { owner_t bad(4097,8192); }); rejects([] { owner_t bad(4096,8192,0); });
    std::cout << "POLL_CHECKS atomic_invalids=" << invalids << " continued_operations=" << operation << "\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_HTIF_POLL_DPI
extern "C" int tsi_htif_poll(const char *s,const char *p,const char *o) { return run(s,p,o); }
extern "C" void tsi_htif_poll_exit(int code) { std::exit(code); }
#else
int main(int argc, char **argv) { if (argc!=4) return 2; return run(argv[1],argv[2],argv[3]); }
#endif
