// Pin only heartbeat's diagnostic wall-clock dependency in this host fixture.
// VCS and its license client retain the real libc time function.
#include <ctime>
#include <cinttypes>
#include <cstring>
#include <limits>
#include "bridges/heartbeat.h"
#include "bridges/clock.h"
#include "core/simif.h"
extern "C" time_t firesim_driver_test_time(time_t *) noexcept;
#define time firesim_driver_test_time
#include "bridges/heartbeat.cc"
#undef time
