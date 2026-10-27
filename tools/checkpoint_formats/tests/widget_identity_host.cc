// Exercise the actual generated initializer and production frame validator.
// Component VCS frames are not hardware checkpoints.
#include "bridges/checkpoint_capture.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <type_traits>

static_assert(std::is_constructible_v<checkpoint_capture_t, simif_t &,
              StreamEngine &, size_t, unsigned, checkpoint_capture_manifest_t>);

int main(int argc, char **argv) {
  try {
    const auto manifest =
#include "bound_manifest.svh"
        ;
    if (argc != 5 || manifest.entries.size() != 7)
      throw std::runtime_error("complete four-cut manifest exercise required");
    unsigned checks = 0;
    for (int i = 1; i < argc; ++i) {
      std::ifstream stream(argv[i], std::ios::binary);
      if (!stream) throw std::runtime_error("missing VCS capture stream");
      std::vector<uint8_t> frames((std::istreambuf_iterator<char>(stream)), {});
      if (frames.size() != 36 * 64) throw std::runtime_error("incomplete frame input");
      uint64_t cycle = 0;
      for (unsigned b = 0; b < 8; ++b) cycle |= uint64_t(frames[12 + b]) << (8*b);
      checkpoint_capture_session_t::validate_frames(frames, manifest, cycle);
      ++checks;
      auto reject = [&](const std::vector<uint8_t> &bad,
                        const checkpoint_capture_manifest_t &metadata) {
        bool caught = false;
        try { checkpoint_capture_session_t::validate_frames(bad, metadata, cycle); }
        catch (const std::exception &) { caught = true; }
        if (!caught) throw std::runtime_error("bad identity/frame accepted");
        ++checks;
      };
      auto wrong = manifest; wrong.wire_hash[0] ^= 1; reject(frames, wrong);
      wrong = manifest; wrong.entries[0].slot ^= 1; reject(frames, wrong);
      auto bad = frames; bad.resize(bad.size() - 1); reject(bad, manifest);
      bad = frames; bad[64 + 42] ^= 1; reject(bad, manifest);
    }
    std::cout << "WIDGET_IDENTITY_HOST_PASS checks=" << checks << " cuts=4\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
