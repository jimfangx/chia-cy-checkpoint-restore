// See LICENSE for license details.
#ifndef __FIRESIM_LOADMEM_READ_H
#define __FIRESIM_LOADMEM_READ_H

#include "core/checkpoint.h"
#include "core/widget_checkpoint.h"
#include <limits>

// One pointer-free loadmem read. Request/response queues, HTIF's destination
// and suspended caller, program loader and context remain separate owners.
// This component alone must never authorize a TSI/CPU checkpoint profile.
class firesim_loadmem_read_t final : public checkpoint_owner_t {
public:
  class services_t {
  public:
    virtual ~services_t() = default;
    virtual bool writes_pending() = 0;
    virtual void issue(uint64_t address, uint64_t bytes) = 0;
    virtual bool receive(uint32_t &word) = 0;
  };
  enum class result_t { progress, blocked, complete };
  bool idle() const { boundary.require_idle(); return state.phase == phase_t::idle; }

  void begin(uint64_t address, uint64_t bytes) {
    boundary.require_idle();
    if (state.phase != phase_t::idle)
      throw std::runtime_error("loadmem read already pending");
    check_request(address, bytes);
    // Allocate before changing the current owner, including on bad_alloc.
    state_t next;
    next.words.reserve(bytes / 4);
    next.address = address;
    next.bytes = bytes;
    next.phase = phase_t::drain;
    state = std::move(next);
  }

  result_t advance(services_t &services) {
    widget_checkpoint_state_t::call_t call(boundary);
    switch (state.phase) {
    case phase_t::idle:
      throw std::runtime_error("loadmem read has not begun");
    case phase_t::drain:
      if (services.writes_pending())
        return result_t::blocked;
      state.phase = phase_t::issue;
      return result_t::progress;
    case phase_t::issue:
      services.issue(state.address, state.bytes);
      state.phase = phase_t::response;
      return result_t::progress;
    case phase_t::response: {
      uint32_t word;
      if (!services.receive(word))
        return result_t::blocked;
      // Capacity is reserved before issue/load, so a successful dequeue is
      // never followed by an allocation that could lose its returned word.
      state.words.push_back(word);
      if (state.words.size() == state.bytes / 4) {
        state.phase = phase_t::complete;
        return result_t::complete;
      }
      return result_t::progress;
    }
    case phase_t::complete:
      return result_t::complete;
    }
    throw std::runtime_error("unknown loadmem read phase");
  }

  const std::vector<uint32_t> &result() const {
    boundary.require_idle();
    if (state.phase != phase_t::complete)
      throw std::runtime_error("loadmem read result is incomplete");
    return state.words;
  }
  void finish() {
    boundary.require_idle();
    if (state.phase != phase_t::complete)
      throw std::runtime_error("cannot finish incomplete loadmem read");
    state = state_t{};
  }

  std::string checkpoint_schema() const override {
    return "firesim.tsi.loadmem-read.v1";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle();
    auto config = configuration();
    config.word(static_cast<uint64_t>(state.phase));
    config.word(state.address);
    config.word(state.bytes);
    config.word(state.words.size());
    for (auto word : state.words)
      config.word(word);
    return std::move(config.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &payload) const override {
    parse(payload);
  }
  void load_checkpoint(const std::vector<uint8_t> &payload) override {
    state = parse(payload);
  }

private:
  static constexpr uint64_t max_bytes = 4096;
  enum class phase_t : uint64_t { idle, drain, issue, response, complete };
  struct state_t {
    phase_t phase = phase_t::idle;
    uint64_t address = 0;
    uint64_t bytes = 0;
    std::vector<uint32_t> words;
  } state;
  widget_checkpoint_state_t boundary;

  static widget_checkpoint_config_t configuration() {
    return {14, {max_bytes, 4}};
  }
  static void check_request(uint64_t address, uint64_t bytes) {
    if (!bytes || bytes > max_bytes || bytes % 4 || address % 4 ||
        address > std::numeric_limits<uint64_t>::max() - (bytes - 1))
      throw std::runtime_error("unsupported loadmem read address/length");
  }
  state_t parse(const std::vector<uint8_t> &payload) const {
    boundary.require_idle();
    const auto config = configuration();
    if (payload.size() < config.bytes.size() + 32 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), payload.begin()))
      throw std::runtime_error("loadmem read configuration/payload mismatch");
    size_t cursor = config.bytes.size();
    auto word = [&]() {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i)
        value |= uint64_t(payload.at(cursor++)) << (8 * i);
      return value;
    };
    const auto phase = word();
    state_t next;
    next.address = word();
    next.bytes = word();
    const auto count = word();
    if (phase > static_cast<uint64_t>(phase_t::complete) || count > max_bytes / 4 ||
        payload.size() != cursor + count * 8)
      throw std::runtime_error("invalid loadmem read phase/response length");
    next.phase = static_cast<phase_t>(phase);
    if (next.phase == phase_t::idle) {
      if (next.address || next.bytes || count)
        throw std::runtime_error("nonempty idle loadmem read");
    } else {
      check_request(next.address, next.bytes);
      if (count > next.bytes / 4 ||
          (next.phase != phase_t::response && next.phase != phase_t::complete && count) ||
          (next.phase == phase_t::response && count == next.bytes / 4) ||
          (next.phase == phase_t::complete && count != next.bytes / 4))
        throw std::runtime_error("inconsistent loadmem read response cursor");
    }
    next.words.reserve(next.bytes / 4);
    for (uint64_t i = 0; i < count; ++i) {
      const auto value = word();
      if (value > std::numeric_limits<uint32_t>::max())
        throw std::runtime_error("invalid loadmem response word");
      next.words.push_back(value);
    }
    return next;
  }
};
#endif
