// Ordinary RTL VCS DPI/VPI loader. Input is produced only after Python's
// checksum, build, StateID completeness and boundary validation. Resolve and
// shape-check every handle before making any deposit. No clocks/reset run here.
#include <vpi_user.h>

#include <fstream>
#include <string>
#include <vector>
#include <unordered_set>
#include <sstream>
#include <cstdio>
#include <cstdlib>

namespace {
struct Deposit {
  vpiHandle handle;
  std::string value;
};
void fail(const char *message, const std::string &path) {
  vpi_printf("RESTORE_ERROR: %s %s\n", message, path.c_str());
}
}

// VCS can print $fatal while returning status zero. Replay failures must also
// be visible to shell/CI callers, independent of simulator finish policies.
extern "C" void semantic_fail(const char *message) {
  vpi_printf("%s\n", message);
  std::fflush(nullptr);
  std::exit(EXIT_FAILURE);
}

extern "C" int semantic_restore(const char *filename, unsigned expected_words) {
  std::ifstream input(filename);
  if (!input) { fail("cannot open validated restore file", filename); return 1; }
  std::vector<Deposit> deposits;
  std::unordered_set<std::string> seen;
  std::string path, value, line, extra;
  unsigned width;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    if (!(row >> path >> width >> value) || (row >> extra)) {
      fail("malformed restore row", line); return 1;
    }
    auto handle = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
    if (!handle || vpi_get(vpiSize, handle) != static_cast<int>(width) || !seen.insert(path).second) {
      fail("missing/reshaped/duplicate state handle", path); return 1;
    }
    const auto type = vpi_get(vpiType, handle);
    if (type != vpiReg && type != vpiMemoryWord) { fail("unsupported state handle", path); return 1; }
    if (value.size() != (width + 3) / 4 || value.find_first_not_of("0123456789abcdef") != std::string::npos) {
      fail("invalid bit vector", path); return 1;
    }
    const unsigned first = value.front() <= '9' ? value.front() - '0' : value.front() - 'a' + 10;
    if (width % 4 && first >= (1u << (width % 4))) { fail("nonzero padding bits", path); return 1; }
    deposits.push_back({handle, value});
  }
  if (!input.eof() || deposits.empty() || deposits.size() != expected_words) {
    fail("incomplete/malformed restore file", filename); return 1;
  }
  for (auto &deposit : deposits) {
    s_vpi_value value{};
    value.format = vpiHexStrVal;
    value.value.str = const_cast<char *>(deposit.value.c_str());
    vpi_put_value(deposit.handle, &value, nullptr, vpiNoDelay);
  }
  vpi_printf("RESTORE: deposited %zu semantic words before first DUT edge\n", deposits.size());
  return 0;
}
