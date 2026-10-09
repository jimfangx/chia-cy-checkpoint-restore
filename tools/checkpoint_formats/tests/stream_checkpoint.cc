// CPU stream host component tests. The queue service is a fixture, not a
// generated RTL/AXI restore adapter or a whole FireSim checkpoint.
#include "bridges/cpu_managed_stream.h"
#include "bridges/fpga_managed_stream.h"
#include "core/config.h"
#include "core/simif.h"
#include <deque>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }

namespace {
const TargetConfig cfg{{4,40,32}, {4,40,64}, 1, {}, {}, {0,0}, "stream-fixture"};
unsigned rejected = 0;
void check(bool b) { if (!b) throw std::runtime_error("stream test assertion"); }
void rejects(const std::function<void()> &fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::runtime_error("expected stream rejection");
}
std::string hex(const std::vector<uint8_t> &data) {
  const char *digits = "0123456789abcdef";
  std::string s;
  for (auto b : data) { s += digits[b >> 4]; s += digits[b & 15]; }
  return s;
}
void write(const std::filesystem::path &p, const std::vector<uint8_t> &b) {
  std::ofstream f(p, std::ios::binary);
  f.write(reinterpret_cast<const char *>(b.data()), b.size()); check(bool(f));
}
std::vector<uint8_t> read(const std::filesystem::path &p) {
  std::ifstream f(p, std::ios::binary); check(bool(f));
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
struct io_t : simif_t, CPUManagedStreamIO {
  explicit io_t(unsigned beat) : simif_t(cfg), beat(beat) {
    // push queues initially hold 2/0 beats; pull queues hold 1/5 beats.
    for (unsigned q = 0; q < 4; ++q)
      for (unsigned n = 0; n < (q == 0 ? 2 : q == 2 ? 1 : q == 3 ? 5 : 0) * width(q % 2); ++n)
        queues[q].push_back((q * 41 + n) & 255);
  }
  unsigned beat;
  std::deque<uint8_t> queues[4];
  std::ostream *trace = nullptr;
  std::function<void()> hook;
  uint64_t calls = 0;
  unsigned width(unsigned s) const { return beat * (s + 1); }
  unsigned capacity(unsigned s) const { return s == 0 ? 3 : 5; }
  uint64_t get_beat_bytes() const override { return beat; }
  CPUManagedStreamIO &get_cpu_managed_stream_io() override { return *this; }
  void write(size_t, uint32_t) override { std::abort(); }
  uint32_t read(size_t a) override { return mmio_read(a); }
  void called() { ++calls; if (hook) hook(); }
  uint32_t mmio_read(size_t a) override {
    check(a >= 256 && a <= 268 && (a - 256) % 4 == 0);
    called(); auto q = (a - 256) / 4;
    auto count = queues[q].size() / width(q % 2);
    if (trace) *trace << "R " << a << ' ' << count << '\n';
    return count;
  }
  size_t cpu_managed_axi4_write(size_t a, const char *data, size_t size) override {
    check(a == 4096 || a == 8192); called(); auto q = a / 4096 - 1;
    check(queues[q].size() + size <= capacity(q) * width(q));
    std::vector<uint8_t> bytes(data, data + size);
    queues[q].insert(queues[q].end(), bytes.begin(), bytes.end());
    if (trace) *trace << "W " << a << ' ' << size << ' ' << hex(bytes) << '\n';
    return size;
  }
  size_t cpu_managed_axi4_read(size_t a, char *data, size_t size) override {
    check(a == 12288 || a == 16384); called(); auto q = a / 4096 - 1;
    check(queues[q].size() >= size);
    std::vector<uint8_t> bytes;
    for (size_t n = 0; n < size; ++n) {
      bytes.push_back(queues[q].front()); queues[q].pop_front(); data[n] = bytes.back();
    }
    if (trace) *trace << "D " << a << ' ' << size << ' ' << hex(bytes) << '\n';
    return size;
  }
  std::vector<uint8_t> snapshot() const {
    std::vector<uint8_t> b;
    for (const auto &q : queues) {
      check(q.size() <= 65535);
      b.push_back(q.size() & 255); b.push_back(q.size() >> 8);
      b.insert(b.end(), q.begin(), q.end());
    }
    return b;
  }
  void restore(const std::vector<uint8_t> &b) {
    size_t pos = 0;
    for (unsigned q = 0; q < 4; ++q) {
      check(pos + 2 <= b.size()); unsigned n = b[pos] + 256 * b[pos + 1]; pos += 2;
      check(pos + n <= b.size() && n % width(q % 2) == 0 && n <= capacity(q % 2) * width(q % 2));
      queues[q] = {b.begin() + pos, b.begin() + pos + n}; pos += n;
    }
    check(pos == b.size());
  }
  void device(unsigned beats) {
    if (trace) *trace << "DEVICE " << beats << '\n';
    for (unsigned q = 0; q < 2; ++q) {
      auto size = std::min({beats * width(q), unsigned(queues[q].size()),
                           capacity(q) * width(q) - unsigned(queues[q + 2].size())});
      while (size--) { queues[q + 2].push_back(queues[q].front()); queues[q].pop_front(); }
    }
  }
};
using CPUManagedStreams::StreamParameters;
std::vector<StreamParameters> params(io_t &io, bool pull) {
  std::vector<StreamParameters> p;
  for (unsigned i = 0; i < 2; ++i) {
    auto q = (pull ? 2 : 0) + i;
    p.emplace_back((pull ? "pull" : "push") + std::to_string(i),
                   (q + 1) * 4096, 256 + q * 4, io.capacity(i), io.width(i));
  }
  return p;
}
struct fixture_t {
  explicit fixture_t(unsigned beat) : io(beat), engine(io, 0, {}, params(io,false), params(io,true)) {}
  io_t io;
  CPUManagedStreamWidget engine;
};
// opcode: init, push, pull, push flush, pull flush. Device advances occur
// before the completed host call; all cuts retain queued payloads.
const unsigned program[][5] = {
  {0,0,0,0,0}, {1,0,3,2,0}, {1,0,3,0,0}, {2,0,4,2,0}, {2,0,4,0,0},
  {1,1,5,3,0}, {1,1,1,1,0}, {2,1,5,0,0}, {2,1,1,0,0}, {3,0,0,0,0},
  {4,1,0,0,0}, {1,0,2,1,1}, {2,0,3,2,1}, {1,0,0,0,0}, {2,1,0,0,0},
  {1,1,4,3,3}, {2,1,5,3,0}, {1,0,3,1,2}, {2,0,3,1,3}, {2,1,5,1,3},
  {0,0,0,0,0}, {3,1,0,0,0}, {4,0,0,0,0}
};
const unsigned operations = sizeof(program) / sizeof(program[0]);
std::filesystem::path out;
std::unique_ptr<fixture_t> fixture;
std::ofstream trace;
unsigned index = 0;
bool restoring = false;
std::string prefix;
void snapshot(const std::string &label) {
  auto &f = *fixture; const auto calls = f.io.calls;
  auto b = f.engine.save_checkpoint(); f.engine.validate_checkpoint(b);
  write(out / (label + ".owner"), b); write(out / (label + ".fixture"), f.io.snapshot());
  check(f.io.calls == calls);
}
void init(const std::filesystem::path &directory, bool restore, unsigned cut, unsigned beat) {
  out = directory; restoring = restore; index = restore ? cut : 0; check(index <= operations);
  fixture = std::make_unique<fixture_t>(beat);
  prefix = restore ? "restore-" + std::to_string(cut) : "reference";
  if (restore) {
    auto b = read(out / ("cut-" + std::to_string(cut) + ".owner"));
    fixture->engine.validate_checkpoint(b); fixture->engine.load_checkpoint(b);
    fixture->io.restore(read(out / ("cut-" + std::to_string(cut) + ".fixture")));
    check(fixture->io.calls == 0); snapshot(prefix + ".initial");
  }
  trace.open(out / (prefix + ".trace")); check(bool(trace)); fixture->io.trace = &trace;
}
void operation(fixture_t &f, unsigned op, std::ostream &log) {
  const auto *p = program[op]; unsigned kind=p[0], s=p[1], num=p[2], req=p[3];
  log << "OP " << op << '\n';
  if (p[4]) f.io.device(p[4]);
  std::vector<uint8_t> data(num * f.io.width(s), 0xa5);
  uint8_t empty_byte = 0;
  void *buffer = data.empty() ? &empty_byte : data.data();
  size_t result = 0;
  if (kind == 0) f.engine.init();
  if (kind == 1) {
    for (unsigned n=0; n<data.size(); ++n) data[n] = (op * 17 + n) & 255;
    result = f.engine.push(s, buffer, data.size(), req * f.io.width(s));
  }
  if (kind == 2) result = f.engine.pull(s, buffer, data.size(), req * f.io.width(s));
  if (kind == 3) f.engine.push_flush(s);
  if (kind == 4) f.engine.pull_flush(s);
  log << "RESULT " << result << ' ' << hex(data) << '\n';
}
int step() {
  if (!restoring) snapshot("cut-" + std::to_string(index));
  if (index == operations) {
    snapshot(prefix + ".final"); trace.close(); fixture.reset(); return 1;
  }
  operation(*fixture, index++, trace); return 0;
}
void negatives(unsigned beat) {
  fixture_t f(beat);
  auto good = f.engine.save_checkpoint();
  auto malformed = [&](std::vector<uint8_t> b) {
    const auto queues=f.io.snapshot(); const auto calls=f.io.calls;
    rejects([&] { f.engine.validate_checkpoint(b); }); rejects([&] { f.engine.load_checkpoint(b); });
    check(f.engine.save_checkpoint() == good && f.io.snapshot() == queues && f.io.calls == calls);
  };
  for (size_t n=0; n<good.size(); ++n) malformed({good.begin(),good.begin()+n});
  auto bad=good; bad.push_back(0); malformed(bad);
  for (size_t n=0; n<good.size()-8; ++n) { bad=good; bad[n]^=1; malformed(bad); }
  for (unsigned flag=2; flag<256; ++flag) { bad=good; bad[bad.size()-8]=flag; malformed(bad); }
  fixture_t changed(beat * 2);
  rejects([&] { changed.engine.load_checkpoint(good); }); check(changed.io.calls == 0);
  // Independently constructed permutations/direction/name/address/geometry.
  for (unsigned change=0; change<7; ++change) {
    auto push=params(f.io,false), pull=params(f.io,true);
    if (change==0) std::swap(push[0],push[1]);
    if (change==1) std::swap(push,pull);
    if (change==2) push[0].stream_name += "changed";
    if (change==3) ++pull[0].dma_addr;
    if (change==4) ++pull[1].count_addr;
    if (change==5) ++push[1].fpga_buffer_size;
    if (change==6) ++pull[1].fpga_buffer_width_bytes;
    CPUManagedStreamWidget engine(f.io,0,{},std::move(push),std::move(pull));
    rejects([&] { engine.load_checkpoint(good); });
  }
  std::ostringstream sink;
  for (unsigned op : {1,2,3,4,5,6,7,8,11,12,13,14,15,16,17,18,19}) {
    for (unsigned phase : {1,2}) for (bool interrupt : {false,true}) {
      fixture_t active(beat); active.engine.init(); auto b=active.engine.save_checkpoint();
      unsigned checked=0;
      active.io.hook = [&] {
        if (active.io.calls != phase) return;
        ++checked;
        rejects([&] { active.engine.save_checkpoint(); });
        rejects([&] { active.engine.validate_checkpoint(b); });
        rejects([&] { active.engine.load_checkpoint(b); });
        rejects([&] { active.engine.init(); });
        rejects([&] { active.engine.push_flush(0); });
        rejects([&] { active.engine.pull_flush(0); });
        uint8_t byte = 0;
        rejects([&] { active.engine.push(0, &byte, 0, 0); });
        rejects([&] { active.engine.pull(0, &byte, 0, 0); });
        if (interrupt) throw std::runtime_error("injected stream I/O interruption");
      };
      // Some requests only read occupancy, so a phase-2 interruption may not run.
      if (interrupt) {
        bool threw=false;
        try { operation(active,op,sink); } catch (const std::runtime_error &) { threw=true; }
        check(threw == bool(checked));
      } else operation(active,op,sink);
      active.io.hook={};
      if (interrupt && checked) {
        rejects([&] { active.engine.save_checkpoint(); });
        rejects([&] { active.engine.validate_checkpoint(b); });
        rejects([&] { active.engine.load_checkpoint(b); });
        rejects([&] { active.engine.init(); });
      } else active.engine.validate_checkpoint(active.engine.save_checkpoint());
    }
  }
  // Empty streams still carry configuration/lifecycle; no generic or peer-DMA
  // engine may inherit support from StreamEngine's completed-call guard.
  CPUManagedStreamWidget empty(f.io,0,{}, {},{});
  auto b=empty.save_checkpoint(); empty.init(); empty.load_checkpoint(b);
  check(empty.save_checkpoint()==b);
  rejects([&] { empty.load_checkpoint(good); });
  StreamEngine unknown;
  check(unknown.checkpoint_schema().empty());
  rejects([&] { unknown.save_checkpoint(); }); rejects([&] { unknown.validate_checkpoint(good); });
  rejects([&] { unknown.load_checkpoint(good); });
  check(f.engine.checkpoint_schema()=="firesim.widget.cpu-managed-stream.v1");
  std::cout << "PASS: stream payload/suspension/reentry/interruption rejections " << rejected << '\n';
}
} // namespace
#ifdef STREAM_CHECKPOINT_DPI
extern "C" int stream_init(const char *directory, int restore, int cut, int beat) {
  try { init(directory,restore,cut,beat); return 0; }
  catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
extern "C" int stream_step() {
  try { return step(); } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return -1; }
}
extern "C" int stream_negative(int beat) {
  try { negatives(beat); return 0; } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#else
int main(int argc, char **argv) {
  try {
    check(argc==5);
    if (std::string(argv[1])=="negative") negatives(std::stoul(argv[4]));
    else { init(argv[2],std::string(argv[1])=="restore",std::stoul(argv[3]),std::stoul(argv[4])); while (!step()) {} }
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
#endif
