#include "durable_capture.h"
#include <sv_vpi_user.h>
#include <set>
#include <sstream>

namespace {
struct Entry {
  const char *path;
  unsigned width, depth;
  bool memory, clock_output;
};
namespace generated {
#include "generated-restore-table.h"
}
namespace harness {
#include "harness-restore-table.h"
}
struct NativeIdentity { const char *owner, *schema; };
#include "aggregate-restore-table.h"
#ifndef AGGREGATE_TARGET_CYCLE_PATH
#error "Live capture requires a manifested target-cycle counter"
#endif

void require(bool ok, const std::string &message) {
  if (!ok) throw std::runtime_error("durable capture: " + message);
}
std::string word(const std::string &path, unsigned width, bool memory,
                 bool harness_bank, bool control) {
  auto handle = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
  const auto type = handle ? vpi_get(vpiType, handle) : -1;
  require(handle && vpi_get(vpiSize, handle) == static_cast<int>(width) &&
          (harness_bank ? type == (control ? vpiBitVar : vpiStructVar)
                        : (type == vpiReg || (memory && type == vpiMemoryWord))),
          "missing/reshaped/wrong-kind handle: " + path);
  s_vpi_value value{};
  value.format = vpiVectorVal;
  vpi_get_value(handle, &value);
  require(value.value.vector, "missing vector: " + path);
  for (size_t i = 0; i < (width + 31ULL) / 32; ++i)
    require(value.value.vector[i].bval == 0, "unknown state: " + path);
  // Do not mask invalid padding supplied by an unsupported VPI adapter.
  if (width % 32)
    require((uint32_t(value.value.vector[width / 32].aval) >> (width % 32)) == 0,
            "nonzero vector padding: " + path);
  std::string result((width + 3ULL) / 4, '0');
  for (size_t i = 0; i < result.size(); ++i)
    result[result.size() - 1 - i] = "0123456789abcdef"[
        (uint32_t(value.value.vector[i / 8].aval) >> (4 * (i % 8))) & 15];
  return result;
}
void low_clocks() {
  for (const auto &paths : {std::vector<const char *>(std::begin(generated::clock_paths), std::end(generated::clock_paths)),
                           std::vector<const char *>(std::begin(harness::clock_paths), std::end(harness::clock_paths))})
    for (const auto *path : paths) {
      auto handle = vpi_handle_by_name(const_cast<char *>(path), nullptr);
      require(handle && vpi_get(vpiSize, handle) == 1, "missing/reshaped clock: " + std::string(path));
      s_vpi_value value{}; value.format = vpiVectorVal;
      vpi_get_value(handle, &value);
      require(value.value.vector && value.value.vector[0].aval == 0 && value.value.vector[0].bval == 0,
              "clock must be known low: " + std::string(path));
    }
  for (const auto *path : harness::unsupported_paths)
    require(!vpi_handle_by_name(const_cast<char *>(path), nullptr), "unsupported harness state: " + std::string(path));
}
struct rtl_t { std::string generated, harness; uint64_t target_cycle = 0; };
rtl_t rtl() {
  rtl_t result;
  uint64_t words = 0;
  for (const auto &e : generated::entries) words += e.depth;
  result.generated = std::string("FSGRTL2 ") + generated::manifest_hash + " " + generated::build_hash +
      " settled_host_negedge " + std::to_string(words) + "\n";
  bool have_cycle = false;
  for (const auto &e : generated::entries) {
    result.generated += std::string(e.path) + " " + std::to_string(e.width) + " " + std::to_string(e.depth) + " ";
    for (unsigned address = 0; address < e.depth; ++address) {
      const auto path = std::string(e.path) + (e.memory ? "[" + std::to_string(address) + "]" : "");
      const auto bits = word(path, e.width, e.memory, false, false);
      require(!e.clock_output || bits.find_first_not_of('0') == std::string::npos,
              "high generated clock: " + path);
      if (path == AGGREGATE_TARGET_CYCLE_PATH) {
        require(!have_cycle && e.width == 64 && e.depth == 1 && !e.memory, "invalid target-cycle counter");
        result.target_cycle = std::stoull(bits, nullptr, 16); have_cycle = true;
      }
      result.generated += bits;
    }
    result.generated += '\n';
  }
  require(have_cycle, "missing target-cycle counter");
  result.harness = std::string("FSHRNS1 ") + harness::manifest_hash + " " + harness::build_hash +
      " settled_host_negedge " + std::to_string(std::size(harness::entries)) + "\n";
  for (const auto &e : harness::entries) {
    require(e.depth == 1 && !e.memory, "unsupported harness shape");
    const auto bits = word(e.path, e.width, false, true, e.clock_output);
    require(!e.clock_output || bits == "0", "high reset/finish cut: " + std::string(e.path));
    result.harness += std::string(e.path) + " " + std::to_string(e.width) + " " + bits + "\n";
  }
  return result;
}
}

std::string capture_durable_snapshot(const aggregate_restore_t::owners_t &owners,
                                    uint64_t host_sample) {
  low_clocks();
  require(owners.size() == std::size(native_identities), "changed native inventory");
  std::set<checkpoint_owner_t *> pointers;
  // Resolve every owner before calling any adapter.
  for (size_t i = 0; i < owners.size(); ++i)
    require(owners[i].first == native_identities[i].owner && owners[i].second &&
            owners[i].second->checkpoint_schema() == native_identities[i].schema &&
            pointers.insert(owners[i].second).second, "unsupported/changed native owner or schema");
  std::vector<std::vector<uint8_t>> payloads;
  for (const auto &[name, owner] : owners) {
    auto payload = owner->save_checkpoint();
    require(!payload.empty(), "empty native payload: " + name);
    owner->validate_checkpoint(payload);
    payloads.push_back(std::move(payload));
  }
  const auto state = rtl();
  for (size_t i = 0; i < owners.size(); ++i)
    require(owners[i].second->checkpoint_schema() == native_identities[i].schema &&
            owners[i].second->save_checkpoint() == payloads[i], "native owner changed during capture");
  // Detect adapter side effects across owners and across the RTL boundary.
  const auto readback = rtl();
  require(state.generated == readback.generated && state.harness == readback.harness,
          "RTL/harness changed during parked capture");
  low_clocks();
  std::string result = std::string("FSAGG1 ") + aggregate_manifest_hash + " " +
      std::to_string(state.target_cycle) + " " + std::to_string(host_sample) + " " + std::to_string(owners.size()) + "\n";
  for (size_t i = 0; i < owners.size(); ++i) {
    result += std::string("HOST ") + native_identities[i].owner + " " + native_identities[i].schema + " " +
        std::to_string(payloads[i].size()) + " ";
    for (auto byte : payloads[i]) {
      result += "0123456789abcdef"[byte >> 4]; result += "0123456789abcdef"[byte & 15];
    }
    result += '\n';
  }
  result += "GENERATED " + std::to_string(state.generated.size()) + "\n" + state.generated;
  result += "HARNESS " + std::to_string(state.harness.size()) + "\n" + state.harness;
  return result;
}
