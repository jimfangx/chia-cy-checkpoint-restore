// See LICENSE for license details.
#ifndef FIRESIM_HTIF_SIGNAL_THREADS_H
#define FIRESIM_HTIF_SIGNAL_THREADS_H
#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <csignal>
#include <dirent.h>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// A fail-closed audit of the kernel's per-thread signal state. This is not a
// thread freezer: callers must already hold exclusive suspension and prohibit
// thread creation/exit, signal delivery and changes to masks/actions throughout
// capture or publication. In particular, observing a mask once cannot establish
// that another running thread will keep it blocked. Nothing here is image data.
namespace firesim_htif_signal_threads {
inline std::vector<std::string> inventory() {
  std::unique_ptr<DIR, int (*)(DIR *)> directory(opendir("/proc/self/task"), closedir);
  if (!directory) throw std::runtime_error("HTIF signal thread inventory unavailable");
  std::vector<std::string> tids;
  for (;;) {
    errno = 0;
    auto *entry = readdir(directory.get());
    if (!entry) {
      if (errno) throw std::runtime_error("HTIF signal thread inventory failed");
      break;
    }
    const std::string tid(entry->d_name);
    if (tid.empty() || tid == "." || tid == "..") continue;
    if (tid.find_first_not_of("0123456789") != std::string::npos)
      throw std::runtime_error("invalid HTIF signal thread inventory");
    tids.push_back(tid);
  }
  std::sort(tids.begin(), tids.end());
  if (tids.empty() || std::adjacent_find(tids.begin(), tids.end()) != tids.end())
    throw std::runtime_error("incomplete HTIF signal thread inventory");
  return tids;
}

inline void guard() {
#if defined(__linux__) && defined(__x86_64__)
  const uint64_t required = (uint64_t(1) << (SIGINT - 1)) |
                            (uint64_t(1) << (SIGTERM - 1)) |
                            (uint64_t(1) << (SIGABRT - 1));
  const auto tids = inventory();
  for (const auto &tid : tids) {
    std::ifstream status("/proc/self/task/" + tid + "/status");
    if (!status) throw std::runtime_error("HTIF signal thread status unavailable: " + tid);
    uint64_t blocked = 0, pending = 0, shared = 0;
    unsigned seen = 0;
    std::string line;
    while (std::getline(status, line)) {
      unsigned bit = 0;
      uint64_t *value = nullptr;
      if (line.compare(0, 7, "SigBlk:") == 0) { bit = 1; value = &blocked; }
      else if (line.compare(0, 7, "SigPnd:") == 0) { bit = 2; value = &pending; }
      else if (line.compare(0, 7, "ShdPnd:") == 0) { bit = 4; value = &shared; }
      if (!bit) continue;
      std::istringstream field(line.substr(7));
      std::string extra;
      if ((seen & bit) || !(field >> std::hex >> *value) || (field >> extra))
        throw std::runtime_error("invalid HTIF signal thread status: " + tid);
      seen |= bit;
    }
    if (!status.eof() || seen != 7)
      throw std::runtime_error("incomplete HTIF signal thread status: " + tid);
    if ((blocked & required) != required)
      throw std::runtime_error("unblocked HTIF signal in thread: " + tid);
    if ((pending | shared) & required)
      throw std::runtime_error("pending HTIF signal in thread: " + tid);
  }
  if (inventory() != tids)
    throw std::runtime_error("HTIF signal thread inventory changed during audit");
#else
  throw std::runtime_error("unsupported HTIF signal thread audit ABI");
#endif
}
} // namespace firesim_htif_signal_threads
#endif
