// Actual exact-source HTIF signal/lifecycle storage, no surrogate signal latch.
#include "fesvr/htif.h"
#include "fesvr/tsi_htif_signal.h"
#include "fesvr/tsi_htif_lifecycle.h"
#include "fesvr/tsi_serial_state.h"
#include <csignal>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <pthread.h>

namespace fs = std::filesystem;
static void require(bool value, const char *why) { if (!value) throw std::runtime_error(why); }
static void save(const fs::path &p, const std::vector<uint8_t> &v) {
  std::ofstream f(p, std::ios::binary); f.write(reinterpret_cast<const char *>(v.data()), v.size());
  require(bool(f), "image output");
}
static std::vector<uint8_t> bytes(const fs::path &p) {
  std::ifstream f(p, std::ios::binary); require(bool(f), "image input");
  return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
class reference_t final : public htif_t {
public:
  unsigned services = 0;
  explicit reference_t(bool signature = false) : htif_t(signature ?
    std::vector<std::string>{"+signature=unsupported", "none"} : std::vector<std::string>{"none"}) {}
  bool exiting() const { return should_exit(); }
  void read_chunk(addr_t, size_t, void *) override { ++services; throw std::runtime_error("unexpected read"); }
  void write_chunk(addr_t, size_t, const void *) override { ++services; throw std::runtime_error("unexpected write"); }
  void reset() override { ++services; throw std::runtime_error("unexpected reset"); }
  size_t chunk_align() override { return 8; }
  size_t chunk_max_size() override { return 1024; }
};
static void mask(int how, int sig) {
  sigset_t set; sigemptyset(&set); sigaddset(&set, sig);
  require(pthread_sigmask(how, &set, nullptr) == 0, "signal mask");
}
static void deliver(int sig) {
  require(std::raise(sig) == 0, "real signal raise");
  mask(SIG_UNBLOCK, sig); mask(SIG_BLOCK, sig);
}
static void fields(reference_t &ref, const fs::path &p) {
  const auto s = firesim_htif_signal_read(ref);
  std::ofstream(p) << s.lifecycle.has_exit << ' ' << s.lifecycle.raw_exit << ' '
    << s.lifecycle.stopped << ' ' << s.delivered << ' ' << ref.exiting() << ' '
    << ref.done() << ' ' << ref.exit_code() << ' ' << ref.services << '\n';
}
static void boundary(reference_t &ref, std::ostream &f, unsigned n) {
  f << n << ' ' << ref.exiting() << ' ' << ref.done() << ' ' << ref.exit_code() << ' ' << ref.services << '\n';
}
static int run(const char *mode, const char *source, const char *destination,
               const char *scenario, const char *detail) {
  try {
    for (int sig : {SIGINT, SIGTERM, SIGABRT}) mask(SIG_BLOCK, sig);
    const std::string op(mode), which(scenario); fs::path out(destination); fs::create_directories(out);
    reference_t ref(which == "signature");
    firesim_tsi_htif_signal_t owner(ref);
    if (op == "capture") {
      if (which == "int") deliver(SIGINT);
      else if (which == "term") deliver(SIGTERM);
      else require(which == "none", "capture scenario");
      unsigned present, stopped; unsigned long raw;
      require(std::sscanf(detail, "%u,%lu,%u", &present, &raw, &stopped) == 3, "capture fields");
      if (present) { const uint32_t v = raw; int signed_raw; std::memcpy(&signed_raw, &v, 4); ref.htif_exit(signed_raw); }
      if (stopped) ref.stop();
      save(out/"captured.signal", owner.save_checkpoint()); fields(ref, out/"captured.fields");
      bool strict_rejected = false;
      try { firesim_tsi_htif_lifecycle_t(ref).save_checkpoint(); }
      catch (const std::runtime_error &) { strict_rejected = true; }
      require(strict_rejected == (which != "none"), "strict lifecycle signal guard changed");
      std::ofstream trace(out/"continuation.txt"); boundary(ref, trace, 0);
      if (ref.exiting() && !ref.done()) ref.stop();
      boundary(ref, trace, 1);
    } else if (op == "restore" || op == "second" || op == "corrupt") {
      auto image = bytes(source); const auto initial = owner.save_checkpoint();
      auto next = owner.prepare_checkpoint(image);
      require(owner.save_checkpoint() == initial && !ref.exiting() && !ref.done(), "preparation published provider");
      image.clear(); next.commit();
      save(out/"readback.signal", owner.save_checkpoint()); fields(ref, out/"readback.fields");
      if (op == "second") {
        std::cout << "SECOND_SIGNAL before=" << ref.exiting() << std::endl;
        deliver(SIGTERM); // real provider exits(-1) if restored delivered=true
        require(ref.exiting(), "first real signal not delivered");
        std::cout << "FIRST_SIGNAL delivered=1\n";
      } else if (op == "corrupt") {
        const bool exiting = ref.exiting(), stopped = ref.done(); const int code = ref.exit_code();
        if (which == "delivered") deliver(SIGINT);
        else if (which == "stopped") ref.stop();
        else if (which == "raw") ref.htif_exit(4);
        else throw std::runtime_error("unknown semantic corruption");
        const char *signal = nullptr;
        if (ref.exiting() != exiting) signal = "should_exit";
        else if (ref.done() != stopped) signal = "stopped";
        else if (ref.exit_code() != code) signal = "exit_code";
        require(signal, "corruption did not change actual provider");
        std::ofstream(out/"first-divergence.txt") << "FIRST_DIVERGENCE boundary=0 signal=" << signal << " acknowledged=0 target_services=0\n";
        fields(ref, out/"corrupted.fields"); save(out/"corrupted.signal", owner.save_checkpoint());
      } else {
        std::ofstream trace(out/"continuation.txt"); boundary(ref, trace, 0);
        if (ref.exiting() && !ref.done()) ref.stop();
        boundary(ref, trace, 1);
        bool rejected = false; try { next.commit(); } catch (const std::runtime_error &) { rejected = true; }
        require(rejected, "candidate committed twice");
      }
    } else if (op == "reject") {
      const auto initial = owner.save_checkpoint();
      bool rejected = false;
      try { auto next = owner.prepare_checkpoint(bytes(source)); next.commit(); }
      catch (const std::runtime_error &) { rejected = true; }
      require(rejected && owner.save_checkpoint() == initial && !ref.exiting() && !ref.done(), "non-atomic malformed rejection");
      save(out/"unchanged.signal", owner.save_checkpoint());
    } else if (op == "guard" || op == "abandon" || op == "publish") {
      auto image = bytes(source);
      firesim_tsi_serial_state_t peer, replacement;
      peer.issue_read(0x80001234, 8); peer.push_response(0x11223344);
      const uint32_t words[]{0xdeadbeef, 0xfedcba98}; replacement.issue_write(0x1234567887654320, 8, words);
      const auto initial_peer = peer.save_checkpoint(), wanted_peer = replacement.save_checkpoint();
      save(out/"before.serial", initial_peer); save(out/"candidate.serial", wanted_peer);
      unsigned callbacks = 0;
      auto publish = [&]() noexcept { peer.swap_state(replacement); ++callbacks; };
      if (which == "signature") {
        bool rejected = false; try { auto next = owner.prepare_checkpoint(image); }
        catch (const std::runtime_error &) { rejected = true; }
        require(rejected && !callbacks && !ref.exiting() && !ref.done(), "signature guard");
      } else {
        const auto initial = owner.save_checkpoint(); auto next = owner.prepare_checkpoint(image);
        require(owner.save_checkpoint() == initial && peer.save_checkpoint() == initial_peer, "early peer publication");
        if (op == "publish") {
          next.commit(publish);
          require(owner.save_checkpoint() == image && peer.save_checkpoint() == wanted_peer && callbacks == 1, "incomplete atomic publication");
          bool rejected = false; try { next.commit(publish); } catch (const std::runtime_error &) { rejected = true; }
          require(rejected && callbacks == 1, "consumed candidate republished peers");
        } else if (op == "guard") {
          const int sig = std::stoi(detail); struct sigaction original{}, action{};
          require(sigaction(sig, nullptr, &original) == 0, "read original action"); action = original;
          if (which == "pending") require(std::raise(sig) == 0, "pending signal");
          else if (which == "delivered") deliver(sig);
          else if (which == "mask") mask(SIG_UNBLOCK, sig);
          else if (which == "handler") { action.sa_handler = SIG_IGN; require(sigaction(sig, &action, nullptr) == 0, "handler change"); }
          else if (which == "flags") { action.sa_flags ^= SA_RESTART; require(sigaction(sig, &action, nullptr) == 0, "flag change"); }
          else if (which == "handler-mask") { sigaddset(&action.sa_mask, SIGUSR1); require(sigaction(sig, &action, nullptr) == 0, "handler-mask change"); }
          else if (which == "occupied-exit") ref.htif_exit(0);
          else if (which == "occupied-stop") ref.stop();
          else throw std::runtime_error("unknown guard");
          bool rejected = false; try { auto other = owner.prepare_checkpoint(image); }
          catch (const std::runtime_error &) { rejected = true; }
          require(rejected, "prepare missed late destination guard");
          rejected = false; try { next.commit(publish); } catch (const std::runtime_error &) { rejected = true; }
          require(rejected && !callbacks && peer.save_checkpoint() == initial_peer, "guard published peers");
          if (which == "pending") { sigset_t set; sigemptyset(&set); sigaddset(&set, sig); int actual;
            require(sigwait(&set, &actual) == 0 && actual == sig, "drain pending"); }
          else if (which == "mask") mask(SIG_BLOCK, sig);
          else if (which == "handler" || which == "flags" || which == "handler-mask")
            require(sigaction(sig, &original, nullptr) == 0, "restore action");
          const auto s = firesim_htif_signal_read(ref);
          require(s.delivered == (which == "delivered") && s.lifecycle.has_exit == (which == "occupied-exit") &&
                  s.lifecycle.raw_exit == 0 && s.lifecycle.stopped == (which == "occupied-stop"), "guard mutated provider");
        } else require(op == "abandon", "transaction mode");
        save(out/"after.signal", owner.save_checkpoint()); fields(ref, out/"after.fields");
      }
      require(peer.save_checkpoint() == (op == "publish" ? wanted_peer : initial_peer), "unexpected peer mutation");
      save(out/"after.serial", peer.save_checkpoint());
      std::ofstream(out/"transaction.txt") << "callbacks=" << callbacks << " target_services=" << ref.services << '\n';
    } else throw std::runtime_error("unknown mode");
    require(ref.services == 0, "target service during provider operation");
    std::cout << "HTIF_SIGNAL mode=" << mode << " scenario=" << scenario << " target_services=0 target_edges=0\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_HTIF_SIGNAL_DPI
extern "C" int tsi_htif_signal(const char *m, const char *s, const char *d, const char *c, const char *v) { return run(m,s,d,c,v); }
extern "C" void tsi_htif_signal_exit(int code) { std::exit(code); }
#else
int main(int argc, char **argv) { if (argc != 6) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5]); }
#endif
