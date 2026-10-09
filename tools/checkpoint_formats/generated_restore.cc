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
#include <vector>

namespace {
struct Entry {
  const char *path;
  unsigned width;
  unsigned depth;
  bool memory;
  bool clock_output;
};
#include "generated-restore-table.h"

struct Deposit {
  vpiHandle handle;
  std::string path;
  std::vector<s_vpi_vecval> value;
};
std::vector<Deposit> pending;

int fail(const char *reason, const std::string &path) {
  vpi_printf("GENERATED_RESTORE_ERROR: %s %s\n", reason, path.c_str());
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
  vpi_printf("GENERATED_RESTORE_ERROR: %s\n", message);
  std::fflush(nullptr);
  std::exit(EXIT_FAILURE);
}

extern "C" int generated_restore(const char *filename) {
  if (!pending.empty()) return fail("unverified previous load", filename);
  if (!low_clock()) return fail("host clock must be known low", clock_path);
  std::ifstream input(filename);
  if (!input) return fail("cannot open staging file", filename);
  std::string line, magic, manifest, build, phase, extra;
  uint64_t count = 0, expected = 0;
  for (const auto &entry : entries) expected += entry.depth;
  if (!std::getline(input, line)) return fail("missing header", filename);
  std::istringstream header(line);
  if (!(header >> magic >> manifest >> build >> phase >> count) || (header >> extra) ||
      magic != "FSGRTL1" || manifest != manifest_hash || build != build_hash ||
      phase != "settled_host_negedge" || count != expected)
    return fail("incompatible header", filename);

  std::vector<Deposit> deposits;
  for (const auto &entry : entries) {
    for (unsigned address = 0; address < entry.depth; ++address) {
      const std::string expected_path = std::string(entry.path) +
          (entry.memory ? "[" + std::to_string(address) + "]" : "");
      if (!std::getline(input, line)) return fail("incomplete state", expected_path);
      std::istringstream row(line);
      std::string path, bits;
      unsigned width = 0;
      if (!(row >> path >> width >> bits) || (row >> extra) ||
          path != expected_path || width != entry.width)
        return fail("wrong state membership/order/shape", expected_path);
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
          (type != vpiReg && !(entry.memory && type == vpiMemoryWord))) {
        vpi_printf("GENERATED_RESTORE_HANDLE: type=%d size=%d expected_width=%u memory=%d\n",
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
  pending.swap(deposits);
  for (auto &deposit : pending) {
    s_vpi_value value{};
    value.format = vpiVectorVal;
    value.value.vector = deposit.value.data();
    vpi_put_value(deposit.handle, &value, nullptr, vpiNoDelay);
  }
  vpi_printf("GENERATED_RESTORE: deposited %zu words with host clock low\n", pending.size());
  return 0;
}

extern "C" int generated_restore_verify() {
  if (pending.empty()) return fail("no pending load", clock_path);
  if (!low_clock()) return fail("host clock advanced during load", clock_path);
  for (const auto &deposit : pending)
    if (!equal(deposit)) return fail("post-settlement readback mismatch", deposit.path);
  vpi_printf("GENERATED_RESTORE: verified %zu words before next edge\n", pending.size());
  pending.clear();
  return 0;
}
