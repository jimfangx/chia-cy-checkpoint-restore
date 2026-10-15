// See LICENSE for license details.
#ifndef __FIRESIM_TSI_PROGRAM_LOADER_H
#define __FIRESIM_TSI_PROGRAM_LOADER_H

#include "core/widget_checkpoint.h"

// TestChip's load_program entry/return and transport selection. ELF/memif and
// HTIF callers are separate owners: this image cannot resume their stacks.
class firesim_tsi_program_loader_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { unstarted, initial_yield, loading, complete };
  firesim_tsi_program_loader_t(bool has_loadmem, uint64_t cache_flush_address)
      : config(23, {uint64_t(has_loadmem), cache_flush_address}),
        has_loadmem(has_loadmem), flush_address(cache_flush_address) {}

  phase_t phase() const { require_usable(); return current; }
  bool loadmem_mode() const { require_usable(); return current == phase_t::loading && has_loadmem; }
  uint64_t cache_flush_address() const { require_usable(); return flush_address; }
  void begin() {
    require_usable();
    if (current != phase_t::unstarted && current != phase_t::complete)
      throw std::runtime_error("TSI program loader already active");
    current = phase_t::initial_yield;
  }
  void enter() { transition(phase_t::initial_yield, phase_t::loading); }
  void finish() { transition(phase_t::loading, phase_t::complete); }
  void interrupt() noexcept { interrupted = true; }
  std::string checkpoint_schema() const override { return "firesim.tsi.program-loader.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    require_usable(); auto image = config; image.word(static_cast<uint64_t>(current));
    return std::move(image.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override { current = parse(image); }

private:
  widget_checkpoint_config_t config;
  const bool has_loadmem;
  const uint64_t flush_address;
  phase_t current = phase_t::unstarted;
  bool interrupted = false;
  void require_usable() const {
    if (interrupted) throw std::runtime_error("interrupted TSI program loader");
  }
  void transition(phase_t before, phase_t after) {
    require_usable();
    if (current != before) throw std::runtime_error("TSI program loader phase mismatch");
    current = after;
  }
  phase_t parse(const std::vector<uint8_t> &image) const {
    require_usable(); const size_t start = config.bytes.size();
    if (image.size() != start + 8 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI program loader configuration/payload mismatch");
    uint64_t phase = 0;
    for (unsigned i = 0; i < 8; ++i) phase |= uint64_t(image[start+i]) << (8*i);
    if (phase > static_cast<uint64_t>(phase_t::complete))
      throw std::runtime_error("invalid TSI program loader phase");
    return static_cast<phase_t>(phase);
  }
};
#endif
