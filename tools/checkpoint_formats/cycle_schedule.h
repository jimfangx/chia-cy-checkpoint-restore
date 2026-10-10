// Target deadlines for live Level-1 cuts. Host edges/operations are not time.
#ifndef FS_CYCLE_SCHEDULE_H
#define FS_CYCLE_SCHEDULE_H
#include <cstdint>
#include <limits>
#include <stdexcept>

class checkpoint_cycle_schedule_t {
  uint64_t interval, origin, last, deadline = 0;
  bool enabled = false;
public:
  checkpoint_cycle_schedule_t(uint64_t interval, uint64_t origin = 0)
      : interval(interval), origin(origin), last(origin) {
    if (!interval) throw std::runtime_error("target interval must be positive");
    const auto maximum = std::numeric_limits<uint64_t>::max();
    enabled = interval <= maximum-origin;
    if (enabled) deadline = origin+interval;
  }
  bool due(uint64_t cycle) {
    if (cycle < last) throw std::runtime_error("target cycle regressed; reinitialize after restore");
    last = cycle;
    return enabled && cycle >= deadline;
  }
  void committed(uint64_t cycle) {
    if (!due(cycle)) throw std::runtime_error("checkpoint committed before target deadline");
    const auto remainder = (cycle-origin)%interval;
    const auto delta = interval-remainder;
    enabled = delta <= std::numeric_limits<uint64_t>::max()-cycle;
    if (enabled) deadline = cycle+delta;
  }
};
#endif
