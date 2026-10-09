// Tests the production scheduler and separate callback owners, not runtime cuts.
#include "core/systematic_scheduler.h"
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>

namespace {
void require(bool ok, const char *why) {
  if (!ok) throw std::runtime_error(why);
}
uint64_t word(const std::vector<uint8_t> &bytes, size_t offset) {
  require(offset + 8 <= bytes.size(), "truncated test word");
  uint64_t result = 0;
  for (unsigned i = 0; i < 8; ++i) result |= uint64_t(bytes[offset + i]) << (8 * i);
  return result;
}
void put(std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i) bytes.at(offset + i) = value >> (8 * i);
}
std::vector<uint8_t> read(const std::string &path) {
  std::ifstream in(path, std::ios::binary);
  require(bool(in), "missing owner file");
  return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
void write(const std::string &path, const std::vector<uint8_t> &bytes) {
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(out), "owner file write failed");
}
class counter_t final : public checkpoint_owner_t {
public:
  uint64_t count = 0;
  std::string schema = "test.scheduler.counter.v1";
  std::string checkpoint_schema() const override { return schema; }
  std::vector<uint8_t> save_checkpoint() const override {
    std::vector<uint8_t> out(8); put(out, 0, count); return out;
  }
  void validate_checkpoint(const std::vector<uint8_t> &bytes) const override {
    require(bytes.size() == 8 && word(bytes, 0) <= 1000, "invalid callback counter");
  }
  void load_checkpoint(const std::vector<uint8_t> &bytes) override {
    validate_checkpoint(bytes); count = word(bytes, 0);
  }
};
struct fixture_t {
  counter_t a, b;
  systematic_scheduler_t scheduler{{"+max-cycles=101"}};
  std::string events;
  fixture_t(bool reversed = false, uint64_t first = 0) {
    auto add_a = [&] {
      scheduler.register_checkpoint_task("A", first, [&] {
        ++a.count;
        events += " A:" + std::to_string(a.count);
        return a.count % 2 ? 3 : 7;
      }, a);
    };
    auto add_b = [&] {
      scheduler.register_checkpoint_task("B", 2, [&] {
        ++b.count;
        events += " B:" + std::to_string(b.count);
        return b.count % 3 ? 5 : 2;
      }, b);
    };
    if (reversed) { add_b(); add_a(); } else { add_a(); add_b(); }
  }
  std::vector<std::pair<std::string, checkpoint_owner_t *>> owners() {
    auto out = scheduler.checkpoint_owners();
    require(out.size() == 3 && out[0].first == "runtime/scheduler" &&
            out[1].first == "runtime/scheduler/callback/A" &&
            out[2].first == "runtime/scheduler/callback/B", "wrong stable owner inventory");
    return out;
  }
};
const int cuts[] = {0, 1, 2, 3, 4, 9, 16, 27, 38, 39, 40, 60, 79, 83, 84, 85, 86, 99};
std::unique_ptr<fixture_t> fixture;
std::unique_ptr<std::ofstream> trace;
std::string directory, prefix;
int is_restore = 0;
void capture(const std::string &base) {
  auto owners = fixture->owners();
  for (size_t i = 0; i < owners.size(); ++i)
    write(base + "." + std::to_string(i) + ".owner", owners[i].second->save_checkpoint());
}
void init(const std::string &out, int cut, bool restore) {
  directory = out; is_restore = restore;
  prefix = out + (restore ? "/restore-" + std::to_string(cut) : "/reference");
  fixture = std::make_unique<fixture_t>();
  if (restore) {
    auto owners = fixture->owners();
    std::vector<std::vector<uint8_t>> bytes;
    for (size_t i = 0; i < owners.size(); ++i) {
      bytes.push_back(read(out + "/cut-" + std::to_string(cut) + "." + std::to_string(i) + ".owner"));
      owners[i].second->validate_checkpoint(bytes.back());
    }
    // Fully validate all owners before any load. The outer coordinator must
    // also validate RTL, build/integrity/membership and park both contexts.
    for (size_t i = 0; i < owners.size(); ++i) owners[i].second->load_checkpoint(bytes[i]);
    for (size_t i = 0; i < owners.size(); ++i)
      require(owners[i].second->save_checkpoint() == bytes[i], "restore before first edge differs");
  }
  trace = std::make_unique<std::ofstream>(prefix + ".trace");
  require(bool(*trace), "trace open failed");
}
void step(int index) {
  if (!is_restore)
    for (int cut : cuts)
      if (index == cut) capture(directory + "/cut-" + std::to_string(cut));
  fixture->events.clear();
  *trace << index;
  if (fixture->scheduler.finished_scheduled_tasks()) {
    *trace << " finished";
  } else if (index % 2 == 0) {
    fixture->scheduler.run_scheduled_tasks();
    *trace << " callbacks" << fixture->events;
  } else {
    auto delta = fixture->scheduler.get_largest_stepsize();
    *trace << " credit " << delta;
  }
  auto state = fixture->scheduler.save_checkpoint();
  *trace << " cycle " << word(state, 40) << " counts " << fixture->a.count << " " << fixture->b.count << "\n";
}
void finish() {
  capture(prefix + ".final");
  trace.reset(); fixture.reset();
}
void negative(const std::string &out) {
  fixture_t f;
  auto payload = read(out + "/cut-27.0.owner");
  f.scheduler.load_checkpoint(payload);
  const auto baseline = f.scheduler.save_checkpoint();
  size_t rejected = 0;
  auto reject = [&](const std::vector<uint8_t> &bad) {
    for (bool load : {false, true}) {
      bool threw = false;
      try {
        if (load) f.scheduler.load_checkpoint(bad); else f.scheduler.validate_checkpoint(bad);
      } catch (const std::runtime_error &) { threw = true; }
      require(threw, "malformed payload accepted");
      require(f.scheduler.save_checkpoint() == baseline, "rejected payload mutated scheduler");
    }
    ++rejected;
  };
  for (size_t i = 0; i < payload.size(); ++i) reject({payload.begin(), payload.begin() + i});
  for (size_t offset : {size_t(0), size_t(8), size_t(16), size_t(24), size_t(32), size_t(48), size_t(56)}) {
    auto bad = payload; put(bad, offset, word(bad, offset) + 1); reject(bad);
  }
  auto bad = payload; put(bad, 40, 102); reject(bad);
  bad = payload; bad.push_back(0); reject(bad);
  // All callback identity/schema bytes and both initial/deadline fields.
  size_t pos = 56;
  for (unsigned t = 0; t < 2; ++t) {
    for (unsigned field = 0; field < 2; ++field) {
      size_t size = word(payload, pos); pos += 8;
      for (size_t i = 0; i < size; ++i) { bad = payload; bad[pos + i] ^= 0x80; reject(bad); }
      pos += size;
    }
    bad = payload; put(bad, pos, word(bad, pos) + 1); reject(bad); pos += 8;
    bad = payload; put(bad, pos, 0); reject(bad); pos += 8;
  }
  auto throws = [](auto &&fn) {
    bool threw = false; try { fn(); } catch (const std::runtime_error &) { threw = true; }
    require(threw, "unsupported/unsafe state accepted");
  };
  fixture_t reordered(true), first(false, 1);
  throws([&] { reordered.scheduler.load_checkpoint(payload); });
  throws([&] { first.scheduler.load_checkpoint(payload); });
  f.a.schema = "test.scheduler.counter.v2";
  throws([&] { f.scheduler.load_checkpoint(payload); });
  f.a.schema.clear();
  require(f.scheduler.checkpoint_schema().empty(), "unaudited callback reports schema");
  throws([&] { f.scheduler.checkpoint_owners(); });
  systematic_scheduler_t legacy({});
  legacy.register_task(0, [] { return 1; });
  require(legacy.checkpoint_schema().empty(), "anonymous callback supported");
  throws([&] { legacy.save_checkpoint(); });
  throws([&] { legacy.validate_checkpoint(payload); });
  throws([&] { legacy.load_checkpoint(payload); });
  throws([&] { legacy.checkpoint_owners(); });
  counter_t owner, other;
  systematic_scheduler_t tested({});
  size_t guarded = 0;
  tested.register_checkpoint_task("guard", 0, [&] {
    throws([&] { tested.save_checkpoint(); });
    throws([&] { tested.load_checkpoint(payload); });
    throws([&] { tested.validate_checkpoint(payload); });
    throws([&] { tested.checkpoint_owners(); });
    throws([&] { tested.run_scheduled_tasks(); });
    throws([&] { tested.get_largest_stepsize(); });
    throws([&] { tested.register_task(0, [] { return 1; }); });
    ++guarded; return 1;
  }, owner);
  tested.run_scheduled_tasks();
  require(guarded == 1, "busy guard not exercised");
  throws([&] { tested.register_checkpoint_task("guard", 1, [] { return 1; }, other); });
  throws([&] { tested.register_checkpoint_task("different", 1, [] { return 1; }, owner); });
  throws([&] { tested.register_checkpoint_task("bad/id", 1, [] { return 1; }, other); });
  checkpoint_owner_t unsupported;
  throws([&] { tested.register_checkpoint_task("bad", 1, [] { return 1; }, unsupported); });
  for (const auto &arg : {"+max-cycles=-1", "+max-cycles=", "+max-cycles=1x", "+max-cycles=18446744073709551616"})
    throws([&] { systematic_scheduler_t invalid({arg}); });
  systematic_scheduler_t wide({"+max-cycles=18446744073709551615"});
  auto wide_bytes = wide.save_checkpoint();
  put(wide_bytes, 40, UINT64_MAX - 2); wide.load_checkpoint(wide_bytes);
  require(wide.get_largest_stepsize() == 2 && wide.finished_scheduled_tasks(), "64-bit horizon wrapped/truncated");
  throws([&] { wide.get_largest_stepsize(); });
  systematic_scheduler_t zero({"+max-cycles=0"});
  require(zero.finished_scheduled_tasks(), "zero horizon changed");
  zero.load_checkpoint(zero.save_checkpoint());
  throws([&] { zero.get_largest_stepsize(); });
  for (int failure = 0; failure < 3; ++failure) {
    counter_t o; systematic_scheduler_t broken({});
    broken.register_checkpoint_task("failure", 1, [failure]() -> uint64_t {
      if (failure == 0) throw std::runtime_error("callback failure");
      return failure == 1 ? 0 : UINT64_MAX;
    }, o);
    require(broken.get_largest_stepsize() == 1, "wrong initial step");
    throws([&] { broken.run_scheduled_tasks(); });
    throws([&] { broken.save_checkpoint(); });
    throws([&] { broken.load_checkpoint(baseline); });
    throws([&] { broken.get_largest_stepsize(); });
  }
  std::cout << "PASS: " << rejected << " atomic malformed scheduler rejections; callback/boundary/horizon negatives\n";
}
} // namespace

#ifdef SCHEDULER_CHECKPOINT_DPI
extern "C" int scheduler_checkpoint_init(const char *out, int cut, int restore) {
  try { init(out, cut, restore); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
extern "C" int scheduler_checkpoint_step(int index) {
  try { step(index); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
extern "C" int scheduler_checkpoint_finish() {
  try { finish(); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#else
int main(int argc, char **argv) {
  try {
    require(argc == 4, "expected mode outdir cut");
    if (std::string(argv[1]) == "negative") { negative(argv[2]); return 0; }
    bool restore = std::string(argv[1]) == "restore";
    int cut = std::stoi(argv[3]); init(argv[2], cut, restore);
    for (int i = restore ? cut : 0; i < 100; ++i) step(i);
    finish(); std::cout << "PASS: scheduler component continuation\n"; return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
