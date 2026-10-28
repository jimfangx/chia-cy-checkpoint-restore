// Public-port stream host transport tests. This is not CPU/FPGA acceptance.
#include "core/checkpoint_capture.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace {
unsigned checks = 0;
void check_impl(bool condition, unsigned line) {
  ++checks;
  if (!condition) throw std::runtime_error("host capture assertion " + std::to_string(checks) +
                                          " at source line " + std::to_string(line));
}
#define check(condition) check_impl((condition), __LINE__)
template <typename F> void rejects(F action) {
  bool rejected = false;
  try { action(); } catch (const std::runtime_error &) { rejected = true; }
  check(rejected);
}
uint32_t le32(const uint8_t *p) {
  return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
void rewrite_crc(std::vector<uint8_t> &frames) {
  uint32_t crc = 0xffffffff;
  for (size_t i = 0; i < frames.size() - 64; ++i) {
    crc ^= frames[i];
    for (unsigned bit = 0; bit < 8; ++bit)
      crc = (crc >> 1) ^ ((crc & 1) ? 0x82f63b78 : 0);
  }
  crc = ~crc;
  for (unsigned i = 0; i < 4; ++i) frames[frames.size() - 36 + i] = crc >> (8*i);
}

class fake_io : public checkpoint_capture_io_t {
public:
  const checkpoint_capture_manifest_t manifest;
  const std::vector<uint8_t> frames;
  uint64_t cycle;
  unsigned commands = 0, publications = 0, polls = 0, ack = 0;
  uint32_t forced_status = 0, forced_error = 0;
  bool wrong_hash = false, wrong_count = false, wrong_crc = false, bad_size = false;
  bool wrong_entry_count = false;
  bool invalid = false, active = false, empty_transfer = true, pending = false;
  uint64_t produced = 0, drained = 0;
  uint32_t shadow_bits = 1169, shadow_index = 0;
  unsigned shadow_captures = 0, shadow_releases = 0, shadow_discards = 0;
  unsigned shadow_fault = 0;
  bool shadow_valid = false;
  std::vector<uint64_t> shadow_words;
  size_t cursor = 0;
  fake_io(checkpoint_capture_manifest_t m, std::vector<uint8_t> f, uint64_t c)
      : manifest(std::move(m)), frames(std::move(f)), cycle(c) {}
  uint32_t read_capture_mmio(uint32_t offset) override {
    switch (offset) {
    case 0x04:
      if (shadow_fault == 9 && shadow_captures) return 1;
      if (pending) { pending = false; return 32; }
      return forced_status ? forced_status : active ? (cursor == frames.size() ? 14 : 6) : 1;
    case 0x08: return forced_error;
    case 0x10: return uint32_t(cycle);
    case 0x14: return uint32_t(cycle >> 32);
    case 0x18: return uint32_t(frames.size() / 64 - 2) + wrong_count;
    case 0x1c: return 0;
    case 0x20: return manifest.entries.size() + wrong_entry_count;
    case 0x24: return le32(frames.data() + frames.size() - 36) ^ wrong_crc;
    case 0x60: return invalid;
    case 0x68: return uint32_t(produced);
    case 0x6c: return uint32_t(produced >> 32);
    case 0x7c: return shadow_index ^ (shadow_fault == 4);
    case 0x80:
      if (shadow_fault == 8 && shadow_index == 3)
        throw std::runtime_error("partial shadow read failure");
      return uint32_t(shadow_words.at(shadow_index));
    case 0x84: return uint32_t(shadow_words.at(shadow_index) >> 32);
    case 0x88: return shadow_fault == 7 && shadow_captures ? 0 : shadow_valid;
    case 0x8c: return uint32_t(cycle + (shadow_fault == 3 ||
        (shadow_fault == 10 && shadow_index + 1 == shadow_words.size())));
    case 0x90: return uint32_t(cycle >> 32);
    case 0x98: return shadow_fault == 11 ? 1 : 2;
    case 0x9c: return shadow_bits + (shadow_fault == 12);
    case 0x94: return (shadow_bits + 63) / 64 + (shadow_fault == 1);
    default:
      if (offset >= 0x40 && offset < 0x60)
        return le32(manifest.wire_hash.data() + offset - 0x40) ^ wrong_hash;
      throw std::runtime_error("unexpected MMIO read");
    }
  }
  void write_capture_mmio(uint32_t offset, uint32_t value) override {
    ++commands;
    if (offset == 0x78) {
      if (value == 1) {
        check(active && cursor == frames.size() && !shadow_valid);
        shadow_valid = true;
        ++shadow_captures;
        shadow_words.resize((shadow_bits + 63) / 64);
        for (size_t i = 0; i < shadow_words.size(); ++i)
          shadow_words[i] = 0x123456789abcdef0ULL ^ i;
        if (shadow_bits % 64)
          shadow_words.back() &= (uint64_t(1) << (shadow_bits % 64)) - 1;
        if (shadow_fault == 5) shadow_words.back() |= uint64_t(1) << (shadow_bits % 64);
        if (shadow_fault == 2) throw std::runtime_error("accepted shadow write transport failure");
      } else if (value == 2) {
        check(shadow_valid);
        if (shadow_fault != 6) shadow_valid = false;
        ++shadow_releases;
      } else if (value == 4) {
        shadow_valid = false;
        ++shadow_discards;
      } else throw std::runtime_error("invalid shadow command");
    } else if (offset == 0x7c) {
      check(shadow_valid && value < shadow_words.size());
      shadow_index = value;
    } else if (offset == 0x64 && value == 1) {
      check(!active && !pending && cursor == frames.size() && drained == produced); invalid = false; ++ack;
    } else if (offset == 0x70) {
      drained = (drained & 0xffffffff00000000ULL) | value;
    } else if (offset == 0x74) {
      drained = (drained & 0xffffffff) | (uint64_t(value) << 32);
    } else if (offset == 0 && value == 1) {
      check(!invalid && !active); active = true; cursor = 0; produced += frames.size()/64;
    } else if (offset == 0 && value == 2) {
      check(active && cursor == frames.size() && !invalid); active = false; ++publications;
    } else if (offset == 0 && value == 4) {
      active = false; invalid = true; pending = true;
    } else throw std::runtime_error("unexpected MMIO write");
  }
  size_t pull_capture_stream(void *buffer, size_t capacity) override {
    check(reinterpret_cast<uintptr_t>(buffer) % 4096 == 0 && capacity % 64 == 0);
    ++polls;
    if (bad_size) return capacity + 1;
    if (empty_transfer && polls % 3 == 1) return 0;
    const size_t count = std::min({capacity, frames.size() - cursor, size_t(128)});
    std::memcpy(buffer, frames.data() + cursor, count);
    cursor += count;
    return count;
  }
  void flush_capture_stream() override {}
};

// Interrupt every individual public MMIO operation on either side of its
// possible acceptance. This models an ambiguous host transfer, not corruption
// of the immutable staging payload or the hardware's cut/ownership contract.
class interrupted_io : public fake_io {
public:
  using fake_io::fake_io;
  unsigned operations = 0, fail_at = 0;
  unsigned corrupt_at_end = 0;
  bool saw_last_word = false;
  bool after = false, release_attempted = false;
  void corrupt(unsigned fault) {
    switch (fault) {
    case 1: wrong_hash = true; break;
    case 2: forced_status = 1; break;
    case 3: invalid = true; break;
    case 4: ++cycle; break;
    case 5: ++produced; break;
    case 6: ++shadow_bits; break;
    case 7: shadow_fault = 4; break;
    case 8: shadow_words.back() |= uint64_t(1) << (shadow_bits % 64); break;
    case 9: wrong_entry_count = true; break;
    case 10: forced_error = 1; break;
    case 11: shadow_fault = 11; break;
    case 12: shadow_fault = 1; break;
    case 13: shadow_valid = false; break;
    case 14: shadow_fault = 3; break;
    default: throw std::runtime_error("invalid metadata fault selector");
    }
  }
  void interrupt(bool accepted) {
    if (operations == fail_at && accepted == after) {
      fail_at = 0;
      throw std::runtime_error("injected interrupted MMIO operation");
    }
  }
  uint32_t read_capture_mmio(uint32_t offset) override {
    ++operations;
    if (offset == 0x04 && saw_last_word && corrupt_at_end) {
      const auto fault = corrupt_at_end;
      corrupt_at_end = 0;
      corrupt(fault);
    }
    interrupt(false);
    const auto value = fake_io::read_capture_mmio(offset);
    if (offset == 0x84 && shadow_index + 1 == shadow_words.size())
      saw_last_word = true;
    interrupt(true);
    return value;
  }
  void write_capture_mmio(uint32_t offset, uint32_t value) override {
    ++operations;
    if (offset == 0x78 && value == 2) release_attempted = true;
    interrupt(false);
    fake_io::write_capture_mmio(offset, value);
    interrupt(true);
  }
};

static_assert(!std::is_copy_constructible<checkpoint_capture_session_t>::value &&
              !std::is_move_constructible<checkpoint_capture_session_t>::value,
              "a live session exclusively owns its staging epoch");
} // namespace

