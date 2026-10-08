// Actual metasim MMIO/CPU-AXI transport + functional-memory component cut.
// No generated RTL, driver stack or whole-runtime restore acceptance is claimed.
#include "emul/mmio.h"
#include "emul/mm.h"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <sstream>

namespace {
constexpr int steps = 88;
const std::vector<int> cuts{0, 1, 3, 6, 9, 12, 16, 19, 23, 27, 35, 42, 55};
std::unique_ptr<mmio_t> transport;
std::unique_ptr<mm_magic_t> memory;
std::ofstream trace;
std::string directory;
bool restoring;
int restore_cut, beat_bytes;

void require(bool condition, const std::string &message) {
  if (!condition) throw std::runtime_error(message);
}

std::vector<uint8_t> read_file(const std::string &path) {
  std::ifstream file(path, std::ios::binary);
  require(file.good(), "cannot read " + path);
  return {std::istreambuf_iterator<char>(file), {}};
}

void write_file(const std::string &path, const std::vector<uint8_t> &bytes) {
  std::ofstream file(path, std::ios::binary);
  file.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(file.good(), "cannot write " + path);
}

std::string hex(const void *data, size_t size) {
  const auto *bytes = static_cast<const uint8_t *>(data);
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (size_t i = 0; i < size; ++i) out << std::setw(2) << unsigned(bytes[i]);
  return out.str();
}

void initialize(const std::string &out, int cut, int beat, bool restore) {
  directory = out;
  restore_cut = cut;
  restoring = restore;
  beat_bytes = beat;
  AXI4Config conf{4, 32, uint64_t(beat * 8)};
  transport = std::make_unique<mmio_t>(conf);
  memory = std::make_unique<mm_magic_t>(conf);
  memory->init(4096, 64);
  auto *data = static_cast<uint8_t *>(memory->get_data());
  for (size_t i = 0; i < 4096; ++i) data[i] = restore ? 0xa5 : (i * 17 + 3) & 255;
  if (restore) {
    const auto name = out + "/cut-" + std::to_string(cut);
    auto mmio = read_file(name + ".mmio.owner"), mem = read_file(name + ".memory.owner");
    // Prevalidate both before modifying either. No requests/ticks precede load.
    transport->validate_checkpoint(mmio);
    memory->validate_checkpoint(mem);
    transport->load_checkpoint(mmio);
    memory->load_checkpoint(mem);
    require(transport->save_checkpoint() == mmio && memory->save_checkpoint() == mem,
            "incomplete restoration before first edge");
  }
  trace.open(out + (restore ? "/restore-" + std::to_string(cut) : "/reference") + ".trace");
  require(trace.good(), "cannot open trace");
}

void save(const std::string &name) {
  write_file(name + ".mmio.owner", transport->save_checkpoint());
  write_file(name + ".memory.owner", memory->save_checkpoint());
}

void step(int c) {
  if (!restoring && std::find(cuts.begin(), cuts.end(), c) != cuts.end())
    save(directory + "/cut-" + std::to_string(c));
  const auto size = transport->get_config().get_size();
  if (c <= 3) {
    const size_t lengths[]{3, 2, 0, 1};
    transport->read_req(64 + c * 128, size, lengths[c]);
  }
  if (c == 0 || c == 1 || c == 4 || c == 6) {
    size_t len = c == 0 ? 3 : c == 1 ? 2 : c == 4 ? 0 : 1;
    std::vector<char> payload((len + 1) * beat_bytes);
    for (size_t i = 0; i < payload.size(); ++i) payload[i] = (i * 13 + c * 7 + 5) & 255;
    std::vector<size_t> strobes(len + 1, beat_bytes == 64 ? ~size_t{0} :
                                (size_t{1} << beat_bytes) - 1);
    if (c == 1) for (auto &strb : strobes) strb &= 0xaaaaaaaaaaaaaaaaULL;
    transport->write_req(64 + c * 128, size, len, payload.data(), strobes.data());
    // Queued bytes must survive caller mutation and destruction.
    std::fill(payload.begin(), payload.end(), char(0xdd));
  }
  std::vector<char> response(4 * beat_bytes, char(0xa5));
  const bool read = c >= 18 && c % 7 == 4 && transport->read_resp(response.data());
  const bool write = c >= 20 && c % 7 == 6 && transport->write_resp();
  trace << c << ' ' << read << ' ' << (read ? hex(response.data(), response.size()) : "-")
        << ' ' << write << ' ' << transport->ar_valid() << ' ' << transport->ar_id()
        << ' ' << transport->ar_addr() << ' ' << transport->ar_size() << ' ' << transport->ar_len()
        << ' ' << transport->aw_valid() << ' ' << transport->aw_id() << ' ' << transport->aw_addr()
        << ' ' << transport->aw_size() << ' ' << transport->aw_len() << ' ' << transport->w_valid()
        << ' ' << transport->w_strb() << ' ' << transport->w_last() << ' '
        << hex(transport->w_data(), beat_bytes) << ' ' << transport->r_ready()
        << ' ' << transport->b_ready() << ' ' << hex(memory->get_data(), 4096) << '\n';

  const bool ar_gate = c >= 2 && c % 4 != 0, aw_gate = c >= 3 && c % 2 != 0;
  const bool w_gate = c >= 5 && c % 3 != 0, r_gate = c >= 10 && c % 3 != 1;
  const bool b_gate = c >= 15 && c % 4 != 2;
  const bool ar = transport->ar_valid() && ar_gate, aw = transport->aw_valid() && aw_gate;
  const bool w = transport->w_valid() && w_gate;
  const auto ar_addr = transport->ar_addr(), ar_id = transport->ar_id();
  const auto ar_size = transport->ar_size(), ar_len = transport->ar_len();
  const auto aw_addr = transport->aw_addr(), aw_id = transport->aw_id();
  const auto aw_size = transport->aw_size(), aw_len = transport->aw_len();
  const auto strb = transport->w_strb();
  const bool last = transport->w_last(), rr = transport->r_ready() && r_gate;
  const bool br = transport->b_ready() && b_gate;
  std::vector<uint32_t> wdata(beat_bytes / 4), rdata(beat_bytes / 4);
  std::memcpy(wdata.data(), transport->w_data(), beat_bytes);
  std::memcpy(rdata.data(), memory->r_data(), beat_bytes);
  transport->tick(c < 2, memory->ar_ready() && ar_gate, memory->aw_ready() && aw_gate,
                  memory->w_ready() && w_gate, memory->r_id(), rdata,
                  memory->r_last(), memory->r_valid() && r_gate,
                  memory->b_id(), memory->b_valid() && b_gate);
  memory->tick(c < 2, ar, ar_addr, ar_id, ar_size, ar_len,
               aw, aw_addr, aw_id, aw_size, aw_len, w, strb, wdata, last, rr, br);
}

void finish() {
  trace.close();
  save(directory + (restoring ? "/restore-" + std::to_string(restore_cut) : "/reference") + ".final");
  require(!transport->ar_valid() && !transport->aw_valid() && !transport->w_valid() &&
              !transport->r_ready() && !transport->b_ready() &&
              !memory->r_valid() && !memory->b_valid(), "workload did not finish all requests");
}

void put(std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i) bytes.at(offset + i) = (value >> (8 * i)) & 255;
}

