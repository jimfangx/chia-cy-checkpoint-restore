// See LICENSE for license details.
#ifndef __FIRESIM_TSI_HTIF_POLL_H
#define __FIRESIM_TSI_HTIF_POLL_H

#include "core/widget_checkpoint.h"
#include <deque>

// The HTIF run-loop caller, independent of its serial-read, idle, device,
// startup and stop children. Services must return before a cut is published.
// In particular, this owner does not certify a suspended syscall or BCD read.
class firesim_tsi_htif_poll_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { ready, tohost_read, tohost_clear, dispatch,
                                  idle, devices, fromhost_read, fromhost_write, complete };
  enum class result_t { progress, blocked, complete };
  class services_t {
  public:
    virtual ~services_t() = default;
    virtual bool exiting() = 0;
    virtual bool read(uint64_t address, uint64_t &value) = 0;
    virtual void write(uint64_t address, uint64_t value) = 0;
    // A restricted caller may reject unowned services before clearing tohost.
    virtual void validate_command(uint64_t) {}
    virtual void dispatch(uint64_t value) = 0;
    virtual void tick_devices() = 0;
    virtual bool idle() = 0;
  };
  firesim_tsi_htif_poll_t(uint64_t tohost, uint64_t fromhost, uint64_t limit = 1048576)
      : config(24, {tohost, fromhost, limit}), tohost_address(tohost),
        fromhost_address(fromhost), limit(limit) {
    if (!limit || limit > 1048576 || (tohost & 7) || (fromhost & 7))
      throw std::runtime_error("unsupported HTIF poll addresses/queue limit");
  }
  phase_t phase() const { boundary.require_idle(); return current.phase; }
  uint64_t pending_read_address() const {
    boundary.require_idle();
    if (current.phase == phase_t::tohost_read) return tohost_address;
    if (current.phase == phase_t::fromhost_read && !current.responses.empty()) return fromhost_address;
    throw std::runtime_error("HTIF poll has no pending read");
  }
  // Device callbacks bind the destination object, never a coroutine-local
  // queue. Callback/device reconstruction remains a separate required owner.
  void respond(uint64_t value) {
    if (!accepting_responses) boundary.require_idle();
    if (current.responses.size() == limit) throw std::runtime_error("HTIF response queue limit");
    current.responses.push_back(value);
  }
  result_t advance(services_t &s) {
    widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::ready:
      current.phase = s.exiting() ? phase_t::complete :
                      tohost_address ? phase_t::tohost_read : phase_t::idle;
      break;
    case phase_t::tohost_read:
      if (!s.read(tohost_address, current.tohost)) return result_t::blocked;
      if (current.tohost) s.validate_command(current.tohost);
      current.phase = current.tohost ? phase_t::tohost_clear : phase_t::idle;
      break;
    case phase_t::tohost_clear:
      s.write(tohost_address, 0); current.phase = phase_t::dispatch; break;
    case phase_t::dispatch:
      device_service(s, false); current.phase = phase_t::devices; break;
    case phase_t::idle:
      if (!s.idle()) return result_t::blocked;
      current.phase = tohost_address ? phase_t::devices : phase_t::ready;
      break;
    case phase_t::devices:
      device_service(s, true); current.tohost = 0; current.phase = phase_t::fromhost_read; break;
    case phase_t::fromhost_read: {
      uint64_t value = 0;
      if (current.responses.empty()) { current.phase = phase_t::ready; break; }
      if (!s.read(fromhost_address, value)) return result_t::blocked;
      current.phase = value ? phase_t::ready : phase_t::fromhost_write; break;
    }
    case phase_t::fromhost_write:
      s.write(fromhost_address, current.responses.front());
      current.responses.pop_front(); current.phase = phase_t::ready; break;
    case phase_t::complete: return result_t::complete;
    }
    return current.phase == phase_t::complete ? result_t::complete : result_t::progress;
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.htif-poll.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); auto out = config;
    out.word(static_cast<uint64_t>(current.phase)); out.word(current.tohost);
    out.word(current.responses.size());
    for (auto value : current.responses) out.word(value);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = parse(image); commit(next);
  }
private:
  struct state_t {
    phase_t phase = phase_t::ready;
    uint64_t tohost = 0;
    std::deque<uint64_t> responses;
  } current;
  friend class firesim_tsi_bcd_t;
  void commit(state_t &next) noexcept {
    static_assert(noexcept(current.responses.swap(next.responses)), "HTIF poll commit must not allocate");
    current.responses.swap(next.responses);
    current.phase = next.phase; current.tohost = next.tohost;
  }
  widget_checkpoint_config_t config;
  const uint64_t tohost_address, fromhost_address, limit;
  widget_checkpoint_state_t boundary;
  bool accepting_responses = false;
  void device_service(services_t &s, bool tick) {
    accepting_responses = true;
    try { if (tick) s.tick_devices(); else s.dispatch(current.tohost); }
    catch (...) { accepting_responses = false; throw; }
    accepting_responses = false;
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const size_t start = config.bytes.size();
    if (image.size() < start + 24 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("HTIF poll configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto phase = word(start), tohost = word(start+8), count = word(start+16);
    if (phase > 8 || count > limit || image.size() != start+24+8*count ||
        ((phase == 2 || phase == 3) && !tohost) ||
        ((phase != 2 && phase != 3 && phase != 5) && tohost) ||
        (phase == 7 && !count) ||
        (!tohost_address && phase != 0 && phase != 4 && phase != 8))
      throw std::runtime_error("incoherent HTIF poll phase/result/response queue");
    state_t next; next.phase = static_cast<phase_t>(phase); next.tohost = tohost;
    for (size_t i = 0; i < count; ++i) next.responses.push_back(word(start+24+8*i));
    return next;
  }
};
#endif
