// Trusted staging for an audited runtime profile. The caller must reject the
// process on any error and hold clocks through all commit/readback/bootstrap.
#ifndef FS_AGGREGATE_RESTORE_H
#define FS_AGGREGATE_RESTORE_H
#include "core/checkpoint.h"
#include <utility>

class aggregate_restore_t {
public:
  using owners_t = std::vector<std::pair<std::string, checkpoint_owner_t *>>;
  void prepare(const std::string &filename, const owners_t &owners);
  void commit_native();
  void commit_rtl();
  uint64_t target_cycle = 0, host_sample = 0;
private:
  enum class phase_t { fresh, poisoned, prepared, native_loaded, rtl_loaded };
  phase_t phase = phase_t::fresh;
  owners_t owners;
  std::vector<std::vector<uint8_t>> payloads;
};
#endif
