// Real HTIF poll/BCD/sealed-terminal component continuations, not CPU cuts.
#include "fesvr/tsi_bcd.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <unistd.h>
namespace fs = std::filesystem;
using images_t = firesim_tsi_bcd_t::sealed_checkpoint_t;
static constexpr uint64_t READ = uint64_t(1) << 56;
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static void save(const fs::path &path, const std::vector<uint8_t> &bytes) {
  std::ofstream file(path, std::ios::binary);
  file.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(file), "cannot save component image");
}
static images_t load(const fs::path &path) {
  images_t images;
  for (const auto *name : {"poll", "terminal", "bcd"}) {
    std::ifstream file(path.string()+"."+name, std::ios::binary);
    require(bool(file), "missing component image");
    images.emplace_back(name, std::vector<uint8_t>(std::istreambuf_iterator<char>(file), {}));
  }
  return images;
}
class memory_t final : public memif_t {
public:
  memory_t() : memif_t(nullptr) {}
  void read(addr_t, size_t, void *) override { throw std::runtime_error("unexpected memif read"); }
  void write(addr_t, size_t, const void *) override { throw std::runtime_error("unexpected memif write"); }
};
struct group_t {
  std::ostringstream events;
  size_t services = 0;
  firesim_tsi_htif_poll_t poll{4096,8192,8};
  firesim_tsi_terminal_t terminal{{65,0,255}, [this](uint8_t ch) {
    ++services; events << "OUTPUT " << unsigned(ch) << '\n';
  }};
  firesim_tsi_bcd_t bcd{poll,8,&terminal};
  images_t images() const {
    return {{"poll",poll.save_checkpoint()},{"terminal",terminal.save_checkpoint()},
            {"bcd",bcd.save_checkpoint()}};
  }
  void capture(const fs::path &path) const {
    for (const auto &[name,bytes] : images()) save(path.string()+"."+name,bytes);
  }
};
struct divergence_t {};
class services_t final : public firesim_tsi_htif_poll_t::services_t {
public:
  services_t(group_t &g, std::string line, size_t operation) : g(g), line(std::move(line)), operation(operation) {}
  void check(const std::string &actual) {
    require(!called, "multiple services per component step"); called = true;
    if (actual != line) {
      g.events << "FIRST_DIVERGENCE host_operation=" << operation << " expected=" << line
               << " actual=" << actual << " acknowledged=0\n";
      throw divergence_t{};
    }
    ++g.services; g.events << actual << '\n';
  }
  bool exiting() override { unsigned value=0; char op; std::istringstream(line) >> op >> value;
    check("X "+std::to_string(value)); return value; }
  bool read(uint64_t address, uint64_t &value) override {
    char op; uint64_t expected=0, ready=0, data=0; std::istringstream(line) >> op >> expected >> ready >> data;
    check("R "+std::to_string(address)+" "+std::to_string(ready)+" "+std::to_string(data));
    // Blocked reads do not publish partial data into the caller.
    if (ready) value = data; return ready;
  }
  void write(uint64_t address, uint64_t value) override {
    check("W "+std::to_string(address)+" "+std::to_string(value));
  }
  void dispatch(uint64_t value) override {
    check("D "+std::to_string(value));
    command_t command(memory, value, [this](uint64_t response) { g.poll.respond(response); });
    g.bcd.handle_command(command);
  }
  void tick_devices() override { check("T"); g.bcd.tick(); }
  bool idle() override { char op; unsigned ready=0; std::istringstream(line) >> op >> ready;
    check("I "+std::to_string(ready)); return ready; }
  void finish() { if (!called) check("N"); }
private:
  group_t &g;
  const std::string line;
  const size_t operation;
  bool called = false;
  memory_t memory;
};
extern void tsi_terminal_fail_allocation_after(long);
static void reject_tests(group_t &g, const images_t &good, const fs::path &out) {
  // Every destination owner differs, so publication of even one peer is visible.
  g.terminal.read(); g.terminal.read(); g.terminal.write(42);
  g.poll.respond(99);
  memory_t memory; command_t command(memory, READ, [](uint64_t){}); g.bcd.handle_command(command);
  const auto before = g.images(); const auto services = g.services; const auto events = g.events.str();
  require(before[0]!=good[0] && before[1]!=good[1] && before[2]!=good[2], "equal destination hides partial restore");
  auto unchanged = [&] {
    require(g.images()==before && g.services==services && g.events.str()==events,
            "polling transaction partially published state or entered services");
  };
  size_t malformed = 0, membership = 0;
  auto reject = [&](const images_t &bad) {
    bool failed=false; try { g.bcd.load_sealed_polling_checkpoint(bad); }
    catch (const std::runtime_error &) { failed=true; }
    require(failed,"invalid polling group accepted"); unchanged();
  };
  for (const auto &bad : std::vector<images_t>{{},{good[0],good[1]},{good[0],good[2]},
       {good[1],good[2]},{good[1],good[0],good[2]},{good[0],good[1],good[1]},
       {good[0],good[1],good[2],good[2]},{{"unknown",good[0].second},good[1],good[2]}}) {
    reject(bad); ++membership;
  }
  for (size_t owner=0; owner<good.size(); ++owner) {
    for (size_t size=0; size<good[owner].second.size(); ++size) {
      auto bad=good; bad[owner].second.resize(size); reject(bad); ++malformed;
    }
    auto bad=good; bad[owner].second.push_back(0); reject(bad); ++malformed;
    // Reject mismatched configuration with otherwise valid peer images.
    bad=good; bad[owner].second[0]^=1; reject(bad); ++malformed;
  }
  long failures=0;
  for (;;++failures) {
    bool exhausted=false; tsi_terminal_fail_allocation_after(failures);
    try { g.bcd.load_sealed_polling_checkpoint(good); }
    catch (const std::bad_alloc &) { exhausted=true; }
    catch (...) { tsi_terminal_fail_allocation_after(-1); throw; }
    tsi_terminal_fail_allocation_after(-1);
    if (!exhausted) break;
    unchanged();
  }
  require(failures>=6 && g.images()==good && g.services==services && g.events.str()==events,
          "polling transaction incomplete or allocation injection missed owners");
  g.capture(out/"preedge");
  // A generic response closure cannot substitute another polling destination.
  firesim_tsi_bcd_t unbound([](uint64_t){},8,&g.terminal);
  const auto unbound_before=unbound.save_checkpoint(); bool failed=false;
  try { unbound.load_sealed_polling_checkpoint(good); } catch(const std::runtime_error &) { failed=true; }
  require(failed && unbound.save_checkpoint()==unbound_before && g.images()==good,
          "unbound polling callback accepted or mutated peers");
  std::cout << "POLLING_TRANSACTION malformed=" << malformed << " membership=" << membership
            << " allocation_failures=" << failures << " binding_rejections=1 unchanged_on_failure=1 services_before_readback=0\n";
}
static int run(const char *mode, const char *source, const char *plan, const char *destination, int cut) {
  try {
    const fs::path out(destination); fs::create_directories(out);
    group_t g;
    if (std::string(mode)=="invalid") { reject_tests(g,load(source),out); return 0; }
    if (std::string(mode)!="capture") {
      const auto good=load(source); g.bcd.load_sealed_polling_checkpoint(good);
      require(g.images()==good && !g.services && g.events.str().empty(),"restore entered services or omitted state");
      g.capture(out/"preedge");
      std::cout << "POLLING_READBACK owners=3 target_edges=0 services=0\n";
    } else g.capture(out/"cut-0");
    std::ifstream file(plan); require(bool(file),"missing component service plan");
    std::string line; size_t operation=0;
    while (std::getline(file,line)) {
      if (operation++ < size_t(cut)) continue;
      services_t services(g,line,operation-1);
      try { g.poll.advance(services); services.finish(); }
      catch (const divergence_t &) {
        std::ofstream(out/"events.log") << g.events.str(); return 3;
      }
      g.capture(out/("cut-"+std::to_string(operation)));
    }
    g.capture(out/"final"); std::ofstream(out/"events.log") << g.events.str();
    return 0;
  } catch(const std::exception &error) { std::cerr << "FAIL " << error.what() << '\n'; return 2; }
}
#ifdef TSI_POLLING_DEVICES_DPI
extern "C" int tsi_polling_devices(const char *m,const char *s,const char *p,const char *d,int cut) { return run(m,s,p,d,cut); }
extern "C" void tsi_polling_devices_exit(int code) { std::exit(code); }
#else
int main(int argc,char **argv) { if (argc!=6) return 2; return run(argv[1],argv[2],argv[3],argv[4],std::stoi(argv[5])); }
#endif