int main(int argc, char **argv) {
  try {
    check(argc == 4);
    std::ifstream image(argv[1], std::ios::binary);
    std::vector<uint8_t> frames((std::istreambuf_iterator<char>(image)), {});
    std::ifstream metadata(argv[2]);
    checkpoint_capture_manifest_t manifest;
    unsigned value, count;
    for (auto &byte : manifest.wire_hash) { metadata >> value; check(value < 256); byte = value; }
    metadata >> count;
    for (unsigned i = 0; i < count; ++i) {
      unsigned bank, slot, width, depth;
      metadata >> bank >> slot >> width >> depth;
      check(bank < 256 && slot < 65536 && width <= 64 && depth);
      manifest.entries.push_back({uint8_t(bank), uint16_t(slot), uint16_t(width), depth});
    }
    check(bool(metadata));
    const uint64_t cycle = std::stoull(argv[3]);
    checkpoint_capture_session_t::validate_frames(frames, manifest, cycle);
    for (size_t i = 0; i < frames.size(); ++i) {
      auto damaged = frames; damaged[i] ^= 1;
      rejects([&] { checkpoint_capture_session_t::validate_frames(damaged, manifest, cycle); });
    }
    for (size_t i = 0; i < frames.size(); ++i) {
      auto short_image = frames; short_image.resize(i);
      rejects([&] { checkpoint_capture_session_t::validate_frames(short_image, manifest, cycle); });
    }
    for (unsigned offset : {0, 8, 10, 12, 20, 28, 32, 36, 38, 39, 41, 50, 63}) {
      auto damaged = frames; damaged[64 + offset] ^= 1; rewrite_crc(damaged);
      rejects([&] { checkpoint_capture_session_t::validate_frames(damaged, manifest, cycle); });
    }
    auto bad_manifest = manifest;
    bad_manifest.wire_hash[0] ^= 1;
    rejects([&] { checkpoint_capture_session_t::validate_frames(frames, bad_manifest, cycle); });
    rejects([&] { checkpoint_capture_session_t::validate_frames(frames, manifest, cycle + 1); });
    // Observation staging remains independent of the validated frame image.
    for (uint32_t bits : {1169U, 1242U}) {
      fake_io io(manifest, frames, cycle);
      io.shadow_bits = bits;
      checkpoint_capture_session_t session(io, manifest);
      rejects([&] { session.capture_live_widget_shadow(bits); });
      session.begin();
      for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
      for (uint32_t bad : {0U, 639U, 712U, 1170U, 1239U, 66775U, 0xffffffffU})
        rejects([&] { session.capture_live_widget_shadow(bad); });
      check(session.phase() == checkpoint_capture_session_t::phase_t::validated);
      for (unsigned capture = 0; capture < 2; ++capture) {
        auto observed = session.capture_live_widget_shadow(bits);
        check(observed.bits == bits && observed.cut_cycle == cycle &&
              observed.words == io.shadow_words && !io.shadow_valid);
        check(io.active && io.publications == 0 && session.validated_frames() == frames);
      }
      check(io.shadow_captures == 2 && io.shadow_releases == 2 && io.shadow_discards == 0);
      session.release_after_publication();
    }
    for (unsigned fault = 0; fault < 13; ++fault) {
      fake_io io(manifest, frames, cycle);
      checkpoint_capture_session_t session(io, manifest);
      session.begin();
      for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
      if (fault == 0) io.shadow_valid = true; // retain an existing foreign epoch
      else io.shadow_fault = fault;
      rejects([&] { session.capture_live_widget_shadow(1169); });
      check(session.phase() == checkpoint_capture_session_t::phase_t::failed && io.active &&
            io.publications == 0);
      if (fault == 0) check(io.shadow_valid && io.shadow_captures == 0 && io.shadow_discards == 0);
      io.shadow_fault = 0;
      for (unsigned i = 0; !session.abort_and_drain(); ++i) check(i < 100);
      if (fault > 1 && fault < 11) check(!io.shadow_valid && io.shadow_discards == 1);
      if (fault >= 11) check(io.shadow_captures == 0 && io.shadow_discards == 0);
      if (fault == 0) check(io.shadow_valid); // abort never discards foreign history
      check(session.phase() == checkpoint_capture_session_t::phase_t::idle);
    }
    std::cout << "CHECKPOINT_WIDGET_SHADOW_HOST_PASS widths=2 captures=4 failures=13\n";
    unsigned retried = 0, rejected = 0, fault_operations = 0;
    for (uint32_t bits : {1169U, 1242U, 1245U}) {
      interrupted_io baseline(manifest, frames, cycle);
      baseline.shadow_bits = bits;
      checkpoint_capture_session_t reference(baseline, manifest);
      reference.begin();
      for (unsigned i = 0; !reference.poll(); ++i) check(i < 100);
      baseline.operations = 0;
      const auto expected = reference.capture_live_widget_shadow(bits);
      const unsigned operations = baseline.operations;
      check(operations > 100);
      fault_operations += operations;
      for (bool after : {false, true}) {
        for (unsigned op = 1; op <= operations; ++op) {
          interrupted_io io(manifest, frames, cycle);
          io.shadow_bits = bits;
          checkpoint_capture_session_t session(io, manifest);
          session.begin();
          for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
          io.operations = 0; io.fail_at = op; io.after = after;
          rejects([&] { session.capture_live_widget_shadow(bits); });
          check(session.phase() == checkpoint_capture_session_t::phase_t::failed &&
                io.active && io.publications == 0 && io.shadow_discards == 0);
          const auto saved = io.shadow_words;
          const bool retryable = io.shadow_valid && io.shadow_captures == 1 && !io.release_attempted;
          const unsigned before = io.operations;
          rejects([&] { session.capture_live_widget_shadow(bits); });
          rejects([&] { session.release_after_publication(); });
          rejects([&] { session.retry_live_widget_shadow(bits + 1); });
          checkpoint_capture_session_t foreign(io, manifest);
          rejects([&] { foreign.retry_live_widget_shadow(bits); });
          check(io.operations == before && io.shadow_words == saved);
          if (retryable) {
            const auto actual = session.retry_live_widget_shadow(bits);
            check(actual.bits == expected.bits && actual.cut_cycle == expected.cut_cycle &&
                  actual.words == expected.words && actual.words == saved);
            check(!io.shadow_valid && io.shadow_captures == 1 && io.shadow_releases == 1 &&
                  io.shadow_discards == 0 && io.active && io.publications == 0 &&
                  session.phase() == checkpoint_capture_session_t::phase_t::validated &&
                  session.validated_frames() == frames);
            const unsigned completed = io.operations;
            rejects([&] { session.retry_live_widget_shadow(bits); });
            check(io.operations == completed);
            session.release_after_publication();
            ++retried;
          } else {
            rejects([&] { session.retry_live_widget_shadow(bits); });
            check(io.shadow_words == saved && io.shadow_captures <= 1 && io.publications == 0);
            for (unsigned i = 0; !session.abort_and_drain(); ++i) check(i < 100);
            ++rejected;
          }
        }
      }
    }
    // A second interruption must retain the same bank, while observed invalid
    // metadata irrevocably revokes retry even if the input later looks healthy.
    unsigned invalid_epochs = 0;
    for (bool late : {false, true}) {
      for (unsigned fault = 0; fault < 15; ++fault) {
        // Selector/padding faults belong to word collection. Other metadata is
        // also changed after the last payload read, at the final identity check.
        if (late && (fault == 0 || fault == 7 || fault == 8)) continue;
        interrupted_io io(manifest, frames, cycle);
        checkpoint_capture_session_t session(io, manifest);
        session.begin();
        for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
        io.shadow_fault = 8;
        rejects([&] { session.capture_live_widget_shadow(1169); });
        io.shadow_fault = 0;
        const auto saved = io.shadow_words;
        if (fault == 0) {
          io.fail_at = io.operations + 7;
          rejects([&] { session.retry_live_widget_shadow(1169); });
          check(io.shadow_valid && io.shadow_captures == 1 && io.shadow_words == saved);
          const auto actual = session.retry_live_widget_shadow(1169);
          check(actual.words == saved && io.shadow_captures == 1 && io.shadow_releases == 1);
          session.release_after_publication();
        } else {
          if (late) io.corrupt_at_end = fault;
          else io.corrupt(fault);
          rejects([&] { session.retry_live_widget_shadow(1169); });
          io.wrong_hash = false; io.forced_status = 0; io.invalid = false;
          io.cycle = cycle; io.produced = frames.size() / 64;
          io.shadow_bits = 1169; io.shadow_fault = 0; io.shadow_words = saved;
          io.wrong_entry_count = false; io.forced_error = 0; io.shadow_valid = true;
          const unsigned before = io.operations;
          rejects([&] { session.retry_live_widget_shadow(1169); });
          check(io.operations == before && io.shadow_valid && io.shadow_captures == 1 &&
                io.shadow_releases == 0 && io.shadow_discards == 0 && io.publications == 0);
          for (unsigned i = 0; !session.abort_and_drain(); ++i) check(i < 100);
          ++invalid_epochs;
        }
      }
    }
    check(invalid_epochs == 26);
    check(retried > 600 && rejected > 40 && retried + rejected == 2 * fault_operations);
    std::cout << "CHECKPOINT_WIDGET_SHADOW_RETRY_PASS widths=3 retried=" << retried
              << " rejected=" << rejected << " operations=" << fault_operations
              << " repeated=1 invalid=" << invalid_epochs << "\n";
    for (unsigned capture = 0; capture < 2; ++capture) {
      fake_io io(manifest, frames, cycle);
      checkpoint_capture_session_t session(io, manifest);
      rejects([&] { session.validated_frames(); });
      rejects([&] { session.release_after_publication(); });
      session.begin();
      rejects([&] { session.begin(); });
      for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
      check(io.active && io.publications == 0 && session.cut_cycle() == cycle);
      check(session.validated_frames() == frames && session.poll());
      session.release_after_publication();
      check(!io.active && io.publications == 1 && session.phase() == checkpoint_capture_session_t::phase_t::idle);
      // Reuse the same object, with no stale stream words entering its next cut.
      session.begin();
      for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
      session.release_after_publication();
      check(io.publications == 2);
    }
    for (unsigned fault = 0; fault < 8; ++fault) {
      fake_io io(manifest, frames, cycle);
      checkpoint_capture_session_t session(io, manifest);
      session.begin();
      switch (fault) {
      case 0: io.forced_status = 16; break;
      case 1: io.forced_status = 1; break;
      case 2: io.forced_error = 1; break;
      case 3: io.invalid = true; break;
      case 4: io.wrong_count = true; break;
      case 5: io.wrong_crc = true; break;
      case 6: io.bad_size = true; break;
      case 7: ++io.cycle; break;
      }
      rejects([&] { for (unsigned i = 0; i < 100; ++i) if (session.poll()) break; });
      check(session.phase() == checkpoint_capture_session_t::phase_t::failed);
      rejects([&] { session.validated_frames(); });
      rejects([&] { session.release_after_publication(); });
      check(io.publications == 0);
      if (fault == 6) {
        // The platform reported an impossible byte count. Consumed history is
        // unknowable; recovery must require a coordinated endpoint/stream reset.
        rejects([&] { session.abort_and_drain(); });
        continue;
      }
      io.forced_status = io.forced_error = 0;
      io.bad_size = io.wrong_count = io.wrong_crc = false;
      io.cycle = cycle;
      for (unsigned i = 0; !session.abort_and_drain(); ++i) check(i < 100);
      check(!io.invalid && !io.active && io.ack == 1);
      session.begin();
      for (unsigned i = 0; !session.poll(); ++i) check(i < 100);
      session.release_after_publication();
      check(io.publications == 1);
    }
    fake_io incompatible(manifest, frames, cycle);
    incompatible.wrong_hash = true;
    checkpoint_capture_session_t incompatible_session(incompatible, manifest);
    rejects([&] { incompatible_session.begin(); });
    check(incompatible.commands == 0);
    std::cout << "CHECKPOINT_CAPTURE_HOST_PASS checks=" << checks << "\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << "\n"; return 1;
  }
}
