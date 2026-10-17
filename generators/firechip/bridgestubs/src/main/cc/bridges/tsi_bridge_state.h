// See LICENSE for license details.
#ifndef __TSI_BRIDGE_STATE_H
#define __TSI_BRIDGE_STATE_H

#include "core/widget_checkpoint.h"

// Host control only. FESVR/HTIF, serial queues, loadmem and generated bridge
// RTL are separate owners. This must never authorize aggregate TSI restore.
class tsi_bridge_state_t final : public checkpoint_owner_t {
public:
  class services_t {
  public:
    virtual ~services_t() = default;
    virtual void create() = 0;
    virtual void write_step(uint32_t step) = 0;
    virtual void loaded_in_target() = 0;
    virtual void go() = 0;
    virtual bool done() = 0;
    virtual void receive() = 0;
    virtual bool data_available() = 0;
    virtual void advance() = 0;
    virtual bool requests_pending() = 0;
    virtual void bypass() = 0;
    virtual bool terminated() = 0;
    virtual void send() = 0;
    virtual bool loaded_in_host() = 0;
  };

  tsi_bridge_state_t(widget_checkpoint_config_t identity, uint32_t step,
                     uint32_t loading_step, uint32_t wait, bool fast)
      : config(std::move(identity)), step(step), loading_step(loading_step),
        initial_wait(wait), initial_fast(fast), wait_remaining(wait), fast(fast) {
    config.word(step);
    config.word(loading_step);
    config.word(wait);
    config.word(fast);
  }

  void initialize(services_t &io) {
    boundary.require_idle();
    if (initialized)
      throw std::runtime_error("TSI bridge already initialized");
    widget_checkpoint_state_t::call_t call(boundary);
    io.create();
    io.write_step(fast ? loading_step : step);
    if (!fast)
      io.loaded_in_target();
    io.go();
    initialized = true;
  }

  void tick(services_t &io) {
    boundary.require_idle();
    require_initialized();
    widget_checkpoint_state_t::call_t call(boundary);
    if (!io.done())
      return;
    if (wait_remaining) {
      --wait_remaining;
      io.go();
      return;
    }
    io.receive();
    if (!io.data_available())
      io.advance();
    if (io.requests_pending())
      io.bypass();
    if (!io.terminated()) {
      io.send();
      if (fast && io.loaded_in_host() && !io.data_available()) {
        io.loaded_in_target();
        io.write_step(step);
        fast = false;
      }
      io.go();
    }
  }

  // Guard public bridge status queries too. The tick service calls FESVR
  // directly rather than recursively invoking these public bridge methods.
  template <typename F> auto query(F callback) -> decltype(callback()) {
    boundary.require_idle();
    require_initialized();
    widget_checkpoint_state_t::call_t call(boundary);
    return callback();
  }

  std::string checkpoint_schema() const override {
    return "firesim.tsi.bridge-control.v1";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle();
    auto image = config;
    image.word(wait_remaining);
    image.word(uint64_t(initialized) | (uint64_t(fast) << 1));
    return std::move(image.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override {
    parse(image);
  }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    const auto next = parse(image);
    // No allocation, callbacks, FESVR construction, MMIO or token advancement.
    wait_remaining = next.wait;
    initialized = next.initialized;
    fast = next.fast;
  }

  // The restricted context image starts after initialization/reset, once the
  // host coroutine reaches polling. Earlier wait/fast-loading calls require a
  // different caller owner and are deliberately not admitted by this adapter.
  void require_context_boundary(bool host_loaded, bool target_loaded) const {
    boundary.require_idle();
    if (!initialized || wait_remaining || fast || !host_loaded || !target_loaded)
      throw std::runtime_error("TSI bridge/context boundary mismatch");
  }
  void require_fresh_context_destination() const {
    boundary.require_idle();
    if (initialized || wait_remaining != initial_wait || fast != initial_fast)
      throw std::runtime_error("TSI bridge context destination is occupied");
  }

private:
  widget_checkpoint_config_t config;
  const uint32_t step, loading_step, initial_wait;
  const bool initial_fast;
  uint32_t wait_remaining;
  bool fast, initialized = false;
  widget_checkpoint_state_t boundary;
  struct candidate_t { uint32_t wait; bool initialized, fast; };

  void require_initialized() const {
    if (!initialized)
      throw std::runtime_error("TSI bridge is not initialized");
  }
  candidate_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle();
    if (image.size() != config.bytes.size() + 16 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI bridge control configuration/payload mismatch");
    auto word = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i)
        value |= uint64_t(image[offset + i]) << (8 * i);
      return value;
    };
    const auto wait = word(config.bytes.size());
    const auto flags = word(config.bytes.size() + 8);
    const bool init = flags & 1, next_fast = flags & 2;
    if (wait > initial_wait || (flags & ~uint64_t(3)) ||
        (next_fast && !initial_fast) ||
        (!init && (wait != initial_wait || next_fast != initial_fast)) ||
        (init && initial_fast && !next_fast && wait))
      throw std::runtime_error("invalid TSI bridge control lifecycle/cursor");
    return {static_cast<uint32_t>(wait), init, next_fast};
  }
};
#endif
