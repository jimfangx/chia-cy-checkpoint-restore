// Native live Level-1 history; all publication occurs while the worker is parked.
#ifndef FS_DURABLE_HISTORY_H
#define FS_DURABLE_HISTORY_H
#include <memory>
#include <cstdint>
#include <stdexcept>
#include <string>

class durable_history_error_t : public std::runtime_error {
public:
  const bool committed;
  durable_history_error_t(bool committed, const std::string &message);
};
class durable_history_t {
  struct impl_t;
  std::unique_ptr<impl_t> impl;
public:
  // Existing private directory, pinned for the lifetime of this capability.
  // Validate/recover committed history before simulation starts; no state load.
  durable_history_t(const std::string &directory, uint64_t retention);
  ~durable_history_t();
  // Encode/validate complete state, sync immutable image, reopen/validate it,
  // atomically commit/sync/read back index, then prune. Failure must not release
  // the parked worker. committed=true means a visible index needs recovery.
  void publish(const std::string &snapshot);
};
#endif
