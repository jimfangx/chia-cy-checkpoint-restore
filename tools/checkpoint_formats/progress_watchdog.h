// Host policy only. Never serialized as Level-1 or Level-2 target state.
#ifndef FS_PROGRESS_WATCHDOG_H
#define FS_PROGRESS_WATCHDOG_H
#include <condition_variable>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <thread>

// Nanosecond policy with an injectable monotonic clock for boundary checks.
// Zero disables a progress deadline; capture_timeout is always bounded.
class checkpoint_progress_policy_t {
  uint64_t host_timeout, cycle_timeout, capture_timeout;
  uint64_t last_time=0, host_time=0, cycle_time=0, capture_time=0;
  uint64_t cycle=0;
  bool initialized=false, capturing=false;
  void time(uint64_t now);
public:
  checkpoint_progress_policy_t(uint64_t host_ns, uint64_t cycle_ns, uint64_t capture_ns);
  void sample(uint64_t now, uint64_t target_cycle);
  void begin_capture(uint64_t now);
  void end_capture(uint64_t now);
  const char *failure(uint64_t now);
};

// The sampler invokes VPI only on the settled main thread. This monitor reads
// mutex-protected host copies and steady_clock, never simulator/native owners.
class checkpoint_progress_watchdog_t {
  std::mutex mutex;
  std::mutex wait_mutex;
  std::condition_variable wake;
  checkpoint_progress_policy_t policy;
  std::thread monitor;
  std::atomic<bool> stopping{false};
  const uint64_t host_ns, cycle_ns, capture_limit_ns;
  uint64_t samples=0, cycle=0, captures=0, capture_start=0, capture_ns=0;
  void check(uint64_t now);
  void watch();
public:
  checkpoint_progress_watchdog_t(uint64_t host_ms, uint64_t cycle_ms, uint64_t capture_ms);
  ~checkpoint_progress_watchdog_t();
  void sample(uint64_t target_cycle);
  void begin_capture();
  void end_capture();
};
#endif
