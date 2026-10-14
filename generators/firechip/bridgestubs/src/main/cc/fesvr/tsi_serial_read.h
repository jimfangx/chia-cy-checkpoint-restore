// See LICENSE for license details.
#ifndef __FIRESIM_TSI_SERIAL_READ_H
#define __FIRESIM_TSI_SERIAL_READ_H

#include "tsi_serial_state.h"

// One serial read, without host addresses or a saved coroutine stack. HTIF's
// destination/caller and the serial FIFOs are separate owners. This component
// does not authorize a complete TSI or CPU checkpoint.
class firesim_tsi_serial_read_t final : public checkpoint_owner_t {
public:
  class services_t {
  public:
    virtual ~services_t() = default;
    virtual void issue(uint64_t address, uint64_t bytes) = 0;
    virtual bool receive(uint32_t &word) = 0;
  };
  enum class result_t { progress, blocked, complete };

  void begin(uint64_t address, uint64_t bytes) {
    require_idle();
    if (current.phase != phase_t::idle)
      throw std::runtime_error("serial read already pending");
    check_request(bytes);
    state_t next;
    next.words.reserve(bytes / 4);
    next.address = address; next.bytes = bytes; next.phase = phase_t::issue;
    current = std::move(next);
  }
  result_t advance(services_t &services) {
    require_idle();
    widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::idle: throw std::runtime_error("serial read has not begun");
    case phase_t::issue:
      services.issue(current.address, current.bytes);
      current.phase = phase_t::response;
      return result_t::progress;
    case phase_t::response: {
      uint32_t word;
      if (!services.receive(word)) return result_t::blocked;
      // begin/load reserved capacity before the queue could be consumed.
      current.words.push_back(word);
      if (current.words.size() == current.bytes / 4) {
        current.phase = phase_t::complete;
        return result_t::complete;
      }
      return result_t::progress;
    }
    case phase_t::complete: return result_t::complete;
    }
    throw std::runtime_error("unknown serial read phase");
  }
  const std::vector<uint32_t> &result() const {
    require_idle();
    if (current.phase != phase_t::complete)
      throw std::runtime_error("serial read result is incomplete");
    return current.words;
  }
  void finish() {
    require_idle();
    if (current.phase != phase_t::complete)
      throw std::runtime_error("cannot finish incomplete serial read");
    current = state_t{};
  }
  // Context switching is outside advance(). An escaping switch failure must
  // invalidate access too, rather than certify an interrupted caller as a cut.
  void interrupt() noexcept { interrupted = true; }
  std::string checkpoint_schema() const override { return "firesim.tsi.serial-read.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    require_idle(); auto image = config;
    image.word(static_cast<uint64_t>(current.phase)); image.word(current.address);
    image.word(current.bytes); image.word(current.words.size());
    for (auto word : current.words) image.word(word);
    return std::move(image.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override { current = parse(image); }

private:
  enum class phase_t : uint64_t { idle, issue, response, complete };
  struct state_t {
    phase_t phase = phase_t::idle;
    uint64_t address = 0, bytes = 0;
    std::vector<uint32_t> words;
  } current;
  widget_checkpoint_config_t config{20, {1024, 4, 2, 2}};
  widget_checkpoint_state_t boundary;
  bool interrupted = false;
  void require_idle() const {
    boundary.require_idle();
    if (interrupted) throw std::runtime_error("interrupted serial read caller");
  }
  static void check_request(uint64_t bytes) {
    // Preserve the original serial protocol's full 64-bit address field.
    if (!bytes || bytes > 1024 || bytes % 4)
      throw std::runtime_error("unsupported serial read length");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    require_idle(); const size_t start = config.bytes.size();
    if (image.size() < start + 32 || (image.size() - start) % 8 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("serial read configuration/payload mismatch");
    auto word = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[offset+i]) << (8*i);
      return value;
    };
    const auto phase = word(start), count = word(start+24);
    state_t next; next.address = word(start+8); next.bytes = word(start+16);
    if (phase > 3 || count > 256 || image.size() != start + 32 + count*8)
      throw std::runtime_error("invalid serial read phase/response count");
    next.phase = static_cast<phase_t>(phase);
    if (next.phase == phase_t::idle) {
      if (next.address || next.bytes || count) throw std::runtime_error("nonempty idle serial read");
    } else {
      check_request(next.bytes);
      if ((next.phase == phase_t::issue && count) ||
          (next.phase == phase_t::response && count >= next.bytes/4) ||
          (next.phase == phase_t::complete && count != next.bytes/4))
        throw std::runtime_error("inconsistent serial read response cursor");
    }
    // Validate every word before allocating the complete candidate.
    for (size_t i = 0; i < count; ++i)
      if (word(start+32+8*i) > std::numeric_limits<uint32_t>::max())
        throw std::runtime_error("wide serial read response word");
    next.words.reserve(next.bytes/4);
    for (size_t i = 0; i < count; ++i) next.words.push_back(uint32_t(word(start+32+8*i)));
    return next;
  }
};

// Shared production adapter: no drain or extra yield before the original read
// packet; unconsumed responses remain owned by the serial FIFO.
class firesim_tsi_serial_read_services_t final : public firesim_tsi_serial_read_t::services_t {
public:
  explicit firesim_tsi_serial_read_services_t(firesim_tsi_serial_state_t &serial) : serial(serial) {}
  void issue(uint64_t address, uint64_t bytes) override { serial.issue_read(address, bytes); }
  bool receive(uint32_t &word) override {
    if (!serial.response_available()) return false;
    word = serial.pop_response(); return true;
  }
private:
  firesim_tsi_serial_state_t &serial;
};
#endif
