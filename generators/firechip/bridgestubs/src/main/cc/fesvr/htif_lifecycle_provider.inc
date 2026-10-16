// Compiled after the unchanged, exact-header-matched FESVR htif.cc. This is
// the only adapter allowed to access the actual private provider fields and
// translation-unit signal latch. No raw object bytes or host pointers escape.
#include "htif_lifecycle.h"
#include <cstring>
#include <pthread.h>
#include <stdexcept>

struct firesim_htif_lifecycle_access_t {
  static void guard(const htif_t &htif) {
    if (!htif.sig_file.empty())
      throw std::runtime_error("HTIF lifecycle signature state is unsupported");
    sigset_t mask, pending;
    if (pthread_sigmask(SIG_BLOCK, nullptr, &mask) != 0 || sigpending(&pending) != 0)
      throw std::runtime_error("cannot inspect HTIF signal state");
    for (int sig : {SIGINT, SIGTERM, SIGABRT}) {
      struct sigaction action{};
      if (sigismember(&mask, sig) != 1 || sigismember(&pending, sig) != 0 ||
          sigaction(sig, nullptr, &action) != 0 || (action.sa_flags & SA_SIGINFO) ||
          action.sa_handler != &handle_signal)
        throw std::runtime_error("unowned HTIF signal mask/pending/handler state");
    }
    if (signal_exit)
      throw std::runtime_error("delivered HTIF signal is unsupported");
  }
  static firesim_htif_lifecycle_state_t read(const htif_t &htif) {
    guard(htif);
    static_assert(sizeof(int) == sizeof(uint32_t), "unsupported HTIF integer ABI");
    uint32_t raw = 0;
    if (htif.exitcode) std::memcpy(&raw, &*htif.exitcode, sizeof(raw));
    return {htif.exitcode.has_value(), raw, htif.stopped};
  }
  static void restore(htif_t &htif, firesim_htif_lifecycle_state_t state) {
    guard(htif);
    if (htif.exitcode.has_value() || htif.stopped || (!state.has_exit && state.raw_exit))
      throw std::runtime_error("HTIF lifecycle restore requires valid state and pristine destination");
    int raw;
    std::memcpy(&raw, &state.raw_exit, sizeof(raw));
    // All checks precede these nonthrowing assignments. Do not reissue an exit
    // command or call stop(): both would be services at the restored boundary.
    if (state.has_exit) htif.exitcode = raw;
    htif.stopped = state.stopped;
  }
};
firesim_htif_lifecycle_state_t firesim_htif_lifecycle_read(const htif_t &htif) {
  return firesim_htif_lifecycle_access_t::read(htif);
}
void firesim_htif_lifecycle_restore(htif_t &htif, firesim_htif_lifecycle_state_t state) {
  firesim_htif_lifecycle_access_t::restore(htif, state);
}