void independent_channels(int beat) {
  // A real AXI ingress can buffer W before AW and multiple W bursts before B.
  // The production memory model's W-ready policy doesn't exercise this case.
  mmio_t mmio(AXI4Config{4, 32, uint64_t(beat * 8)});
  const size_t size = mmio.get_config().get_size();
  std::vector<char> data(3 * beat, char(0x73));
  std::vector<size_t> strobes(3, beat == 64 ? ~size_t{0} : (size_t{1} << beat) - 1);
  mmio.write_req(64, size, 2, data.data(), strobes.data());
  mmio.write_req(256, size, 0, data.data(), strobes.data());
  const std::vector<uint32_t> dummy(beat / 4);
  mmio.tick(false, false, false, true, 0, dummy, false, false, 0, false);
  require(mmio.aw_valid() && !mmio.b_ready() && mmio.w_valid() && !mmio.w_last(),
          "incorrect W-before-AW behavior");
  auto before_aw = mmio.save_checkpoint();
  mmio_t fresh(mmio.get_config());
  fresh.load_checkpoint(before_aw);
  require(fresh.save_checkpoint() == before_aw, "W-before-AW cut rejected/lost state");
  // Accept AW and the second W together; then the final W and next burst W.
  for (int i = 0; i < 3; ++i) {
    for (auto *owner : {&mmio, &fresh})
      owner->tick(false, false, i == 0, true, 0, dummy, false, false, 0, false);
    require(mmio.save_checkpoint() == fresh.save_checkpoint(), "independent AW/W continuation differs");
  }
  require(!mmio.w_valid() && mmio.b_ready(), "later burst was not buffered");
  mmio.tick(false, false, false, false, 0, dummy, false, false, 0, true);
  const auto awaiting_driver = mmio.save_checkpoint();
  fresh.load_checkpoint(awaiting_driver);
  require(fresh.save_checkpoint() == awaiting_driver && fresh.write_resp() &&
              fresh.aw_valid() && fresh.aw_addr() == 256 && !fresh.w_valid(),
          "B response with later buffered W data lost state");
}

