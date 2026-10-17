// See LICENSE for license details.
// Audited source integration of the original FESVR tsi.cc protocol. Only FIFO
// and pointer-free read/wrapper progress. Caller owners authorize fresh entry.
#include "tsi.h"

void firesim_fesvr_tsi_t::host_thread(void *arg) {
  auto tsi = static_cast<firesim_fesvr_tsi_t *>(arg);
  tsi->host_wrapper.enter();
  if (tsi->host_wrapper.phase() != firesim_tsi_host_wrapper_t::phase_t::tail) {
    try { tsi->run_host(); tsi->host_wrapper.returned(); }
    catch (...) { tsi->host_wrapper.interrupt(); throw; }
  }
  while (true) tsi->switch_to_target();
}

firesim_fesvr_tsi_t::firesim_fesvr_tsi_t(int argc, char **argv) : htif_t(argc, argv) {
  target = context_t::current();
}

void firesim_fesvr_tsi_t::reset() {
  uint32_t one = 1;
  write_chunk(0x2000000, sizeof(uint32_t), &one);
}

void firesim_fesvr_tsi_t::read_chunk(addr_t address, size_t bytes, void *destination) {
  if (!destination) throw std::runtime_error("missing serial read destination");
  serial_read.begin(address, bytes);
  firesim_tsi_serial_read_services_t services(serial);
  try {
    for (;;) {
      const auto progress = serial_read.advance(services);
      if (progress == firesim_tsi_serial_read_t::result_t::complete) break;
      if (progress == firesim_tsi_serial_read_t::result_t::blocked) switch_to_target();
    }
    const auto &words = serial_read.result();
    std::copy(words.begin(), words.end(), static_cast<uint32_t *>(destination));
    serial_read.finish();
  } catch (...) {
    serial_read.interrupt();
    throw;
  }
}

void firesim_fesvr_tsi_t::write_chunk(addr_t address, size_t bytes, const void *source) {
  serial.issue_write(address, bytes, source);
}

void firesim_fesvr_tsi_t::switch_to_host() {
  require_target_thread();
  // Check the original creator before allocating a child or entering any
  // service. A fresh coroutine must not accidentally bind a foreign thread.
  if (context_t::current() != target)
    throw std::runtime_error("TSI host entry requires its original target context");
  validate_host_entry();
  // Constructing a fresh component must not enter an unowned HTIF context.
  // Upstream init only enters its trampoline and yields; doing it immediately
  // before the first host service preserves that service's original behavior.
  if (!host_initialized) {
    host.init(host_thread, this);
    host_initialized = true;
  }
  host.switch_to();
}
void firesim_fesvr_tsi_t::switch_to_target() {
  host_suspended = true;
  target->switch_to();
  host_suspended = false;
}
