// Production run-loop + scheduler component test. Services model completion
// independently of issued credit; this is not a whole FireSim runtime cut.
#include "core/stepped_run_loop.h"
#include "core/systematic_scheduler.h"
#include <fstream>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <sstream>

namespace {
void require(bool ok, const char *why) {
  if (!ok) throw std::runtime_error(why);
}
uint64_t word(const std::vector<uint8_t> &bytes, size_t offset) {
  uint64_t value = 0;
  for (unsigned i = 0; i < 8; ++i) value |= uint64_t(bytes.at(offset + i)) << (8 * i);
  return value;
}
void put(std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i) bytes.at(offset + i) = value >> (8 * i);
}
std::vector<uint8_t> read(const std::string &path) {
  std::ifstream in(path, std::ios::binary);
  require(bool(in), "missing payload");
  return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
void write(const std::string &path, const std::vector<uint8_t> &bytes) {
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(out), "owner write failed");
}
struct fixture_t final : stepped_run_loop_t::services_t, checkpoint_owner_t {
  const uint64_t count, stop, horizon;
  stepped_run_loop_t loop;
  systematic_scheduler_t scheduler;
  // completed target cycles, pending credit, issued steps, polls, samples,
  // callbacks, and one counter for each bridge. All belong to services.
  std::vector<uint64_t> fields;
  std::string event;
  bool probe = false, fail = false;
  fixture_t(uint64_t count, uint64_t stop, uint64_t horizon)
      : count(count), stop(stop), horizon(horizon), loop(count),
        scheduler({"+max-cycles=" + std::to_string(horizon)}), fields(6 + count) {
    scheduler.register_checkpoint_task("profile", 0, [&] {
      ++fields[5]; return 4;
    }, *this);
  }
  std::string checkpoint_schema() const override { return "test.stepped-services.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    std::vector<uint8_t> out(8 * (3 + fields.size()));
    put(out, 0, count); put(out, 8, stop); put(out, 16, horizon);
    for (size_t i = 0; i < fields.size(); ++i) put(out, 24 + 8 * i, fields[i]);
    return out;
  }
  void validate_checkpoint(const std::vector<uint8_t> &bytes) const override {
    require(bytes.size() == 8 * (3 + fields.size()) && word(bytes, 0) == count &&
            word(bytes, 8) == stop && word(bytes, 16) == horizon, "invalid services");
    require(word(bytes, 24) <= horizon && word(bytes, 32) <= horizon - word(bytes, 24),
            "invalid completed/pending credit");
  }
  void load_checkpoint(const std::vector<uint8_t> &bytes) override {
    validate_checkpoint(bytes);
    auto replacement = fields;
    for (size_t i = 0; i < fields.size(); ++i) replacement[i] = word(bytes, 24 + 8 * i);
    fields.swap(replacement);
  }
  template <class F> static void throws(F &&f) {
    bool threw = false;
    try { f(); } catch (const std::runtime_error &) { threw = true; }
    require(threw, "unsafe operation accepted");
  }
  void guard() {
    if (probe) {
      // Every service call may suspend on MMIO. Reject all entry points while
      // that synchronous stack is alive, even in non-MMIO-looking callbacks.
      std::vector<uint8_t> payload(48);
      throws([&] { loop.save_checkpoint(); });
      throws([&] { loop.validate_checkpoint(payload); });
      throws([&] { loop.load_checkpoint(payload); });
      throws([&] { loop.advance(*this); });
      throws([&] { loop.finished(); });
      throws([&] { loop.target_done(); });
    }
    if (fail) throw std::runtime_error("service interrupted after possible external effects");
  }
  bool horizon_reached() override {
    guard(); bool done = scheduler.finished_scheduled_tasks();
    event = "horizon " + std::to_string(done); return done;
  }
  void run_tasks() override {
    guard(); scheduler.run_scheduled_tasks(); event = "tasks";
  }
  void issue_step() override {
    guard(); require(fields[1] == 0, "overlapping step");
    fields[1] = scheduler.get_largest_stepsize(); ++fields[2];
    event = "issue " + std::to_string(fields[1]);
  }
  bool step_done() override {
    guard(); ++fields[3];
    if (fields[1]) { --fields[1]; ++fields[0]; }
    event = "poll " + std::to_string(fields[1] == 0); return fields[1] == 0;
  }
  void tick_bridge(uint64_t index) override {
    guard(); ++fields.at(6 + index); event = "tick " + std::to_string(index);
  }
  bool sample_done() override {
    guard(); ++fields[4]; bool done = stop && fields[0] >= stop;
    event = "sample " + std::to_string(done); return done;
  }
  std::vector<checkpoint_owner_t *> owners() { return {&loop, &scheduler, this}; }
};
std::unique_ptr<fixture_t> fixture;
std::unique_ptr<std::ofstream> trace;
std::string directory, prefix;
bool restoring;
void capture(const std::string &base) {
  auto owners = fixture->owners();
  for (size_t i = 0; i < owners.size(); ++i)
    write(base + "." + std::to_string(i) + ".owner", owners[i]->save_checkpoint());
}
void init(const std::string &out, int cut, bool restore, int count, int stop, int horizon) {
  directory = out; restoring = restore;
  prefix = out + (restore ? "/restore-" + std::to_string(cut) : "/reference");
  fixture = std::make_unique<fixture_t>(count, stop, horizon);
  if (restore) {
    std::vector<std::vector<uint8_t>> bytes;
    auto owners = fixture->owners();
    for (size_t i = 0; i < owners.size(); ++i) {
      bytes.push_back(read(out + "/cut-" + std::to_string(cut) + "." + std::to_string(i) + ".owner"));
      owners[i]->validate_checkpoint(bytes.back());
    }
    for (size_t i = 0; i < owners.size(); ++i) owners[i]->load_checkpoint(bytes[i]);
    for (size_t i = 0; i < owners.size(); ++i)
      require(owners[i]->save_checkpoint() == bytes[i], "restore differs before first edge");
  }
  trace = std::make_unique<std::ofstream>(prefix + ".trace");
  require(bool(*trace), "trace open failed");
}
void step(int index) {
  if (!restoring) capture(directory + "/cut-" + std::to_string(index));
  fixture->event = "terminal";
  fixture->loop.advance(*fixture);
  *trace << index << " " << fixture->event;
  for (auto value : fixture->fields) *trace << " " << value;
  *trace << "\n";
}
void finish() { capture(prefix + ".final"); trace.reset(); fixture.reset(); }
void negative() {
  size_t rejected = 0, guarded = 0;
  for (uint64_t count : {0, 1, 3}) {
    fixture_t f(count, 0, 17);
    auto baseline = f.loop.save_checkpoint();
    auto reject = [&](const std::vector<uint8_t> &bytes) {
      fixture_t::throws([&] { f.loop.validate_checkpoint(bytes); });
      fixture_t::throws([&] { f.loop.load_checkpoint(bytes); });
      require(f.loop.save_checkpoint() == baseline, "rejected payload mutated loop");
      ++rejected;
    };
    for (size_t size = 0; size < baseline.size(); ++size)
      reject({baseline.begin(), baseline.begin() + size});
    auto bad = baseline; bad.push_back(0); reject(bad);
    for (size_t offset : {0, 8, 16}) {
      bad = baseline; put(bad, offset, word(bad, offset) ^ 1); reject(bad);
    }
    for (uint64_t phase : {uint64_t(7), UINT64_MAX}) {
      bad = baseline; put(bad, 24, phase); reject(bad);
    }
    for (uint64_t phase = 0; phase <= 6; ++phase) {
      for (uint64_t index : {uint64_t(0), uint64_t(1), count, UINT64_MAX}) {
        for (uint64_t done : {uint64_t(0), uint64_t(1), uint64_t(2), UINT64_MAX}) {
          bad = baseline; put(bad, 24, phase); put(bad, 32, index); put(bad, 40, done);
          bool valid = (phase == 4 ? index < count : index == 0) &&
                       done <= 1 && (!done || phase == 6);
          if (valid) {
            f.loop.validate_checkpoint(bad); f.loop.load_checkpoint(bad);
            require(f.loop.save_checkpoint() == bad, "valid state roundtrip mismatch");
            f.loop.load_checkpoint(baseline);
          } else reject(bad);
        }
      }
    }
    f.probe = true;
    for (int i = 0; i < 128; ++i) f.loop.advance(f);
    require(f.loop.finished() && !f.loop.target_done(), "guard probe did not reach horizon");
    for (uint64_t phase = 0; phase < 6; ++phase) {
      if (phase == 4 && !count) continue;
      fixture_t broken(count, 0, 17);
      auto payload = baseline; put(payload, 24, phase);
      broken.loop.load_checkpoint(payload); broken.fail = true;
      fixture_t::throws([&] { broken.loop.advance(broken); });
      fixture_t::throws([&] { broken.loop.advance(broken); });
      fixture_t::throws([&] { broken.loop.save_checkpoint(); });
      fixture_t::throws([&] { broken.loop.load_checkpoint(baseline); });
      fixture_t::throws([&] { broken.loop.validate_checkpoint(baseline); });
      fixture_t::throws([&] { broken.loop.finished(); });
      fixture_t::throws([&] { broken.loop.target_done(); });
      ++guarded;
    }
  }
  std::cout << "PASS: " << rejected << " atomic malformed rejections; " << guarded
            << " interrupted phases and all suspended/reentrant operation guards\n";
}
} // namespace

#ifdef STEPPED_LOOP_CHECKPOINT_DPI
extern "C" int stepped_loop_checkpoint_init(const char *out, int cut, int restore,
                                             int count, int stop, int horizon) {
  try {
    if (restore == 2) negative(); else init(out, cut, restore, count, stop, horizon);
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int stepped_loop_checkpoint_step(int index) {
  try { step(index); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int stepped_loop_checkpoint_finish() {
  try { finish(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
#else
int main(int argc, char **argv) {
  try {
    require(argc == 8, "expected mode outdir cut bridges stop horizon operations");
    if (std::string(argv[1]) == "negative") { negative(); return 0; }
    bool restore = std::string(argv[1]) == "restore";
    int cut = std::stoi(argv[3]);
    init(argv[2], cut, restore, std::stoi(argv[4]), std::stoi(argv[5]), std::stoi(argv[6]));
    for (int i = restore ? cut : 0; i < std::stoi(argv[7]); ++i) step(i);
    finish(); std::cout << "PASS: stepped-loop component continuation\n"; return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
