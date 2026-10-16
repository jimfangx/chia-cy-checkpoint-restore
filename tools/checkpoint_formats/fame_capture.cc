// Read-only diagnostic capture. No deposits, clocks, reset or driver calls.
// The compiler-bound plan is fully shape-checked before any snapshot is opened.
#include <vpi_user.h>
#include <algorithm>
#include <cctype>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

namespace {
struct Word { vpiHandle handle; unsigned width; std::string path, saved; };
std::vector<Word> words;
int error(const char *what, const std::string &path) {
  vpi_printf("FAME_CAPTURE_ERROR: %s %s\n", what, path.c_str());
  return 1;
}
std::string read(const Word &word) {
  s_vpi_value value{}; value.format = vpiHexStrVal;
  vpi_get_value(word.handle, &value);
  std::string result = value.value.str ? value.value.str : "";
  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  if (result.empty() || result.find_first_not_of("0123456789abcdef") != std::string::npos)
    return "";
  const auto digits = (word.width + 3) / 4;
  if (result.size() > digits) return "";
  result.insert(0, digits - result.size(), '0');
  return result;
}
}
extern "C" int fame_capture_init(const char *filename, const char *scope, unsigned expected) {
  if (!words.empty()) return error("duplicate initialization", scope);
  std::string parent(scope); const auto last = parent.rfind('.');
  if (last == std::string::npos) return error("invalid bound monitor scope", scope);
  parent.resize(last); parent += '.';
  std::ifstream input(filename);
  if (!input) return error("cannot open plan", filename);
  std::vector<Word> candidate;
  std::unordered_set<std::string> seen;
  std::string line, path, extra; unsigned width;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    if (!(row >> path >> width) || (row >> extra) || !width || !seen.insert(path).second)
      return error("malformed/duplicate plan row", line);
    path = parent + path;
    auto handle = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
    if (!handle || vpi_get(vpiSize, handle) != static_cast<int>(width) ||
        (vpi_get(vpiType, handle) != vpiReg && vpi_get(vpiType, handle) != vpiMemoryWord))
      return error("missing/reshaped/non-storage handle", path);
    candidate.push_back({handle, width, path, ""});
  }
  if (!input.eof() || candidate.empty() || candidate.size() != expected)
    return error("incomplete plan", filename);
  words.swap(candidate);
  vpi_printf("FAME_CAPTURE_PLAN words=%zu\n", words.size());
  return 0;
}
extern "C" int fame_capture_save(const char *filename) {
  if (words.empty()) return error("uninitialized capture", filename);
  for (auto &word : words) {
    word.saved = read(word);
    if (word.saved.empty()) return error("unknown semantic bits", word.path);
  }
  std::ofstream output(filename, std::ios::out | std::ios::trunc);
  if (!output) return error("cannot open snapshot", filename);
  for (const auto &word : words)
    output << word.path << ' ' << word.width << ' ' << word.saved << '\n';
  output.close();
  if (!output) return error("incomplete snapshot write", filename);
  vpi_printf("FAME_CAPTURE_STATE words=%zu path=%s\n", words.size(), filename);
  return 0;
}
extern "C" int fame_capture_verify() {
  if (words.empty()) return error("uninitialized readback", "");
  for (const auto &word : words)
    if (word.saved.empty() || read(word) != word.saved)
      return error("semantic state changed before original edge", word.path);
  vpi_printf("FAME_CAPTURE_PRE_EDGE_READBACK words=%zu\n", words.size());
  return 0;
}
