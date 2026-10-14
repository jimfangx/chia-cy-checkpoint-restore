// See LICENSE for license details.
// Audited source integration of the original FESVR tsi.cc protocol. Only FIFO
// ownership changes. The suspended host stack/read destination remain unowned.
#include "tsi.h"

void firesim_fesvr_tsi_t::host_thread(void *arg) {
  auto tsi = static_cast<firesim_fesvr_tsi_t *>(arg);
  tsi->run();
  while (true) tsi->target->switch_to();
}

firesim_fesvr_tsi_t::firesim_fesvr_tsi_t(int argc, char **argv) : htif_t(argc, argv) {
  target = context_t::current();
  host.init(host_thread, this);
}

void firesim_fesvr_tsi_t::reset() {
  uint32_t one = 1;
  write_chunk(0x2000000, sizeof(uint32_t), &one);
}

void firesim_fesvr_tsi_t::read_chunk(addr_t address, size_t bytes, void *destination) {
  auto result = static_cast<uint32_t *>(destination);
  serial.issue_read(address, bytes);
  for (size_t i = 0; i < bytes / sizeof(uint32_t); ++i) {
    while (!serial.response_available()) switch_to_target();
    result[i] = serial.pop_response();
  }
}

void firesim_fesvr_tsi_t::write_chunk(addr_t address, size_t bytes, const void *source) {
  serial.issue_write(address, bytes, source);
}

void firesim_fesvr_tsi_t::switch_to_host() { host.switch_to(); }
void firesim_fesvr_tsi_t::switch_to_target() { target->switch_to(); }
