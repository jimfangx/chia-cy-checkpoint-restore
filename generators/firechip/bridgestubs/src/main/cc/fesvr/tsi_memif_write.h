// See LICENSE for license details.
#ifndef __FIRESIM_TSI_MEMIF_WRITE_H
#define __FIRESIM_TSI_MEMIF_WRITE_H

#include "tsi_serial_read.h"
#include <array>
#include <type_traits>

// FireSim's eight-byte-aligned memif write caller. Match installed memif.cc:
// head read/merge/write, tail read/merge/write, then aligned body chunks.
// The copied payload, body cursor and partial serial read are owned here;
// outbound/inbound FIFOs and the device/HTIF caller remain separate owners.
class firesim_tsi_memif_write_t final : public checkpoint_owner_t {
public:
  static constexpr uint64_t maximum = 1048576;
  enum class phase_t : uint64_t { idle, head, tail, body, complete };
  enum class result_t { progress, blocked, complete };
  class services_t : public firesim_tsi_serial_read_t::services_t {
  public:
    virtual void write(uint64_t address, size_t bytes, const uint32_t *words) = 0;
  };

  bool idle() const { require_idle(); return current.phase == phase_t::idle; }
  bool pending_write(uint64_t address, const std::vector<uint8_t> &bytes) const {
    require_idle();
    return current.phase != phase_t::idle && current.address == address && current.data == bytes;
  }
  bool pending_merge() const {
    require_idle();
    if (current.phase != phase_t::head && current.phase != phase_t::tail) return false;
    const auto prefix = head_size(current.address, current.data.size());
    const auto count = current.phase == phase_t::head ? prefix : (current.data.size()-prefix)%8;
    const auto offset = current.phase == phase_t::head ? 0 : current.data.size()-count;
    return count && current.read.pending_for((current.address+offset)&~uint64_t(7), 8);
  }
  void begin(uint64_t address, const std::vector<uint8_t> &bytes) {
    require_idle();
    if (!idle()) throw std::runtime_error("memif write already pending");
    check_range(address, bytes.size());
    state_t next; next.address = address; next.data = bytes;
    next.phase = bytes.empty() ? phase_t::complete :
                 address % 8 ? phase_t::head : phase_t::tail;
    current = std::move(next);
  }
  result_t advance(services_t &s) {
    require_idle(); widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::idle: throw std::runtime_error("memif write has not begun");
    case phase_t::head:
    case phase_t::tail: {
      const bool head = current.phase == phase_t::head;
      const auto prefix = head_size(current.address, current.data.size());
      const auto count = head ? prefix : (current.data.size() - prefix) % 8;
      if (!count) { current.phase = phase_t::body; break; }
      const auto offset = head ? 0 : current.data.size() - count;
      const auto address = (current.address + offset) & ~uint64_t(7);
      if (current.read.idle()) current.read.begin(address, 8);
      for (;;) {
        const auto result = current.read.advance(s);
        if (result == firesim_tsi_serial_read_t::result_t::blocked) return result_t::blocked;
        if (result == firesim_tsi_serial_read_t::result_t::complete) break;
      }
      auto words = current.read.result();
      // Explicit little-endian byte merge, independent of host char alignment.
      const auto first = head ? current.address % 8 : 0;
      for (size_t i = 0; i < count; ++i) {
        const auto byte = first + i, shift = 8 * (byte % 4);
        words[byte / 4] = (words[byte / 4] & ~(uint32_t(255) << shift)) |
                             (uint32_t(current.data[offset+i]) << shift);
      }
      s.write(address, 8, words.data());
      current.read.finish();
      current.phase = head ? phase_t::tail : phase_t::body;
      break;
    }
    case phase_t::body: {
      const auto prefix = head_size(current.address, current.data.size());
      const auto length = (current.data.size() - prefix) & ~uint64_t(7);
      if (current.cursor < length) {
        const auto count = std::min(uint64_t(1024), length - current.cursor);
        std::array<uint32_t, 256> words{};
        for (size_t i = 0; i < count; ++i)
          words[i/4] |= uint32_t(current.data[prefix+current.cursor+i]) << (8*(i%4));
        s.write(current.address + prefix + current.cursor, count, words.data());
        current.cursor += count;
      }
      if (current.cursor == length) current.phase = phase_t::complete;
      break;
    }
    case phase_t::complete: return result_t::complete;
    }
    return current.phase == phase_t::complete ? result_t::complete : result_t::progress;
  }
  void finish() {
    require_idle();
    if (current.phase != phase_t::complete) throw std::runtime_error("incomplete memif write");
    current = state_t{};
  }
  void interrupt() noexcept { interrupted = true; }
  std::string checkpoint_schema() const override { return "firesim.tsi.memif-write.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    require_idle(); auto out = config;
    out.word(static_cast<uint64_t>(current.phase)); out.word(current.address);
    out.word(current.cursor); out.word(current.data.size());
    out.bytes.insert(out.bytes.end(), current.data.begin(), current.data.end());
    const auto read = current.read.save_checkpoint();
    out.word(read.size()); out.bytes.insert(out.bytes.end(), read.begin(), read.end());
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    static_assert(std::is_nothrow_move_assignable<state_t>::value, "memif publication must not allocate");
    current = parse(image);
  }

