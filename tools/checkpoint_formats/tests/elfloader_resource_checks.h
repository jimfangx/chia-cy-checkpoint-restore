#ifndef CHECKPOINT_ELFLOADER_RESOURCE_CHECKS_H
#define CHECKPOINT_ELFLOADER_RESOURCE_CHECKS_H
#include <filesystem>
#include <fstream>
#include <string>
#include <utility>
#include <stdexcept>

inline size_t elf_process_descriptors() {
  size_t result = 0;
  for (const auto &entry : std::filesystem::directory_iterator("/proc/self/fd")) {
    (void)entry;
    ++result;
  }
  return result;
}

// Count kernel resources rather than relying on LeakSanitizer, which does not
// report leaked mmap regions. Each test uses a private, sealed ELF snapshot.
inline std::pair<size_t, size_t> elf_snapshot_resources() {
  size_t descriptors = 0, mappings = 0;
  for (const auto &entry : std::filesystem::directory_iterator("/proc/self/fd")) {
    std::error_code error;
    const auto target = std::filesystem::read_symlink(entry.path(), error).string();
    if (!error && target.find("memfd:firesim-tsi-elf") != std::string::npos) ++descriptors;
  }
  std::ifstream file("/proc/self/maps");
  if (!file) throw std::runtime_error("cannot audit ELF mappings");
  std::string line;
  while (std::getline(file, line))
    if (line.find("memfd:firesim-tsi-elf") != std::string::npos) ++mappings;
  return {descriptors, mappings};
}
#endif
