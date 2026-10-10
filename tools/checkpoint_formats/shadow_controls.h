#pragma once
#include <charconv>
#include <cstdint>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

// These observer controls are excluded from future-environment compatibility
// only after complete validation. Ordinary production builds still reject them.
struct checkpoint_shadow_controls_t {
  std::map<std::string, std::string> values;
  bool contains(const std::string &arg) const { return values.count(arg.substr(0, arg.find('='))); }
  static checkpoint_shadow_controls_t parse(const std::vector<std::string> &args, bool restoring) {
    checkpoint_shadow_controls_t result;
    for (const auto &arg : args) {
      if (arg.rfind("+shadow-", 0) != 0) continue;
#ifndef FS_CHECKPOINT_SHADOW
      throw std::runtime_error("live shadow requires FS_CHECKPOINT_SHADOW=1 build");
#endif
      const auto split = arg.find('=');
      const auto key = arg.substr(0, split);
      if (split == std::string::npos || split + 1 == arg.size() ||
          (key != "+shadow-socket" && key != "+shadow-identity" &&
           key != "+shadow-first-cycle" && key != "+shadow-level1-cycle") ||
          !result.values.emplace(key, arg.substr(split + 1)).second)
        throw std::runtime_error("invalid/duplicate live shadow control: " + key);
    }
    if (result.values.empty()) return result;
    if (!restoring || result.values.size() != 4)
      throw std::runtime_error("live shadow requires public restore and all four controls");
    const auto &socket = result.values.at("+shadow-socket");
    const auto &identity = result.values.at("+shadow-identity");
    if (socket.size() >= 108 || socket.front() != '/' || socket.find_first_of("\r\n") != std::string::npos ||
        identity.size() != 64 || identity.find_first_not_of("0123456789abcdef") != std::string::npos)
      throw std::runtime_error("invalid live shadow socket/session identity");
    for (const auto &key : {"+shadow-first-cycle", "+shadow-level1-cycle"}) {
      const auto &text = result.values.at(key);
      uint64_t cycle = 0;
      const auto parsed = std::from_chars(text.data(), text.data() + text.size(), cycle);
      if ((text != "0" && text.front() == '0') || parsed.ec != std::errc{} ||
          parsed.ptr != text.data() + text.size() ||
          (std::string(key) == "+shadow-first-cycle" && cycle == std::numeric_limits<uint64_t>::max()))
        throw std::runtime_error("invalid live shadow cycle origin");
    }
    return result;
  }
};
