// Native driver installation against the real bridge/widget/stream classes.
// Only the external simif and stream devices are test doubles; no FPGA claim.
#include "bridges/checkpoint_capture.h"
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>

// Supply the platform boundary without linking a simulation run loop. Any
// attempt to access a platform during installation fails this test.
simif_t::simif_t(const TargetConfig &config) : config(config) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { throw std::runtime_error("unexpected CPU IO"); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { throw std::runtime_error("unexpected FPGA IO"); }
int simif_t::run(simulation_t &) { throw std::runtime_error("unexpected run"); }

namespace {
unsigned checks = 0;
void check(bool condition) {
  ++checks;
  if (!condition) throw std::runtime_error("native install assertion " + std::to_string(checks));
}
template <typename F> void rejects(F action) {
  bool rejected = false;
  try { action(); } catch (const std::exception &) { rejected = true; }
  check(rejected);
}
struct no_io_sim : simif_t {
  static const TargetConfig target;
  unsigned operations = 0;
  no_io_sim() : simif_t(target) {}
  void write(size_t, uint32_t) override { ++operations; throw std::runtime_error("unexpected MMIO write"); }
  uint32_t read(size_t) override { ++operations; throw std::runtime_error("unexpected MMIO read"); }
};
const TargetConfig no_io_sim::target{};
struct no_io_stream : FPGAToCPUStreamDriver {
  unsigned &operations;
  explicit no_io_stream(unsigned &operations) : operations(operations) {}
  void init() override { ++operations; throw std::runtime_error("unexpected stream init"); }
  size_t pull(void *, size_t, size_t) override { ++operations; throw std::runtime_error("unexpected stream pull"); }
  void flush() override { ++operations; throw std::runtime_error("unexpected stream flush"); }
};
struct test_engine : StreamEngine {
  unsigned operations = 0;
  explicit test_engine(unsigned count) {
    for (unsigned i = 0; i < count; ++i)
      fpga_to_cpu_streams.push_back(std::make_unique<no_io_stream>(operations));
  }
};
checkpoint_native_capture_binding_t binding(uint32_t bits = 130) {
  return {1, bits, 3, 2, 1, 252, 251, 2, bits + 3 + 1452};
}
checkpoint_capture_manifest_t manifest(const checkpoint_native_capture_binding_t &b) {
  checkpoint_capture_manifest_t m{};
  m.wire_hash[0] = 0x23;
  m.wire_hash[31] = 0x81;
  m.entries.push_back({1, 0, 9, 2});
  if (b.capture_native_control)
    m.entries.push_back({uint8_t(b.native_control_bank), 0, 64,
        uint32_t((uint64_t(b.native_bits) + b.physical_clock_gates + 150 + 63) / 64)});
  if (b.native_bits / 64)
    m.entries.push_back({uint8_t(b.snapshot_bank), 0, 64, b.native_bits / 64});
  if (b.native_bits % 64)
    m.entries.push_back({uint8_t(b.snapshot_bank), 1, uint16_t(b.native_bits % 64), 1});
  return m;
}
struct test_registry {
  StreamEngine *engine;
  std::unique_ptr<checkpoint_capture_t> installed;
  StreamEngine *get_stream_engine() { return engine; }
  void add_widget(checkpoint_capture_t *driver) {
    check(!installed && driver);
    installed.reset(driver);
  }
};
} // namespace

int main() {
  try {
    no_io_sim simif;
    test_engine engine(64), empty(0);
    const auto good = binding();
    const auto metadata = manifest(good);
    for (unsigned bits : {1U, 63U, 64U, 65U, 130U, 70000U}) {
      for (unsigned control : {0U, 1U}) {
        auto b = binding(bits); b.capture_native_control = control;
        checkpoint_capture_t driver(simif, &engine, 256, 1, manifest(b), b);
        check(driver.capture_session().phase() == checkpoint_capture_session_t::phase_t::idle);
        check(driver.checkpoint_schema().empty());
        rejects([&] { driver.save_checkpoint(); });
        driver.init(); driver.tick(); driver.finish();
      }
    }
    for (unsigned fault = 0; fault < 31; ++fault) {
      auto b = good;
      auto m = metadata;
      StreamEngine *selected = &engine;
      size_t base = 256;
      unsigned stream = 1;
      switch (fault) {
      case 0: selected = nullptr; break;
      case 1: selected = &empty; break;
      case 2: stream = 64; break;
      case 3: base = 1; break;
      case 4: base = std::numeric_limits<size_t>::max(); break;
      case 5: b.original_entries = 0; break;
      case 6: b.original_entries = 65536; break;
      case 7: b.native_bits = 0; break;
      case 8: b.native_bits = std::numeric_limits<uint32_t>::max(); break;
      case 9: b.physical_clock_gates = 0; break;
      case 10: b.physical_clock_gates = 65536; break;
      case 11: b.external_owners = 0; break;
      case 12: b.external_owners = 65535; break;
      case 13: b.capture_native_control = 2; break;
      case 14: b.snapshot_bank = 255; break;
      case 15: b.native_control_bank = b.snapshot_bank; break;
      case 16: b.native_control_bank = 256; break;
      case 17: b.shadow_layout_version = 1; break;
      case 18: ++b.shadow_bits; break;
      case 19: m.wire_hash.fill(0); break;
      case 20: m.wire_hash.fill(0xff); break;
      case 21: m.entries.pop_back(); break;
      case 22: m.entries[0].bank = b.snapshot_bank; break;
      case 23: m.entries[0].bank = b.native_control_bank; break;
      case 24: m.entries[1].depth++; break;
      case 25: m.entries[1].width = 63; break;
      case 26: m.entries[2].slot = 1; break;
      case 27: m.entries[3].width = 1; break;
      case 28: m.entries[0].bank = 255; m.entries[0].width = 1; m.entries[0].depth = 1; break;
      case 29: m.entries[0].width = 0; break;
      case 30: m.entries[1].bank = m.entries[2].bank; m.entries[1].slot = m.entries[2].slot; break;
      }
      rejects([&] { checkpoint_capture_t driver(simif, selected, base, stream, m, b); });
      check(simif.operations == 0 && engine.operations == 0 && empty.operations == 0);
    }
    // Exact original physical CE suffix remains legal and cannot be invented
    // by confusing the original ROM count with the complete stream count.
    auto physical = metadata;
    for (unsigned i = 0; i < 3; ++i)
      physical.entries.insert(physical.entries.begin() + 1 + i, {255, uint16_t(i), 1, 1});
    auto physical_binding = good; physical_binding.original_entries += 3;
    checkpoint_capture_t physical_driver(simif, &engine, 0, 0, physical, physical_binding);
    check(physical_driver.checkpoint_schema().empty());
    // The legacy constructor continues accepting its original metadata ABI.
    checkpoint_capture_t legacy(simif, engine, 0, 0, metadata);
    check(legacy.checkpoint_schema().empty());
#ifdef CHECKPOINT_NATIVE_GENERATED_CONSTRUCTOR
    test_registry registry{&engine, {}};
#include "native_constructor.h"
    check(bool(registry.installed));
    check(registry.installed->checkpoint_schema().empty());
    registry.installed.reset();
    registry.engine = nullptr;
    rejects([&] {
#include "native_constructor.h"
    });
    check(!registry.installed);
#endif
    check(simif.operations == 0 && engine.operations == 0 && empty.operations == 0);
    std::cout << "NATIVE_CAPTURE_INSTALL_HOST_PASS checks=" << checks << " negatives=31 no_io=1\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
