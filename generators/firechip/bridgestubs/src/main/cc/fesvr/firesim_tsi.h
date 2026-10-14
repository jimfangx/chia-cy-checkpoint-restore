// See LICENSE for license details
#ifndef __FIRESIM_TSI_H
#define __FIRESIM_TSI_H

#include "testchip_tsi.h"
#include "loadmem_read.h"
#include "loadmem_queues.h"
#include "tsi_host_control.h"

struct firesim_loadmem_t {
  firesim_loadmem_t() : addr(0), size(0) {}
  firesim_loadmem_t(size_t addr, size_t size) : addr(addr), size(size) {}
  size_t addr;
  size_t size;
};

class firesim_tsi_t final : public testchip_tsi_t {
public:
  firesim_tsi_t(int argc, char **argv, bool has_loadmem);
  ~firesim_tsi_t() {}

  bool busy() { return host_control.busy(); };
  bool loaded_in_host() { return host_control.loaded_in_host(); };
  void set_loaded_in_target(bool loaded) { host_control.set_loaded_in_target(loaded); };

  void tick();
  void tick(bool out_valid, uint32_t out_bits, bool in_ready) { tick(); };

  bool recv_loadmem_write_req(firesim_loadmem_t &loadmem);
  bool recv_loadmem_read_req(firesim_loadmem_t &loadmem);
  void recv_loadmem_data(void *buf, size_t len);
  bool has_loadmem_reqs();

  void send_loadmem_word(uint32_t word);

  void load_program() override;

  // Component owner only. HTIF/context and all request/response queues must
  // also be reconstructed before complete TSI checkpointing can be enabled.
  const checkpoint_owner_t &loadmem_read_owner() const { return loadmem_read; }
  const checkpoint_owner_t &loadmem_queue_owner() const { return loadmem_queues; }
  const checkpoint_owner_t &host_control_owner() const { return host_control; }

protected:
  void idle() override;

  void reset() override;

  void load_mem_write(addr_t addr, size_t nbytes, const void *src) override;
  void load_mem_read(addr_t addr, size_t nbytes, void *dst) override;

  // This must be exactly the same as hKey.dataBits in the LoadMem widget
  // See discussion here: https://github.com/firesim/firesim/pull/1401
  // TODO: Avoid hardcoding this value here
  size_t chunk_align() override { return 8; }

private:
  firesim_loadmem_read_t loadmem_read;
  firesim_loadmem_queues_t loadmem_queues;
  firesim_tsi_host_control_t host_control;
};
#endif // __FIRESIM_TSI_H
