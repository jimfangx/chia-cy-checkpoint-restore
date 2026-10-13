// Complete production gate span loader. Validate every value and every actual
// word handle before depositing anything. Retain compact hex bytes, not one
// string/handle/hash-table entry per memory address. The only storage models
// supported here are the independently audited CKDFF state and CKMEM contents.
#include <vpi_user.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

namespace {
struct Span {
  vpiHandle handle;
  std::string path, values;
  unsigned width, depth;
  bool memory;
};
vpiHandle resolve(const std::string &path) {
  auto h = vpi_handle_by_name(const_cast<char *>(path.c_str()), nullptr);
  if (h) return h;
  std::string escaped;
  std::size_t begin = 0, end;
  while ((end = path.find('.', begin)) != std::string::npos) {
    const auto component = path.substr(begin, end - begin);
    escaped += component.find('[') != std::string::npos ? "\\" + component + " " : component;
    escaped += ".";
    begin = end + 1;
  }
  escaped += path.substr(begin);
  return vpi_handle_by_name(const_cast<char *>(escaped.c_str()), nullptr);
}
bool error(const std::string &message, const std::string &path) {
  vpi_printf("PRODUCTION_GATE_RESTORE_ERROR: %s %s\n", message.c_str(), path.c_str());
  return false;
}
bool hex(const std::string &value, unsigned width) {
  if (!width || value.size() != (width + 3ull)/4 ||
      value.find_first_not_of("0123456789abcdef") != std::string::npos) return false;
  unsigned first = value[0] <= '9' ? value[0]-'0' : value[0]-'a'+10;
  return !(width % 4) || first < (1u << (width % 4));
}
vpiHandle word(const Span &span, unsigned address) {
  return span.memory ? vpi_handle_by_index(span.handle, static_cast<int>(address)) : span.handle;
}
bool storage_word(vpiHandle handle, bool memory) {
  if (!handle) return false;
  const int type = vpi_get(vpiType,handle);
  // VCS exposes SystemVerilog unpacked reg arrays as vpiRegArray, whose
  // indexed children are vpiReg. Legacy Verilog arrays use vpiMemoryWord.
  return type == vpiReg || (memory && type == vpiMemoryWord);
}
bool load(const char *filename, unsigned expected_words, unsigned long long expected_bits,
          std::vector<Span> &spans) {
  std::ifstream input(filename);
  std::string line;
  if (!input || !std::getline(input,line) || line != "PRODUCTION_GATE_RESTORE_V1")
    return error("missing file or unsupported span header", filename);
  std::unordered_set<std::string> seen;
  std::unordered_set<vpiHandle> seen_handles;
  unsigned long long words = 0, bits = 0;
  bool ended = false;
  while (std::getline(input,line)) {
    std::istringstream row(line);
    std::string kind, extra;
    if (!(row >> kind)) return error("empty span",filename);
    if (kind == "END") {
      unsigned long long declared_words, declared_bits;
      if (!(row >> declared_words >> declared_bits) || (row >> extra) ||
          declared_words != words || declared_bits != bits ||
          words != expected_words || bits != expected_bits || !words)
        return error("incomplete span totals",filename);
      ended = true;
      break;
    }
    Span span{};
    if ((kind != "R" && kind != "M") || !(row >> span.path >> span.width >> span.depth) ||
        (row >> extra) || !span.width || !span.depth || span.width > 0x7fffffffu || span.depth > 0x7fffffffu ||
        (kind == "R" && (span.width != 1 || span.depth != 1)) || !seen.insert(span.path).second)
      return error("malformed/duplicate/unsupported span",line);
    span.memory = kind == "M";
    const std::string suffix = span.memory ? ".contents" : ".state";
    if (span.path.rfind("production_gate_tb.dut.",0) != 0 ||
        span.path.size() < suffix.size() || span.path.compare(span.path.size()-suffix.size(),suffix.size(),suffix))
      return error("unsupported span storage path",span.path);
    span.handle = resolve(span.path);
    const int type = span.handle ? vpi_get(vpiType,span.handle) : -1;
    if (!span.handle || !seen_handles.insert(span.handle).second ||
        (span.memory ? (type != vpiMemory && type != vpiRegArray) : type != vpiReg) ||
        (span.memory && vpi_get(vpiSize,span.handle) != static_cast<int>(span.depth)))
      return error("missing/reshaped span handle type="+std::to_string(span.handle ? vpi_get(vpiType,span.handle) : -1)+
                   " size="+std::to_string(span.handle ? vpi_get(vpiSize,span.handle) : -1)+
                   " expected_depth="+std::to_string(span.depth),span.path);
    words += span.depth;
    bits += static_cast<unsigned long long>(span.width)*span.depth;
    if (words > expected_words || bits > expected_bits) return error("extra storage",span.path);
    const unsigned digits = (span.width+3ull)/4;
    span.values.reserve(static_cast<std::size_t>(digits+1)*span.depth);
    for (unsigned address=0; address<span.depth; ++address) {
      if (!std::getline(input,line) || !hex(line,span.width)) return error("invalid span bit vector",span.path);
      auto h = word(span,address);
      if (!storage_word(h,span.memory) ||
          vpi_get(vpiSize,h) != static_cast<int>(span.width))
        return error("missing/reshaped span word",span.path+"["+std::to_string(address)+"]");
      span.values += line;
      span.values += '\0';
    }
    spans.push_back(std::move(span));
  }
  if (!ended || std::getline(input,line) || !input.eof()) return error("missing END or extra data",filename);
  return true;
}
}

