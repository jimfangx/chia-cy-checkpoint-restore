// See LICENSE for license details.
#ifndef __FIRESIM_TSI_HTIF_EXIT_H
#define __FIRESIM_TSI_HTIF_EXIT_H

#include "core/widget_checkpoint.h"

// Direct HTIF pass/fail and no-signature stop component. The installed syscall
// session, signal latch and outer caller are separate required owners. No cut
// is allowed inside a service (neither of these services may yield).
class firesim_tsi_htif_exit_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { running, requested, stopped };
  phase_t phase() const { boundary.require_idle(); return current.phase; }
  uint32_t raw_exit() const { boundary.require_idle(); return current.raw; }

  template<class Service> void request(uint64_t payload, Service service) {
    widget_checkpoint_state_t::call_t call(boundary);
    if (current.phase != phase_t::running || payload >> 48 || !(payload & 1))
      throw std::runtime_error("unsupported HTIF direct exit request");
    // Installed syscall_t stores its 48-bit payload in optional<int>. Preserve
    // the exact low 32 bits, including negative status and truncation.
    service();
    current.raw = uint32_t(payload);
    current.phase = phase_t::requested;
  }
  template<class Service> void stop(Service service) {
    widget_checkpoint_state_t::call_t call(boundary);
    if (current.phase != phase_t::requested)
      throw std::runtime_error("HTIF exit component has no owned stop request");
    service();
    current.phase = phase_t::stopped;
  }
  // This checks visible installed state; it does not own the installed signal
  // latch, optional<int>, or stopped field, and cannot admit a complete HTIF cut.
  void validate_observed(bool exiting, bool stopped, int code) const {
    boundary.require_idle();
    const int64_t signed_raw = current.raw < 0x80000000u ? int64_t(current.raw) :
                              int64_t(current.raw) - 0x100000000LL;
    const int expected = signed_raw >= 0 ? signed_raw / 2 : (signed_raw - 1) / 2;
    if (exiting != (current.phase != phase_t::running) ||
        stopped != (current.phase == phase_t::stopped) || code != expected)
      throw std::runtime_error("unowned HTIF signal/exit/stop state");
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.htif-direct-exit.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); auto out = config;
    out.word(static_cast<uint64_t>(current.phase)); out.word(current.raw);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override { current = parse(image); }

private:
  struct state_t { phase_t phase = phase_t::running; uint32_t raw = 0; } current;
  widget_checkpoint_config_t config{31, {1, 32, 0}}; // revision, installed int bits, no signature
  widget_checkpoint_state_t boundary;
  state_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const size_t start = config.bytes.size();
    if (image.size() != start + 16 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("HTIF exit configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto phase = word(start), raw = word(start+8);
    if (phase > 2 || raw > 0xffffffffu || (!phase && raw) || (phase && !(raw & 1)))
      throw std::runtime_error("incoherent HTIF direct exit phase/status");
    return {static_cast<phase_t>(phase), uint32_t(raw)};
  }
};
#endif
