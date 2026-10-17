// Compiled after the unchanged, exact-header-matched FESVR htif.cc. This is
// the only adapter allowed to access the actual private provider fields and
// translation-unit signal latch. No raw object bytes or host pointers escape.
#include "htif_lifecycle.h"
#include "htif_signal.h"
#include "htif_signal_threads.h"
#include "htif_dormant_proxy.h"
#include <fcntl.h>
#include <cstring>
#include <pthread.h>
#include <stdexcept>

struct firesim_htif_lifecycle_access_t {
  static void proxy_links(const htif_t &htif) {
    const auto &proxy = htif.syscall_proxy;
    if (proxy.htif != &htif || proxy.memif != &htif.mem ||
        !proxy.chroot.empty() || !htif.dynamic_devices.empty())
      throw std::runtime_error("unsupported inherited HTIF proxy links/session");
  }
  static void validate_proxy(const htif_t &htif) {
    proxy_links(htif);
    const auto &proxy = htif.syscall_proxy;
    if (!proxy.fds.fds.empty() || !proxy.fds_index.empty() || !proxy.table.empty())
      throw std::runtime_error("inherited HTIF proxy resources are not retired");
  }
  static void retire_proxy(htif_t &htif) {
    proxy_links(htif);
    auto &proxy = htif.syscall_proxy;
    if (proxy.fds_index != std::vector<reg_t>{0, 1, 2} ||
        proxy.fds.fds.size() != 3 || proxy.table.size() != 2048)
      throw std::runtime_error("inherited HTIF proxy is not pristine");
    const auto &fds = proxy.fds.fds;
    for (size_t i = 0; i < 3; ++i) {
      if (fds[i] <= 2 || fcntl(fds[i], F_GETFD) < 0)
        throw std::runtime_error("invalid inherited HTIF proxy descriptor");
      for (size_t j = 0; j < i; ++j)
        if (fds[i] == fds[j]) throw std::runtime_error("aliased inherited proxy descriptors");
    }
    // Linux close releases the descriptor even on EINTR. Never retry it or
    // leave a stale number for the installed destructor to close again.
    bool failed = false;
    for (auto &fd : proxy.fds.fds) {
      const auto owned = fd; fd = -1;
      if (close(owned) && errno != EINTR) failed = true;
    }
    proxy.fds_index.clear(); proxy.fds.fds.clear(); proxy.table.clear();
    if (failed) throw std::runtime_error("cannot retire inherited HTIF proxy descriptors");
    validate_proxy(htif);
  }
  static void signal_guard(const htif_t &htif) {
    if (!htif.sig_file.empty())
      throw std::runtime_error("HTIF signal signature state is unsupported");
    sigset_t mask, pending;
    if (pthread_sigmask(SIG_BLOCK, nullptr, &mask) != 0 || sigpending(&pending) != 0)
      throw std::runtime_error("cannot inspect HTIF signal state");
    for (int sig : {SIGINT, SIGTERM, SIGABRT}) {
      struct sigaction action{};
      if (sigismember(&mask, sig) != 1 || sigismember(&pending, sig) != 0 ||
          sigaction(sig, nullptr, &action) != 0 || action.sa_handler != &handle_signal)
        throw std::runtime_error("unsupported HTIF signal mask/pending/handler state");
      // Exact GNU/Linux BSD signal() ABI, as compiled by this provider. The
      // kernel restorer flag is process-local machinery, not image data.
      // Reject altered restart, stack, one-shot, siginfo and handler masks.
#if defined(__linux__) && defined(__x86_64__)
      constexpr unsigned restorer = 0x04000000;
      if (unsigned(action.sa_flags) != (unsigned(SA_RESTART) | restorer))
        throw std::runtime_error("unsupported HTIF signal action flags");
      for (int member = 1; member < NSIG; ++member)
        if (sigismember(&action.sa_mask, member) != int(member == sig))
          throw std::runtime_error("unsupported HTIF signal action mask");
#else
      throw std::runtime_error("unsupported HTIF signal provider ABI");
#endif
    }
    firesim_htif_signal_threads::guard();
  }
  static firesim_htif_signal_state_t signal_read(const htif_t &htif) {
    signal_guard(htif);
    static_assert(sizeof(int) == sizeof(uint32_t), "unsupported HTIF integer ABI");
    uint32_t raw = 0;
    if (htif.exitcode) std::memcpy(&raw, &*htif.exitcode, sizeof(raw));
    return {{htif.exitcode.has_value(), raw, htif.stopped}, signal_exit};
  }
  static void signal_validate_restore(const htif_t &htif, firesim_htif_signal_state_t state) {
    signal_guard(htif);
    if (signal_exit || htif.exitcode.has_value() || htif.stopped ||
        (!state.lifecycle.has_exit && state.lifecycle.raw_exit))
      throw std::runtime_error("HTIF signal restore requires valid state and pristine destination");
  }
  static void signal_publish(htif_t &htif, firesim_htif_signal_state_t state,
                             void (*publish_peers)(void *) noexcept, void *peers) {
    signal_validate_restore(htif, state);
    int raw;
    std::memcpy(&raw, &state.lifecycle.raw_exit, sizeof(raw));
    if (publish_peers) publish_peers(peers);
    if (state.lifecycle.has_exit) htif.exitcode = raw;
    htif.stopped = state.lifecycle.stopped;
    signal_exit = state.delivered;
  }
  static void guard(const htif_t &htif) {
    // Polling/host/context groups use this API, rather than the delivered-signal
    // owner. They must enforce the same all-thread and exact-action admission
    // at capture, preparation, publication and each fresh-context resume.
    // This audit still requires the caller's exclusive suspension contract.
    signal_guard(htif);
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
  static void validate_restore(const htif_t &htif, firesim_htif_lifecycle_state_t state) {
    guard(htif);
    if (htif.exitcode.has_value() || htif.stopped || (!state.has_exit && state.raw_exit))
      throw std::runtime_error("HTIF lifecycle restore requires valid state and pristine destination");
  }
  static void publish(htif_t &htif, firesim_htif_lifecycle_state_t state,
                      void (*publish_peers)(void *) noexcept, void *peers) {
    validate_restore(htif, state);
    int raw;
    std::memcpy(&raw, &state.raw_exit, sizeof(raw));
    // No guard or allocation may follow peer publication. The external caller
    // owns suspension, exclusion and the supported thread/signal policy.
    if (publish_peers) publish_peers(peers);
    // All checks precede these nonthrowing assignments. Do not reissue an exit
    // command or call stop(): both would be services at the restored boundary.
    if (state.has_exit) htif.exitcode = raw;
    htif.stopped = state.stopped;
  }
};
firesim_htif_signal_state_t firesim_htif_signal_read(const htif_t &htif) {
  return firesim_htif_lifecycle_access_t::signal_read(htif);
}
void firesim_htif_signal_validate_restore(const htif_t &htif, firesim_htif_signal_state_t state) {
  firesim_htif_lifecycle_access_t::signal_validate_restore(htif, state);
}
void firesim_htif_signal_publish(htif_t &htif, firesim_htif_signal_state_t state,
                                void (*publish_peers)(void *) noexcept, void *peers) {
  firesim_htif_lifecycle_access_t::signal_publish(htif, state, publish_peers, peers);
}
void firesim_htif_lifecycle_validate_restore(const htif_t &htif, firesim_htif_lifecycle_state_t state) {
  firesim_htif_lifecycle_access_t::validate_restore(htif, state);
}
void firesim_htif_lifecycle_publish(htif_t &htif, firesim_htif_lifecycle_state_t state,
                                  void (*publish_peers)(void *) noexcept, void *peers) {
  firesim_htif_lifecycle_access_t::publish(htif, state, publish_peers, peers);
}
firesim_htif_lifecycle_state_t firesim_htif_lifecycle_read(const htif_t &htif) {
  return firesim_htif_lifecycle_access_t::read(htif);
}
void firesim_htif_lifecycle_restore(htif_t &htif, firesim_htif_lifecycle_state_t state) {
  firesim_htif_lifecycle_access_t::publish(htif, state, nullptr, nullptr);
}

extern "C" const firesim_htif_lifecycle_api_t *firesim_htif_lifecycle_api() {
  static const firesim_htif_lifecycle_api_t api{
      &firesim_htif_lifecycle_read, &firesim_htif_lifecycle_validate_restore, &firesim_htif_lifecycle_publish};
  return &api;
}
extern "C" const firesim_htif_dormant_proxy_api_t *firesim_htif_dormant_proxy_api() {
  static const firesim_htif_dormant_proxy_api_t api{
      &firesim_htif_lifecycle_access_t::retire_proxy,
      &firesim_htif_lifecycle_access_t::validate_proxy};
  return &api;
}
