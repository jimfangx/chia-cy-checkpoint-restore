// See LICENSE for license details.
#ifndef FIRESIM_TSI_SYSCALL_EXIT_H
#define FIRESIM_TSI_SYSCALL_EXIT_H

#include "tsi_memif_read.h"
#include "tsi_memif_write.h"
#include "tsi_htif_lifecycle.h"
#include "fesvr/htif.h"
#include <array>

// Explicit little-endian RV64 syscall-93 parent. Owns magicmem, selection,
// return/writeback and response progress, including both nested memif callers.
// The actual HTIF lifecycle and serial FIFOs are mandatory transaction peers.
// Session/descriptors, polling response queue and outer context remain separate
// owners. This component is deliberately not enabled by CPU admission or tick().
class firesim_tsi_syscall_exit_t final : public checkpoint_owner_t {
public:
  enum class phase_t : uint64_t { idle, reading, invoking, writing, responding, complete };
  enum class result_t { progress, blocked, complete };
  class services_t : public firesim_tsi_memif_write_t::services_t {
  public:
    virtual void respond(uint64_t value) = 0;
  };
  using images_t = std::vector<std::pair<std::string, std::vector<uint8_t>>>;
  firesim_tsi_syscall_exit_t(htif_t &htif, firesim_tsi_serial_state_t &serial)
      : htif(htif), serial(serial), lifecycle(htif) {}
  void begin(uint64_t command) {
    boundary.require_idle(); validate(current, provider_state());
    if (current.phase != phase_t::idle) throw std::runtime_error("syscall exit already pending");
    check_command(command);
    state_t next; next.command = command; next.phase = phase_t::reading;
    next.read.begin(command, 64); current = std::move(next);
  }
  result_t advance(services_t &services) {
    boundary.require_idle(); validate(current, provider_state());
    widget_checkpoint_state_t::call_t call(boundary);
    switch (current.phase) {
    case phase_t::idle: throw std::runtime_error("syscall exit has not begun");
    case phase_t::reading: {
      const auto result = current.read.advance(services);
      if (result == firesim_tsi_memif_read_t::result_t::blocked) return result_t::blocked;
      if (result == firesim_tsi_memif_read_t::result_t::complete) {
        const auto &data = current.read.result();
        for (unsigned i = 0; i < 8; ++i) current.args[i] = word(data, 8*i);
        // Never issue a host syscall or writeback for an unowned selector.
        if (current.args[0] != 93) throw std::runtime_error("unsupported checkpoint syscall (requires 93)");
        current.read.finish(); current.phase = phase_t::invoking;
      }
      break;
    }
    case phase_t::invoking: {
      // Allocate the complete write child before changing the actual provider.
      // Match installed sys_exit: code << 1 | 1, optional<int> truncation, zero
      // return, and a write of all eight target-endian words before respond(1).
      auto data = payload(current.args);
      firesim_tsi_memif_write_t next; next.begin(current.command, data);
      htif.htif_exit(uint32_t((current.args[1] << 1) | 1));
      static_assert(std::is_nothrow_move_assignable<firesim_tsi_memif_write_t>::value,
                    "syscall write publication must not allocate");
      current.write = std::move(next); current.phase = phase_t::writing;
      break;
    }
    case phase_t::writing: {
      const auto result = current.write.advance(services);
      if (result == firesim_tsi_memif_write_t::result_t::blocked) return result_t::blocked;
      if (result == firesim_tsi_memif_write_t::result_t::complete) {
        current.write.finish(); current.phase = phase_t::responding;
      }
      break;
    }
    case phase_t::responding:
      services.respond(1); current.phase = phase_t::complete; break;
    case phase_t::complete: return result_t::complete;
    }
    return current.phase == phase_t::complete ? result_t::complete : result_t::progress;
  }
  // No finish/reset: a syscall exit leaves its provider occupied. Destruction
  // and the enclosing HTIF stop/return caller require independent ownership.
  std::string checkpoint_schema() const override { return "firesim.tsi.syscall-exit.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); validate(current, provider_state());
    auto out = config; out.word(uint64_t(current.phase)); out.word(current.command);
    for (auto arg : current.args) out.word(arg);
    for (const auto &image : {current.read.save_checkpoint(), current.write.save_checkpoint()}) {
      out.word(image.size()); out.bytes.insert(out.bytes.end(), image.begin(), image.end());
    }
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = parse(image); validate(next, provider_state());
    current = std::move(next);
  }
  images_t save_components() const {
    return {{"syscall", save_checkpoint()}, {"serial", serial.save_checkpoint()},
            {"lifecycle", lifecycle.save_checkpoint()}};
  }
  void load_components(const images_t &images) {
    boundary.require_idle(); save_components();
    if (images.size() != 3 || images[0].first != "syscall" ||
        images[1].first != "serial" || images[2].first != "lifecycle")
      throw std::runtime_error("syscall restore requires ordered caller/serial/lifecycle owners");
    auto next = parse(images[0].second);
    firesim_tsi_serial_state_t queues; queues.load_checkpoint(images[1].second);
    auto provider = lifecycle.prepare_checkpoint(images[2].second);
    validate(next, provider.restored_state());
    // Destination provider rechecks immediately before nonthrowing publication.
    // No service, request, exit, response, edge or startup is replayed here.
    auto publish = [&]() noexcept { current = std::move(next); serial.swap_state(queues); };
    provider.commit(publish);
  }
private:
  friend class firesim_tsi_polling_syscall_t;
  friend class firesim_tsi_t;
  struct state_t {
    phase_t phase = phase_t::idle;
    uint64_t command = 0;
    std::array<uint64_t, 8> args{};
    firesim_tsi_memif_read_t read;
    firesim_tsi_memif_write_t write;
  } current;
  static_assert(std::is_nothrow_move_assignable<state_t>::value, "syscall publication must not allocate");
  htif_t &htif;
  firesim_tsi_serial_state_t &serial;
  firesim_tsi_htif_lifecycle_t lifecycle;
  widget_checkpoint_config_t config{34, {1, 64, 93, 8, 8, 1024, 0}};
  widget_checkpoint_state_t boundary;
  firesim_htif_lifecycle_state_t provider_state() const {
    if (htif.get_target_endianness() != endianness_little)
      throw std::runtime_error("syscall exit requires little-endian target");
    return firesim_htif_require_lifecycle_api().read(htif);
  }
  static uint64_t word(const std::vector<uint8_t> &image, size_t at) {
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image.at(at+i)) << (8*i);
    return value;
  }
  static void check_command(uint64_t command) {
    if (command >> 48 || (command & 1) || command > 0xffffffffffffULL-63)
      throw std::runtime_error("unsupported syscall command/address range");
  }
  static std::vector<uint8_t> payload(const std::array<uint64_t, 8> &args) {
    std::vector<uint8_t> bytes(64);
    for (unsigned i = 1; i < 8; ++i)
      for (unsigned j = 0; j < 8; ++j) bytes[8*i+j] = uint8_t(args[i] >> (8*j));
    return bytes;
  }
  static void validate(const state_t &s, firesim_htif_lifecycle_state_t provider) {
    if (s.phase != phase_t::idle) check_command(s.command);
    const bool decoded = s.phase >= phase_t::invoking;
    if ((!decoded && s.args != std::array<uint64_t, 8>{}) ||
        (decoded && s.args[0] != 93) || (s.phase == phase_t::idle && s.command))
      throw std::runtime_error("incoherent syscall request/selection");
    if (s.phase == phase_t::reading ? !s.read.pending_read(s.command, 64) : !s.read.idle())
      throw std::runtime_error("incoherent syscall read child");
    if (s.phase == phase_t::writing ? !s.write.pending_write(s.command, payload(s.args)) : !s.write.idle())
      throw std::runtime_error("incoherent syscall write child");
    const bool executed = s.phase >= phase_t::writing;
    if (provider.has_exit != executed || provider.stopped ||
        provider.raw_exit != (executed ? uint32_t((s.args[1] << 1) | 1) : 0))
      throw std::runtime_error("incoherent syscall provider exit/writeback boundary");
  }
  state_t parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const auto start = config.bytes.size();
    if (image.size() < start+96 || !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("syscall configuration/payload mismatch");
    const auto phase = word(image, start);
    if (phase > 5) throw std::runtime_error("invalid syscall phase");
    state_t next; next.phase = phase_t(phase); next.command = word(image, start+8);
    for (unsigned i = 0; i < 8; ++i) next.args[i] = word(image, start+16+8*i);
    size_t at = start+80;
    auto child = [&]() {
      if (image.size()-at < 8) throw std::runtime_error("missing syscall child length");
      const auto size = word(image, at); at += 8;
      if (size > image.size()-at) throw std::runtime_error("truncated syscall child");
      std::vector<uint8_t> bytes(image.begin()+at, image.begin()+at+size); at += size; return bytes;
    };
    next.read.load_checkpoint(child()); next.write.load_checkpoint(child());
    if (at != image.size()) throw std::runtime_error("trailing syscall payload");
    validate(next, {phase >= 3, phase >= 3 ? uint32_t((next.args[1] << 1) | 1) : 0, false});
    return next;
  }
};
#endif