extern "C" void semantic_fail(const char *message) {
  vpi_printf("%s\n",message);
  std::fflush(nullptr);
  std::exit(EXIT_FAILURE);
}
extern "C" int production_gate_restore(const char *filename, unsigned words, unsigned long long bits) {
  std::vector<Span> spans;
  if (!load(filename,words,bits,spans)) return 1;
  for (auto &span : spans) {
    const auto stride = (span.width+3ull)/4+1;
    for (unsigned address=0; address<span.depth; ++address) {
      s_vpi_value value{};
      value.format = vpiHexStrVal;
      value.value.str = &span.values[stride*address];
      vpi_put_value(word(span,address),&value,nullptr,vpiNoDelay);
    }
  }
  vpi_printf("PRODUCTION_GATE_RESTORE: words=%u bits=%llu spans=%zu before_first_edge=1\n",words,bits,spans.size());
  return 0;
}
extern "C" int production_gate_verify(const char *filename, unsigned words, unsigned long long bits) {
  std::vector<Span> spans;
  if (!load(filename,words,bits,spans)) return 1;
  for (const auto &span : spans) {
    const auto stride = (span.width+3ull)/4+1;
    for (unsigned address=0; address<span.depth; ++address) {
      const char *expected = &span.values[stride*address];
      s_vpi_value actual{};
      actual.format = vpiVectorVal;
      vpi_get_value(word(span,address),&actual);
      for (unsigned bit=0; bit<span.width; ++bit) {
        char digit = expected[stride-2-bit/4];
        unsigned nibble = digit <= '9' ? digit-'0' : digit-'a'+10;
        unsigned mask = 1u << (bit%32);
        if ((actual.value.vector[bit/32].bval & mask) ||
            bool(actual.value.vector[bit/32].aval & mask) != bool(nibble & (1u << (bit%4)))) {
          error("readback mismatch",span.path+"["+std::to_string(address)+"] bit="+std::to_string(bit));
          return 1;
        }
      }
    }
  }
  vpi_printf("PRODUCTION_GATE_READBACK: words=%u bits=%llu before_first_edge=1\n",words,bits);
  return 0;
}
extern "C" int production_gate_flip(const char *path, unsigned bit_index) {
  auto handle = resolve(path);
  if (!handle || (vpi_get(vpiType,handle) != vpiReg && vpi_get(vpiType,handle) != vpiMemoryWord) ||
      bit_index >= static_cast<unsigned>(vpi_get(vpiSize,handle))) return error("invalid corruption handle",path) ? 0 : 1;
  s_vpi_value value{};
  value.format = vpiVectorVal;
  vpi_get_value(handle,&value);
  std::vector<s_vpi_vecval> copy(value.value.vector, value.value.vector+(vpi_get(vpiSize,handle)+31)/32);
  for (const auto &part : copy) if (part.bval) return error("unknown corruption state",path) ? 0 : 1;
  copy[bit_index/32].aval ^= 1u << (bit_index%32);
  value.value.vector = copy.data();
  vpi_put_value(handle,&value,nullptr,vpiNoDelay);
  s_vpi_value readback{};
  readback.format = vpiVectorVal;
  vpi_get_value(handle,&readback);
  for (unsigned i=0; i<copy.size(); ++i)
    if (copy[i].aval != readback.value.vector[i].aval || readback.value.vector[i].bval)
      return error("corruption readback failed",path) ? 0 : 1;
  vpi_printf("PRODUCTION_GATE_FLIP: path=%s bit=%u verified=1\n",path,bit_index);
  return 0;
}
