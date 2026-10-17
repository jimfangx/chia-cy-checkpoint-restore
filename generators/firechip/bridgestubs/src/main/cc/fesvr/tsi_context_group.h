// See LICENSE for license details.
#ifndef FIRESIM_TSI_CONTEXT_GROUP_H
#define FIRESIM_TSI_CONTEXT_GROUP_H
#include "tsi_host_group.h"

// Restricted host-component continuation with a freshly constructed coroutine.
// Exclusive provider access and the explicit all-thread signal policy remain
// required. This is not simulator/bridge/memory or CPU checkpoint admission.
class firesim_tsi_context_group_t {
public:
  using images_t = firesim_tsi_t::polling_cut_t;
  explicit firesim_tsi_context_group_t(firesim_tsi_t &tsi) : tsi(tsi), host(tsi) {}
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    void commit() {
      if (consumed) throw std::runtime_error("TSI context candidate already committed");
      require_pristine(tsi);
      parent.commit_with([&]() noexcept {
        tsi.host_wrapper.swap_state(wrapper);
        tsi.restored_host_context = true;
      });
      consumed = true;
    }
  private:
    friend class firesim_tsi_context_group_t;
    prepared_t(firesim_tsi_t &tsi, const images_t &images)
        : tsi(tsi), parent(firesim_tsi_host_group_t(tsi).prepare(prefix(images))) {
      require_pristine(tsi);
      wrapper.load_checkpoint(images[15].second);
      firesim_tsi_host_execution_t outer; outer.load_checkpoint(images[14].second);
      require_boundary(wrapper, outer);
    }
    firesim_tsi_t &tsi;
    firesim_tsi_host_wrapper_t wrapper;
    firesim_tsi_host_group_t::prepared_t parent;
    bool consumed = false;
  };
  prepared_t prepare(const images_t &images) const { return prepared_t(tsi, images); }
  void load(const images_t &images) const { auto next = prepare(images); next.commit(); }
  images_t inspect() const {
    auto result = host.inspect();
    if (tsi.context_resume_active ||
        (!tsi.host_context_initialized() && !tsi.restored_host_context))
      throw std::runtime_error("TSI context group requires suspended source or prepared destination");
    require_boundary(tsi.host_wrapper, tsi.host_execution);
    result.emplace_back("wrapper", tsi.host_wrapper.save_checkpoint());
    return result;
  }
  bool native_context_initialized() const { return tsi.host_context_initialized(); }
  // Recreate only the audited wrapper/run_host frames. The first entry starts
  // at the restored semantic outer phase, never HTIF start/reset/program load.
  // Ordinary tick() remains disabled for metadata/component restores.
  void resume() const {
    inspect();
    if (!tsi.restored_host_context)
      throw std::runtime_error("TSI context continuation requires restored component group");
    tsi.context_resume_active = true;
    try { tsi.switch_to_host(); tsi.context_resume_active = false; }
    catch (...) { tsi.context_resume_active = false; throw; }
    inspect();
  }
private:
  firesim_tsi_t &tsi;
  firesim_tsi_host_group_t host;
  static void require_pristine(const firesim_tsi_t &tsi) {
    if (tsi.restored_host_context || tsi.context_resume_active || tsi.host_context_initialized() ||
        tsi.host_wrapper.phase() != firesim_tsi_host_wrapper_t::phase_t::fresh)
      throw std::runtime_error("TSI context destination wrapper is occupied");
  }
  static void require_boundary(const firesim_tsi_host_wrapper_t &wrapper,
                               const firesim_tsi_host_execution_t &outer) {
    using wp = firesim_tsi_host_wrapper_t::phase_t;
    using op = firesim_tsi_host_execution_t::phase_t;
    if (!((wrapper.phase() == wp::execution && outer.phase() == op::polling) ||
          (wrapper.phase() == wp::tail && outer.phase() == op::returned)))
      throw std::runtime_error("TSI wrapper/outer suspension mismatch");
  }
  static images_t prefix(const images_t &images) {
    if (images.size() != 16 || images[15].first != "wrapper")
      throw std::runtime_error("TSI context group requires sixteen ordered owners");
    return images_t(images.begin(), images.begin()+15);
  }
};
#endif
