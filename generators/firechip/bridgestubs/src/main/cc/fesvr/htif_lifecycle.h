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
// Read-only destination preflight. Repeat immediately before publication;
// preparing a candidate does not reserve signal or destination state.
void firesim_htif_lifecycle_validate_restore(const htif_t &, firesim_htif_lifecycle_state_t);
// All provider guards run before the callback. The callback must only publish
// already prepared peers, must not access HTIF or signals, and must not throw.
// Caller retains exclusive suspended-provider access throughout this call.
// After the callback, provider field assignment cannot allocate or throw.
void firesim_htif_lifecycle_publish(htif_t &, firesim_htif_lifecycle_state_t,
                                  void (*publish_peers)(void *) noexcept, void *);
// Destination must have absent exit and stopped=false. No HTIF service, device,
// memory operation, coroutine switch or target edge is performed.
void firesim_htif_lifecycle_restore(htif_t &, firesim_htif_lifecycle_state_t);
#endif
