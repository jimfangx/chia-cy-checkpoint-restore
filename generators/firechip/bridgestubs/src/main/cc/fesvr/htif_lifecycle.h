// See LICENSE for license details.
#ifndef FIRESIM_HTIF_LIFECYCLE_H
#define FIRESIM_HTIF_LIFECYCLE_H

#include <cstdint>
class htif_t;

// Actual provider fields, independent of direct-command/poll continuation.
// This API exists only in the opt-in build-local HTIF provider. It is not a
// complete session, signal, descriptor or context checkpoint interface.
struct firesim_htif_lifecycle_state_t {
  bool has_exit;
  uint32_t raw_exit;
  bool stopped;
};

// Caller must externally suspend HTIF and serialize provider access. INT, TERM
// and ABRT must be blocked in this thread. Pending/delivered signals, changed
// handlers and signature mode are rejected; process signal state is not loaded.
firesim_htif_lifecycle_state_t firesim_htif_lifecycle_read(const htif_t &);
// Destination must have absent exit and stopped=false. No HTIF service, device,
// memory operation, coroutine switch or target edge is performed.
void firesim_htif_lifecycle_restore(htif_t &, firesim_htif_lifecycle_state_t);
#endif