private:
  struct state_t {
    phase_t phase = phase_t::idle;
    uint64_t address = 0, cursor = 0;
    std::vector<uint8_t> data;
    firesim_tsi_serial_read_t read;
  } current;
  widget_checkpoint_config_t config{28, {1, 8, 1024, maximum}};
  widget_checkpoint_state_t boundary;
  bool interrupted = false;
  void require_idle() const {
    boundary.require_idle();
    if (interrupted) throw std::runtime_error("interrupted memif write caller");
  }
  static uint64_t head_size(uint64_t address, uint64_t size) {
    return address % 8 ? std::min(size, 8 - address % 8) : 0;
  }
  static void check_range(uint64_t address, uint64_t size) {
    if (size > maximum || (size && size-1 > ~uint64_t(0)-address))
      throw std::runtime_error("unsupported memif write length/address wrap");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    require_idle(); const auto start = config.bytes.size();
    if (image.size() < start+40 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("memif write configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image.at(at+i)) << (8*i);
      return value;
    };
    const auto phase = word(start), address = word(start+8), cursor = word(start+16), size = word(start+24);
    check_range(address, size);
    if (phase > 4 || size > image.size()-start-40 ||
        word(start+32+size) != image.size()-start-40-size)
      throw std::runtime_error("invalid memif write phase/payload/child size");
    const auto prefix = head_size(address, size), body = (size-prefix) & ~uint64_t(7);
    if ((phase == 0 && (address || cursor || size)) ||
        (phase != 0 && phase != 4 && !size) ||
        (phase == 1 && !prefix) ||
        (phase < 3 && cursor) || cursor > body ||
        (phase == 3 && cursor != body && cursor % 1024) ||
        (phase == 4 && cursor != body))
      throw std::runtime_error("incoherent memif write phase/body cursor");
    state_t next; next.phase = static_cast<phase_t>(phase); next.address = address; next.cursor = cursor;
    next.data.assign(image.begin()+start+32, image.begin()+start+32+size);
    next.read.load_checkpoint({image.begin()+start+40+size, image.end()});
    if (!next.read.idle()) {
      const auto tail = (size-prefix) % 8;
      const auto child_address = (address + (phase == 1 ? 0 : size-tail)) & ~uint64_t(7);
      if ((phase != 1 && phase != 2) || (phase == 2 && !tail) ||
          !next.read.pending_for(child_address, 8))
        throw std::runtime_error("incoherent memif write serial-read child");
    }
    return next;
  }
};
#endif
