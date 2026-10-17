// Real worker-signal faults at the restricted sixteen-owner aggregate API.
// Test parking/inherited masks provide exclusion; no production coordinator.
#define TSI_CONTEXT_GROUP_DPI
#include "tsi_context_group_fesvr.cc"
#include <condition_variable>
#include <mutex>

__attribute__((constructor)) static void context_blocked_inheritance() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
  if (pthread_sigmask(SIG_BLOCK, &set, nullptr)) std::abort();
}

class context_worker_t {
public:
  explicit context_worker_t(int unblocked = 0) : worker([this, unblocked] {
    sigset_t one; sigemptyset(&one);
    if (unblocked) {
      sigaddset(&one, unblocked);
      require(!pthread_sigmask(SIG_UNBLOCK, &one, nullptr), "worker unblock");
    }
    std::unique_lock<std::mutex> lock(mutex);
    ready = true; changed.notify_all();
    changed.wait(lock, [this] { return repair_requested; });
    if (unblocked) require(!pthread_sigmask(SIG_BLOCK, &one, nullptr), "worker reblock");
    if (pending) {
      sigemptyset(&one); sigaddset(&one, pending);
      timespec timeout{};
      require(sigtimedwait(&one, nullptr, &timeout) == pending, "worker drain");
    }
    repaired = true; changed.notify_all();
    changed.wait(lock, [this] { return released; });
  }) {
    std::unique_lock<std::mutex> lock(mutex);
    changed.wait(lock, [this] { return ready; });
  }
  void pend(int sig) {
    std::lock_guard<std::mutex> lock(mutex);
    require(!pthread_kill(worker.native_handle(), sig), "worker signal"); pending = sig;
  }
  void repair() {
    std::unique_lock<std::mutex> lock(mutex);
    repair_requested = true; changed.notify_all();
    changed.wait(lock, [this] { return repaired; });
  }
  ~context_worker_t() {
    repair();
    { std::lock_guard<std::mutex> lock(mutex); released = true; }
    changed.notify_all(); worker.join();
  }
private:
  std::mutex mutex;
  std::condition_variable changed;
  bool ready = false, repair_requested = false, repaired = false, released = false;
  int pending = 0;
  std::thread worker;
};

// Lifecycle and syscall images both consult the guarded provider. Exclude
// both while a real signal violation is installed, then check them after
// repair, before any retry or service.
static images_t accessible_context(const firesim_tsi_t &tsi) {
  auto result = peers(tsi);
  result.emplace_back("outer", tsi.host_execution_owner().save_checkpoint());
  result.emplace_back("wrapper", tsi.host_wrapper_owner().save_checkpoint());
  return result;
}

