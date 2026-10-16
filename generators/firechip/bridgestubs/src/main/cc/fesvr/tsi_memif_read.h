// See LICENSE for license details.
#ifndef __FIRESIM_TSI_MEMIF_READ_H
#define __FIRESIM_TSI_MEMIF_READ_H

#include "tsi_serial_read.h"
#include <type_traits>

// Explicit caller for installed memif_t::read with FireSim's align=8/max=1024.
// Match its head, tail, then body transaction order, including partial words.
// The result is owned bytes, never a host pointer into a suspended caller.
// Serial FIFOs and the enclosing HTIF/syscall caller remain separate owners.
class firesim_tsi_memif_read_t final : public checkpoint_owner_t {
public:
  static constexpr uint64_t maximum = 1048576;
  enum class phase_t : uint64_t { idle, head, tail, body, complete };
  enum class result_t { progress, blocked, complete };
  using services_t = firesim_tsi_serial_read_t::services_t;

  bool idle() const { require_idle(); return current.phase == phase_t::idle; }
  bool pending_read(uint64_t address, uint64_t bytes) const {
    require_idle();
    return current.phase != phase_t::idle && current.address == address && current.data.size() == bytes;
  }
  void begin(uint64_t address, uint64_t bytes) {
    require_idle();
    if (!idle()) throw std::runtime_error("memif read already pending");
    check_range(address, bytes);
    state_t next; next.address = address; next.data.resize(bytes);
    next.phase = !bytes ? phase_t::complete : address % 8 ? phase_t::head : phase_t::tail;
    current = std::move(next);
  }
  result_t advance(services_t &services) {
    require_idle(); widget_checkpoint_state_t::call_t call(boundary);
    if (current.phase == phase_t::idle) throw std::runtime_error("memif read has not begun");
    if (current.phase == phase_t::complete) return result_t::complete;
    const auto request = chunk(current);
    if (request.count) {
      if (current.read.idle()) current.read.begin(request.address, request.bytes);
      for (;;) {
        const auto result = current.read.advance(services);
        if (result == firesim_tsi_serial_read_t::result_t::blocked) return result_t::blocked;
        if (result == firesim_tsi_serial_read_t::result_t::complete) break;
      }
      const auto &words = current.read.result();
      for (uint64_t i = 0; i < request.count; ++i) {
        const auto byte = request.first + i;
        current.data[request.offset+i] = uint8_t(words[byte/4] >> (8*(byte%4)));
      }
      current.read.finish();
    }
    if (current.phase == phase_t::head) current.phase = phase_t::tail;
    else if (current.phase == phase_t::tail) current.phase = phase_t::body;
    else {
      current.cursor += request.count;
      if (current.cursor == body_size(current)) current.phase = phase_t::complete;
    }
    return current.phase == phase_t::complete ? result_t::complete : result_t::progress;
  }
  const std::vector<uint8_t> &result() const {
    require_idle();
    if (current.phase != phase_t::complete) throw std::runtime_error("incomplete memif read result");
    return current.data;
  }
  void finish() {
    require_idle();
    if (current.phase != phase_t::complete) throw std::runtime_error("incomplete memif read");
    current = state_t{};
  }
  void interrupt() noexcept { interrupted = true; }
  void swap_state(firesim_tsi_memif_read_t &other) noexcept { std::swap(current, other.current); }
  std::string checkpoint_schema() const override { return "firesim.tsi.memif-read.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    require_idle(); auto out = config;
    out.word(static_cast<uint64_t>(current.phase)); out.word(current.address);
    out.word(current.cursor); out.word(current.data.size());
    out.bytes.insert(out.bytes.end(), current.data.begin(), current.data.end());
    const auto child = current.read.save_checkpoint(); out.word(child.size());
    out.bytes.insert(out.bytes.end(), child.begin(), child.end());
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    static_assert(std::is_nothrow_move_assignable<state_t>::value, "memif read publication must not allocate");
    current = parse(image);
  }
  // Component transaction only: enclosing callers and a simulator-wide cut
  // still need their own ownership/admission checks. Never publish one peer
  // before the other's parsing/allocation has completed.
  void load_serial_checkpoint(firesim_tsi_serial_state_t &serial,
                              const std::vector<uint8_t> &image,
                              const std::vector<uint8_t> &queues) {
    require_idle(); serial.request_available();
    firesim_tsi_memif_read_t next; firesim_tsi_serial_state_t peer;
    next.load_checkpoint(image); peer.load_checkpoint(queues);
    swap_state(next); serial.swap_state(peer);
  }

private:
  struct state_t {
    phase_t phase = phase_t::idle;
    uint64_t address = 0, cursor = 0;
    std::vector<uint8_t> data;
    firesim_tsi_serial_read_t read;
  } current;
  struct chunk_t { uint64_t address, bytes, offset, first, count; };
  widget_checkpoint_config_t config{30, {1, 8, 1024, maximum}};
  widget_checkpoint_state_t boundary;
  bool interrupted = false;
  void require_idle() const {
    boundary.require_idle();
    if (interrupted) throw std::runtime_error("interrupted memif read caller");
  }
  static uint64_t prefix_size(const state_t &s) {
    return s.address % 8 ? std::min(uint64_t(s.data.size()), 8-s.address%8) : 0;
  }
  static uint64_t body_size(const state_t &s) { return (s.data.size()-prefix_size(s)) & ~uint64_t(7); }
  static chunk_t chunk(const state_t &s) {
    const auto prefix = prefix_size(s), tail = (s.data.size()-prefix)%8;
    if (s.phase == phase_t::head) return {s.address & ~uint64_t(7), 8, 0, s.address%8, prefix};
    if (s.phase == phase_t::tail) return {s.address+s.data.size()-tail, 8, s.data.size()-tail, 0, tail};
    const auto count = std::min(uint64_t(1024), body_size(s)-s.cursor);
    return {s.address+prefix+s.cursor, count, prefix+s.cursor, 0, count};
  }
  static void check_range(uint64_t address, uint64_t bytes) {
    if (bytes > maximum || (bytes && bytes-1 > ~uint64_t(0)-address))
      throw std::runtime_error("unsupported memif read length/address wrap");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    require_idle(); const auto start = config.bytes.size();
    if (image.size() < start+40 || !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("memif read configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image.at(at+i)) << (8*i);
      return value;
    };
    const auto phase = word(start), address = word(start+8), cursor = word(start+16), size = word(start+24);
    check_range(address, size);
    if (phase > 4 || size > image.size()-start-40 || word(start+32+size) != image.size()-start-40-size)
      throw std::runtime_error("invalid memif read phase/payload/child size");
    const auto prefix = address%8 ? std::min(size, 8-address%8) : 0;
    const auto body = (size-prefix) & ~uint64_t(7), tail = (size-prefix)%8;
    if ((phase == 0 && (address || cursor || size)) || (phase != 0 && phase != 4 && !size) ||
        (phase == 1 && !prefix) || (phase < 3 && cursor) || cursor > body ||
        (phase == 3 && cursor != body && cursor%1024) || (phase == 4 && cursor != body))
      throw std::runtime_error("incoherent memif read phase/body cursor");
    // Unfilled output bytes have one canonical representation. Never accept an
    // image claiming completed bytes that the caller has not yet read.
    for (uint64_t i = 0; i < size; ++i) {
      const bool filled = phase == 4 || (phase >= 2 && i < prefix) ||
                          (phase == 3 && (i < prefix+cursor || i >= size-tail));
      if (!filled && image[start+32+i]) throw std::runtime_error("nonzero unread memif byte");
    }
    state_t next; next.phase = static_cast<phase_t>(phase); next.address = address; next.cursor = cursor;
    next.data.assign(image.begin()+start+32, image.begin()+start+32+size);
    next.read.load_checkpoint({image.begin()+start+40+size, image.end()});
    if (!next.read.idle()) {
      if (phase < 1 || phase > 3) throw std::runtime_error("inactive memif read has serial child");
      const auto request = chunk(next);
      if (!request.count || !next.read.pending_for(request.address, request.bytes))
        throw std::runtime_error("incoherent memif read serial child");
    }
    return next;
  }
};

// Normal runtime serial policy. No state is hidden in this adapter: the
// immutable flush address belongs to program/startup metadata, and the FIFO
// and pending child retain every issued packet. issue() never yields, so a
// blocked continuation cannot repeat a flush or read. Startup loadmem must
// select its separate caller before constructing this service.
class firesim_tsi_memif_read_services_t final : public firesim_tsi_memif_read_t::services_t {
public:
  firesim_tsi_memif_read_services_t(firesim_tsi_serial_state_t &serial, uint64_t flush)
      : serial(serial), flush(flush) {}
  void issue(uint64_t address, uint64_t bytes) override {
    if (!bytes || bytes > 1024 || bytes % 8 || address % 8 || bytes-1 > ~uint64_t(0)-address)
      throw std::runtime_error("unsupported runtime memif serial chunk");
    if (flush) {
      // Avoid address+bytes and final-line overflow at the end of the address
      // space. The reader has already validated its complete byte range.
      const auto last = address + bytes - 1;
      for (uint64_t base = address & ~uint64_t(63);;) {
        const uint32_t words[2] = {uint32_t(base), uint32_t(base >> 32)};
        serial.issue_write(flush, sizeof(words), words);
        if (last - base < 64) break;
        base += 64;
      }
    }
    serial.issue_read(address, bytes);
  }
  bool receive(uint32_t &word) override {
    if (!serial.response_available()) return false;
    word = serial.pop_response(); return true;
  }
private:
  firesim_tsi_serial_state_t &serial;
  uint64_t flush;
};
#endif
