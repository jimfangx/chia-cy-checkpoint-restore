// See LICENSE for license details.
#ifndef FIRESIM_TSI_HOST_WRAPPER_H
#define FIRESIM_TSI_HOST_WRAPPER_H
#include "core/widget_checkpoint.h"

// Semantic host_thread continuation. Native stacks, callbacks, root/creator
// pointers and signal masks are process-local resources, never image bytes.
class firesim_tsi_host_wrapper_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { fresh, execution, tail };
  phase_t phase() const { require_valid(); return current; }
  void enter() { require_valid(); if (current == phase_t::fresh) current = phase_t::execution; }
  void returned() {
    require_valid();
    if (current != phase_t::execution) throw std::runtime_error("TSI wrapper return outside execution");
    current = phase_t::tail;
  }
  void interrupt() noexcept { poisoned = true; }
  std::string checkpoint_schema() const override { return "firesim.tsi.host-wrapper.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    require_valid(); auto out = config; out.word(static_cast<uint64_t>(current)); return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override { current = parse(image); }
private:
  friend class firesim_tsi_context_group_t;
  void swap_state(firesim_tsi_host_wrapper_t &other) noexcept { std::swap(current, other.current); }
  phase_t current = phase_t::fresh;
  bool poisoned = false;
  widget_checkpoint_config_t config{36, {1}};
  void require_valid() const { if (poisoned) throw std::runtime_error("interrupted TSI host wrapper"); }
  phase_t parse(const std::vector<uint8_t> &image) const {
    require_valid(); const auto start = config.bytes.size();
    if (image.size() != start+8 || !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI host wrapper configuration/payload mismatch");
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[start+i]) << (8*i);
    if (value > 2) throw std::runtime_error("invalid TSI host wrapper phase");
    return static_cast<phase_t>(value);
  }
};
#endif
