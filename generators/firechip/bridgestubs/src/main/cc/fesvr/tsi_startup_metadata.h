// See LICENSE for license details.
#ifndef __FIRESIM_TSI_STARTUP_METADATA_H
#define __FIRESIM_TSI_STARTUP_METADATA_H

#include "core/widget_checkpoint.h"
#include <fesvr/elfloader.h>
#include <fstream>
#include <iterator>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>

// A sealed, process-local copy prevents ELF path changes while installed
// FESVR is suspended loading a payload. Never serialize this descriptor.
class firesim_tsi_elf_snapshot_t {
public:
  explicit firesim_tsi_elf_snapshot_t(const std::vector<uint8_t> &bytes) {
    fd = memfd_create("firesim-tsi-elf", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (fd < 0) throw std::runtime_error("cannot snapshot TSI ELF");
    size_t done = 0;
    while (done < bytes.size()) {
      const auto n = ::write(fd, bytes.data() + done, bytes.size() - done);
      if (n <= 0) { ::close(fd); throw std::runtime_error("cannot write TSI ELF snapshot"); }
      done += n;
    }
    if (fcntl(fd, F_ADD_SEALS, F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL) < 0) {
      ::close(fd); throw std::runtime_error("cannot seal TSI ELF snapshot");
    }
  }
  ~firesim_tsi_elf_snapshot_t() { ::close(fd); }
  firesim_tsi_elf_snapshot_t(const firesim_tsi_elf_snapshot_t &) = delete;
  firesim_tsi_elf_snapshot_t &operator=(const firesim_tsi_elf_snapshot_t &) = delete;
  std::string path() const { return "/proc/self/fd/" + std::to_string(fd); }
private:
  int fd;
};

inline std::vector<uint8_t> firesim_tsi_elf_bytes(const std::string &path) {
  std::ifstream file(path, std::ios::binary);
  if (!file) throw std::runtime_error("TSI metadata requires an accessible explicit ELF path");
  std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
  if (file.bad() || bytes.empty()) throw std::runtime_error("cannot read TSI metadata ELF");
  return bytes;
}

struct firesim_tsi_startup_metadata_t {
  std::vector<uint8_t> elf;
  reg_t entry = 0;
  std::map<std::string, uint64_t> symbols;

  std::vector<uint8_t> image(const std::vector<std::string> &arguments,
                             const std::vector<uint8_t> &configuration) const {
    // Version 2 binds the destination's transport and pristine owner contract.
    // Legacy metadata images cannot certify that contract and must reject.
    widget_checkpoint_config_t out(25, {2});
    auto blob = [&](const auto &value) {
      out.word(value.size()); out.bytes.insert(out.bytes.end(), value.begin(), value.end());
    };
    blob(configuration);
    out.word(arguments.size());
    for (const auto &arg : arguments) blob(arg);
    blob(elf); out.word(entry); out.word(symbols.size());
    for (const auto &[name, address] : symbols) { blob(name); out.word(address); }
    return std::move(out.bytes);
  }

  // Decode only the trusted, local ELF. Invalid checkpoint bytes are compared
  // to this complete canonical image and never passed into FESVR's ELF parser.
  static firesim_tsi_startup_metadata_t probe(std::vector<uint8_t> elf) {
    firesim_tsi_startup_metadata_t result;
    result.elf = std::move(elf);
    firesim_tsi_elf_snapshot_t snapshot(result.elf);
    class nop_memif_t final : public memif_t {
    public:
      nop_memif_t() : memif_t(nullptr) {}
      void read(addr_t, size_t, void *) override { throw std::runtime_error("metadata ELF read target memory"); }
      void write(addr_t, size_t, const void *) override {}
      endianness_t get_target_endianness() const override { return endianness_little; }
    } mem;
    result.symbols = load_elf(snapshot.path().c_str(), &mem, &result.entry, 0x80000000);
    return result;
  }
};
#endif
