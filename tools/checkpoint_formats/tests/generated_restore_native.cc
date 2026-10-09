// Sanitizer checks of the actual VPI loader with controllable handle faults.
// Actual generated RTL behavior is checked separately in fresh VCS processes.
#include "../generated_restore.cc"
#include <cassert>
#include <iostream>
#include <map>

namespace {
struct MockHandle {
  int type;
  int width;
  std::vector<s_vpi_vecval> value;
};
std::map<std::string, MockHandle> handles;
size_t deposit_count = 0;
MockHandle &mock(vpiHandle handle) {
  return *reinterpret_cast<MockHandle *>(handle);
}
}

extern "C" vpiHandle vpi_handle_by_name(PLI_BYTE8 *name, vpiHandle) {
  const auto found = handles.find(name);
  return found == handles.end() ? nullptr : reinterpret_cast<vpiHandle>(&found->second);
}
extern "C" PLI_INT32 vpi_get(PLI_INT32 property, vpiHandle handle) {
  assert(property == vpiType || property == vpiSize);
  return property == vpiType ? mock(handle).type : mock(handle).width;
}
extern "C" void vpi_get_value(vpiHandle handle, p_vpi_value value) {
  assert(value->format == vpiVectorVal);
  value->value.vector = mock(handle).value.data();
}
extern "C" vpiHandle vpi_put_value(vpiHandle handle, p_vpi_value value,
                                   p_vpi_time time, PLI_INT32 flags) {
  assert(value->format == vpiVectorVal && !time && flags == vpiNoDelay);
  auto &destination = mock(handle).value;
  destination.assign(value->value.vector, value->value.vector + destination.size());
  ++deposit_count;
  return nullptr;
}
extern "C" PLI_INT32 vpi_printf(PLI_BYTE8 *, ...) { return 0; }

int main(int argc, char **argv) {
  assert(argc == 2);
  std::vector<std::string> paths;
  for (const auto &entry : entries) {
    for (unsigned i = 0; i < entry.depth; ++i) {
      std::string path = std::string(entry.path) + (entry.memory ? "[" + std::to_string(i) + "]" : "");
      handles.emplace(path, MockHandle{entry.memory ? vpiMemoryWord : vpiReg,
                                      static_cast<int>(entry.width),
                                      std::vector<s_vpi_vecval>((entry.width + 31ULL) / 32)});
      paths.push_back(path);
    }
  }
  handles.emplace(clock_path, MockHandle{vpiReg, 1, std::vector<s_vpi_vecval>(1)});
  std::ifstream file(argv[1]);
  const std::string good{std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
  assert(!good.empty());
  const std::string bad_path = std::string(argv[1]) + ".invalid";
  size_t rejections = 0;
  auto reject = [&](const char *path) {
    assert(generated_restore(path) == 1 && deposit_count == 0 && pending.empty());
    ++rejections;
  };
  // Every byte-truncated prefix, except the optional final newline, must fail.
  for (size_t i = 0; i + 1 < good.size(); ++i) {
    { std::ofstream bad(bad_path); bad << good.substr(0, i); }
    reject(bad_path.c_str());
  }
  reject("/nonexistent/generated-restore-staging");
  auto &clock = handles.at(clock_path);
  clock.value[0].aval = 1; reject(argv[1]); clock.value[0].aval = 0;
  clock.value[0].bval = 1; reject(argv[1]); clock.value[0].bval = 0;
  for (const auto &path : paths) {
    const auto original = handles.at(path);
    handles.erase(path); reject(argv[1]); handles.emplace(path, original);
    handles.at(path).width++; reject(argv[1]); handles.at(path).width--;
    handles.at(path).type = vpiNet; reject(argv[1]); handles.at(path).type = original.type;
  }
  assert(generated_restore_verify() == 1); ++rejections;
  assert(generated_restore(argv[1]) == 0 && deposit_count == paths.size());
  // Reentrant/unverified loads cannot modify state a second time.
  assert(generated_restore(argv[1]) == 1 && deposit_count == paths.size()); ++rejections;
  assert(generated_restore_verify() == 0 && pending.empty());
  for (const auto &entry : entries) {
    for (unsigned address = 0; address < entry.depth; ++address) {
      const auto &value = handles.at(std::string(entry.path) +
          (entry.memory ? "[" + std::to_string(address) + "]" : "")).value;
      // The independent fixture uses all-ones values, including a 257-bit
      // scalar and both 9-bit memory words. Check each 32-bit limb directly.
      for (size_t i = 0; i < value.size(); ++i) {
        const unsigned bits = std::min(32u, entry.width - 32u * static_cast<unsigned>(i));
        assert(value[i].aval == (bits == 32 ? UINT32_MAX : (uint32_t{1} << bits) - 1));
        assert(value[i].bval == 0);
      }
    }
  }
  // Exercise VCS's scalarized memory-word representation as well.
  for (const auto &path : paths) handles.at(path).type = vpiReg;
  assert(generated_restore(argv[1]) == 0 && generated_restore_verify() == 0);
  assert(generated_restore(argv[1]) == 0);
  handles.at(paths.back()).value[0].bval = 1;
  assert(generated_restore_verify() == 1 && !pending.empty()); ++rejections;
  assert(generated_restore(argv[1]) == 1 && deposit_count == paths.size() * 3); ++rejections;
  std::cout << "GENERATED_RESTORE_NATIVE: words=" << paths.size()
            << " rejections=" << rejections << " wide_bits=257\n";
}
