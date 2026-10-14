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

#define SAI_CMD_READ 0
#define SAI_CMD_WRITE 1
#define SAI_ADDR_CHUNKS 2
#define SAI_LEN_CHUNKS 2

class firesim_fesvr_tsi_t : public htif_t {
public:
  firesim_fesvr_tsi_t(int argc, char **argv);
  virtual ~firesim_fesvr_tsi_t() = default;
  bool data_available() { return serial.request_available(); }
  void send_word(uint32_t word) { serial.push_response(word); }
  uint32_t recv_word() { return serial.pop_request(); }
  void switch_to_host();
  uint32_t in_bits() { return serial.request_front(); }
  bool in_valid() { return serial.request_available(); }
  bool out_ready() { return true; }
  void tick(bool out_valid, uint32_t out_bits, bool in_ready) { serial.tick(out_valid, out_bits, in_ready); }
  const checkpoint_owner_t &serial_queue_owner() const { return serial; }
protected:
  void reset() override;
  void read_chunk(addr_t address, size_t bytes, void *destination) override;
  void write_chunk(addr_t address, size_t bytes, const void *source) override;
  void switch_to_target();
  size_t chunk_align() override { return 4; }
  size_t chunk_max_size() override { return 1024; }
private:
  context_t host;
  context_t *target;
  firesim_tsi_serial_state_t serial;
  static void host_thread(void *tsi);
};

// TestChip's existing source uses the upstream type spelling. Library tsi_t
// symbols stay distinct and unused; no ABI/layout patch of libfesvr is needed.
using tsi_t = firesim_fesvr_tsi_t;
#endif
