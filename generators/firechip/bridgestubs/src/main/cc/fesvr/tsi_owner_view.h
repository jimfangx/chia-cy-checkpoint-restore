// See LICENSE for license details.
#ifndef FIRESIM_TSI_OWNER_VIEW_H
#define FIRESIM_TSI_OWNER_VIEW_H
#include "core/checkpoint.h"
#include "tsi_thread_owner.h"
#include <type_traits>

// A retained observation reference must enforce the same access policy as its
// getter. Keep a reference to the owner slot (including optional owner slots),
// so replacement during aggregate publication does not leave a dangling view.
// Neither this view nor its process-local bindings are checkpoint payloads.
// The containing TSI must outlive its views, just as for its former raw refs.
template <class Owner> class firesim_tsi_owner_view_t final : public checkpoint_owner_t {
public:
  firesim_tsi_owner_view_t(const firesim_tsi_thread_owner_t &thread, Owner &owner)
      : thread(thread), owner(owner) {}
  firesim_tsi_owner_view_t(const firesim_tsi_owner_view_t &) = delete;
  firesim_tsi_owner_view_t &operator=(const firesim_tsi_owner_view_t &) = delete;
  std::string checkpoint_schema() const override { return get().checkpoint_schema(); }
  std::vector<uint8_t> save_checkpoint() const override { return get().save_checkpoint(); }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override {
    get().validate_checkpoint(image);
  }
  // Preserve component-level fault injection through checkpoint_owner_t. This
  // still requires the creator and does not authorize aggregate publication.
  void load_checkpoint(const std::vector<uint8_t> &image) override { get().load_checkpoint(image); }
private:
  const firesim_tsi_thread_owner_t &thread;
  Owner &owner;
  checkpoint_owner_t &get() const {
    thread.require(); // Before reading the optional slot or any owner state.
    if constexpr (std::is_base_of<checkpoint_owner_t, Owner>::value) return owner;
    else {
      if (!owner) throw std::runtime_error("TSI component owner is unavailable");
      return *owner;
    }
  }
};
#endif
