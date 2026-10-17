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
#include "tsi_htif_poll.h"
#include "tsi_htif_exit.h"
#include "tsi_startup_metadata.h"
#include "tsi_bcd.h"
#include "tsi_memif_write.h"
#include "tsi_memif_read.h"
#include "tsi_bcd_identity.h"
#include "tsi_syscall_exit.h"
#include "tsi_host_execution.h"
#include <memory>

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

  bool busy() { require_target_thread(); return host_control.busy(); };
  bool loaded_in_host() { require_target_thread(); return host_control.loaded_in_host(); };
  void set_loaded_in_target(bool loaded) { require_target_thread(); host_control.set_loaded_in_target(loaded); };

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
  memif_t &memif() override { require_target_thread(); return runtime_memif; }

  // Component owner only. HTIF/context and all request/response queues must
  // also be reconstructed before complete TSI checkpointing can be enabled.
  const checkpoint_owner_t &loadmem_read_owner() const { require_target_thread(); return loadmem_read_view; }
  const checkpoint_owner_t &loadmem_queue_owner() const { require_target_thread(); return loadmem_queues_view; }
  const checkpoint_owner_t &host_control_owner() const { require_target_thread(); return host_control_view; }
  const checkpoint_owner_t &init_accesses_owner() const { require_target_thread(); return init_control_view; }
  const checkpoint_owner_t &program_loader_owner() const { require_target_thread(); return program_loader_view; }
  // Component observation only; no coroutine or complete HTIF admission.
  const checkpoint_owner_t &host_execution_owner() const { require_target_thread(); return host_execution_view; }
  const checkpoint_owner_t &htif_poll_owner() const {
    require_target_thread();
    if (!htif_poll) throw std::runtime_error("HTIF polling has not started or uses unsupported devices");
    return htif_poll_view;
  }
  const checkpoint_owner_t &bcd_owner() const {
    require_target_thread();
    if (!bcd) throw std::runtime_error("default HTIF BCD has not started");
    return bcd_view;
  }
  const checkpoint_owner_t &terminal_owner() const { require_target_thread(); return terminal_view; }
  // Independent write child only; its device/HTIF caller is not restored.
  const checkpoint_owner_t &memif_write_owner() const { require_target_thread(); return memif_write_view; }
  const checkpoint_owner_t &memif_read_owner() const { require_target_thread(); return memif_read_view; }
  const checkpoint_owner_t &bcd_identity_owner() const { require_target_thread(); return bcd_identity_view; }
  const checkpoint_owner_t &syscall_exit_owner() const {
    require_target_thread();
    if (!syscall_exit) throw std::runtime_error("restricted syscall mode is disabled");
    return syscall_exit_view;
  }
  // Direct pass/fail and no-signature stop only. This never restores the
  // installed session/signal/exit fields or certifies a complete HTIF cut.
  std::vector<uint8_t> save_htif_exit_component() const;

  // Reset/initialization component dispatcher only. These calls never resume
  // HTIF or its context. A complete CPU profile still requires their owners.
  bool advance_initialization();
  std::vector<uint8_t> save_initialization_checkpoint() const;
  void load_initialization_checkpoint(const std::vector<uint8_t> &image);

  // Read-only images of the eight protocol components, plus BCD and terminal
  // in sealed mode, at an
  // externally suspended steady-state poll. This is an audit, not a complete
  // HTIF/TSI image: metadata, devices, contexts and RTL remain unowned.
  using polling_cut_t = std::vector<std::pair<std::string, std::vector<uint8_t>>>;
  polling_cut_t inspect_polling_cut() const;

  // Twelve known sealed polling components only. Requires metadata-only preparation in
  // a fresh caller and a sealed terminal. This does not restore syscall,
  // signal, exit or context state and must not enable HTIF/CPU continuation.
  void prepare_polling_components(const polling_cut_t &images);
  // Destination-bound preparation without publication. All images are parsed
  // and owned by the candidate; commit rechecks the fresh destination before
  // nonthrowing publication. The suspended TSI must outlive its candidate.
  class prepared_polling_components_t {
  public:
    ~prepared_polling_components_t();
    prepared_polling_components_t(const prepared_polling_components_t &) = delete;
    prepared_polling_components_t &operator=(const prepared_polling_components_t &) = delete;
    prepared_polling_components_t(prepared_polling_components_t &&) = delete;
    prepared_polling_components_t &operator=(prepared_polling_components_t &&) = delete;
    void commit();
  private:
    friend class firesim_tsi_t;
    friend class firesim_tsi_polling_lifecycle_t;
    friend class firesim_tsi_polling_syscall_t;
    friend class firesim_tsi_host_group_t;
    struct state_t;
    explicit prepared_polling_components_t(firesim_tsi_t &tsi, const polling_cut_t &images,
                                           bool completed_exit = false, bool syscall = false);
    void recheck();
    void publish() noexcept;
    void require_exit_boundary(firesim_tsi_htif_exit_t::phase_t phase) const;
    void require_syscall_boundary(const firesim_tsi_syscall_exit_t &caller,
                                 firesim_htif_lifecycle_state_t provider,
                                 bool completed_stop = false) const;
    void require_host_boundary(const firesim_tsi_host_execution_t &outer,
                               firesim_htif_lifecycle_state_t provider) const;
    std::unique_ptr<state_t> state;
  };
  prepared_polling_components_t prepare_polling_components_candidate(const polling_cut_t &images);
  polling_cut_t inspect_prepared_polling_components() const;
  // Explicit component service, not tick()/complete HTIF admission. Resume
  // until the next serial-read or idle yield, with no context/start/reset.
  // Sealed BCD read/write and identity commands only. The identity caller and
  // its read/merge/write child are explicit owners. Syscall, exit,
  // signals and other devices fail closed before clearing tohost.
  void advance_prepared_polling_components();

  // Startup metadata component only; does not restore devices or a caller.
  std::vector<uint8_t> save_startup_metadata() const;
  void prepare_startup_metadata(const std::vector<uint8_t> &image);

