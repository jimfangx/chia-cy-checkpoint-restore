// See LICENSE for license details.
#ifndef FIRESIM_TSI_HTIF_LIFECYCLE_H
#define FIRESIM_TSI_HTIF_LIFECYCLE_H
#include "core/widget_checkpoint.h"
#include "htif_lifecycle.h"

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
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    const auto state = parse(image);
    firesim_htif_lifecycle_restore(htif, state);
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
