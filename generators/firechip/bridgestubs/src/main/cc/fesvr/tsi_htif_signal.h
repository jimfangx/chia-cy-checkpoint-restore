// See LICENSE for license details.
#ifndef FIRESIM_TSI_HTIF_SIGNAL_H
#define FIRESIM_TSI_HTIF_SIGNAL_H
#include "core/widget_checkpoint.h"
#include "htif_signal.h"
#include <type_traits>

// Provider component only. Does not reconstruct signal-caused stop callers,
// sessions, descriptors, executable contexts or complete CPU checkpoints.
class firesim_tsi_htif_signal_t final : public checkpoint_owner_t {
public:
  explicit firesim_tsi_htif_signal_t(htif_t &htif) : htif(htif) {}
  std::string checkpoint_schema() const override { return "firesim.tsi.htif-signal.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    const auto state = firesim_htif_signal_read(htif);
    auto out = config;
    out.word(state.lifecycle.has_exit); out.word(state.lifecycle.raw_exit);
    out.word(state.lifecycle.stopped); out.word(state.delivered);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  class prepared_t {
  public:
    prepared_t(const prepared_t &) = delete;
    prepared_t &operator=(const prepared_t &) = delete;
    prepared_t(prepared_t &&) = delete;
    prepared_t &operator=(prepared_t &&) = delete;
    firesim_htif_signal_state_t restored_state() const { return state; }
    template <typename Publish> void commit(Publish &publish) {
      static_assert(std::is_nothrow_invocable<Publish &>::value,
                    "HTIF signal peer publication must be noexcept");
      if (consumed) throw std::runtime_error("HTIF signal candidate already committed");
      firesim_htif_signal_publish(htif, state, [](void *p) noexcept {
        (*static_cast<Publish *>(p))();
      }, &publish);
      consumed = true;
    }
    void commit() { auto publish = []() noexcept {}; commit(publish); }
  private:
    friend class firesim_tsi_htif_signal_t;
    prepared_t(htif_t &htif, firesim_htif_signal_state_t state) : htif(htif), state(state) {
      firesim_htif_signal_validate_restore(htif, state);
    }
    htif_t &htif;
    const firesim_htif_signal_state_t state;
    bool consumed = false;
  };
  prepared_t prepare_checkpoint(const std::vector<uint8_t> &image) const {
    return prepared_t(htif, parse(image));
  }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = prepare_checkpoint(image); next.commit();
  }
private:
  htif_t &htif;
  // revision, raw int width, exact BSD actions + blocked/no-pending policy
  widget_checkpoint_config_t config{33, {1, 32, 1}};
  firesim_htif_signal_state_t parse(const std::vector<uint8_t> &image) const {
    const auto start = config.bytes.size();
    if (image.size() != start + 32 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("HTIF signal configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto present = word(start), raw = word(start+8), stopped = word(start+16), delivered = word(start+24);
    if (present > 1 || raw > 0xffffffffu || stopped > 1 || delivered > 1 || (!present && raw))
      throw std::runtime_error("invalid HTIF signal/lifecycle fields");
    return {{bool(present), uint32_t(raw), bool(stopped)}, bool(delivered)};
  }
};
#endif
