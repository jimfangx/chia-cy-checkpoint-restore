// Production frame validation of the complete generated wide/deep fixture.
#include "core/checkpoint_capture.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

static unsigned checks = 0;
template <typename F> void rejects(F operation) {
  bool rejected = false;
  try { operation(); } catch (const std::runtime_error &) { rejected = true; }
  if (!rejected) throw std::runtime_error("corrupt physical stream accepted");
  ++checks;
}
int main(int argc, char **argv) {
  if (argc != 3) return 2;
  const auto manifest =
#include "descriptor-manifest.inc"
  ;
  std::ifstream file(argv[1], std::ios::binary);
  if (!file) return 2;
  const std::vector<uint8_t> raw((std::istreambuf_iterator<char>(file)), {});
  const auto cycle = std::stoull(argv[2]);
  checkpoint_capture_session_t::validate_frames(raw, manifest, cycle);
  ++checks;
  for (auto size : {size_t(0), size_t(1), size_t(63), size_t(64), raw.size()-1, raw.size()-64}) {
    const std::vector<uint8_t> truncated(raw.begin(), raw.begin()+size);
    rejects([&] { checkpoint_capture_session_t::validate_frames(truncated, manifest, cycle); });
  }
  auto bad = raw; bad[64+42] ^= 1;
  rejects([&] { checkpoint_capture_session_t::validate_frames(bad, manifest, cycle); });
  rejects([&] { checkpoint_capture_session_t::validate_frames(raw, manifest, cycle+1); });
  auto other = manifest; other.wire_hash[0] ^= 1;
  rejects([&] { checkpoint_capture_session_t::validate_frames(raw, other, cycle); });
  other = manifest; other.entries.pop_back();
  rejects([&] { checkpoint_capture_session_t::validate_frames(raw, other, cycle); });
  other = manifest; other.entries[0].depth--;
  rejects([&] { checkpoint_capture_session_t::validate_frames(raw, other, cycle); });
  other = manifest; other.entries[0].slot++;
  rejects([&] { checkpoint_capture_session_t::validate_frames(raw, other, cycle); });
  std::cout << "CHUNKED_CAPTURE_HOST_PASS checks=" << checks << " words=65564\n";
}
