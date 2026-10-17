// See LICENSE for license details
#ifndef __TSIBRIDGE_H
#define __TSIBRIDGE_H

#include "bridges/serial_data.h"
#include "core/bridge_driver.h"
#include "tsi_bridge_state.h"
#include <memory>
#include <array>
#include <thread>

class loadmem_t;
class firesim_tsi_t;
class firesim_loadmem_t;

struct TSIBRIDGEMODULE_struct {
  uint64_t in_bits;
  uint64_t in_valid;
  uint64_t in_ready;
  uint64_t out_bits;
  uint64_t out_valid;
  uint64_t out_ready;
  uint64_t step_size;
  uint64_t done;
  uint64_t start;
};

class tsibridge_t : public bridge_driver_t {
public:
  /// The identifier for the bridge type used for casts.
  static char KIND;

  tsibridge_t(simif_t &simif,
              loadmem_t &loadmem_widget,
              const TSIBRIDGEMODULE_struct &mmio_addrs,
              int tsino,
              const std::vector<std::string> &args,
              bool has_mem,
              int64_t mem_host_offset);
  ~tsibridge_t();
  virtual void init();
  virtual void tick();
  virtual bool terminate();
  virtual int exit_code();

  // Inspection of this component does not enable the bridge's unsupported
  // aggregate checkpoint contract or restore the FESVR coroutine.
  const checkpoint_owner_t &control_owner() const { return *control; }
  std::string host_component_scope() const override { return "tsi-polling"; }
  host_component_images_t inspect_host_components() const override;

  // Restricted host-component coordination, not checkpoint_owner_t admission.
  // Caller exclusively suspends the bridge, descriptor operations and other
  // argument parsers, has no active libc getopt continuation, and owns the
  // process signal policy. Dynamic HTIF devices remain unsupported.
  // Capture/prepare/commit run on the FESVR creator; only these bytes may cross
  // to VCS. The bridge must outlive every candidate.
  struct context_image_t {
    std::vector<uint8_t> metadata, control, context;
  };
  using context_build_t = std::array<uint8_t, 32>;
  context_image_t capture_restricted_context(context_build_t build) const;
  class prepared_context_t {
  public:
    ~prepared_context_t();
    prepared_context_t(const prepared_context_t &) = delete;
    prepared_context_t &operator=(const prepared_context_t &) = delete;
    void commit();
    // The coordinator holds its creator/process exclusion guards from sealing
    // through publication and readback. Sealing may allocate/throw but never
    // publishes. Publishing is single-use, allocation-free and cannot unwind a
    // partly published aggregate. These APIs do not acquire process exclusion.
    void seal_publication();
    void publish_sealed() noexcept;
  private:
    friend class tsibridge_t;
    prepared_context_t(tsibridge_t &, const context_image_t &, context_build_t);
    tsibridge_t &bridge;
    std::vector<uint8_t> pristine_control;
    std::unique_ptr<tsi_bridge_state_t> control;
    std::unique_ptr<firesim_tsi_t> tsi;
    const std::thread::id creator = std::this_thread::get_id();
    bool sealed = false;
    bool consumed = false;
  };
  std::unique_ptr<prepared_context_t>
  prepare_restricted_context(const context_image_t &image, context_build_t build);

private:
  const TSIBRIDGEMODULE_struct mmio_addrs;
  loadmem_t &loadmem_widget;

  firesim_tsi_t *fesvr = nullptr;
  bool restored_context = false;
  bool has_mem;
  // host memory offset based on the number of memory models and their size
  int64_t mem_host_offset;
  std::unique_ptr<tsi_bridge_state_t> control;
  class services_t;

  // Arguments passed to firesim_tsi.
  char **tsi_argv = nullptr;
  int tsi_argc;

  // Tell the widget to start enqueuing tokens
  void go();
  // Moves data to and from the widget and fesvr
  void send(); // FESVR -> Widget
  void recv(); // Widget -> FESVR

  // Helper functions to handoff fesvr requests to the loadmem unit
  void handle_loadmem_read(firesim_loadmem_t loadmem);
  void handle_loadmem_write(firesim_loadmem_t loadmem);
  void tsi_bypass_via_loadmem();
};

#endif // __TSIBRIDGE_H
