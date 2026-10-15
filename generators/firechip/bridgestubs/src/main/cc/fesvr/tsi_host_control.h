// See LICENSE for license details.
#ifndef __TSI_HOST_CONTROL_H
#define __TSI_HOST_CONTROL_H

#include "core/widget_checkpoint.h"

// FireSim-owned coroutine control only. The FESVR caller, serial protocol,
// TestChip reset and program loader remain distinct, unsupported owners.
// Each transition completes before switch_to_target() can suspend the caller.
class firesim_tsi_host_control_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { ready, idle, reset_wait, reset_child };
  phase_t current_phase() const { require_usable(); return phase; }
  bool loaded_in_target() const { require_usable(); return target_loaded; }
  void swap_state(firesim_tsi_host_control_t &other) noexcept {
    std::swap(phase, other.phase); std::swap(remaining, other.remaining);
    std::swap(is_busy, other.is_busy); std::swap(host_loaded, other.host_loaded);
    std::swap(target_loaded, other.target_loaded);
  }
  explicit firesim_tsi_host_control_t(uint64_t idle_count)
      : config(18, {idle_count}), idle_count(idle_count) {}

  bool busy() const { require_usable(); return is_busy; }
  bool loaded_in_host() const { require_usable(); return host_loaded; }
  void set_loaded_in_target(bool value) { require_usable(); target_loaded = value; }

  void begin_idle() {
    require_ready();
    phase = phase_t::idle;
    remaining = idle_count;
    is_busy = false;
  }
  // True requests exactly one original switch_to_target(). The caller's next
  // invocation follows that switch's return, including the final idle yield.
  bool advance_idle() {
    require_phase(phase_t::idle);
    if (remaining) { --remaining; return true; }
    is_busy = true;
    phase = phase_t::ready;
    return false;
  }
  void begin_reset() {
    require_ready();
    host_loaded = true;
    phase = phase_t::reset_wait;
  }
  bool advance_reset() {
    require_phase(phase_t::reset_wait);
    if (!target_loaded) return true;
    phase = phase_t::reset_child;
    return false;
  }
  void finish_reset() {
    require_phase(phase_t::reset_child);
    phase = phase_t::ready;
  }
  // An escaping switch/child exception leaves an unowned interrupted caller.
  // Such an instance cannot publish or accept even this component's image.
  void interrupt() noexcept { interrupted = true; }

  std::string checkpoint_schema() const override {
    return "firesim.tsi.host-control.v1";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    require_usable();
    auto result = config;
    result.word(static_cast<uint64_t>(phase));
    result.word(remaining);
    result.word(uint64_t(is_busy) | (uint64_t(host_loaded) << 1) |
                (uint64_t(target_loaded) << 2));
    return std::move(result.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override {
    parse(image);
  }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    const auto next = parse(image);
    // All validation precedes the first assignment; no callbacks, coroutine
    // advancement, memory allocation, MMIO or serial traffic during commit.
    phase = next.phase;
    remaining = next.remaining;
    is_busy = next.flags & 1;
    host_loaded = next.flags & 2;
    target_loaded = next.flags & 4;
  }

private:
  widget_checkpoint_config_t config;
  const uint64_t idle_count;
  phase_t phase = phase_t::ready;
  uint64_t remaining = 0;
  bool is_busy = false, host_loaded = false, target_loaded = false;
  bool interrupted = false;
  struct candidate_t { phase_t phase; uint64_t remaining, flags; };
  void require_usable() const {
    if (interrupted) throw std::runtime_error("interrupted TSI host control");
  }
  void require_phase(phase_t expected) const {
    require_usable();
    if (phase != expected) throw std::runtime_error("TSI host control phase mismatch");
  }
  void require_ready() const { require_phase(phase_t::ready); }
  candidate_t parse(const std::vector<uint8_t> &image) const {
    require_usable();
    if (image.size() != config.bytes.size() + 24 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI host control configuration/payload mismatch");
    auto word = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i)
        value |= uint64_t(image[offset + i]) << (8 * i);
      return value;
    };
    const auto p = word(config.bytes.size());
    const auto count = word(config.bytes.size() + 8);
    const auto flags = word(config.bytes.size() + 16);
    if (p > static_cast<uint64_t>(phase_t::reset_child) || flags & ~uint64_t(7) ||
        (p == 1 && (count > idle_count || (flags & 1))) ||
        (p != 1 && count) || (p >= 2 && !(flags & 2)))
      throw std::runtime_error("invalid TSI host control phase/cursor/flags");
    return {static_cast<phase_t>(p), count, flags};
  }
};
#endif
