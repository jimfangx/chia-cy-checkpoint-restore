// See LICENSE for license details.
#ifndef FIRESIM_TSI_POLLING_SYSCALL_H
#define FIRESIM_TSI_POLLING_SYSCALL_H
#include "firesim_tsi.h"

// Restricted syscall-93 polling components. This owns no session/descriptors,
// process signal coordinator, startup/return stack or simulator state. Requires
// exclusive suspended access and the exact-provider lifecycle signal policy.
class firesim_tsi_polling_syscall_t {
public:
  using images_t = firesim_tsi_t::polling_cut_t;
  explicit firesim_tsi_polling_syscall_t(firesim_tsi_t &tsi) : tsi(tsi) { require_mode(tsi); }
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    void commit() {
      if (consumed) throw std::runtime_error("syscall polling candidate already committed");
      require_mode(tsi); polling.recheck(); require_pristine_caller(tsi);
      auto publish = [&]() noexcept {
        polling.publish();
        tsi.syscall_exit->current = std::move(caller.current);
      };
      lifecycle.commit(publish);
      consumed = true;
    }
  private:
    friend class firesim_tsi_polling_syscall_t;
    prepared_t(firesim_tsi_t &tsi, const images_t &images)
        : tsi(tsi), caller(tsi, tsi.serial),
          polling(tsi, protocol(tsi, images), true, true),
          lifecycle(firesim_tsi_htif_lifecycle_t(tsi).prepare_checkpoint(images.at(13).second)) {
      require_mode(tsi); require_pristine_caller(tsi);
      caller.current = caller.parse(images[12].second);
      polling.require_syscall_boundary(caller, lifecycle.restored_state());
    }
    firesim_tsi_t &tsi;
    firesim_tsi_syscall_exit_t caller;
    firesim_tsi_t::prepared_polling_components_t polling;
    firesim_tsi_htif_lifecycle_t::prepared_t lifecycle;
    bool consumed = false;
  };
  prepared_t prepare(const images_t &images) const { return prepared_t(tsi, images); }
  void load(const images_t &images) const { auto next = prepare(images); next.commit(); }
  images_t inspect() const {
    require_mode(tsi);
    if (!tsi.htif_poll || !tsi.bcd || !tsi.memif_read.idle() ||
        tsi.prepared_polling_service_active || tsi.prepared_polling_service_poisoned)
      throw std::runtime_error("syscall polling requires suspended complete protocol owners");
    if (tsi.polling_components_prepared) {
      if (!tsi.metadata_prepared || tsi.metadata_poisoned || tsi.host_context_initialized() ||
          tsi.polling_active || tsi.default_devices)
        throw std::runtime_error("syscall polling requires a fresh metadata-only destination");
    } else if (!tsi.polling_active || !tsi.host_context_suspended()) {
      throw std::runtime_error("syscall polling requires live target-context suspension");
    }
    const auto provider = firesim_htif_require_lifecycle_api().read(tsi);
    firesim_tsi_t::validate_polling_components(*tsi.htif_poll, tsi.program_loader, tsi.init_control,
        tsi.host_control, tsi.serial_read, tsi.loadmem_read, tsi.loadmem_queues,
        tsi.bcd_identity, tsi.memif_write, true, true);
    firesim_tsi_t::validate_syscall_boundary(*tsi.htif_poll, *tsi.syscall_exit, provider);
    auto result = tsi.polling_components();
    result.emplace_back("syscall", tsi.syscall_exit->save_checkpoint());
    result.emplace_back("lifecycle", firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint());
    protocol(tsi, result);
    const auto after = firesim_htif_require_lifecycle_api().read(tsi);
    if (provider.has_exit != after.has_exit || provider.raw_exit != after.raw_exit ||
        provider.stopped != after.stopped)
      throw std::runtime_error("syscall provider changed during inspection");
    return result;
  }
  // Resume explicit callers until a blocked read/idle or polling completion.
  // Completion does not call stop(), enter a coroutine, or recreate a session.
  void advance() const {
    inspect();
    if (!tsi.polling_components_prepared ||
        tsi.htif_poll->phase() == firesim_tsi_htif_poll_t::phase_t::complete)
      throw std::runtime_error("syscall continuation requires an unfinished fresh component group");
    tsi.advance_prepared_syscall_components();
    inspect();
  }
private:
  firesim_tsi_t &tsi;
  static void require_mode(const firesim_tsi_t &tsi) {
    if (!tsi.syscall_exit || !tsi.metadata_supported || !tsi.owned_default_devices || tsi.default_devices ||
        tsi.terminal->checkpoint_schema().empty() ||
        tsi.htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::running ||
        tsi.htif_exit_component.raw_exit())
      throw std::runtime_error("syscall polling requires restricted sealed default mode");
  }
  static void require_pristine_caller(const firesim_tsi_t &tsi) {
    tsi.syscall_exit->boundary.require_idle();
    if (tsi.syscall_exit->current.phase != firesim_tsi_syscall_exit_t::phase_t::idle)
      throw std::runtime_error("syscall polling destination caller is occupied");
  }
  static images_t protocol(firesim_tsi_t &tsi, const images_t &images) {
    require_mode(tsi);
    if (images.size() != 14 || images[12].first != "syscall" || images[13].first != "lifecycle")
      throw std::runtime_error("syscall polling requires fourteen ordered owners");
    // This restricted mode never dispatches BCD or consumes terminal bytes.
    widget_checkpoint_config_t bcd(26, {1, 1048576}); bcd.word(0);
    const auto terminal = std::find_if(tsi.metadata_pristine_components.begin(),
        tsi.metadata_pristine_components.end(), [](const auto &image) { return image.first == "terminal"; });
    if (terminal == tsi.metadata_pristine_components.end() ||
        images[8].second != bcd.bytes || images[9].second != terminal->second)
      throw std::runtime_error("syscall polling has unowned device work");
    return images_t(images.begin(), images.begin()+12);
  }
};
#endif
