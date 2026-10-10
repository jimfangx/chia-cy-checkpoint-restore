// Complete live Level-1 snapshot collection for an audited VCS profile.
#ifndef FS_DURABLE_CAPTURE_H
#define FS_DURABLE_CAPTURE_H
#include "aggregate_restore.h"

// The coordinator must park the completed-operation worker and hold all
// clocks low across this call and publication. This API issues no deposits,
// native loads, MMIO operations or simulation edges. It returns canonical
// FSAGG1 staging for encode_durable_capture/publish_durable_capture.
std::string capture_durable_snapshot(const aggregate_restore_t::owners_t &owners,
                                    uint64_t host_sample);
#endif
