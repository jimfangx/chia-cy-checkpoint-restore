// Actual FireSim mm_magic_t continuation test, also called from VCS via DPI.
#include "emul/mm.h"

#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <sstream>

namespace {
constexpr size_t memory_bytes = 4096;
constexpr int steps = 42;
const std::vector<int> cuts{0, 4, 8, 12, 17, 20, 26, 36};
std::unique_ptr<mm_magic_t> memory;
std::ofstream trace;
std::string directory;
bool restoring;
int restore_cut, beat_bytes;

void require(bool value, const std::string &message) {
  if (!value)
    throw std::runtime_error(message);
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
  for (size_t i = 0; i < size; ++i)
    out << std::setw(2) << unsigned(bytes[i]);
  return out.str();
}

void initialize(const std::string &out, int cut, int beat, bool restore) {
  directory = out;
  restoring = restore;
  restore_cut = cut;
  beat_bytes = beat;
  memory = std::make_unique<mm_magic_t>(AXI4Config{4, 32, uint64_t(beat * 8)});
  memory->init(memory_bytes, 64);
  auto *data = static_cast<uint8_t *>(memory->get_data());
  for (size_t i = 0; i < memory_bytes; ++i)
    data[i] = restore ? 0xa5 : (i * 17 + 3) & 255;
  if (restore) {
    auto bytes = read_file(out + "/cut-" + std::to_string(cut) + ".owner");
    memory->validate_checkpoint(bytes);
    memory->load_checkpoint(bytes);
    require(memory->save_checkpoint() == bytes,
            "not all owner state restored before first edge");
  }
  trace.open(out + (restore ? "/restore-" + std::to_string(cut) : "/reference") + ".trace");
  require(trace.good(), "cannot open trace");
}

void step(int c) {
  if (!restoring) {
    for (int cut : cuts)
      if (c == cut)
        write_file(directory + "/cut-" + std::to_string(cut) + ".owner",
                   memory->save_checkpoint());
  }
  // Observe every AXI output before this edge, including held responses/data.
  trace << c << ' ' << memory->ar_ready() << ' ' << memory->aw_ready() << ' '
        << memory->w_ready() << ' ' << memory->r_valid() << ' '
        << memory->r_id() << ' ' << memory->r_resp() << ' ' << memory->r_last()
        << ' ' << hex(memory->r_data(), beat_bytes) << ' ' << memory->b_valid()
        << ' ' << memory->b_id() << ' ' << memory->b_resp() << ' '
        << hex(memory->get_data(), memory_bytes) << '\n';

  bool ar = c == 2 || c == 10 || c == 14 || c == 37;
  bool aw = c == 1 || c == 12 || c == 34;
  bool w = c == 3 || c == 7 || c == 9 || c == 11 || c == 13 ||
           c == 16 || c == 18 || c == 36 || c == 39;
  std::vector<uint32_t> data(beat_bytes / 4);
  for (size_t i = 0; i < data.size(); ++i)
    data[i] = 0xa1b2c300U + c * 0x01010101U + i;
  uint64_t strobe = beat_bytes == 64 ? ~uint64_t{0} : (uint64_t{1} << beat_bytes) - 1;
  if (c == 7 || c == 16)
    strobe &= 0xaaaaaaaaaaaaaaaaULL;
  unsigned size = 0;
  while ((1U << size) < unsigned(beat_bytes))
    ++size;
  memory->tick(c == 35, ar, 64, c == 2 ? 7 : c == 10 ? 8 : 9,
               size, c == 2 ? 3 : c == 10 ? 2 : 1,
               aw, c == 1 ? 64 : c == 12 ? 512 : 1024 + beat_bytes / 2,
               c == 1 ? 5 : 6, c == 34 ? size - 1 : size,
               c == 1 ? 3 : c == 12 ? 2 : 1,
               w, strobe, data, c == 11 || c == 18 || c == 39,
               c >= 20 && c % 2 == 0, c >= 25 && c % 3 == 1);
}

void finish() {
  trace.close();
  write_file(directory + (restoring ? "/restore-" + std::to_string(restore_cut) :
                                      "/reference") + ".final.owner",
             memory->save_checkpoint());
}

void put_u64(std::vector<uint8_t> &bytes, size_t offset, uint64_t value) {
  for (unsigned i = 0; i < 8; ++i)
    bytes.at(offset + i) = (value >> (8 * i)) & 255;
}

void negative_tests(const std::string &out, int beat) {
  initialize(out, 17, beat, true);
  const auto original = memory->save_checkpoint();
  size_t rejected = 0;
  auto reject = [&](const std::vector<uint8_t> &bytes) {
    bool validation_failed = false, load_failed = false;
    try { memory->validate_checkpoint(bytes); }
    catch (const std::runtime_error &) { validation_failed = true; }
    try { memory->load_checkpoint(bytes); }
    catch (const std::runtime_error &) { load_failed = true; }
    require(validation_failed && load_failed, "accepted malformed owner payload");
    require(memory->save_checkpoint() == original, "rejection mutated owner state");
    ++rejected;
  };
  // Every prefix; failure must precede ANY DRAM or queue change.
  for (size_t n = 0; n < original.size(); ++n)
    reject({original.begin(), original.begin() + n});
  for (auto field : std::vector<std::pair<size_t, uint64_t>>{
           {0, 0}, {8, 2}, {16, 5}, {24, 31}, {32, 128}, {40, 8192},
           {48, 32}, {64, 2}, {80, 16}, {88, 3}, {88, uint64_t(beat * 2)},
           {96, 0}, {96, 257}, {104 + memory_bytes + size_t(beat), ~uint64_t{0}}}) {
    auto bytes = original;
    put_u64(bytes, field.first, field.second);
    reject(bytes);
  }
  size_t b_count = 104 + memory_bytes + beat;
  size_t r_count = b_count + 8 + 8; // exactly one pending B at cut 17
  for (auto field : std::vector<std::pair<size_t, uint64_t>>{
           {b_count + 8, 16}, {r_count, ~uint64_t{0}},
           {r_count + 8, 16}, {r_count + 16, 2},
           {original.size() - beat - 8, 0}}) {
    auto bytes = original;
    put_u64(bytes, field.first, field.second);
    reject(bytes);
  }
  auto trailing = original;
  trailing.push_back(0);
  reject(trailing);

  // Geometry mismatch on a separately initialized model is rejected atomically.
  struct geometry { AXI4Config conf; size_t bytes; int line; };
  for (const auto &g : std::vector<geometry>{
           {{3, 32, uint64_t(beat * 8)}, memory_bytes, 64},
           {{4, 31, uint64_t(beat * 8)}, memory_bytes, 64},
           {{4, 32, uint64_t(beat == 4 ? 64 : 32)}, memory_bytes, 64},
           {{4, 32, uint64_t(beat * 8)}, memory_bytes / 2, 64},
           {{4, 32, uint64_t(beat * 8)}, memory_bytes, 128}}) {
    mm_magic_t other(g.conf);
    other.init(g.bytes, g.line);
    auto before = other.save_checkpoint();
    bool failed = false;
    try { other.load_checkpoint(original); }
    catch (const std::runtime_error &) { failed = true; }
    require(failed && other.save_checkpoint() == before, "geometry load changed memory");
    ++rejected;
  }
  mm_magic_t uninitialized(AXI4Config{4, 32, uint64_t(beat * 8)});
  bool failed = false;
  try { uninitialized.load_checkpoint(original); }
  catch (const std::runtime_error &) { failed = true; }
  require(failed, "uninitialized memory accepted restore");
  require(memory->mm_t::checkpoint_schema().empty(), "base memory driver supports checkpoint");
  failed = false;
  try { memory->mm_t::save_checkpoint(); }
  catch (const std::runtime_error &) { failed = true; }
  require(failed, "base memory driver silently omitted state");
  for (bool load : {false, true}) {
    failed = false;
    try {
      if (load) memory->mm_t::load_checkpoint(original);
      else memory->mm_t::validate_checkpoint(original);
    } catch (const std::runtime_error &) { failed = true; }
    require(failed, "base memory driver accepted unaudited restore");
  }
  std::cout << "PASS: " << rejected << " malformed/mismatched payloads rejected atomically, "
            << "uninitialized/unaudited memory fails closed, beat=" << beat << '\n';
}
} // namespace

extern "C" int mm_checkpoint_init(const char *out, int cut, int beat, int restore) {
  try { initialize(out, cut, beat, restore); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int mm_checkpoint_step(int c) {
  try { step(c); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}
extern "C" int mm_checkpoint_finish() {
  try { finish(); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; std::exit(1); }
}

#ifndef MEMORY_CHECKPOINT_DPI
int main(int argc, char **argv) {
  try {
    require(argc == 5, "usage: memory_checkpoint MODE OUT CUT BEAT");
    int cut = std::stoi(argv[3]), beat = std::stoi(argv[4]);
    std::string mode = argv[1];
    if (mode == "negative") {
      negative_tests(argv[2], beat);
    } else {
      require(mode == "reference" || mode == "restore", "unknown mode");
      initialize(argv[2], cut, beat, mode == "restore");
      for (int c = mode == "restore" ? cut : 0; c < steps; ++c)
        step(c);
      finish();
      std::cout << "PASS: memory owner " << mode << " cut=" << cut << " beat=" << beat << '\n';
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
#endif
