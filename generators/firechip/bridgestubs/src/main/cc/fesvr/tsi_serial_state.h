// See LICENSE for license details.
#ifndef __FIRESIM_TSI_SERIAL_STATE_H
#define __FIRESIM_TSI_SERIAL_STATE_H

#include "core/widget_checkpoint.h"
#include <deque>
#include <limits>

// The two serial FIFOs only. A suspended read's destination and callers are
// separate owners; restoring these queues cannot restore the FESVR coroutine.
class firesim_tsi_serial_state_t final : public checkpoint_owner_t {
public:
  void swap_state(firesim_tsi_serial_state_t &other) noexcept {
    requests.swap(other.requests); responses.swap(other.responses);
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.serial-queues.v1"; }
  bool request_available() const { state.require_idle(); return !requests.empty(); }
  uint32_t request_front() const {
    state.require_idle();
    if (requests.empty()) throw std::runtime_error("empty TSI request queue");
    return requests.front();
  }
  bool response_available() const { state.require_idle(); return !responses.empty(); }
  uint32_t pop_request() {
    widget_checkpoint_state_t::call_t call(state);
    if (requests.empty()) throw std::runtime_error("empty TSI request queue");
    auto word = requests.front(); requests.pop_front(); return word;
  }
  uint32_t pop_response() {
    widget_checkpoint_state_t::call_t call(state);
    if (responses.empty()) throw std::runtime_error("empty TSI response queue");
    auto word = responses.front(); responses.pop_front(); return word;
  }
  void push_response(uint32_t word) {
    widget_checkpoint_state_t::call_t call(state); responses.push_back(word);
  }
  void tick(bool valid, uint32_t word, bool ready) {
    widget_checkpoint_state_t::call_t call(state);
    if (valid) responses.push_back(word);
    if (ready && !requests.empty()) requests.pop_front();
  }
  void issue_read(uint64_t address, size_t bytes) { issue(0, address, bytes, nullptr); }
  void issue_write(uint64_t address, size_t bytes, const void *source) { issue(1, address, bytes, source); }

  std::vector<uint8_t> save_checkpoint() const override {
    state.require_idle(); auto result = config;
    result.word(requests.size());
    for (auto word : requests) result.word(word);
    result.word(responses.size());
    for (auto word : responses) result.word(word);
    return std::move(result.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = parse(image);
    // Both queues and every word validate and allocate before either swap.
    requests.swap(next.first); responses.swap(next.second);
  }

private:
  widget_checkpoint_config_t config{19, {4, 2, 2, 1024}};
  widget_checkpoint_state_t state;
  std::deque<uint32_t> requests, responses;
  void issue(uint32_t command, uint64_t address, size_t bytes, const void *source) {
    state.require_idle();
    if (!bytes || bytes % 4 || bytes > 1024 || (command && !source))
      throw std::runtime_error("unsupported TSI serial chunk");
    widget_checkpoint_state_t::call_t call(state);
    auto next = requests;
    const uint64_t length = bytes / 4 - 1;
    next.push_back(command);
    next.push_back(uint32_t(address)); next.push_back(uint32_t(address >> 32));
    next.push_back(uint32_t(length)); next.push_back(uint32_t(length >> 32));
    if (command) {
      auto words = static_cast<const uint32_t *>(source);
      next.insert(next.end(), words, words + bytes / 4);
    }
    requests.swap(next);
  }
  std::pair<std::deque<uint32_t>, std::deque<uint32_t>>
  parse(const std::vector<uint8_t> &image) const {
    state.require_idle();
    const size_t start = config.bytes.size();
    if (image.size() < start + 16 || (image.size() - start) % 8 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("TSI serial configuration/payload mismatch");
    auto word = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[offset + i]) << (8 * i);
      return value;
    };
    const uint64_t nr = word(start);
    const size_t available = (image.size() - start) / 8;
    if (nr > available - 2) throw std::runtime_error("invalid TSI serial request count");
    const size_t response_offset = start + 8 + size_t(nr) * 8;
    const uint64_t ns = word(response_offset);
    if (ns != available - 2 - nr) throw std::runtime_error("invalid TSI serial response count");
    // Validate the entire payload before allocating any candidate FIFO.
    for (size_t offset = start + 8; offset < image.size(); offset += 8)
      if (offset != response_offset && word(offset) > std::numeric_limits<uint32_t>::max())
        throw std::runtime_error("wide TSI serial word");
    std::pair<std::deque<uint32_t>, std::deque<uint32_t>> next;
    for (size_t i = 0; i < nr; ++i) next.first.push_back(uint32_t(word(start + 8 + 8 * i)));
    for (size_t i = 0; i < ns; ++i) next.second.push_back(uint32_t(word(response_offset + 8 + 8 * i)));
    return next;
  }
};
#endif
