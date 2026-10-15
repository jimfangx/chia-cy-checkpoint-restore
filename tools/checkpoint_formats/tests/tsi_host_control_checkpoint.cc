// Fresh-process continuation of production FireSim host control. This has no
// FESVR context and does not authorize aggregate CPU checkpoint support.
#include "fesvr/tsi_host_control.h"
#include "fesvr/tsi_htif_poll.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>
namespace fs = std::filesystem;
static void require(bool b, const std::string &s) { if (!b) throw std::runtime_error(s); }
static std::vector<uint8_t> read(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "missing input");
  return {std::istreambuf_iterator<char>(f), {}};
}
static void save(const fs::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); require(bool(f), "cannot save owner");
}
static std::vector<std::string> lines(const char *p) {
  std::ifstream f(p); require(bool(f), "missing commands/oracle");
  std::vector<std::string> result; std::string s;
  while (std::getline(f, s)) result.push_back(s);
  return result;
}
static std::string operation(firesim_tsi_host_control_t &o, const std::string &s) {
  std::istringstream in(s); std::string op; in >> op;
  if (op == "IDLE_BEGIN") o.begin_idle();
  else if (op == "IDLE_NEXT") return op + (o.advance_idle() ? " YIELD" : " RETURN");
  else if (op == "RESET_BEGIN") o.begin_reset();
  else if (op == "RESET_NEXT") return op + (o.advance_reset() ? " YIELD" : " CHILD");
  else if (op == "RESET_END") o.finish_reset();
  else if (op == "TARGET") { bool v; in >> v; o.set_loaded_in_target(v); return op + " " + std::to_string(v); }
  else if (op == "QUERY") return op + " BUSY=" + std::to_string(o.busy()) + " HOST=" + std::to_string(o.loaded_in_host());
  else throw std::runtime_error("unknown operation");
  return op;
}
static size_t checks(uint64_t count) {
  firesim_tsi_host_control_t o(count); size_t n = 0;
  auto reject = [&](auto f) {
    bool failed = false; try { f(); } catch (const std::runtime_error &) { failed = true; }
    require(failed, "missing rejection"); ++n;
  };
  auto unchanged = [&](auto f) { auto before = o.save_checkpoint(); reject(f); require(before == o.save_checkpoint(), "partial mutation"); };
  unchanged([&] { o.advance_idle(); }); unchanged([&] { o.advance_reset(); }); unchanged([&] { o.finish_reset(); });
  o.begin_idle(); auto image = o.save_checkpoint();
  for (size_t i = 0; i < image.size(); ++i) {
    unchanged([&] { o.validate_checkpoint({image.begin(), image.begin() + i}); });
    unchanged([&] { o.load_checkpoint({image.begin(), image.begin() + i}); });
  }
  auto extra = image; extra.push_back(0); unchanged([&] { o.load_checkpoint(extra); });
  for (size_t at = 0; at < 40; ++at) {
    auto bad = image; bad[at] ^= 1; unchanged([&] { o.load_checkpoint(bad); });
  }
  unchanged([&] { o.begin_idle(); }); unchanged([&] { o.begin_reset(); }); unchanged([&] { o.finish_reset(); });
  unchanged([&] { o.advance_reset(); });
  // Every interrupted phase rejects all state access and all future actions.
  for (unsigned phase = 0; phase < 4; ++phase) {
    firesim_tsi_host_control_t broken(count);
    if (phase == 1) broken.begin_idle();
    if (phase >= 2) broken.begin_reset();
    if (phase == 3) { broken.set_loaded_in_target(true); broken.advance_reset(); }
    broken.interrupt();
    reject([&] { broken.save_checkpoint(); }); reject([&] { broken.validate_checkpoint(image); });
    reject([&] { broken.load_checkpoint(image); }); reject([&] { broken.busy(); });
    reject([&] { broken.loaded_in_host(); }); reject([&] { broken.set_loaded_in_target(true); });
    reject([&] { broken.begin_idle(); }); reject([&] { broken.advance_idle(); });
    reject([&] { broken.begin_reset(); }); reject([&] { broken.advance_reset(); }); reject([&] { broken.finish_reset(); });
  }
  return n;
}
static int run(const char *mode, const char *destination, const char *commands,
               const char *expected, const char *image, const char *cut_text, const char *variant) {
  try {
    const uint64_t count = std::stoull(variant); fs::path out(destination); fs::create_directories(out);
    firesim_tsi_host_control_t owner(count);
    require(owner.checkpoint_schema() == "firesim.tsi.host-control.v1", "wrong owner schema");
    if (std::string(mode) == "check") { std::cout << "ATOMIC_CHECKS " << checks(count) << '\n'; return 0; }
    if (std::string(mode) == "invalid") {
      owner.set_loaded_in_target(true); const auto before = owner.save_checkpoint(); bool failed = false;
      try { owner.load_checkpoint(read(image)); } catch (const std::exception &) { failed = true; }
      require(failed && before == owner.save_checkpoint(), "invalid image partially restored");
      save(out / "unchanged.owner", before); std::cout << "REJECTED_BEFORE_MUTATION zero_edges=1\n"; return 0;
    }
    if (std::string(mode) == "readback") {
      owner.load_checkpoint(read(image)); save(out / "preedge.owner", owner.save_checkpoint());
      fs::path poll_image(image); poll_image.replace_extension(".poll");
      if (fs::is_regular_file(poll_image)) {
        firesim_tsi_htif_poll_t poll(0x80002000,0x80002008);
        poll.load_checkpoint(read(poll_image)); save(out / "preedge.poll",poll.save_checkpoint());
        std::cout << "COMPLETE_ACTUAL_POLL_READBACK target_edges=0 context_entries=0 services=0\n";
      }
      std::cout << "COMPLETE_READBACK zero_edges=1 restore_services=0\n"; return 0;
    }
    auto ops = lines(commands), wanted = lines(expected); require(ops.size() == wanted.size(), "bad oracle");
    const bool reference = std::string(mode) == "reference";
    size_t first = reference ? 0 : std::stoull(cut_text), acknowledged = 0;
    require(first <= ops.size(), "bad cut");
    if (!reference) owner.load_checkpoint(read(image));
    save(out / "preedge.owner", owner.save_checkpoint());
    save(out / ("cut-" + std::to_string(first) + ".owner"), owner.save_checkpoint());
    std::ofstream trace(out / "trace");
    for (size_t i = first; i < ops.size(); ++i) {
      auto actual = "OP " + std::to_string(i + 1) + " C " + std::to_string(101 + i) + " " + operation(owner, ops[i]);
      if (actual != wanted[i]) {
        std::ofstream f(out / "first-divergence.json");
        f << "{\"operation\":" << i+1 << ",\"fixture_cycle\":" << 101+i << ",\"acknowledged\":" << acknowledged
          << ",\"expected\":\"" << wanted[i] << "\",\"actual\":\"" << actual << "\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE " + actual);
      }
      trace << actual << '\n'; ++acknowledged;
      save(out / ("cut-" + std::to_string(i+1) + ".owner"), owner.save_checkpoint());
    }
    std::cout << "COMPLETE_READBACK zero_edges=1 restore_services=0 acknowledged=" << acknowledged << '\n'; return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_HOST_CHECKPOINT_DPI
extern "C" int tsi_host_checkpoint(const char *m, const char *o, const char *c, const char *e, const char *i, const char *s, const char *v) {
  return run(m, o, c, e, i, s, v);
}
extern "C" void tsi_host_exit(int s) { std::exit(s); }
#else
int main(int argc, char **argv) { if (argc != 8) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]); }
#endif
