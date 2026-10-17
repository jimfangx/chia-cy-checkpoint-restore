// See LICENSE for license details.
#ifndef FIRESIM_TSI_HOST_EXECUTION_H
#define FIRESIM_TSI_HOST_EXECUTION_H
#include "core/widget_checkpoint.h"

// Pointer-free run_host caller. Startup, polling children, installed stop/exit,
// the host_thread wrapper and its context remain separate owners. A component
// restore alone must never authorize tick() or reconstruct a coroutine stack.
class firesim_tsi_host_execution_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { startup, polling, stop, return_code, returned };
  enum class result_t { progress, blocked, complete };
  class services_t {
  public:
    virtual ~services_t() = default;
    virtual void start() = 0;
    virtual result_t poll() = 0;
    virtual void stop() = 0;
    virtual int exit_code() = 0;
  };
  phase_t phase() const { boundary.require_idle(); return current.phase; }
  int exit_code() const {
    boundary.require_idle();
    if (current.phase != phase_t::returned)
      throw std::runtime_error("TSI outer return value is not available");
    return decode(current.raw);
  }
  result_t advance(services_t &s) {
    // A yielding startup or a nested ordinary device still has stack state.
    // Inspection/reentry/restore during any service rejects, and an escaping
    // exception poisons this owner permanently.
    widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::startup: s.start(); current.phase = phase_t::polling; break;
    case phase_t::polling: {
      const auto result = s.poll();
      if (result == result_t::blocked) return result;
      if (result == result_t::complete) current.phase = phase_t::stop;
      break;
    }
    case phase_t::stop: s.stop(); current.phase = phase_t::return_code; break;
    case phase_t::return_code:
      current.raw = static_cast<uint32_t>(s.exit_code());
      current.phase = phase_t::returned;
      return result_t::complete;
    case phase_t::returned: return result_t::complete;
    }
    return result_t::progress;
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.host-execution.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); auto out = config;
    out.word(static_cast<uint64_t>(current.phase)); out.word(current.raw);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override { current = parse(image); }
private:
  static_assert(sizeof(int) == 4, "TSI outer exit ABI requires 32-bit int");
  struct state_t { phase_t phase = phase_t::startup; uint32_t raw = 0; } current;
  widget_checkpoint_config_t config{35, {1, 32}};
  widget_checkpoint_state_t boundary;
  static int decode(uint32_t raw) {
    return raw < 0x80000000u ? int(raw) : int(int64_t(raw) - 0x100000000LL);
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const size_t start = config.bytes.size();
    if (image.size() != start + 16 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI host execution configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto p = word(start), raw = word(start+8);
    if (p > 4 || raw > 0xffffffffu || (p != 4 && raw))
      throw std::runtime_error("incoherent TSI outer phase/return value");
    return {static_cast<phase_t>(p), uint32_t(raw)};
  }
};
#endif