static int threads_run(const char *operation, const char *fault, int sig,
                       const char *elf, const char *input, const char *metadata,
                       const char *source, const char *destination) {
  try {
    require(sig == SIGINT || sig == SIGTERM || sig == SIGABRT, "unexpected signal");
    sigset_t signals; sigemptyset(&signals);
    for (int s : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&signals, s);
    require(!pthread_sigmask(SIG_BLOCK, &signals, nullptr), "block aggregate signals");
    const std::string op(operation), kind(fault); const fs::path out(destination);
    fs::create_directories(out);
    std::vector<std::string> args{"threads", "+permissive", "+no_hart0_msip", "+idle-counts=3",
      "+checkpoint-syscall-exit", "+checkpoint-terminal-input="+std::string(input), "+permissive-off", elf};
    std::vector<char *> argv; for (auto &s : args) argv.push_back(s.data());
    firesim_tsi_t tsi(argv.size(), argv.data(), true); context_group_t group(tsi);
    tsi.prepare_startup_metadata(bytes(metadata)); const auto good = load_context(source);
    auto candidate = group.prepare(good);
    const bool pristine = op == "prepare" || op == "commit";
    if (!pristine) { candidate.commit(); if (op == "resume-live") group.resume(); }
    const auto before = accessible_context(tsi);
    const auto verified_before = context_unprepared(tsi);
    const auto fields = firesim_htif_require_lifecycle_api().read(tsi);
    const auto initialized = group.native_context_initialized();
    if (!pristine) save(out/"before", group.inspect());
    save(out/"before-unprepared", before);
    save(out/"before-verified", verified_before);
    context_worker_t first(kind == "worker-mask" ? sig : 0), second;
    struct sigaction saved_action{}; require(!sigaction(sig, nullptr, &saved_action), "read action");
    if (kind == "worker-pending") first.pend(sig);
    else if (kind == "second-worker-pending") second.pend(sig);
    else if (kind == "shared-pending") require(!kill(getpid(), sig), "shared signal");
    else if (kind == "action-flags" || kind == "action-mask") {
      auto changed = saved_action;
      if (kind == "action-flags") changed.sa_flags ^= SA_RESTART;
      else sigaddset(&changed.sa_mask, SIGUSR1);
      require(!sigaction(sig, &changed, nullptr), "alter action");
    } else require(kind == "worker-mask", "unknown worker fault");
    bool rejected = false; std::string reason;
    try {
      if (op == "prepare") { auto next = group.prepare(good); }
      else if (op == "commit") candidate.commit();
      else if (op == "capture") group.inspect();
      else { require(op == "resume-fresh" || op == "resume-live", "unknown worker operation"); group.resume(); }
    } catch (const std::runtime_error &e) { rejected = true; reason = e.what(); }
    // No guarded provider read is possible while the violation is installed.
    // Check every accessible owner now, then all sixteen/provider fields after
    // repairing the policy while the same two workers remain parked and alive.
    const auto after = accessible_context(tsi);
    const auto after_initialized = group.native_context_initialized();
    if (kind == "shared-pending") {
      sigset_t one; sigemptyset(&one); sigaddset(&one, sig); timespec timeout{};
      require(sigtimedwait(&one, nullptr, &timeout) == sig, "shared drain");
    }
    require(!sigaction(sig, &saved_action, nullptr), "restore action");
    first.repair(); second.repair();
    require(rejected, "aggregate admission ignored actual worker/action fault");
    require(after == before && after_initialized == initialized, "worker fault changed aggregate/context");
    save(out/"after-unprepared", after);
    const auto verified_after = context_unprepared(tsi);
    require(verified_after == verified_before, "worker fault changed syscall/provider peers");
    save(out/"after-verified", verified_after);
    const auto actual = firesim_htif_require_lifecycle_api().read(tsi);
    require(fields.has_exit == actual.has_exit && fields.raw_exit == actual.raw_exit && fields.stopped == actual.stopped,
            "worker fault changed actual provider");
    if (pristine) {
      bool absent = false; try { tsi.htif_poll_owner(); } catch (const std::runtime_error &) { absent = true; }
      require(absent, "worker fault published polling child");
      // A rejected commit retains its exact candidate for a single valid retry.
      if (op == "prepare") { auto next = group.prepare(good); next.commit(); }
      else candidate.commit();
      require(group.inspect() == good, "worker retry restore differs");
    } else {
      save(out/"after", group.inspect());
      if (op != "capture") group.resume();
    }
    save(out/"retry", group.inspect());
    std::ofstream(out/"rejection.txt") << reason << '\n';
    std::cout << "CONTEXT_THREAD_GUARD operation=" << op << " fault=" << kind << " signal=" << sig
              << " rejected=1 owners=16 unchanged=1 retry=1 initialized=" << initialized
              << " services_on_rejection=0 target_edges=0\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_CONTEXT_THREADS_DPI
extern "C" int tsi_context_threads(const char *o, const char *f, int s, const char *e,
  const char *i, const char *m, const char *p, const char *d) { return threads_run(o,f,s,e,i,m,p,d); }
#else
int main(int argc, char **argv) { return argc == 9 ? threads_run(argv[1],argv[2],std::stoi(argv[3]),argv[4],argv[5],argv[6],argv[7],argv[8]) : 2; }
#endif
