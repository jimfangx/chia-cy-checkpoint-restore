// Actual production host timing component, not a full FireSim runtime cut.
#include "emul/host_timing.h"
#include <algorithm>
#include <climits>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>

namespace {
constexpr int operations = 7200;
const int cuts[] = {0, 1, 2, 3, 5, 17, 310, 311, 312, 313, 623, 624, 625, 626, 1250, 2500, 7199};
void require(bool ok, const char *why) {
  if (!ok) throw std::runtime_error(why);
}
template <class F> void throws(F &&f) {
  bool rejected = false;
  try { f(); } catch (const std::runtime_error &) { rejected = true; }
  require(rejected, "unsupported/invalid operation accepted");
}
void put(std::vector<uint8_t> &bytes, size_t index, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i) bytes.at(index * 8 + i) = value >> (i * 8);
}
std::vector<uint8_t> read(const std::string &path) {
  std::ifstream in(path, std::ios::binary);
  require(bool(in), "missing owner file");
  return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
void write(const std::string &path, const std::vector<uint8_t> &bytes) {
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(out), "owner write failed");
}
void negative(uint64_t maximum, uint64_t seed) {
  host_timing_t owner(maximum, seed);
  owner.begin_delay();
  auto baseline = owner.save_checkpoint();
  size_t rejected = 0;
  auto invalid = [&](const std::vector<uint8_t> &bytes) {
    throws([&] { owner.validate_checkpoint(bytes); });
    require(owner.save_checkpoint() == baseline, "validation mutated owner");
    throws([&] { owner.load_checkpoint(bytes); });
    require(owner.save_checkpoint() == baseline, "invalid load mutated owner");
    ++rejected;
  };
  for (size_t i = 0; i < baseline.size(); ++i)
    invalid({baseline.begin(), baseline.begin() + i});
  for (auto change : std::vector<std::pair<size_t, uint64_t>>{
       {0, 0}, {1, 2}, {2, 0}, {2, maximum + 1}, {3, seed ^ (uint64_t{1} << 63)},
       {4, maximum + 1}, {4, 0}, {5, maximum + 1}, {6, 311}, {319, 313},
       {319, std::numeric_limits<uint64_t>::max()}}) {
    auto corrupt = baseline; put(corrupt, change.first, change.second); invalid(corrupt);
  }
  auto corrupt = baseline;
  corrupt.push_back(0); invalid(corrupt);
  corrupt = baseline;
  for (size_t i = 7; i < 319; ++i) put(corrupt, i, 0);
  invalid(corrupt);
  corrupt = baseline; put(corrupt, 4, 0); put(corrupt, 5, 0); invalid(corrupt);
  host_timing_t different(maximum == 1 ? 2 : maximum - 1, seed);
  throws([&] { different.load_checkpoint(baseline); });
  host_timing_t seed_mismatch(maximum, seed ^ 1);
  throws([&] { seed_mismatch.load_checkpoint(baseline); });
  throws([&] { owner.begin_delay(); });
  host_timing_t empty;
  throws([&] { empty.complete_tick(); });
  throws([&] { empty.run_delay({}); });
  throws([] { host_timing_t zero(0); });
  throws([] { host_timing_t big(uint64_t{INT_MAX} + 1); });
  for (const auto &bad : {"", "-1", "+1", " 1", "1 ", "1x", "18446744073709551616"})
    throws([&] { host_timing_t::parse_unsigned(bad, std::numeric_limits<uint64_t>::max()); });
  throws([] { host_timing_t::parse_unsigned("2147483648", INT_MAX); });
  require(host_timing_t::parse_unsigned("18446744073709551615", std::numeric_limits<uint64_t>::max()) ==
          std::numeric_limits<uint64_t>::max(), "full-width seed parsing failed");
  require(host_timing_t::parse_unsigned("0000", INT_MAX) == 0, "leading zeros changed parsing");
  // Every synchronous draw/commit must reproduce the previous production loop.
  std::mt19937_64 legacy(seed);
  host_timing_t synchronous(maximum, seed);
  for (int i = 0; i < 1500; ++i) {
    uint64_t expected = legacy() % maximum + 1, ticks = 0;
    synchronous.run_delay([&] {
      require(synchronous.pending_ticks() == expected - ticks, "commit order differs");
      throws([&] { synchronous.save_checkpoint(); });
      throws([&] { synchronous.validate_checkpoint(baseline); });
      throws([&] { synchronous.load_checkpoint(baseline); });
      throws([&] { synchronous.begin_delay(); });
      throws([&] { synchronous.complete_tick(); });
      throws([&] { synchronous.run_delay([] {}); });
      ++ticks;
    });
    require(ticks == expected && synchronous.pending_ticks() == 0, "legacy timing differs");
  }
  // A pending component delay resumes without redrawing, including last tick.
  host_timing_t restored(maximum, seed);
  restored.load_checkpoint(baseline);
  uint64_t pending = restored.pending_ticks(), ticks = 0;
  restored.run_delay([&] { ++ticks; });
  require(ticks == pending, "pending delay redrawn on resume");
  owner.run_delay([] {});
  require(owner.save_checkpoint() == restored.save_checkpoint(), "pending continuation differs");
  host_timing_t failed(maximum, seed);
  throws([&] { failed.run_delay([] { throw std::runtime_error("interrupted RTL handoff"); }); });
  throws([&] { failed.save_checkpoint(); });
  throws([&] { failed.validate_checkpoint(baseline); });
  throws([&] { failed.load_checkpoint(baseline); });
  throws([&] { failed.begin_delay(); });
  throws([&] { failed.complete_tick(); });
  throws([&] { failed.run_delay([] {}); });
  // Upper bound configuration is supported without looping billions of ticks.
  host_timing_t wide(INT_MAX, seed);
  wide.begin_delay();
  auto wide_bytes = wide.save_checkpoint();
  host_timing_t wide_restored(INT_MAX, seed);
  wide_restored.load_checkpoint(wide_bytes);
  require(wide_restored.save_checkpoint() == wide_bytes, "maximum delay restore differs");
  std::cout << "PASS: " << rejected << " atomic malformed timing rejections; legacy/suspended/failure/config negatives\n";
}
std::unique_ptr<host_timing_t> fixture;
std::unique_ptr<std::ofstream> trace;
std::string directory, prefix;
bool is_restore;
void init(const std::string &out, int cut, int mode, uint64_t maximum, uint64_t seed) {
  require(cut >= 0 && cut < operations && mode >= 0 && mode <= 2, "invalid test options");
  if (mode == 2) { negative(maximum, seed); return; }
  directory = out; is_restore = mode == 1;
  prefix = out + (is_restore ? "/restore-" + std::to_string(cut) : "/reference");
  fixture = std::make_unique<host_timing_t>(maximum, seed);
  if (is_restore) {
    auto bytes = read(out + "/cut-" + std::to_string(cut) + ".owner");
    fixture->validate_checkpoint(bytes);
    fixture->load_checkpoint(bytes);
    require(fixture->save_checkpoint() == bytes, "restore before first edge differs");
  }
  trace = std::make_unique<std::ofstream>(prefix + ".trace");
  require(bool(*trace), "trace open failed");
}
void step(int index) {
  if (!is_restore && std::find(std::begin(cuts), std::end(cuts), index) != std::end(cuts))
    write(directory + "/cut-" + std::to_string(index) + ".owner", fixture->save_checkpoint());
  *trace << index;
  if (!fixture->pending_ticks()) { fixture->begin_delay(); *trace << " begin "; }
  else { fixture->complete_tick(); *trace << " tick "; }
  *trace << fixture->pending_ticks() << '\n';
}
void finish() {
  write(prefix + ".final.owner", fixture->save_checkpoint());
  trace->close();
  require(bool(*trace), "trace close failed");
}
} // namespace

#ifdef HOST_TIMING_CHECKPOINT_DPI
// VCS may return zero for $fatal; failures must exit the process explicitly.
extern "C" int host_timing_checkpoint_init(const char *out, int cut, int mode,
                                            unsigned long long maximum, unsigned long long seed) {
  try { init(out, cut, mode, maximum, seed); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int host_timing_checkpoint_step(int index) {
  try { step(index); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int host_timing_checkpoint_finish() {
  try { finish(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
#else
int main(int argc, char **argv) {
  try {
    require(argc == 6, "expected mode outdir cut maximum seed");
    int mode = std::stoi(argv[1]), cut = std::stoi(argv[3]);
    init(argv[2], cut, mode, std::stoull(argv[4]), std::stoull(argv[5]));
    if (mode != 2) {
      for (int i = mode == 1 ? cut : 0; i < operations; ++i) step(i);
      finish();
    }
    std::cout << "PASS: host timing component continuation\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
