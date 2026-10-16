// See LICENSE for license details.
#ifndef FIRESIM_TSI_HTIF_LIFECYCLE_H
#define FIRESIM_TSI_HTIF_LIFECYCLE_H
#include "core/widget_checkpoint.h"
#include "htif_lifecycle.h"
#include <type_traits>

// Component adapter for actual provider exitcode/stopped storage. Does not
// restore the direct-exit recorder, caller, session, descriptors or signals.
class firesim_tsi_htif_lifecycle_t final : public checkpoint_owner_t {
public:
  explicit firesim_tsi_htif_lifecycle_t(htif_t &htif) : htif(htif) {}
  std::string checkpoint_schema() const override { return "firesim.tsi.htif-lifecycle.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    auto state = firesim_htif_lifecycle_read(htif);
    auto out = config;
    out.word(state.has_exit); out.word(state.raw_exit); out.word(state.stopped);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  // A destination-bound, single-use candidate. The HTIF destination must
  // outlive it. Preparation and final publication both check actual provider
  // state; validate_checkpoint above remains a format-only interface.
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    template <typename Publish> void commit(Publish &publish_peers) {
      static_assert(std::is_nothrow_invocable<Publish &>::value,
                    "lifecycle peer publication must be noexcept");
      if (consumed) throw std::runtime_error("HTIF lifecycle candidate already committed");
      firesim_htif_lifecycle_publish(htif, state, [](void *p) noexcept {
        (*static_cast<Publish *>(p))();
      }, &publish_peers);
      consumed = true;
    }
    void commit() { auto publish = []() noexcept {}; commit(publish); }
  private:
    friend class firesim_tsi_htif_lifecycle_t;
    prepared_t(htif_t &htif, firesim_htif_lifecycle_state_t state) : htif(htif), state(state) {
      firesim_htif_lifecycle_validate_restore(htif, state);
    }
    htif_t &htif;
    const firesim_htif_lifecycle_state_t state;
    bool consumed = false;
  };
  prepared_t prepare_checkpoint(const std::vector<uint8_t> &image) const {
    return prepared_t(htif, parse(image));
  }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = prepare_checkpoint(image);
    next.commit();
  }
private:
  htif_t &htif;
  widget_checkpoint_config_t config{32, {1, 32, 0}}; // revision, int bits, no signature/signals
  firesim_htif_lifecycle_state_t parse(const std::vector<uint8_t> &image) const {
    const auto start = config.bytes.size();
    if (image.size() != start + 24 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("HTIF lifecycle configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    auto present = word(start), raw = word(start+8), stopped = word(start+16);
    if (present > 1 || raw > 0xffffffffu || stopped > 1 || (!present && raw))
      throw std::runtime_error("invalid HTIF lifecycle fields");
    return {bool(present), uint32_t(raw), bool(stopped)};
  }
};
#endif
