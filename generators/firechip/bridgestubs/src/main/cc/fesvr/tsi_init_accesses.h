// See LICENSE for license details.
#ifndef __FIRESIM_TSI_INIT_ACCESSES_H
#define __FIRESIM_TSI_INIT_ACCESSES_H

#include "core/widget_checkpoint.h"
#include <limits>

// TestChip reset's ordered caller and persistent child buffers. Child serial,
// cache-flush and HTIF/context owners are independent; this does not enable a
// complete TSI checkpoint. No pointer, callback or coroutine stack is saved.
class firesim_tsi_init_accesses_t final : public checkpoint_owner_t {
public:
  struct access_t { uint64_t address; uint32_t data; bool store; };
  enum class phase_t : uint64_t {
    idle, ready, read_child, read_return, write_child, write_return,
    msip_child, msip_return, complete
  };
  phase_t phase() const { usable(); return state.phase; }
  uint32_t pending_read_data() const {
    require_phase(phase_t::read_child); return state.data;
  }
  void swap_state(firesim_tsi_init_accesses_t &other) noexcept {
    std::swap(state, other.state);
  }
  firesim_tsi_init_accesses_t(std::vector<access_t> accesses, bool msip)
      : accesses(std::move(accesses)), msip(msip),
        config(21, {uint64_t(msip), this->accesses.size()}) {
    for (const auto &a : this->accesses) {
      config.word(a.address); config.word(a.data); config.word(a.store);
    }
  }
  void begin() {
    usable();
    if (state.phase != phase_t::idle && state.phase != phase_t::complete)
      throw std::runtime_error("TSI initialization already pending");
    state = {phase_t::ready, 0, 0};
  }
  // Select once before entering the child. Returning from a restored child
  // requires explicit caller reconstruction, not another select/issue.
  phase_t select() {
    require_phase(phase_t::ready);
    if (state.index < accesses.size()) {
      const auto &a = accesses[state.index];
      state.phase = a.store ? phase_t::write_child : phase_t::read_child;
      state.data = a.store ? a.data : 0;
    } else {
      state.phase = msip ? phase_t::msip_child : phase_t::complete;
      state.data = msip ? 1 : 0;
    }
    return state.phase;
  }
  uint64_t address() const {
    usable();
    if (state.phase == phase_t::read_child || state.phase == phase_t::read_return ||
        state.phase == phase_t::write_child || state.phase == phase_t::write_return)
      return accesses[state.index].address;
    if (state.phase == phase_t::msip_child || state.phase == phase_t::msip_return)
      return 0x2000000;
    throw std::runtime_error("no selected TSI initialization access");
  }
  uint32_t *read_destination() {
    require_phase(phase_t::read_child); return &state.data;
  }
  const uint32_t *write_source() const {
    usable();
    if (state.phase != phase_t::write_child && state.phase != phase_t::msip_child)
      throw std::runtime_error("no selected TSI initialization write");
    return &state.data;
  }
  uint32_t read_result() const {
    require_phase(phase_t::read_return); return state.data;
  }
  uint32_t write_result() const {
    require_phase(phase_t::write_return); return state.data;
  }
  void child_returned() {
    usable();
    switch (state.phase) {
    case phase_t::read_child: state.phase = phase_t::read_return; break;
    case phase_t::write_child: state.phase = phase_t::write_return; break;
    case phase_t::msip_child: state.phase = phase_t::msip_return; break;
    default: throw std::runtime_error("TSI initialization child is not pending");
    }
  }
  void retire() {
    usable();
    if (state.phase == phase_t::read_return || state.phase == phase_t::write_return) {
      ++state.index; state.phase = phase_t::ready;
    } else if (state.phase == phase_t::msip_return) {
      state.phase = phase_t::complete;
    } else throw std::runtime_error("TSI initialization child has not returned");
    state.data = 0;
  }
  void interrupt() noexcept { interrupted = true; }
  std::string checkpoint_schema() const override { return "firesim.tsi.init-accesses.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    usable(); auto result = config;
    result.word(static_cast<uint64_t>(state.phase));
    result.word(state.index); result.word(state.data);
    return std::move(result.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    // Fixed-size commit after full configuration/phase/cursor/data validation.
    // No services, context switch, allocation or target edge during commit.
    state = parse(image);
  }
private:
  const std::vector<access_t> accesses;
  const bool msip;
  widget_checkpoint_config_t config;
  struct state_t { phase_t phase; uint64_t index; uint32_t data; };
  state_t state{phase_t::idle, 0, 0};
  bool interrupted = false;
  void usable() const {
    if (interrupted) throw std::runtime_error("interrupted TSI initialization caller");
  }
  void require_phase(phase_t expected) const {
    usable();
    if (state.phase != expected) throw std::runtime_error("TSI initialization phase mismatch");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    usable(); const auto start = config.bytes.size();
    if (image.size() != start + 24 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI initialization configuration/payload mismatch");
    auto word = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[offset+i]) << (8*i);
      return value;
    };
    const auto phase = word(start), index = word(start+8), data = word(start+16);
    if (phase > 8 || index > accesses.size() || data > std::numeric_limits<uint32_t>::max())
      throw std::runtime_error("invalid TSI initialization phase/cursor/data");
    const auto p = static_cast<phase_t>(phase);
    if ((p == phase_t::idle && (index || data)) ||
        ((p == phase_t::ready || p == phase_t::complete) && data) ||
        (p == phase_t::complete && index != accesses.size()) ||
        (phase >= 2 && phase <= 5 && (index == accesses.size() ||
          accesses[index].store != (phase >= 4) ||
          (phase >= 4 && data != accesses[index].data))) ||
        ((p == phase_t::msip_child || p == phase_t::msip_return) &&
          (!msip || index != accesses.size() || data != 1)))
      throw std::runtime_error("inconsistent TSI initialization state");
    return {p, index, uint32_t(data)};
  }
};
#endif
