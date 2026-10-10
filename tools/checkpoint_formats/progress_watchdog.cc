#include "progress_watchdog.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <stdexcept>
#include <unistd.h>

namespace {
void require(bool ok, const char *message) {
  if(!ok) throw std::runtime_error(std::string("checkpoint watchdog: ")+message);
}
uint64_t now_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
}
uint64_t ns(uint64_t ms) {
  require(ms<=uint64_t(std::numeric_limits<int64_t>::max())/1000000,
          "timeout exceeds steady-clock range");
  return ms*1000000;
}
void report_failure(const char *reason,uint64_t cycle,uint64_t samples,uint64_t captures,uint64_t capture_ns) {
  char message[512];
  const int length=snprintf(message,sizeof(message),"FS_CHECKPOINT_WATCHDOG_FAILURE reason=%s target_cycle=%llu samples=%llu captures=%llu capture_ns=%llu\n",
          reason,(unsigned long long)cycle,(unsigned long long)samples,
          (unsigned long long)captures,(unsigned long long)capture_ns);
  // Do not acquire stdio locks potentially held by the stalled simulator.
  if(length>0 && size_t(length)<sizeof(message)) {
    const auto ignored=write(STDERR_FILENO,message,size_t(length)); (void)ignored;
  }
  std::_Exit(EXIT_FAILURE);
}
}
checkpoint_progress_policy_t::checkpoint_progress_policy_t(uint64_t host_ns, uint64_t cycle_ns, uint64_t capture_ns)
  : host_timeout(host_ns),cycle_timeout(cycle_ns),capture_timeout(capture_ns) {
  require((host_timeout || cycle_timeout) && capture_timeout,"missing progress/capture timeout");
}
void checkpoint_progress_policy_t::time(uint64_t now) {
  require(!initialized || now>=last_time,"monotonic time regressed"); last_time=now;
}
void checkpoint_progress_policy_t::sample(uint64_t now, uint64_t target_cycle) {
  time(now); require(!capturing,"sample during capture");
  require(!initialized || target_cycle>=cycle,"target cycle regressed; initialize after restore");
  host_time=now;
  if(!initialized || cycle!=target_cycle) cycle_time=now;
  cycle=target_cycle; initialized=true;
}
void checkpoint_progress_policy_t::begin_capture(uint64_t now) {
  time(now); require(initialized && !capturing,"uninitialized/nested capture");
  capturing=true; capture_time=now;
}
void checkpoint_progress_policy_t::end_capture(uint64_t now) {
  time(now); require(capturing,"capture is not active");
  require(now-capture_time<capture_timeout,"capture deadline expired");
  // Exclude only elapsed capture time; pre-existing cycle-stall age survives.
  const auto elapsed=now-capture_time;
  host_time+=elapsed; cycle_time+=elapsed; capturing=false;
}
const char *checkpoint_progress_policy_t::failure(uint64_t now) {
  time(now);
  if(!initialized) return nullptr;
  if(capturing) return now-capture_time>=capture_timeout ? "capture_stall" : nullptr;
  if(host_timeout && now-host_time>=host_timeout) return "host_progress_stall";
  if(cycle_timeout && now-cycle_time>=cycle_timeout) return "target_cycle_stall";
  return nullptr;
}

checkpoint_progress_watchdog_t::checkpoint_progress_watchdog_t(uint64_t host_ms, uint64_t cycle_ms, uint64_t capture_ms)
  : policy(ns(host_ms),ns(cycle_ms),ns(capture_ms)),
    host_ns(ns(host_ms)),cycle_ns(ns(cycle_ms)),capture_limit_ns(ns(capture_ms)) {
  policy.sample(now_ns(),0);
  monitor=std::thread(&checkpoint_progress_watchdog_t::watch,this);
}
checkpoint_progress_watchdog_t::~checkpoint_progress_watchdog_t() {
  stopping=true; wake.notify_one();
  monitor.join();
}
void checkpoint_progress_watchdog_t::check(uint64_t now) {
  if(const auto *reason=policy.failure(now)) {
    // Avoid VCS exit handlers tearing down a parked DPI worker. Failure does
    // not publish/prune history, acknowledge capture, or run target edges.
    report_failure(reason,cycle,samples,captures,capture_ns);
  }
}
void checkpoint_progress_watchdog_t::watch() {
  checkpoint_progress_policy_t cached(host_ns,cycle_ns,capture_limit_ns);
  cached.sample(now_ns(),0);
  uint64_t observed_cycle=0,observed_samples=0,observed_captures=0,observed_capture_ns=0;
  std::unique_lock<std::mutex> wait_lock(wait_mutex);
  while(!stopping) {
    {
      // A stalled simulator can hold its sampling lock. Never wait for that
      // lock: the last coherent copy continues aging under steady_clock.
      std::unique_lock<std::mutex> sample_lock(mutex,std::try_to_lock);
      if(sample_lock.owns_lock()) {
        cached=policy; observed_cycle=cycle; observed_samples=samples;
        observed_captures=captures; observed_capture_ns=capture_ns;
      }
    }
    if(const auto *reason=cached.failure(now_ns()))
      report_failure(reason,observed_cycle,observed_samples,observed_captures,observed_capture_ns);
    wake.wait_for(wait_lock,std::chrono::milliseconds(1),[&]{ return stopping.load(); });
  }
}
void checkpoint_progress_watchdog_t::sample(uint64_t target_cycle) {
  std::lock_guard<std::mutex> lock(mutex);
  const auto now=now_ns(); check(now); policy.sample(now,target_cycle);
  cycle=target_cycle;
  if(++samples==1) {
    printf("FS_CHECKPOINT_WATCHDOG_ARMED target_cycle=%llu sampler=settled_operation clock=steady_clock\n",
           (unsigned long long)cycle); std::fflush(stdout);
  }
}
void checkpoint_progress_watchdog_t::begin_capture() {
  std::lock_guard<std::mutex> lock(mutex);
  const auto now=now_ns(); check(now); policy.begin_capture(now); capture_start=now;
}
void checkpoint_progress_watchdog_t::end_capture() {
  std::lock_guard<std::mutex> lock(mutex);
  const auto now=now_ns(); check(now); policy.end_capture(now);
  const auto elapsed=now-capture_start; capture_ns+=elapsed; ++captures;
  printf("FS_CHECKPOINT_WATCHDOG_CAPTURE_ACCOUNTED target_cycle=%llu elapsed_ns=%llu total_ns=%llu captures=%llu\n",
         (unsigned long long)cycle,(unsigned long long)elapsed,
         (unsigned long long)capture_ns,(unsigned long long)captures); std::fflush(stdout);
}
