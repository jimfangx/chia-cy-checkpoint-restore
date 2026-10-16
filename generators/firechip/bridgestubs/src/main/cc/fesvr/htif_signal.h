// See LICENSE for license details.
#ifndef FIRESIM_HTIF_SIGNAL_H
#define FIRESIM_HTIF_SIGNAL_H
#include "htif_lifecycle.h"

// Opt-in exact-source provider projection. The process-wide delivered latch
// and private lifecycle fields form one publication unit. There are no host
// pointers, signal numbers, raw sigaction bytes or pending kernel signals in it.
struct firesim_htif_signal_state_t {
  firesim_htif_lifecycle_state_t lifecycle;
  bool delivered;
};

// The coordinator must exclusively suspend every HTIF instance and prevent
// INT/TERM/ABRT delivery in all threads throughout access. This thread must
// have those signals blocked, no corresponding pending signals, and the exact
// original BSD signal() actions. Other process/thread signal state is outside
// this component. Changed actions, signature mode and pending signals reject.
// This contract alone does not authorize a complete process/TSI checkpoint.
firesim_htif_signal_state_t firesim_htif_signal_read(const htif_t &);
void firesim_htif_signal_validate_restore(const htif_t &, firesim_htif_signal_state_t);
// Destination must have no delivered latch, absent exit and stopped=false.
// All guards precede a nonthrowing, allocation-free peer callback and provider
// publication. Callback must not access HTIF/signals or invoke any service.
void firesim_htif_signal_publish(htif_t &, firesim_htif_signal_state_t,
                                void (*)(void *) noexcept, void *);
#endif
