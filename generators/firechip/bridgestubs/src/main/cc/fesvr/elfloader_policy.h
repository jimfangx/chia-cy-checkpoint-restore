// Observe the installed HTIF's nonvirtual XLEN policy at its actual loader call.
#ifndef FIRESIM_ELFLOADER_POLICY_H
#define FIRESIM_ELFLOADER_POLICY_H

#include <fesvr/elfloader.h>
#include <stdexcept>
#include <string>

// Used only around a synchronous, preloaded metadata probe. Never span a
// coroutine yield or serialize this process-local observer. Ordinary ELF loads
// have no observer and retain their existing behavior.
class firesim_elfloader_policy_t {
public:
  firesim_elfloader_policy_t(std::string path, reg_t *entry, reg_t offset)
      : path(std::move(path)), entry(entry), offset(offset) {
    if (active) {
      active->invalid = true;
      throw std::runtime_error("nested HTIF loader policy observation");
    }
    active = this;
  }
  ~firesim_elfloader_policy_t() { active = nullptr; }
  firesim_elfloader_policy_t(const firesim_elfloader_policy_t &) = delete;
  firesim_elfloader_policy_t &operator=(const firesim_elfloader_policy_t &) = delete;

  static void observe(const char *path, memif_t *mem, reg_t *entry,
                      reg_t offset, unsigned required_xlen) {
    if (!active) return;
    auto &s = *active;
    if (s.invalid || ++s.calls != 1 || !path || s.path != path || !mem ||
        s.entry != entry || s.offset != offset) {
      s.invalid = true;
      throw std::runtime_error("unexpected HTIF loader policy provider call");
    }
    s.required_xlen = required_xlen;
  }
  unsigned result() const {
    if (invalid || calls != 1)
      throw std::runtime_error("missing or invalid HTIF loader policy provider");
    return required_xlen;
  }
private:
  static inline thread_local firesim_elfloader_policy_t *active = nullptr;
  std::string path;
  reg_t *entry;
  reg_t offset;
  unsigned calls = 0, required_xlen = 0;
  bool invalid = false;
};
#endif
