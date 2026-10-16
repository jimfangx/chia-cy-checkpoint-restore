// See LICENSE for license details.
#ifndef FIRESIM_TSI_POLLING_LIFECYCLE_H
#define FIRESIM_TSI_POLLING_LIFECYCLE_H
#include "firesim_tsi.h"
#include "tsi_htif_lifecycle.h"

// Opt-in provider only: twelve sealed polling owners, the direct-exit
// recorder and actual HTIF exit/stopped fields. Session, descriptors, signals,
// syscall parent and outer context are still separate, unsupported owners.
// Caller must exclusively suspend the TSI, obey the lifecycle signal policy,
// and keep the TSI alive until every candidate has been destroyed.
class firesim_tsi_polling_lifecycle_t {
public:
  using images_t = firesim_tsi_t::polling_cut_t;
  explicit firesim_tsi_polling_lifecycle_t(firesim_tsi_t &tsi) : tsi(tsi) {}
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    void commit() {
      if (consumed) throw std::runtime_error("TSI polling/lifecycle candidate already committed");
      // Every allocating destination/peer check precedes the provider's final
      // signal/optional-exit/stopped guard. Publication never calls commit()
      // on another candidate, replays a service, or enters a context.
      polling.recheck();
      require_pristine_exit(tsi);
      auto publish = [&]() noexcept {
        polling.publish();
        tsi.htif_exit_component.swap_state(exit);
      };
      lifecycle.commit(publish);
      consumed = true;
    }
  private:
    friend class firesim_tsi_polling_lifecycle_t;
    prepared_t(firesim_tsi_t &tsi, const images_t &images)
        : tsi(tsi), exit(parsed_exit(images)),
          polling(tsi, protocol(images), exit.phase() == firesim_tsi_htif_exit_t::phase_t::stopped),
          lifecycle(firesim_tsi_htif_lifecycle_t(tsi).prepare_checkpoint(images.at(13).second)) {
      validate_exit(exit, lifecycle.restored_state());
      polling.require_exit_boundary(exit.phase());
      require_pristine_exit(tsi);
    }
    firesim_tsi_t &tsi;
    firesim_tsi_htif_exit_t exit;
    firesim_tsi_t::prepared_polling_components_t polling;
    firesim_tsi_htif_lifecycle_t::prepared_t lifecycle;
    bool consumed = false;
  };
  prepared_t prepare(const images_t &images) const { return prepared_t(tsi, images); }
  void load(const images_t &images) const { auto next = prepare(images); next.commit(); }

  // Explicit pending direct-exit caller continuation. Returns false at the
  // next serial-read yield, true after the actual no-signature provider stop.
  // Stopped images restore through this group for complete terminal readback;
  // tick/context admission is unchanged. Session/descriptors and coroutine
  // return remain unsupported. Restore itself never calls stop().
  bool advance_pending_exit() const {
    inspect(); // full raw provider state and signal/signature checks, before service
    if (!tsi.polling_components_prepared ||
        tsi.htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::requested)
      throw std::runtime_error("prepared exit requires a fresh requested-exit group");
    const bool stopped = tsi.advance_prepared_exit_components();
    if (stopped) inspect_completed_exit(); else inspect();
    return stopped;
  }
  images_t inspect_completed_exit() const {
    const auto state = firesim_htif_lifecycle_read(tsi);
    validate_exit(tsi.htif_exit_component, state);
    if (tsi.htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::stopped ||
        !tsi.htif_poll || tsi.htif_poll->phase() != firesim_tsi_htif_poll_t::phase_t::complete ||
        !tsi.memif_read.idle())
      throw std::runtime_error("prepared exit has not completed its owned caller");
    auto result = tsi.inspect_fresh_polling_protocol(true);
    result.emplace_back("exit", tsi.htif_exit_component.save_checkpoint());
    result.emplace_back("lifecycle", firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint());
    const auto after = firesim_htif_lifecycle_read(tsi);
    if (state.has_exit != after.has_exit || state.raw_exit != after.raw_exit || state.stopped != after.stopped)
      throw std::runtime_error("HTIF lifecycle changed during completed-exit inspection");
    return result;
  }

  // Read every owned byte before service. Requested-exit cuts are admitted
  // only at the actual queued-response read yield. The ordinary polling and
  // tick interfaces still reject exit/stop; use advance_pending_exit explicitly.
  images_t inspect() const {
    if (tsi.terminal->checkpoint_schema().empty() || !tsi.memif_read.idle())
      throw std::runtime_error("TSI polling/lifecycle requires sealed protocol and no syscall parent");
    auto state = firesim_htif_lifecycle_read(tsi);
    validate_exit(tsi.htif_exit_component, state);
    using ep = firesim_tsi_htif_exit_t::phase_t;
    if (tsi.htif_exit_component.phase() == ep::stopped ||
        (tsi.htif_exit_component.phase() == ep::requested && (!tsi.htif_poll ||
         tsi.htif_poll->phase() != firesim_tsi_htif_poll_t::phase_t::fromhost_read)))
      throw std::runtime_error("TSI aggregate lacks this exit/stop parent boundary");
    auto result = tsi.polling_components_prepared ? tsi.inspect_fresh_polling_protocol() :
                                                  tsi.inspect_live_polling_protocol();
    result.emplace_back("exit", tsi.htif_exit_component.save_checkpoint());
    result.emplace_back("lifecycle", firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint());
    // Inspection is externally suspended; detect provider changes as well as
    // the protocol owners' existing double readback.
    auto after = firesim_htif_lifecycle_read(tsi);
    if (state.has_exit != after.has_exit || state.raw_exit != after.raw_exit || state.stopped != after.stopped)
      throw std::runtime_error("HTIF lifecycle changed during aggregate inspection");
    return result;
  }
private:
  firesim_tsi_t &tsi;
  static images_t protocol(const images_t &images) {
    if (images.size() != 14 || images[12].first != "exit" || images[13].first != "lifecycle")
      throw std::runtime_error("TSI polling/lifecycle requires fourteen ordered owners");
    // The twelve-owner parser checks every protocol name and order.
    return images_t(images.begin(), images.begin()+12);
  }
  static firesim_tsi_htif_exit_t parsed_exit(const images_t &images) {
    if (images.size() != 14 || images[12].first != "exit" || images[13].first != "lifecycle")
      throw std::runtime_error("TSI polling/lifecycle requires fourteen ordered owners");
    firesim_tsi_htif_exit_t result;
    result.load_checkpoint(images[12].second);
    return result;
  }
  static void require_pristine_exit(const firesim_tsi_t &tsi) {
    if (tsi.htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::running ||
        tsi.htif_exit_component.raw_exit() != 0)
      throw std::runtime_error("TSI polling/lifecycle requires pristine direct-exit owner");
  }
  static void validate_exit(const firesim_tsi_htif_exit_t &exit, firesim_htif_lifecycle_state_t state) {
    using ep = firesim_tsi_htif_exit_t::phase_t;
    const auto phase = exit.phase();
    if (state.has_exit != (phase != ep::running) || state.raw_exit != exit.raw_exit() ||
        state.stopped != (phase == ep::stopped))
      throw std::runtime_error("TSI direct-exit/lifecycle phase or raw-status mismatch");
  }
};
#endif
