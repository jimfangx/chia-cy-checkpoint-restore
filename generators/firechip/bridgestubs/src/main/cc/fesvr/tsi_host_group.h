// See LICENSE for license details.
#ifndef FIRESIM_TSI_HOST_GROUP_H
#define FIRESIM_TSI_HOST_GROUP_H
#include "tsi_polling_syscall.h"

// Restricted sealed syscall-93 protocol, provider and explicit outer caller.
// No host_thread wrapper/context, production signal coordinator, or simulator
// state is reconstructed. Exclusive suspended-provider access is mandatory.
class firesim_tsi_host_group_t {
public:
  using images_t = firesim_tsi_t::polling_cut_t;
  explicit firesim_tsi_host_group_t(firesim_tsi_t &tsi) : tsi(tsi) { require_mode(tsi); }
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    void commit() {
      commit_with([]() noexcept {});
    }
  private:
    friend class firesim_tsi_context_group_t;
    template <class Publish> void commit_with(Publish &&extra) {
      tsi.require_target_thread();
      static_assert(noexcept(extra()), "TSI peer publication must not throw");
      if (consumed) throw std::runtime_error("TSI host candidate already committed");
      require_mode(tsi); polling.recheck(); require_pristine_outer(tsi);
      auto publish = [&]() noexcept {
        polling.publish();
        tsi.syscall_exit->current = std::move(caller.current);
        tsi.host_execution.swap_state(outer);
        extra();
      };
      lifecycle.commit(publish);
      consumed = true;
    }
    friend class firesim_tsi_host_group_t;
    prepared_t(firesim_tsi_t &tsi, const images_t &images)
        : tsi(tsi), caller(tsi, tsi.serial),
          polling(tsi, protocol(tsi, images), true, true),
          lifecycle(firesim_tsi_htif_lifecycle_t(tsi).prepare_checkpoint(images.at(13).second)) {
      require_pristine_outer(tsi);
      caller.current = caller.parse(images[12].second);
      outer.load_checkpoint(images[14].second);
      polling.require_syscall_boundary(caller, lifecycle.restored_state(), true);
      polling.require_host_boundary(outer, lifecycle.restored_state());
    }
    firesim_tsi_t &tsi;
    firesim_tsi_syscall_exit_t caller;
    firesim_tsi_host_execution_t outer;
    firesim_tsi_t::prepared_polling_components_t polling;
    firesim_tsi_htif_lifecycle_t::prepared_t lifecycle;
    bool consumed = false;
  };
  prepared_t prepare(const images_t &images) const {
    tsi.require_target_thread();
    return prepared_t(tsi, images);
  }
  void load(const images_t &images) const { auto next = prepare(images); next.commit(); }
  images_t inspect() const {
    tsi.require_target_thread();
    require_mode(tsi);
    if (!tsi.htif_poll || !tsi.bcd || !tsi.memif_read.idle() ||
        tsi.prepared_polling_service_active || tsi.prepared_polling_service_poisoned)
      throw std::runtime_error("TSI host aggregate requires suspended protocol owners");
    const auto phase = tsi.host_execution.phase();
    if (tsi.polling_components_prepared) {
      if (!tsi.metadata_prepared || tsi.metadata_poisoned || tsi.polling_active ||
          (tsi.host_context_initialized() && (!tsi.restored_host_context || !tsi.host_context_suspended())))
        throw std::runtime_error("TSI host aggregate requires fresh metadata-only destination");
    } else if (!tsi.host_context_suspended() ||
               tsi.polling_active != (phase == firesim_tsi_host_execution_t::phase_t::polling ||
                                      phase == firesim_tsi_host_execution_t::phase_t::stop)) {
      throw std::runtime_error("TSI host aggregate requires live outer suspension");
    }
    const auto provider = firesim_htif_require_lifecycle_api().read(tsi);
    firesim_tsi_t::validate_polling_components(*tsi.htif_poll, tsi.program_loader, tsi.init_control,
        tsi.host_control, tsi.serial_read, tsi.loadmem_read, tsi.loadmem_queues,
        tsi.bcd_identity, tsi.memif_write, true, true);
    firesim_tsi_t::validate_syscall_boundary(*tsi.htif_poll, *tsi.syscall_exit, provider, true);
    firesim_tsi_t::validate_host_boundary(tsi.host_execution, *tsi.htif_poll, provider);
    auto result = tsi.polling_components();
    result.emplace_back("syscall", tsi.syscall_exit->save_checkpoint());
    result.emplace_back("lifecycle", firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint());
    result.emplace_back("outer", tsi.host_execution.save_checkpoint());
    protocol(tsi, result);
    const auto after = firesim_htif_require_lifecycle_api().read(tsi);
    if (provider.has_exit != after.has_exit || provider.raw_exit != after.raw_exit ||
        provider.stopped != after.stopped || result.back().second != tsi.host_execution.save_checkpoint())
      throw std::runtime_error("TSI host aggregate changed during inspection");
    return result;
  }
  // Reach the next blocked polling child, then expose stop and return-code
  // boundaries separately. These are host operations, not target cycles.
  void advance() const {
    inspect();
    if (!tsi.polling_components_prepared || tsi.restored_host_context ||
        tsi.host_execution.phase() == firesim_tsi_host_execution_t::phase_t::returned)
      throw std::runtime_error("TSI host continuation requires unfinished fresh aggregate");
    tsi.advance_prepared_host_components();
    inspect();
  }
private:
  firesim_tsi_t &tsi;
  static void require_mode(const firesim_tsi_t &tsi) {
    tsi.require_target_thread();
    firesim_tsi_polling_syscall_t::require_mode(tsi);
  }
  static void require_pristine_outer(const firesim_tsi_t &tsi) {
    firesim_tsi_polling_syscall_t::require_pristine_caller(tsi);
    if (tsi.host_execution.phase() != firesim_tsi_host_execution_t::phase_t::startup)
      throw std::runtime_error("TSI host destination outer caller is occupied");
  }
  static images_t protocol(firesim_tsi_t &tsi, const images_t &images) {
    require_mode(tsi);
    if (images.size() != 15 || images[14].first != "outer")
      throw std::runtime_error("TSI host aggregate requires fifteen ordered owners");
    return firesim_tsi_polling_syscall_t::protocol(tsi, images_t(images.begin(), images.begin()+14));
  }
};
#endif
