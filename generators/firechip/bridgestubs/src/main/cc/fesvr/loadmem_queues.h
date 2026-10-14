// See LICENSE for license details.
#ifndef __FIRESIM_LOADMEM_QUEUES_H
#define __FIRESIM_LOADMEM_QUEUES_H

#include "core/widget_checkpoint.h"
#include <deque>
#include <limits>
#include <memory>

// The four production TSI load-memory queues, including bytes belonging to a
// write request already handed to the bridge. HTIF/context, the read operation
// and bridge MMIO remain independent owners; this does not authorize CPU cuts.
class firesim_loadmem_queues_t final : public checkpoint_owner_t {
public:
  struct request_t { uint64_t address, bytes; };
  void enqueue_write(uint64_t address, uint64_t bytes, const void *source) {
    boundary.require_idle();
    check_request({address, bytes});
    if (!source) throw std::runtime_error("null loadmem write source");
    widget_checkpoint_state_t::call_t call(boundary);
    const auto *data = static_cast<const uint8_t *>(source);
    state->write_data.insert(state->write_data.end(), data, data + bytes);
    state->writes.push_back({address, bytes});
  }
  void enqueue_read(uint64_t address, uint64_t bytes) {
    boundary.require_idle();
    check_request({address, bytes});
    widget_checkpoint_state_t::call_t call(boundary);
    state->reads.push_back({address, bytes});
  }
  bool pop_write(request_t &request) {
    boundary.require_idle();
    if (state->active.bytes)
      throw std::runtime_error("previous loadmem write data not drained");
    if (state->writes.empty()) return false;
    request = state->writes.front();
    state->active = request;
    state->consumed = 0;
    state->writes.pop_front();
    return true;
  }
  bool pop_read(request_t &request) {
    boundary.require_idle();
    if (state->reads.empty()) return false;
    request = state->reads.front(); state->reads.pop_front(); return true;
  }
  void pop_write_data(void *destination, size_t bytes) {
    boundary.require_idle();
    if (!destination || !bytes || !state->active.bytes ||
        bytes > state->active.bytes - state->consumed)
      throw std::runtime_error("invalid loadmem write-data drain");
    auto *data = static_cast<uint8_t *>(destination);
    for (size_t i = 0; i < bytes; ++i) {
      data[i] = state->write_data.front(); state->write_data.pop_front();
    }
    state->consumed += bytes;
    if (state->consumed == state->active.bytes) {
      state->active = {0, 0}; state->consumed = 0;
    }
  }
  void push_response(uint32_t word) {
    widget_checkpoint_state_t::call_t call(boundary);
    state->responses.push_back(word);
  }
  bool pop_response(uint32_t &word) {
    boundary.require_idle();
    if (state->responses.empty()) return false;
    word = state->responses.front(); state->responses.pop_front(); return true;
  }
  bool writes_pending() const {
    boundary.require_idle();
    return state->active.bytes || !state->writes.empty();
  }
  bool requests_pending() const {
    return writes_pending() || !state->reads.empty();
  }
  std::string checkpoint_schema() const override { return "firesim.tsi.loadmem-queues.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    boundary.require_idle();
    auto result = configuration();
    result.word(state->active.address); result.word(state->active.bytes);
    result.word(state->consumed);
    for (const auto *queue : {&state->writes, &state->reads}) {
      result.word(queue->size());
      for (auto request : *queue) { result.word(request.address); result.word(request.bytes); }
    }
    result.word(state->write_data.size());
    result.bytes.insert(result.bytes.end(), state->write_data.begin(), state->write_data.end());
    result.word(state->responses.size());
    for (auto word : state->responses) result.word(word);
    return std::move(result.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &payload) const override { parse(payload); }
  void load_checkpoint(const std::vector<uint8_t> &payload) override {
    auto next = parse(payload); // Validate and allocate every queue before mutation.
    state.swap(next);           // No-throw commit, with no dequeue or bridge I/O.
  }
private:
  static constexpr uint64_t max_bytes = 4096;
  struct state_t {
    std::deque<request_t> writes, reads;
    std::deque<uint8_t> write_data;
    std::deque<uint32_t> responses;
    request_t active{0, 0};
    uint64_t consumed = 0;
  };
  std::unique_ptr<state_t> state = std::make_unique<state_t>();
  widget_checkpoint_state_t boundary;
  static widget_checkpoint_config_t configuration() { return {16, {max_bytes, 4}}; }
  static void check_request(request_t request) {
    if (!request.bytes || request.bytes > max_bytes || request.bytes % 4 || request.address % 4 ||
        request.address > std::numeric_limits<uint64_t>::max() - (request.bytes - 1))
      throw std::runtime_error("invalid loadmem queue request");
  }
  std::unique_ptr<state_t> parse(const std::vector<uint8_t> &payload) const {
    boundary.require_idle();
    const auto config = configuration();
    if (payload.size() < config.bytes.size() ||
        !std::equal(config.bytes.begin(), config.bytes.end(), payload.begin()))
      throw std::runtime_error("loadmem queues configuration mismatch");
    size_t cursor = config.bytes.size();
    auto word = [&]() {
      if (payload.size() - cursor < 8) throw std::runtime_error("truncated loadmem queue word");
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(payload[cursor++]) << (8 * i);
      return value;
    };
    auto next = std::make_unique<state_t>();
    next->active = {word(), word()}; next->consumed = word();
    uint64_t expected_bytes = 0;
    if (next->active.bytes) {
      check_request(next->active);
      if (next->consumed >= next->active.bytes) throw std::runtime_error("invalid active write cursor");
      expected_bytes = next->active.bytes - next->consumed;
    } else if (next->active.address || next->consumed) {
      throw std::runtime_error("nonempty idle write cursor");
    }
    for (auto *queue : {&next->writes, &next->reads}) {
      const auto count = word();
      if (count > (payload.size() - cursor) / 16) throw std::runtime_error("invalid request queue length");
      for (uint64_t i = 0; i < count; ++i) {
        request_t request{word(), word()}; check_request(request);
        if (queue == &next->writes) {
          if (request.bytes > std::numeric_limits<uint64_t>::max() - expected_bytes)
            throw std::runtime_error("loadmem write byte-count overflow");
          expected_bytes += request.bytes;
        }
        queue->push_back(request);
      }
    }
    const auto count = word();
    if (count != expected_bytes || count > payload.size() - cursor)
      throw std::runtime_error("incomplete loadmem write data");
    next->write_data.insert(next->write_data.end(), payload.begin() + cursor, payload.begin() + cursor + count);
    cursor += count;
    const auto responses = word();
    if (responses > (payload.size() - cursor) / 8 || payload.size() - cursor != responses * 8)
      throw std::runtime_error("invalid response queue length/trailing data");
    for (uint64_t i = 0; i < responses; ++i) {
      const auto value = word();
      if (value > std::numeric_limits<uint32_t>::max()) throw std::runtime_error("invalid response queue word");
      next->responses.push_back(value);
    }
    return next;
  }
};
#endif
