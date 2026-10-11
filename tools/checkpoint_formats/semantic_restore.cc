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
// Synthesis can emit escaped module instance names such as count_reg[0].
// VPI requires the backslash and terminating space for those *intermediate*
// hierarchy components. Restore rows use whitespace-free logical names; the
// final component remains a normal register or memory-word expression.
vpiHandle resolve_storage(const std::string &path) {
  auto handle = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
  if (handle) return handle;
  std::string escaped;
  std::size_t begin = 0, end;
  while ((end = path.find('.', begin)) != std::string::npos) {
    auto component = path.substr(begin, end - begin);
    if (component.find('[') != std::string::npos) {
      escaped += "\\" + component + " ";
    } else {
      escaped += component;
    }
    escaped += ".";
    begin = end + 1;
  }
  escaped += path.substr(begin);
  return vpi_handle_by_name(const_cast<char *>(escaped.c_str()), nullptr);
}
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
    auto handle = resolve_storage(path);
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

// Stream complete post-settle readback without generating one SV assertion per
// memory word. The validated Level-2 restore file remains the independent oracle.
extern "C" int semantic_verify(const char *filename, unsigned expected_words) {
  std::ifstream input(filename);
  if (!input) { fail("cannot open readback oracle", filename); return 1; }
  std::unordered_set<std::string> seen;
  std::string path, expected, line, extra;
  unsigned width, words = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    if (!(row >> path >> width >> expected) || (row >> extra) || !width ||
        expected.size() != (width + 3) / 4 ||
        expected.find_first_not_of("0123456789abcdef") != std::string::npos) {
      fail("malformed readback oracle", line); return 1;
    }
    auto handle = resolve_storage(path);
    if (!handle || vpi_get(vpiSize, handle) != static_cast<int>(width) || !seen.insert(path).second ||
        (vpi_get(vpiType, handle) != vpiReg && vpi_get(vpiType, handle) != vpiMemoryWord)) {
      fail("missing/reshaped/duplicate readback handle", path); return 1;
    }
    unsigned first = expected.front() <= '9' ? expected.front() - '0' : expected.front() - 'a' + 10;
    if (width % 4 && first >= (1u << (width % 4))) {
      fail("nonzero readback padding", path); return 1;
    }
    s_vpi_value actual{};
    actual.format = vpiVectorVal;
    vpi_get_value(handle, &actual);
    for (unsigned bit = 0; bit < width; ++bit) {
      char digit = expected[expected.size() - 1 - bit / 4];
      unsigned nibble = digit <= '9' ? digit - '0' : digit - 'a' + 10;
      unsigned mask = 1u << (bit % 32);
      if ((actual.value.vector[bit / 32].bval & mask) ||
          bool(actual.value.vector[bit / 32].aval & mask) != bool(nibble & (1u << (bit % 4)))) {
        fail("semantic readback mismatch", path); return 1;
      }
    }
    ++words;
  }
  if (!input.eof() || !words || words != expected_words) {
    fail("incomplete readback oracle", filename); return 1;
  }
  vpi_printf("RESTORE_VERIFY: matched %u semantic words before first DUT edge\n", words);
  return 0;
}