void negative_tests(const std::string &out, int beat) {
  independent_channels(beat);
  initialize(out, 16, beat, true);
  const auto original = transport->save_checkpoint();
  size_t rejected = 0;
  auto reject = [&](const std::vector<uint8_t> &bytes) {
    bool validation_failed = false, load_failed = false;
    try { transport->validate_checkpoint(bytes); } catch (const std::runtime_error &) { validation_failed = true; }
    try { transport->load_checkpoint(bytes); } catch (const std::runtime_error &) { load_failed = true; }
    require(validation_failed && load_failed && transport->save_checkpoint() == original,
            "malformed payload accepted or rejection mutated state");
    ++rejected;
  };
  for (size_t n = 0; n < original.size(); ++n) reject({original.begin(), original.begin() + n});
  for (auto field : std::vector<std::pair<size_t, uint64_t>>{
           {0, 0}, {8, 2}, {16, 3}, {24, 31}, {32, 1024}, {40, 2}, {48, 2},
           {40, 0}, {48, 0}, {56 + size_t(beat), ~uint64_t{0}},
           {64 + size_t(beat), 1}, {72 + size_t(beat), uint64_t{1} << 32},
           {80 + size_t(beat), 7}, {88 + size_t(beat), 256}}) {
    auto changed = original;
    put(changed, field.first, field.second);
    reject(changed);
  }
  // Find queue fields from the actual payload, then corrupt their structure.
  auto get = [&](size_t offset) {
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= uint64_t(original.at(offset + i)) << (8 * i);
    return value;
  };
  size_t aw_count = 64 + beat + 32 * get(56 + beat);
  size_t w_count = aw_count + 8 + 32 * get(aw_count);
  size_t r_count = w_count + 8 + (16 + beat) * get(w_count);
  size_t b_count = r_count + 8 + (16 + beat) * get(r_count);
  for (size_t count : {aw_count, w_count, r_count, b_count}) {
    auto changed = original; put(changed, count, ~uint64_t{0}); reject(changed);
  }
  require(get(w_count) > 0 && get(r_count) > 0, "negative fixture missing W/R queues");
  for (auto field : std::vector<std::pair<size_t, uint64_t>>{
           {w_count + 16, 2}, {r_count + 8, 16}, {r_count + 16, 2}, {r_count + 16, 1}}) {
    auto changed = original; put(changed, field.first, field.second); reject(changed);
  }
  require(get(b_count) == 1, "negative fixture missing completed B response");
  for (uint64_t id : {uint64_t{1}, uint64_t{16}}) {
    auto changed = original; put(changed, b_count + 8, id); reject(changed);
  }
  if (beat < 64) {
    auto changed = original; put(changed, w_count + 8, uint64_t{1} << beat); reject(changed);
  }
  auto trailing = original; trailing.push_back(0); reject(trailing);
  for (const auto &conf : std::vector<AXI4Config>{{3, 32, uint64_t(beat * 8)},
           {4, 31, uint64_t(beat * 8)}, {4, 32, uint64_t(beat == 4 ? 64 : 32)}}) {
    mmio_t other(conf);
    const auto before = other.save_checkpoint();
    bool failed = false;
    try { other.load_checkpoint(original); } catch (const std::runtime_error &) { failed = true; }
    require(failed && other.save_checkpoint() == before, "geometry rejection mutated state");
    ++rejected;
  }
  mmio_t unsupported(AXI4Config{4, 32, 1024});
  bool failed = false;
  try { unsupported.save_checkpoint(); } catch (const std::runtime_error &) { failed = true; }
  require(failed, "unsupported geometry accepted capture");
  // Narrow request ownership and a maximum AXI burst, with high strobe bits.
  mmio_t narrow(AXI4Config{4, 32, uint64_t(beat * 8)});
  std::vector<char> payload(2 * 256, char(0x59));
  std::vector<size_t> strobes(256, 3);
  narrow.write_req(64, 1, 255, payload.data(), strobes.data());
  std::fill(payload.begin(), payload.end(), char(0));
  auto bytes = narrow.save_checkpoint();
  mmio_t fresh(narrow.get_config());
  fresh.load_checkpoint(bytes);
  require(fresh.save_checkpoint() == bytes && fresh.w_strb() == 3 &&
              static_cast<char *>(fresh.w_data())[0] == char(0x59) &&
              static_cast<char *>(fresh.w_data())[2] == 0, "narrow/max-burst ownership failed");
  mmio_t wide(AXI4Config{64, 64, 512});
  wide.read_req(~uint64_t{0} - 63, 6, 0);
  wide.tick(false, true, false, false, 0, std::vector<uint32_t>(16), false, false, 0, false);
  auto wide_bytes = wide.save_checkpoint();
  mmio_t wide_fresh(wide.get_config());
  wide_fresh.load_checkpoint(wide_bytes);
  require(wide_fresh.save_checkpoint() == wide_bytes && wide_fresh.r_ready(),
          "64-bit ID/address geometry lost state");
  std::cout << "PASS: " << rejected << " malformed/mismatched MMIO payloads rejected atomically; "
            << "narrow/max-burst ownership, beat=" << beat << '\n';
}
} // namespace

extern "C" int mmio_checkpoint_init(const char *out, int cut, int beat, int restore) {
  try { independent_channels(beat); initialize(out, cut, beat, restore); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int mmio_checkpoint_step(int c) {
  try { step(c); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int mmio_checkpoint_finish() {
  try { finish(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
#ifndef MMIO_CHECKPOINT_DPI
int main(int argc, char **argv) {
  try {
    require(argc == 5, "mode out cut beat");
    const std::string mode = argv[1];
    const int cut = std::stoi(argv[3]), beat = std::stoi(argv[4]);
    if (mode == "negative") { negative_tests(argv[2], beat); return 0; }
    initialize(argv[2], cut, beat, mode == "restore");
    for (int c = mode == "restore" ? cut : 0; c < steps; ++c) step(c);
    finish();
    std::cout << "PASS: MMIO/memory component continuation cut=" << cut << " beat=" << beat << '\n';
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
