// See LICENSE for license details.
// FireSim's source-integrated FESVR serial adapter. Algorithms originate in
// toolchains/riscv-tools/riscv-isa-sim/fesvr/tsi.{h,cc}. Installed HTIF/context
// and the toolchain archive are unchanged. All TestChip/FireSim clients must
// compile against this header; it deliberately uses a distinct C++ class name.
#ifndef __FIRESIM_OWNED_TSI_H
#define __FIRESIM_OWNED_TSI_H

#include <fesvr/htif.h>
#include <fesvr/context.h>
#include "tsi_serial_state.h"
#include "tsi_serial_read.h"
#include "tsi_host_wrapper.h"
#include "tsi_thread_owner.h"
#include "tsi_owner_view.h"

#define SAI_CMD_READ 0
#define SAI_CMD_WRITE 1
#define SAI_ADDR_CHUNKS 2
#define SAI_LEN_CHUNKS 2

class firesim_fesvr_tsi_t : public htif_t {
public:
  firesim_fesvr_tsi_t(int argc, char **argv);
  virtual ~firesim_fesvr_tsi_t() = default;
  void require_target_thread() const { thread_owner.require(); }
  bool data_available() { require_target_thread(); return serial.request_available(); }
  void send_word(uint32_t word) { require_target_thread(); serial.push_response(word); }
  uint32_t recv_word() { require_target_thread(); return serial.pop_request(); }
  void switch_to_host();
  uint32_t in_bits() { require_target_thread(); return serial.request_front(); }
  bool in_valid() { require_target_thread(); return serial.request_available(); }
  bool out_ready() { require_target_thread(); return true; }
  void tick(bool out_valid, uint32_t out_bits, bool in_ready) { require_target_thread(); serial.tick(out_valid, out_bits, in_ready); }
  const checkpoint_owner_t &serial_queue_owner() const { require_target_thread(); return serial_view; }
  const checkpoint_owner_t &serial_read_owner() const { require_target_thread(); return serial_read_view; }
  const checkpoint_owner_t &host_wrapper_owner() const { require_target_thread(); return host_wrapper_view; }
protected:
  const firesim_tsi_thread_owner_t &target_thread_policy() const { return thread_owner; }
  virtual int run_host() { return htif_t::run(); }
  virtual void validate_host_entry() const {}
  void reset() override;
  void read_chunk(addr_t address, size_t bytes, void *destination) override;
  void write_chunk(addr_t address, size_t bytes, const void *source) override;
  void switch_to_target();
  size_t chunk_align() override { return 4; }
  size_t chunk_max_size() override { return 1024; }
  firesim_tsi_serial_state_t serial;
  firesim_tsi_serial_read_t serial_read;
private:
  const firesim_tsi_thread_owner_t thread_owner;
  friend class firesim_tsi_context_group_t;
  firesim_tsi_host_wrapper_t host_wrapper;
  context_t host;
  context_t *target;
  bool host_initialized = false;
  bool host_suspended = false;
  firesim_tsi_owner_view_t<firesim_tsi_serial_state_t> serial_view{thread_owner, serial};
  firesim_tsi_owner_view_t<firesim_tsi_serial_read_t> serial_read_view{thread_owner, serial_read};
  firesim_tsi_owner_view_t<firesim_tsi_host_wrapper_t> host_wrapper_view{thread_owner, host_wrapper};
protected:
  bool host_context_initialized() const { return host_initialized; }
  bool host_context_suspended() const { return host_initialized && host_suspended; }
private:
  static void host_thread(void *tsi);
};

// TestChip's existing source uses the upstream type spelling. Library tsi_t
// symbols stay distinct and unused; no ABI/layout patch of libfesvr is needed.
using tsi_t = firesim_fesvr_tsi_t;
#endif
