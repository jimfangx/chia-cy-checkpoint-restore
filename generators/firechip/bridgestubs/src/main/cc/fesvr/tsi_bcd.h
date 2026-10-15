// See LICENSE for license details.
#ifndef __FIRESIM_TSI_BCD_H
#define __FIRESIM_TSI_BCD_H

#include "core/widget_checkpoint.h"
#include "tsi_terminal.h"
#include "tsi_htif_poll.h"
#include <fesvr/device.h>
#include <fesvr/memif.h>
#include <fesvr/term.h>
#include <array>
#include <deque>

// Default HTIF device 1. Upstream bcd_t retains command_t callbacks into the
// suspended run loop. Keep raw commands instead and bind responses to the
// destination polling owner at construction. The terminal is an external
// service, NOT checkpointed here; this is not complete HTIF/CPU ownership.
class firesim_tsi_bcd_t final : public device_t, public checkpoint_owner_t {
public:
  using response_t = std::function<void(uint64_t)>;
  explicit firesim_tsi_bcd_t(response_t response, uint64_t limit = 1048576,
                            firesim_tsi_terminal_t *terminal = nullptr)
      : config(26, {1, limit}), response(std::move(response)), limit(limit), terminal(terminal) {
    if (!this->response || !limit || limit > 1048576)
      throw std::runtime_error("unsupported BCD response binding/queue limit");
    register_command(0, [this](command_t cmd) {
      widget_checkpoint_state_t::call_t call(boundary);
      if (cmd.device() != 1 || pending.size() == this->limit)
        throw std::runtime_error("BCD device/queue limit mismatch");
      pending.push_back((uint64_t(cmd.device()) << 56) |
                        (uint64_t(cmd.cmd()) << 48) | cmd.payload());
    }, "read");
    register_command(1, [this](command_t cmd) {
      widget_checkpoint_state_t::call_t call(boundary);
      if (cmd.device() != 1) throw std::runtime_error("BCD device mismatch");
      if (this->terminal) this->terminal->write(cmd.payload());
      else canonical_terminal_t::write(cmd.payload());
    }, "write");
    register_command(255, [this](command_t cmd) {
      widget_checkpoint_state_t::call_t call(boundary);
      if (cmd.device() != 1) throw std::runtime_error("BCD device mismatch");
      // Same 64-byte command/identity table as installed device_t/bcd_t.
      std::array<char, 64> name{};
      const auto what = cmd.payload() % 256;
      const char *text = what == 0 ? "read" : what == 1 ? "write" :
                         what == 255 ? "bcd" : "";
      std::copy(text, text + std::strlen(text), name.begin());
      cmd.memif().write(cmd.payload() / 256, name.size(), name.data());
      cmd.respond(1);
    }, "identity");
  }
  // This binding permits a transaction over the actual response destination.
  // An arbitrary callback cannot establish ownership of a polling queue.
  explicit firesim_tsi_bcd_t(firesim_tsi_htif_poll_t &poll, uint64_t limit = 1048576,
                            firesim_tsi_terminal_t *terminal = nullptr)
      : firesim_tsi_bcd_t([&poll](uint64_t value) { poll.respond(value); }, limit, terminal) {
    bound_poll = &poll;
  }
  const char *identity() override { return "bcd"; }
  void tick() override {
    widget_checkpoint_state_t::call_t call(boundary);
    if (pending.empty()) return;
    const int ch = terminal ? terminal->read() : canonical_terminal_t::read();
    if (ch == -1) return;
    response((pending.front() & 0xffff000000000000ULL) | (0x100 | ch));
    pending.pop_front();
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.bcd.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle(); auto out = config; out.word(pending.size());
    for (auto command : pending) out.word(command);
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = parse(image); pending.swap(next);
  }
  // Component transaction only: the poll response queue and all other HTIF
  // owners must be restored separately before a complete caller can resume.
  // Ordered names are part of this interface: missing/extra/reordered peers
  // cannot silently select a partial restore. Use the terminal bound to this
  // device, never a caller-supplied replacement with different service wiring.
  using sealed_checkpoint_t = std::vector<std::pair<std::string, std::vector<uint8_t>>>;
  void load_sealed_checkpoint(const sealed_checkpoint_t &images) {
    if (!terminal || images.size() != 2 || images[0].first != "terminal" || images[1].first != "bcd")
      throw std::runtime_error("sealed BCD restore requires ordered terminal and BCD owners");
    // Both parses check supported/idle boundaries and allocate all replacement
    // storage before publication. validate+load would parse/allocate a second
    // time and could fail after changing the first owner.
    auto next_terminal = terminal->parse(images[0].second);
    auto next_pending = parse(images[1].second);
    static_assert(noexcept(pending.swap(next_pending)), "BCD commit must not allocate");
    terminal->commit(next_terminal);
    pending.swap(next_pending);
  }
  // Three-owner component transaction. Serial transport, syscall, startup,
  // signal/exit and context owners remain outside this group. Ordered images
  // must come from a caller-validated coherent cut; membership alone cannot
  // prove their provenance. Never resume a complete TSI from just this group.
  void load_sealed_polling_checkpoint(const sealed_checkpoint_t &images) {
    if (!bound_poll || !terminal || images.size() != 3 || images[0].first != "poll" ||
        images[1].first != "terminal" || images[2].first != "bcd")
      throw std::runtime_error("sealed polling restore requires bound poll, terminal and BCD owners");
    auto next_terminal = terminal->parse(images[1].second);
    auto next_pending = parse(images[2].second);
    auto next_poll = bound_poll->parse(images[0].second);
    static_assert(noexcept(pending.swap(next_pending)), "BCD commit must not allocate");
    terminal->commit(next_terminal);
    pending.swap(next_pending);
    bound_poll->commit(next_poll);
  }
private:
  widget_checkpoint_config_t config;
  const response_t response;
  const uint64_t limit;
  firesim_tsi_terminal_t *const terminal;
  firesim_tsi_htif_poll_t *bound_poll = nullptr;
  std::deque<uint64_t> pending;
  widget_checkpoint_state_t boundary;
  std::deque<uint64_t> parse(const std::vector<uint8_t> &image) const {
    boundary.require_idle(); const size_t start = config.bytes.size();
    if (image.size() < start + 8 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("BCD configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto count = word(start);
    if (count > limit || image.size() != start + 8 + 8*count)
      throw std::runtime_error("BCD queue length mismatch");
    std::deque<uint64_t> next;
    for (size_t i = 0; i < count; ++i) {
      const auto command = word(start + 8 + 8*i);
      if ((command >> 48) != 0x100)
        throw std::runtime_error("BCD pending command is not device 1/read");
      next.push_back(command);
    }
    return next;
  }
};
#endif
