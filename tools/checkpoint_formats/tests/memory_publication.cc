// Production memory-owner transactions; synthetic AXI, no whole-CPU claim.
#include "emul/mm.h"
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <new>
#include <thread>
#include <type_traits>

static_assert(!std::is_copy_constructible_v<mm_magic_t> && !std::is_move_constructible_v<mm_magic_t>);

static thread_local long fail_after = -1;
static thread_local bool allocation_failed = false;
void *operator new(std::size_t n) {
  if (fail_after >= 0 && fail_after-- == 0) {
    fail_after = -1; allocation_failed = true; throw std::bad_alloc();
  }
  if (void *p = std::malloc(n ? n : 1)) return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

static constexpr AXI4Config geometry{16, 34, 64};
static constexpr size_t memory_size = 4096;
using memory_t = std::unique_ptr<mm_magic_t>;
using group_t = std::vector<memory_t>;
using image_t = std::vector<std::vector<uint8_t>>;
using candidates_t = std::vector<std::unique_ptr<mm_magic_t::restore_t>>;
static void check(bool ok) { if (!ok) throw std::runtime_error("memory publication assertion"); }
static unsigned rejections = 0;
template<class F> static void reject(F fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejections; return; }
  throw std::runtime_error("memory publication accepted invalid candidate");
}
static group_t make_group(unsigned banks) {
  group_t group;
  for (unsigned i = 0; i < banks; ++i) {
    auto m = std::make_unique<mm_magic_t>(geometry); m->init(memory_size, 64);
    group.push_back(std::move(m));
  }
  return group;
}
static image_t capture(const group_t &group) {
  image_t image;
  for (const auto &m : group) image.push_back(m->save_checkpoint());
  return image;
}
static candidates_t prepare(group_t &group, const image_t &image) {
  check(group.size() == image.size()); candidates_t candidates;
  for (size_t i = 0; i < group.size(); ++i)
    candidates.push_back(group[i]->prepare_checkpoint(image[i]));
  return candidates;
}
static void seal(group_t &group, candidates_t &candidates) {
  for (size_t i = 0; i < group.size(); ++i) group[i]->seal_checkpoint(*candidates[i]);
}
static void publish(group_t &group, candidates_t &candidates) {
  allocation_failed = false; fail_after = 0;
  for (size_t i = 0; i < group.size(); ++i) {
    static_assert(noexcept(group[i]->publish_sealed_checkpoint(*candidates[i])));
    group[i]->publish_sealed_checkpoint(*candidates[i]);
  }
  const bool no_allocation = fail_after == 0 && !allocation_failed;
  fail_after = -1; check(no_allocation);
}
static void save(const std::filesystem::path &out, const std::string &name, const image_t &image) {
  std::filesystem::create_directories(out);
  for (size_t i = 0; i < image.size(); ++i) {
    std::ofstream f(out / (name + "." + std::to_string(i)), std::ios::binary);
    f.write(reinterpret_cast<const char *>(image[i].data()), image[i].size()); check(bool(f));
  }
}
static image_t load(const std::filesystem::path &out, unsigned banks) {
  image_t image;
  for (unsigned i = 0; i < banks; ++i) {
    std::ifstream f(out / ("cut." + std::to_string(i)), std::ios::binary); check(bool(f));
    image.emplace_back(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
  }
  return image;
}
static void initialize(group_t &group) {
  for (unsigned b = 0; b < group.size(); ++b) {
    auto *bytes = static_cast<uint8_t *>(group[b]->get_data());
    for (size_t i = 0; i < memory_size; ++i) bytes[i] = uint8_t(i * 13 + b * 17 + 3);
  }
}
static void tick(mm_magic_t &m, unsigned bank, unsigned step) {
  const std::vector<uint32_t> data{0x12345678u + bank, 0xabcdef00u + step};
  const uint64_t strobes[] = {0x55, 0xaa, 0xff};
  const bool writing = step >= 2 && step <= 4;
  m.tick(false, step == 1, 64, 7 + bank, 3, 2,
         step == 1, 64, 11 + bank, 3, 2,
         writing, writing ? strobes[step - 2] : 0, data, step == 4,
         step == 2 || step == 3 || step == 5, step == 5);
}
// Cut 0 is pristine; cut 1 has pending AW/read responses; cut 2 has a partial
// strobed write; cut 3 has a complete write and buffered B/last-R responses.
static unsigned cut_step(unsigned cut) { return cut == 3 ? 4 : cut; }
static void advance(group_t &group, unsigned first, unsigned last) {
  for (unsigned step = first; step <= last; ++step)
    for (unsigned b = 0; b < group.size(); ++b) tick(*group[b], b, step);
}
static void observe(std::ostream &f, group_t &group, unsigned step) {
  for (unsigned b = 0; b < group.size(); ++b) {
    auto &m = *group[b]; f << step << ' ' << b << ' ' << m.b_valid() << ' ' << m.b_id()
      << ' ' << m.r_valid() << ' ' << m.r_id() << ' ' << m.r_last();
    auto *bytes = static_cast<uint8_t *>(m.r_data());
    for (unsigned j = 0; j < 8; ++j) f << ' ' << unsigned(bytes[j]);
    f << '\n';
  }
}
static group_t *fatal_group;
static const image_t *fatal_expected;
static const char *fatal_mode;
static mm_magic_t *fatal_extra = nullptr;
static void terminated() noexcept {
  fail_after = -1;
  try {
    check(capture(*fatal_group) == *fatal_expected);
    if (fatal_extra) check(fatal_extra->save_checkpoint() == fatal_expected->front());
    std::fprintf(stderr, "MEMORY_FATAL mode=%s unchanged=1 target_edges=0\n", fatal_mode);
    std::fflush(stderr); std::_Exit(86);
  } catch (...) { std::_Exit(87); }
}
static void set_u64(std::vector<uint8_t> &bytes, size_t field, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i) bytes[field * 8 + i] = uint8_t(value >> (i * 8));
}
static int execute(const char *mode, const char *source, const char *destination,
                   unsigned cut, unsigned banks) {
 try {
  check(cut < 4 && (banks == 1 || banks == 4));
  auto group = make_group(banks); const auto initial = capture(group);
  auto unchanged = [&] { check(capture(group) == initial); };
  const std::string action(mode);
  if (action == "negative" || action.starts_with("fatal-")) {
    auto incoming = make_group(banks); initialize(incoming);
    advance(incoming, 1, cut_step(cut)); const auto image = capture(incoming);
    if (action.starts_with("fatal-")) {
      std::set_terminate(terminated); fatal_group = &group; fatal_expected = &initial; fatal_mode = mode;
      auto c = prepare(group, image);
      if (action == "fatal-unsealed") group[0]->publish_sealed_checkpoint(*c[0]);
      seal(group, c); unchanged();
      if (action == "fatal-thread") { std::thread t([&] { group[0]->publish_sealed_checkpoint(*c[0]); }); t.join(); }
      if (action == "fatal-destination") {
        auto other = make_group(banks); fatal_group = &other;
        other[0]->publish_sealed_checkpoint(*c[0]);
      }
      if (action == "fatal-recycled") {
        alignas(mm_magic_t) unsigned char storage[sizeof(mm_magic_t)];
        auto *retired = new (storage) mm_magic_t(geometry); retired->init(memory_size, 64);
        auto old = retired->prepare_checkpoint(image[0]); retired->seal_checkpoint(*old); retired->~mm_magic_t();
        auto *replacement = new (storage) mm_magic_t(geometry); replacement->init(memory_size, 64);
        fatal_extra = replacement; replacement->publish_sealed_checkpoint(*old);
        replacement->~mm_magic_t();
      }
      if (action == "fatal-consumed" || action == "fatal-stale" || action == "fatal-legacy") {
        auto other = prepare(group, image); seal(group, other);
        if (action == "fatal-legacy") {
          group[0]->load_checkpoint(initial[0]); unchanged();
          group[0]->publish_sealed_checkpoint(*c[0]);
        }
        publish(group, c); fatal_expected = &image;
        group[0]->publish_sealed_checkpoint(action == "fatal-consumed" ? *c[0] : *other[0]);
      }
      throw std::runtime_error("fatal contract returned");
    }
    // Reject malformed bytes in every member before any publication.
    for (unsigned b = 0; b < banks; ++b) {
      for (unsigned variant = 0; variant < 11; ++variant) {
        auto bad = image;
        switch (variant) {
          case 0: bad[b].clear(); break;
          case 1: bad[b].pop_back(); break;
          case 2: bad[b].push_back(0); break;
          case 3: bad[b][0] ^= 1; break;
          case 4: set_u64(bad[b], 1, 9); break;
          case 5: set_u64(bad[b], 2, 15); break;
          case 6: set_u64(bad[b], 5, 8192); break;
          case 7: set_u64(bad[b], 8, 2); break;
          case 8: set_u64(bad[b], 10, 1u << 17); break;
          case 9: set_u64(bad[b], 11, 3); break;
          case 10: set_u64(bad[b], 12, 257); break;
        }
        reject([&] { prepare(group, bad); }); unchanged();
      }
      // Check that every complete destination owner participates in sealing.
      auto c = prepare(group, image);
      static_cast<uint8_t *>(group[b]->get_data())[memory_size - 1] ^= 1;
      const auto changed = capture(group);
      reject([&] { seal(group, c); }); check(capture(group) == changed);
      static_cast<uint8_t *>(group[b]->get_data())[memory_size - 1] ^= 1; unchanged();
      auto altered = make_group(banks); auto altered_candidate = prepare(altered, image);
      tick(*altered[b], b, 1); const auto advanced = capture(altered);
      reject([&] { seal(altered, altered_candidate); }); check(capture(altered) == advanced);
    }
    mm_magic_t uninitialized(geometry);
    reject([&] { uninitialized.prepare_checkpoint(image[0]); }); unchanged();
    for (const AXI4Config incompatible : {AXI4Config{15, 34, 64}, AXI4Config{16, 33, 64}, AXI4Config{16, 34, 32}}) {
      mm_magic_t other(incompatible); other.init(memory_size, 64); const auto before = other.save_checkpoint();
      reject([&] { other.prepare_checkpoint(image[0]); }); check(other.save_checkpoint() == before); unchanged();
    }
    for (unsigned variant = 0; variant < 2; ++variant) {
      mm_magic_t other(geometry); other.init(variant ? memory_size : 8192, variant ? 32 : 64);
      const auto before = other.save_checkpoint();
      reject([&] { other.prepare_checkpoint(image[0]); }); check(other.save_checkpoint() == before); unchanged();
    }
    auto c = prepare(group, image);
    std::thread foreign([&] { reject([&] { seal(group, c); }); }); foreign.join(); unchanged();
    auto other = make_group(banks);
    reject([&] { other[0]->seal_checkpoint(*c[0]); }); check(capture(other) == initial); unchanged();
    // Incoming images are owned; later caller mutation cannot change publication.
    { auto transient = image; auto owned = prepare(group, transient); transient.clear();
      seal(group, owned); unchanged(); }
    unchanged();
    reject([&] { group[0]->init(memory_size, 64); }); unchanged();
    unsigned preparation_failures = 0, sealing_failures = 0;
    for (long limit = 0;; ++limit) {
      check(limit < 20000); allocation_failed = false; fail_after = limit;
      try { auto abandoned = prepare(group, image); fail_after = -1; check(!allocation_failed); unchanged(); break; }
      catch (const std::exception &) { fail_after = -1; check(allocation_failed); ++preparation_failures; unchanged(); }
    }
    for (long limit = 0;; ++limit) {
      check(limit < 20000); auto staged = prepare(group, image);
      allocation_failed = false; fail_after = limit;
      try { seal(group, staged); fail_after = -1; check(!allocation_failed); unchanged(); break; }
      catch (const std::exception &) { fail_after = -1; check(allocation_failed); ++sealing_failures; unchanged(); }
    }
    // A legacy load with identical bytes still invalidates earlier candidates.
    group[0]->load_checkpoint(initial[0]); reject([&] { seal(group, c); }); unchanged();
    c = prepare(group, image); auto stale = prepare(group, image);
    seal(group, c); reject([&] { seal(group, c); }); unchanged();
    publish(group, c); check(capture(group) == image);
    reject([&] { seal(group, stale); }); check(capture(group) == image);
    reject([&] { seal(group, c); }); check(capture(group) == image);
    save(destination, "published", capture(group));
    std::cout << "MEMORY_NEGATIVE rejected=" << rejections << " preparation_failures=" << preparation_failures
      << " sealing_failures=" << sealing_failures << " publication_allocations=0 partial_publication=0 cancellation_unchanged=1 target_edges=0\n";
    return 0;
  }
  const auto step = cut_step(cut);
  if (action == "reference") {
    initialize(group); advance(group, 1, step); save(destination, "cut", capture(group));
  } else {
    check(action == "restore"); auto image = load(source, banks); auto c = prepare(group, image);
    unchanged(); image.clear(); // No dependence on the caller's image lifetime.
    std::vector<void *> aliases; for (auto &m : group) aliases.push_back(m->get_data());
    seal(group, c); unchanged(); publish(group, c);
    for (unsigned b = 0; b < banks; ++b) check(group[b]->get_data() == aliases[b]);
    save(destination, "readback", capture(group));
  }
  std::ofstream trace(std::filesystem::path(destination) / "trace"); observe(trace, group, step);
  for (unsigned n = step + 1; n <= 6; ++n) { advance(group, n, n); observe(trace, group, n); }
  check(bool(trace)); save(destination, "final", capture(group));
  std::cout << "MEMORY_PASS banks=" << banks << " cut=" << cut << " stable_aliases=1 target_edges=0\n";
  return 0;
 } catch (const std::exception &e) {
  fail_after = -1; std::cerr << "MEMORY_FAIL " << e.what() << '\n'; return 2;
 }
}
#ifdef MEMORY_PUBLICATION_DPI
extern "C" int memory_publication_test(const char *m, const char *s, const char *d, unsigned c, unsigned b) {
  return execute(m, s, d, c, b);
}
#else
int main(int argc, char **argv) {
  return argc == 6 ? execute(argv[1], argv[2], argv[3], std::stoul(argv[4]), std::stoul(argv[5])) : 2;
}
#endif
