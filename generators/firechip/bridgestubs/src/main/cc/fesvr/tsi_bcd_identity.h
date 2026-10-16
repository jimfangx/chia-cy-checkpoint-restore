// See LICENSE for license details.
#ifndef __FIRESIM_TSI_BCD_IDENTITY_H
#define __FIRESIM_TSI_BCD_IDENTITY_H

#include "tsi_memif_write.h"
#include <cstring>

// Explicit device-1/command-255 caller. It owns the raw command and the
// write/response/return cursor; the bound memif child and serial FIFOs are
// independent owners. No command_t callback or suspended C++ stack is saved.
// This component transaction does not restore its parent HTIF polling caller.
class firesim_tsi_bcd_identity_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { idle, writing, responding, complete };
  enum class result_t { progress, blocked, complete };
  class services_t : public firesim_tsi_memif_write_t::services_t {
  public:
    virtual void respond(uint64_t value) = 0;
  };
  firesim_tsi_bcd_identity_t(firesim_tsi_memif_write_t &writer,
                           firesim_tsi_serial_state_t &serial) : writer(writer), serial(serial) {}
  bool idle() const { boundary.require_idle(); return current.phase == phase_t::idle; }
  bool pending_for(uint64_t command) const {
    boundary.require_idle(); validate_child(current, writer);
    return current.phase != phase_t::idle && current.command == command;
  }
  bool blocked_for(uint64_t command) const {
    return pending_for(command) && current.phase == phase_t::writing && writer.pending_merge();
  }
  // Publish only state, preserving this caller's destination-bound child and
  // FIFO references. Candidate parsing/validation must precede this swap.
  void swap_state(firesim_tsi_bcd_identity_t &other) noexcept {
    std::swap(current, other.current);
  }
  void begin(uint64_t command) {
    boundary.require_idle();
    if (!idle() || !writer.idle()) throw std::runtime_error("BCD identity caller/child already pending");
    check_command(command);
    writer.begin(address(command), payload(command));
    current = {phase_t::writing, command};
  }
  result_t advance(services_t &s) {
    boundary.require_idle(); validate_child(current, writer);
    widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::idle: throw std::runtime_error("BCD identity caller has not begun");
    case phase_t::writing: {
      const auto result = writer.advance(s);
      if (result == firesim_tsi_memif_write_t::result_t::blocked) return result_t::blocked;
      if (result == firesim_tsi_memif_write_t::result_t::complete) {
        writer.finish(); current.phase = phase_t::responding;
      }
      break;
    }
    case phase_t::responding:
      // Same command_t::respond encoding as the installed device implementation.
      s.respond((current.command & 0xffff000000000000ULL) | 1);
      current.phase = phase_t::complete; break;
    case phase_t::complete: return result_t::complete;
    }
    return current.phase == phase_t::complete ? result_t::complete : result_t::progress;
  }
  void finish() {
    boundary.require_idle(); validate_child(current, writer);
    if (current.phase != phase_t::complete) throw std::runtime_error("incomplete BCD identity caller");
    current = {};
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.bcd-identity.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); validate_child(current, writer);
    auto out = config; out.word(static_cast<uint64_t>(current.phase)); out.word(current.command);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override {
    validate_child(parse(image), writer);
  }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    const auto next = parse(image); validate_child(next, writer); current = next;
  }
  using images_t = std::vector<std::pair<std::string, std::vector<uint8_t>>>;
  void load_components(const images_t &images) {
    boundary.require_idle(); writer.save_checkpoint(); serial.save_checkpoint();
    if (images.size() != 3 || images[0].first != "identity" ||
        images[1].first != "write" || images[2].first != "serial")
      throw std::runtime_error("BCD identity preparation requires ordered caller/write/serial owners");
    const auto next = parse(images[0].second);
    firesim_tsi_memif_write_t child;
    firesim_tsi_serial_state_t transport;
    child.load_checkpoint(images[1].second); transport.load_checkpoint(images[2].second);
    validate_child(next, child);
    // All parsing, allocation and relationships precede nonthrowing publication.
    static_assert(std::is_nothrow_move_assignable<firesim_tsi_memif_write_t>::value,
                  "identity write publication must not allocate");
    static_assert(std::is_nothrow_move_assignable<firesim_tsi_serial_state_t>::value,
                  "identity serial publication must not allocate");
    writer = std::move(child); serial = std::move(transport); current = next;
  }
private:
  struct state_t { phase_t phase = phase_t::idle; uint64_t command = 0; } current;
  firesim_tsi_memif_write_t &writer;
  firesim_tsi_serial_state_t &serial;
  widget_checkpoint_config_t config{29, {1, 255, 64, 8, 1024}};
  widget_checkpoint_state_t boundary;
  static void check_command(uint64_t command) {
    if ((command >> 48) != 0x1ff) throw std::runtime_error("unsupported BCD identity command");
  }
  static uint64_t address(uint64_t command) { return (command & 0xffffffffffffULL) / 256; }
  static std::vector<uint8_t> payload(uint64_t command) {
    std::vector<uint8_t> bytes(64);
    const auto what = command & 255;
    const char *name = what == 0 ? "read" : what == 1 ? "write" : what == 255 ? "bcd" : "";
    std::copy(name, name + std::strlen(name), bytes.begin()); return bytes;
  }
  static void validate_child(const state_t &state, const firesim_tsi_memif_write_t &writer) {
    if (state.phase == phase_t::writing ?
          !writer.pending_write(address(state.command), payload(state.command)) : !writer.idle())
      throw std::runtime_error("BCD identity caller/write-child relationship mismatch");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const auto start = config.bytes.size();
    if (image.size() != start+16 || !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("BCD identity configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto phase = word(start), command = word(start+8);
    if (phase > 3 || (!phase && command)) throw std::runtime_error("invalid BCD identity phase/command");
    if (phase) check_command(command);
    return {static_cast<phase_t>(phase), command};
  }
};
#endif
