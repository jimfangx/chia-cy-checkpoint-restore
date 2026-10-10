// Immutable compatibility owner for the audited FCFS VCS test-entry profile.
// This does not authorize production plusargs or other driver configurations.
#ifndef FS_RUNTIME_IDENTITY_H
#define FS_RUNTIME_IDENTITY_H
#include "core/checkpoint.h"

// Load the audited release's lazily opened diagnostic tables before pinning
// the immutable ELF inventory. Handles remain owned for the process lifetime.
void checkpoint_vcs_runtime_warmup();

class runtime_identity_t final : public checkpoint_owner_t {
public:
  explicit runtime_identity_t(const std::vector<std::string> &args);
  std::string checkpoint_schema() const override {
    return "firesim.runtime.fcfs-config-and-loaded-elf.v1";
  }
  std::vector<uint8_t> save_checkpoint() const override;
  void validate_checkpoint(const std::vector<uint8_t> &) const override;
  void load_checkpoint(const std::vector<uint8_t> &bytes) override {
    validate_checkpoint(bytes); // Immutable configuration, never overwrite it.
  }
private:
  std::vector<uint8_t> configuration, identity;
  std::vector<uint8_t> current_identity() const;
};
#endif