protected:
  int run_host() override;
  void validate_host_entry() const override;
  void idle() override;

  void reset() override;
  std::map<std::string, uint64_t> load_payload(const std::string &payload,
                                             reg_t *entry, reg_t offset) override;
  bool is_address_preloaded(addr_t, size_t) override { return preparing_metadata; }

  void load_mem_write(addr_t addr, size_t nbytes, const void *src) override;
  void load_mem_read(addr_t addr, size_t nbytes, void *dst) override;

  // This must be exactly the same as hKey.dataBits in the LoadMem widget
  // See discussion here: https://github.com/firesim/firesim/pull/1401
  // TODO: Avoid hardcoding this value here
  size_t chunk_align() override { return 8; }

private:
  friend class firesim_tsi_polling_lifecycle_t;
  friend class firesim_tsi_polling_syscall_t;
  friend class firesim_tsi_host_group_t;
  friend class firesim_tsi_context_group_t;
  bool restored_host_context = false;
  bool context_resume_active = false;
  static void validate_host_boundary(const firesim_tsi_host_execution_t &outer,
      const firesim_tsi_htif_poll_t &poll, firesim_htif_lifecycle_state_t provider);
  void advance_prepared_host_components();
  polling_cut_t inspect_live_polling_protocol() const;
  polling_cut_t inspect_fresh_polling_protocol(bool completed_exit = false) const;
  // Only the guarded lifecycle group may finish an already requested exit.
  // No startup, device dispatch, session reconstruction or context entry.
  bool advance_prepared_exit_components();
  // Installed syscall_t retains the virtual memif() result when the default
  // session is constructed. Its caller/descriptor state remains unowned.
  class runtime_memif_t final : public memif_t {
  public:
    explicit runtime_memif_t(firesim_tsi_t &tsi) : memif_t(&tsi), tsi(tsi) {}
    void read(addr_t address, size_t bytes, void *destination) override;
  private:
    firesim_tsi_t &tsi;
  } runtime_memif;
  void read_runtime_memif(addr_t address, size_t bytes, void *destination);
  // These upstream objects allocate tables/handlers and duplicate host file
  // descriptors. A coroutine stack may be discarded without unwinding, so
  // their process-local lifetime must belong to the TSI object. This is not
  // a semantic device checkpoint: terminal/filesystem state remains unowned.
  struct default_devices_t {
    syscall_t syscall;
    device_list_t list;
    default_devices_t(htif_t &htif, device_t &bcd) : syscall(&htif) {
      list.register_device(&syscall);
      list.register_device(&bcd);
    }
  };
  bool owned_default_devices;
  std::unique_ptr<firesim_tsi_terminal_t> terminal;
  bool polling_active = false;
  firesim_tsi_host_execution_t host_execution;
  std::unique_ptr<firesim_tsi_htif_poll_t> htif_poll;
  std::unique_ptr<firesim_tsi_bcd_t> bcd;
  // Destroy the table/syscall before the devices and polling callback owner.
  std::unique_ptr<default_devices_t> default_devices;
  firesim_tsi_htif_exit_t htif_exit_component;
  // Explicit opt-in syscall-93 dispatch. Ordinary installed sessions retain
  // their existing syscall path; this caller never owns session/descriptors.
  std::unique_ptr<firesim_tsi_syscall_exit_t> syscall_exit;
  firesim_tsi_program_loader_t program_loader;
  firesim_tsi_memif_write_t memif_write;
  firesim_tsi_memif_read_t memif_read;
  firesim_tsi_bcd_identity_t bcd_identity;
  firesim_loadmem_read_t loadmem_read;
  firesim_loadmem_queues_t loadmem_queues;
  firesim_tsi_host_control_t host_control;
  firesim_tsi_init_accesses_t init_control;
  widget_checkpoint_config_t initialization_config;
  bool initialization_component_restored = false;
  std::vector<std::string> metadata_arguments;
  bool metadata_supported = false;
  bool preparing_metadata = false;
  bool metadata_prepared = false;
  bool metadata_poisoned = false;
  bool polling_components_prepared = false;
  bool prepared_polling_service_active = false;
  bool prepared_polling_service_poisoned = false;
  class polling_services_t;
  class host_execution_services_t;
  firesim_tsi_startup_metadata_t startup_metadata;
  polling_cut_t metadata_pristine_components;
  polling_cut_t metadata_components() const;
  uint64_t metadata_revision() const { return terminal->checkpoint_schema().empty() ? 3 : 4; }
  std::vector<uint8_t> metadata_configuration(unsigned required_xlen) const;
  unsigned preflight_startup_metadata(const firesim_tsi_startup_metadata_t &candidate);
  void check_startup_metadata() const;
  polling_cut_t polling_components() const;
  void require_pristine_polling_destination();
  static void validate_polling_components(const firesim_tsi_htif_poll_t &poll,
      const firesim_tsi_program_loader_t &program, const firesim_tsi_init_accesses_t &init,
      const firesim_tsi_host_control_t &host, const firesim_tsi_serial_read_t &read,
      const firesim_loadmem_read_t &loadread, const firesim_loadmem_queues_t &queues,
      const firesim_tsi_bcd_identity_t &identity, const firesim_tsi_memif_write_t &writer,
      bool completed_exit = false, bool syscall = false);
  static void validate_initialization(const firesim_tsi_host_control_t &host,
                                      const firesim_tsi_init_accesses_t &init,
                                      const firesim_tsi_serial_read_t &read);
  // Stable checked views follow owner slots across atomic publication.
  firesim_tsi_owner_view_t<firesim_loadmem_read_t> loadmem_read_view{target_thread_policy(), loadmem_read};
  firesim_tsi_owner_view_t<firesim_loadmem_queues_t> loadmem_queues_view{target_thread_policy(), loadmem_queues};
  firesim_tsi_owner_view_t<firesim_tsi_host_control_t> host_control_view{target_thread_policy(), host_control};
  firesim_tsi_owner_view_t<firesim_tsi_init_accesses_t> init_control_view{target_thread_policy(), init_control};
  firesim_tsi_owner_view_t<firesim_tsi_program_loader_t> program_loader_view{target_thread_policy(), program_loader};
  firesim_tsi_owner_view_t<firesim_tsi_host_execution_t> host_execution_view{target_thread_policy(), host_execution};
  firesim_tsi_owner_view_t<std::unique_ptr<firesim_tsi_htif_poll_t>> htif_poll_view{target_thread_policy(), htif_poll};
  firesim_tsi_owner_view_t<std::unique_ptr<firesim_tsi_bcd_t>> bcd_view{target_thread_policy(), bcd};
  firesim_tsi_owner_view_t<std::unique_ptr<firesim_tsi_terminal_t>> terminal_view{target_thread_policy(), terminal};
  firesim_tsi_owner_view_t<firesim_tsi_memif_write_t> memif_write_view{target_thread_policy(), memif_write};
  firesim_tsi_owner_view_t<firesim_tsi_memif_read_t> memif_read_view{target_thread_policy(), memif_read};
  firesim_tsi_owner_view_t<firesim_tsi_bcd_identity_t> bcd_identity_view{target_thread_policy(), bcd_identity};
  firesim_tsi_owner_view_t<std::unique_ptr<firesim_tsi_syscall_exit_t>> syscall_exit_view{target_thread_policy(), syscall_exit};
  void flush_program_cache_lines(addr_t address, size_t bytes);
  void write_identity(uint64_t address, const firesim_tsi_bcd_t::identity_t &bytes);
  bool dispatch_identity(uint64_t command);
  bool dispatch_syscall_exit(uint64_t command);
  void advance_prepared_syscall_components();
  static void validate_syscall_boundary(const firesim_tsi_htif_poll_t &poll,
      const firesim_tsi_syscall_exit_t &caller, firesim_htif_lifecycle_state_t provider,
      bool completed_stop = false);
};
#endif // __FIRESIM_TSI_H
