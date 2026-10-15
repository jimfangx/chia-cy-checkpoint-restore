// See LICENSE for license details
#ifndef __FIRESIM_TSI_H
#define __FIRESIM_TSI_H

// Include the owned base through a normal project header before TestChip's
// system include. GCC -MMD otherwise omits this transitive ABI dependency from
// firesim_tsi/bridge objects in VCS's cached external-C Makefile.
#include "tsi.h"
#include "testchip_tsi.h"
#include "loadmem_read.h"
#include "loadmem_queues.h"
#include "tsi_host_control.h"
#include "tsi_init_accesses.h"
#include "tsi_program_loader.h"

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
  void read_chunk(addr_t address, size_t bytes, void *destination) override;
  void write_chunk(addr_t address, size_t bytes, const void *source) override;

  // Component owner only. HTIF/context and all request/response queues must
  // also be reconstructed before complete TSI checkpointing can be enabled.
  const checkpoint_owner_t &loadmem_read_owner() const { return loadmem_read; }
  const checkpoint_owner_t &loadmem_queue_owner() const { return loadmem_queues; }
  const checkpoint_owner_t &host_control_owner() const { return host_control; }
  const checkpoint_owner_t &init_accesses_owner() const { return init_control; }
  const checkpoint_owner_t &program_loader_owner() const { return program_loader; }

  // Reset/initialization component dispatcher only. These calls never resume
  // HTIF or its context. A complete CPU profile still requires their owners.
  bool advance_initialization();
  std::vector<uint8_t> save_initialization_checkpoint() const;
  void load_initialization_checkpoint(const std::vector<uint8_t> &image);

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
  firesim_tsi_program_loader_t program_loader;
  firesim_loadmem_read_t loadmem_read;
  firesim_loadmem_queues_t loadmem_queues;
  firesim_tsi_host_control_t host_control;
  firesim_tsi_init_accesses_t init_control;
  widget_checkpoint_config_t initialization_config;
  bool initialization_component_restored = false;
  static void validate_initialization(const firesim_tsi_host_control_t &host,
                                      const firesim_tsi_init_accesses_t &init,
                                      const firesim_tsi_serial_read_t &read);
  void flush_program_cache_lines(addr_t address, size_t bytes);
};
#endif // __FIRESIM_TSI_H
