// VCS VPI loader for generated RTL only. Not a whole-runtime .fsckpt loader.
// All validation and handle resolution precedes ANY deposit. A coordinator
// must hold host clocks low, then call generated_restore_verify after delta
// settlement and before allowing the next clock edge. Readback failure is
// terminal: the partially loaded process must never resume.
#include <vpi_user.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

// Harness banks use the same all-handles-before-deposit implementation with
// their own table, format and DPI symbols. Runtime coordination is separate.
#ifndef RESTORE_TABLE
#define RESTORE_TABLE "generated-restore-table.h"
#define RESTORE_MAGIC "FSGRTL1"
#define RESTORE_PHASE "settled_host_negedge"
#define RESTORE_LOG "GENERATED_RESTORE"
#define RESTORE_ENTRY_MAGIC "FSGRTL2"
#endif
#ifndef RESTORE_ACCEPTED_TYPE
#define RESTORE_ACCEPTED_TYPE(entry, type) \
  ((type) == vpiReg || ((entry).memory && (type) == vpiMemoryWord))
#endif

namespace {
struct Entry {
  const char *path;
  unsigned width;
  unsigned depth;
  bool memory;
  bool clock_output;
};
#include RESTORE_TABLE

struct Deposit {
  vpiHandle handle;
  std::string path;
  std::vector<s_vpi_vecval> value;
};
std::vector<Deposit> pending;
std::vector<Deposit> prepared;
uint64_t deposited_words = 0;

int fail(const char *reason, const std::string &path) {
  vpi_printf(RESTORE_LOG "_ERROR: %s %s\n", reason, path.c_str());
  return 1;
}

bool low_clock() {
  for (const auto *path : clock_paths) {
    auto handle = vpi_handle_by_name(const_cast<char *>(path), nullptr);
    if (!handle || vpi_get(vpiSize, handle) != 1) return false;
    s_vpi_value value{};
    value.format = vpiVectorVal;
    vpi_get_value(handle, &value);
    if (!value.value.vector || value.value.vector[0].aval != 0 ||
        value.value.vector[0].bval != 0) return false;
  }
  return true;
}

bool equal(const Deposit &deposit) {
  s_vpi_value value{};
  value.format = vpiVectorVal;
  vpi_get_value(deposit.handle, &value);
  if (!value.value.vector) return false;
  for (size_t i = 0; i < deposit.value.size(); ++i)
    if (value.value.vector[i].aval != deposit.value[i].aval ||
        value.value.vector[i].bval != 0) return false;
  return true;
}
}

extern "C" void generated_restore_fail(const char *message) {
  vpi_printf(RESTORE_LOG "_ERROR: %s\n", message);
  std::fflush(nullptr);
  std::exit(EXIT_FAILURE);
}

