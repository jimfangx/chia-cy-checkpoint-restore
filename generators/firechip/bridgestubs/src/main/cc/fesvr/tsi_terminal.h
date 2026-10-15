// See LICENSE for license details.
#ifndef __FIRESIM_TSI_TERMINAL_H
#define __FIRESIM_TSI_TERMINAL_H

#include "core/widget_checkpoint.h"
#include <fesvr/term.h>
#include <functional>

// A sealed byte stream has deterministic EOF and no process-local input
// descriptor/termios state. Live terminals remain explicitly unsupported.
// Output before the cut is read back as a transcript, never emitted again.
// Syscall descriptors and signal state are separate, still unowned services.
class firesim_tsi_terminal_t final : public checkpoint_owner_t {
public:
  static constexpr uint64_t maximum = 1048576;
  using output_t = std::function<void(uint8_t)>;
  firesim_tsi_terminal_t() = default;
  explicit firesim_tsi_terminal_t(std::vector<uint8_t> input,
      output_t output = [](uint8_t ch) { canonical_terminal_t::write(ch); })
      : sealed(true), input(std::move(input)), output(std::move(output)) {
    if (this->input.size() > maximum || !this->output)
      throw std::runtime_error("unsupported sealed terminal input/output binding");
  }
  int read() {
    widget_checkpoint_state_t::call_t call(boundary);
    if (!sealed) return canonical_terminal_t::read();
    return cursor == input.size() ? -1 : input[cursor++];
  }
  void write(uint8_t ch) {
    widget_checkpoint_state_t::call_t call(boundary);
    if (!sealed) { canonical_terminal_t::write(ch); return; }
    if (transcript.size() == maximum)
      throw std::runtime_error("sealed terminal output transcript limit");
    // Allocate before the irreversible service. Failed services poison this
    // owner; a thrown operation cannot become an acknowledged checkpoint cut.
    if (transcript.size() == transcript.capacity())
      transcript.reserve(std::min<uint64_t>(maximum, std::max<size_t>(64, transcript.capacity() * 2)));
    output(ch);
    transcript.push_back(ch);
  }
  std::string checkpoint_schema() const override {
    return sealed ? "firesim.tsi.terminal.sealed.v1" : "";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    require_supported(); auto out = configuration();
    out.word(cursor); out.word(transcript.size());
    out.bytes.insert(out.bytes.end(), transcript.begin(), transcript.end());
    return std::move(out.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &image) const override { parse(image); }
  void load_checkpoint(const std::vector<uint8_t> &image) override {
    auto next = parse(image); commit(next);
  }
private:
  // Only the bound BCD coordinator may publish a prepared terminal alongside
  // its prepared command queue. No public prepared object can outlive a cut.
  friend class firesim_tsi_bcd_t;
  void commit(std::pair<uint64_t, std::vector<uint8_t>> &next) noexcept {
    static_assert(noexcept(transcript.swap(next.second)), "terminal commit must not allocate");
    transcript.swap(next.second); cursor = next.first;
  }
  bool sealed = false;
  const std::vector<uint8_t> input;
  output_t output;
  uint64_t cursor = 0;
  std::vector<uint8_t> transcript;
  widget_checkpoint_state_t boundary;
  void require_supported() const {
    boundary.require_idle();
    if (!sealed) throw std::runtime_error("live terminal checkpoint is unsupported");
  }
  widget_checkpoint_config_t configuration() const {
    widget_checkpoint_config_t config(27, {1, maximum, input.size()});
    config.bytes.insert(config.bytes.end(), input.begin(), input.end());
    return config;
  }
  std::pair<uint64_t, std::vector<uint8_t>> parse(const std::vector<uint8_t> &image) const {
    require_supported(); const auto config = configuration(); const size_t start = config.bytes.size();
    if (image.size() < start + 16 ||
        !std::equal(config.bytes.begin(), config.bytes.end(), image.begin()))
      throw std::runtime_error("sealed terminal configuration/payload mismatch");
    auto word = [&](size_t at) {
      uint64_t value = 0;
      for (unsigned i = 0; i < 8; ++i) value |= uint64_t(image[at+i]) << (8*i);
      return value;
    };
    const auto next = word(start), count = word(start + 8);
    if (next > input.size() || count > maximum || image.size() != start + 16 + count)
      throw std::runtime_error("sealed terminal cursor/transcript mismatch");
    return {next, {image.begin() + start + 16, image.end()}};
  }
};
#endif
