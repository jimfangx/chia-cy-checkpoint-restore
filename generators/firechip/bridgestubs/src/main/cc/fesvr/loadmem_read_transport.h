// See LICENSE for license details.
#ifndef __FIRESIM_LOADMEM_READ_TRANSPORT_H
#define __FIRESIM_LOADMEM_READ_TRANSPORT_H

#include "bridges/loadmem.h"
#include <algorithm>
#include <limits>
#include <stdexcept>

// Synchronous transport only. The caller/queues, MMIO and generated memory
// pipeline are separate Level-1 owners; no checkpoint can cut inside this call.
template <class SendWord>
void firesim_read_loadmem(loadmem_t &memory, uint64_t address, size_t bytes,
                          int64_t host_offset, SendWord send_word) {
  constexpr size_t word_bytes = sizeof(uint32_t);
  const auto maximum = std::numeric_limits<uint64_t>::max();
  const size_t chunk = memory.get_mem_data_chunk();
  if (!bytes || bytes > 4096 || bytes % word_bytes || address % word_bytes ||
      !chunk || (chunk & (chunk - 1)) || chunk > 4096 / word_bytes ||
      bytes - 1 > maximum - address)
    throw std::runtime_error("unsupported TSI loadmem read request");

  // Avoid unsigned wrap, including negation of INT64_MIN, before any MMIO or
  // response publication. Validate the entire translated range first.
  uint64_t host_address;
  if (host_offset < 0) {
    const uint64_t magnitude = uint64_t(-(host_offset + 1)) + 1;
    if (address < magnitude)
      throw std::runtime_error("TSI loadmem read host address underflow");
    host_address = address - magnitude;
  } else {
    if (uint64_t(host_offset) > maximum - address)
      throw std::runtime_error("TSI loadmem read host address overflow");
    host_address = address + uint64_t(host_offset);
  }
  if (host_address % word_bytes || bytes - 1 > maximum - host_address)
    throw std::runtime_error("unsupported TSI loadmem read host range");

  const size_t beat_bytes = chunk * word_bytes;
  std::vector<uint32_t> data(chunk);
  struct value_t {
    mpz_t value;
    value_t() { mpz_init(value); }
    ~value_t() { mpz_clear(value); }
  } buffer;
  while (bytes) {
    // The widget returns a whole host-memory beat. Select the requested lanes
    // explicitly, including a narrow request starting inside a wider beat.
    const size_t lane = (host_address % beat_bytes) / word_bytes;
    memory.read_mem(host_address - host_address % beat_bytes, buffer.value);
    std::fill(data.begin(), data.end(), 0);
    mpz_export(data.data(), nullptr, -1, word_bytes, 0, 0, buffer.value);
    const size_t words = std::min(bytes / word_bytes, chunk - lane);
    for (size_t i = 0; i < words; ++i)
      send_word(data[lane + i]);
    const size_t consumed = words * word_bytes;
    bytes -= consumed;
    if (bytes)
      host_address += consumed;
  }
}

#endif // __FIRESIM_LOADMEM_READ_TRANSPORT_H