namespace {
int prepare(std::istream &input, const char *filename) {
  if (!pending.empty() || !prepared.empty()) return fail("unconsumed previous load", filename);
  if (!low_clock()) return fail("host clock must be known low", clock_path);
  std::string line, magic, manifest, build, phase, extra;
  uint64_t count = 0, expected = 0;
  for (const auto &entry : entries) expected += entry.depth;
  if (!std::getline(input, line)) return fail("missing header", filename);
  std::istringstream header(line);
  if (!(header >> magic >> manifest >> build >> phase >> count) || (header >> extra) ||
      (magic != RESTORE_MAGIC
#ifdef RESTORE_ENTRY_MAGIC
       && magic != RESTORE_ENTRY_MAGIC
#endif
       ) || manifest != manifest_hash || build != build_hash ||
      phase != RESTORE_PHASE || count != expected)
    return fail("incompatible header", filename);

  const bool entry_encoded =
#ifdef RESTORE_ENTRY_MAGIC
      magic == RESTORE_ENTRY_MAGIC;
#else
      false; // Packed harness banks retain their independent format.
#endif

  std::vector<Deposit> deposits;
  deposits.reserve(expected);
  for (const auto &entry : entries) {
    std::string packed;
    const size_t digits = (entry.width + 3ULL) / 4;
    if (entry_encoded) {
      if (!std::getline(input, line)) return fail("incomplete entry", entry.path);
      std::istringstream row(line);
      std::string path;
      uint64_t width = 0, depth = 0;
      if (!(row >> path >> width >> depth >> packed) || (row >> extra) ||
          path != entry.path || width != entry.width || depth != entry.depth ||
          packed.size() != digits * entry.depth)
        return fail("wrong entry membership/order/shape", entry.path);
    }
    for (unsigned address = 0; address < entry.depth; ++address) {
      const std::string expected_path = std::string(entry.path) +
          (entry.memory ? "[" + std::to_string(address) + "]" : "");
      std::string word;
      if (!entry_encoded) {
        if (!std::getline(input, line)) return fail("incomplete state", expected_path);
        std::istringstream row(line);
        std::string path;
        unsigned width = 0;
        if (!(row >> path >> width >> word) || (row >> extra) ||
            path != expected_path || width != entry.width)
          return fail("wrong state membership/order/shape", expected_path);
      }
      const std::string &path = expected_path;
      const unsigned width = entry.width;
      const std::string_view bits = entry_encoded
          ? std::string_view(packed).substr(size_t(address) * digits, digits)
          : std::string_view(word);
      if (bits.size() != (width + 3ULL) / 4 ||
          bits.find_first_not_of("0123456789abcdef") != std::string::npos)
        return fail("invalid bit vector", path);
      auto nibble = [](char c) -> uint32_t { return c <= '9' ? c - '0' : c - 'a' + 10; };
      if (width % 4 && nibble(bits.front()) >= (1u << (width % 4)))
        return fail("nonzero padding", path);
      if (entry.clock_output && bits.find_first_not_of('0') != std::string::npos)
        return fail("high generated clock would advance target", path);
      auto handle = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
      // VCS exposes some statically indexed FIRRTL memory words as vpiReg
      // (including depth-one banks). Their full indexed paths and widths are
      // still exact; emitted declaration coverage separately binds the bank
      // kind/depth to the compiled table. Nets remain unsupported.
      const int type = handle ? vpi_get(vpiType, handle) : -1;
      if (!handle || vpi_get(vpiSize, handle) != static_cast<int>(width) ||
          !RESTORE_ACCEPTED_TYPE(entry, type)) {
        vpi_printf(RESTORE_LOG "_HANDLE: type=%d size=%d expected_width=%u memory=%d\n",
                   handle ? vpi_get(vpiType, handle) : -1,
                   handle ? vpi_get(vpiSize, handle) : -1, width, entry.memory);
        return fail("missing/reshaped/wrong-kind handle", path);
      }
      Deposit deposit{handle, path, std::vector<s_vpi_vecval>((width + 31ULL) / 32)};
      for (size_t i = 0; i < bits.size(); ++i)
        deposit.value[i / 8].aval |= nibble(bits[bits.size() - 1 - i]) << (4 * (i % 8));
      deposits.push_back(std::move(deposit));
    }
  }
  if (std::getline(input, line) || !input.eof()) return fail("trailing/malformed state", filename);
  // No heap allocations or input/handle validation remains after this point.
  prepared.swap(deposits);
  vpi_printf(RESTORE_LOG ": prepared %zu words without deposits\n", prepared.size());
  return 0;
}
}

extern "C" int generated_restore_prepare_text(const char *text) {
  if (!text) return fail("missing staging text", clock_path);
  std::istringstream input(text);
  return prepare(input, "aggregate staging");
}

extern "C" int generated_restore_commit() {
  if (prepared.empty() || !pending.empty()) return fail("no prepared load", clock_path);
  if (!low_clock()) return fail("clock advanced after preparation", clock_path);
  pending.swap(prepared);
  for (auto &deposit : pending) {
    s_vpi_value value{};
    value.format = vpiVectorVal;
    value.value.vector = deposit.value.data();
    vpi_put_value(deposit.handle, &value, nullptr, vpiNoDelay);
    ++deposited_words;
  }
  vpi_printf(RESTORE_LOG ": deposited %zu words with host clock low\n", pending.size());
  return 0;
}

extern "C" uint64_t generated_restore_deposit_count() { return deposited_words; }

extern "C" int generated_restore(const char *filename) {
  std::ifstream input(filename);
  if (!input) return fail("cannot open staging file", filename);
  if (prepare(input, filename)) return 1;
  return generated_restore_commit();
}

extern "C" int generated_restore_verify() {
  if (pending.empty()) return fail("no pending load", clock_path);
  if (!low_clock()) return fail("host clock advanced during load", clock_path);
  for (const auto &deposit : pending)
    if (!equal(deposit)) return fail("post-settlement readback mismatch", deposit.path);
  vpi_printf(RESTORE_LOG ": verified %zu words before next edge\n", pending.size());
  pending.clear();
  return 0;
}
