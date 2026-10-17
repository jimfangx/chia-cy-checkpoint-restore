// Mailbox lifecycle and creator identity, including teardown and exceptions.
#include "emul/driver_thread.h"
#include <atomic>
#include <iostream>
#include <memory>
#include <csignal>
#include <pthread.h>

void tsi_terminal_fail_allocation_after(long count);

static void check(bool b) {
  if (!b) throw std::runtime_error("driver creator assertion");
}
static unsigned rejected = 0;
template<class F> static void rejects(F fn) {
  try { fn(); } catch (const std::runtime_error &) { ++rejected; return; }
  throw std::logic_error("missing driver creator rejection");
}
struct capture_t {
  std::thread::id &destroyer;
  ~capture_t() { destroyer = std::this_thread::get_id(); }
};
struct resident_t final : emul_driver_thread_t::resource_t {
  emul_driver_thread_t &worker;
  std::thread::id creator;
  unsigned &destroyed;
  bool &capture_gone;
  resident_t(emul_driver_thread_t &w, unsigned &d, bool &g)
      : worker(w), creator(std::this_thread::get_id()), destroyed(d), capture_gone(g) {}
  ~resident_t() override {
    // Also proves cleanup does not hold the mailbox mutex.
    if (std::this_thread::get_id()!=creator || worker.reserved() || !capture_gone)
      std::abort();
    ++destroyed;
  }
};
static void test_residents() {
  unsigned destroyed=0, launched=0, exceptions=0;
  const auto before=rejected;
  for (unsigned trial=0;trial<32;++trial) {
    bool capture_gone=true;
    emul_driver_thread_t worker;
    rejects([&] { worker.retain({}); });
    worker.reserve();
    rejects([&] { worker.retain({}); });
    std::thread foreign([&] { rejects([&] { worker.retain({}); }); });
    foreign.join();
    worker.invoke([&] {
      rejects([&] { worker.retain({}); });
      worker.retain(std::make_unique<resident_t>(worker,destroyed,capture_gone));
      rejects([&] { worker.retain(std::make_unique<emul_driver_thread_t::resource_t>()); });
    });
    try { worker.invoke([] { throw std::bad_alloc(); }); }
    catch(const std::bad_alloc &) { ++exceptions; }
    check(destroyed==trial);
    worker.invoke([&] { check(std::this_thread::get_id()==worker.get_id()); });
    if (trial%2) {
      worker.cancel_reserved();
    } else {
      capture_gone=false;
      auto capture=std::shared_ptr<int>(new int, [&](int *p) {
        check(std::this_thread::get_id()==worker.get_id());
        check(destroyed==trial); capture_gone=true; delete p;
      });
      worker.launch([&,capture=std::move(capture)] {
        check(destroyed==trial && !capture_gone); ++launched;
        rejects([&] { worker.retain({}); });
      });
      worker.join();
    }
    check(destroyed==trial+1);
  }
  check(destroyed==32 && launched==16 && exceptions==32 && rejected-before==176);
  std::cout<<"DRIVER_RESIDENT_PASS destroyed=32 launches=16 cancellations=16 exceptions=32 rejections=176 capture_order=1\n";
}

static void test_prepared_launch() {
  static_assert(noexcept(std::declval<emul_driver_thread_t &>().launch_prepared()));
  unsigned destroyed=0, launched=0, allocation_failures=0;
  const auto before=rejected;
  for (unsigned trial=0;trial<32;++trial) {
    emul_driver_thread_t worker;
    bool capture_gone=true;
    rejects([&] { worker.prepare_launch([] {}); });
    worker.reserve();
    rejects([&] { worker.prepare_launch({}); });
    worker.invoke([&] {
      worker.retain(std::make_unique<resident_t>(worker,destroyed,capture_gone));
      rejects([&] { worker.prepare_launch([] {}); });
    });
    capture_gone=false;
    auto capture=std::shared_ptr<int>(new int, [&](int *p) {
      check(std::this_thread::get_id()==worker.get_id() && destroyed==trial);
      capture_gone=true; delete p;
    });
    // The allocating std::function conversion must fail before installation.
    auto task=[&,capture=std::move(capture)] {
      check(!capture_gone && destroyed==trial && !worker.launch_prepared_pending());
      ++launched;
    };
    tsi_terminal_fail_allocation_after(0);
    try { worker.prepare_launch(task); }
    catch(const std::bad_alloc &) { ++allocation_failures; }
    tsi_terminal_fail_allocation_after(-1);
    check(allocation_failures==trial+1 && !worker.launch_prepared_pending() && launched==(trial+1)/2);
    worker.prepare_launch(std::move(task));
    check(worker.launch_prepared_pending());
    rejects([&] { worker.prepare_launch([] {}); });
    rejects([&] { worker.launch([] {}); });
    std::thread foreign([&] { rejects([&] { worker.prepare_launch([] {}); }); });
    foreign.join();
    try {
      worker.invoke([&] {
        check(worker.launch_prepared_pending() && destroyed==trial && !capture_gone);
        throw std::bad_alloc();
      });
    } catch(const std::bad_alloc &) {}
    check(worker.launch_prepared_pending() && destroyed==trial && !capture_gone);
    if (trial%2) worker.cancel_reserved();
    else {
      // No allocation or callable copy is permitted after publication.
      tsi_terminal_fail_allocation_after(0);
      worker.launch_prepared();
      tsi_terminal_fail_allocation_after(-1);
      worker.join();
      rejects([&] { worker.prepare_launch([] {}); });
    }
    check(destroyed==trial+1 && capture_gone && !worker.launch_prepared_pending());
  }
  check(launched==16 && destroyed==32 && allocation_failures==32 && rejected-before==208);
  std::cout<<"DRIVER_PREPARED_LAUNCH_PASS destroyed=32 launches=16 cancellations=16 allocation_failures=32 rejections=208 allocation_free_commit=1 capture_order=1\n";
}

// An actual creator-owned lock and signal mask survive controller publication.
// They model exclusion resources; no claim is made about VCS's other threads.
struct publication_guard_t final : emul_driver_thread_t::resource_t {
  emul_driver_thread_t &worker;
  std::unique_lock<std::mutex> lock;
  sigset_t previous;
  bool &live;
  unsigned &destroyed;
  publication_guard_t(emul_driver_thread_t &w, std::mutex &m, bool &l, unsigned &d)
      : worker(w), lock(m), live(l), destroyed(d) {
    check(std::this_thread::get_id()==worker.get_id() && !live);
    sigset_t block; sigemptyset(&block); sigaddset(&block,SIGUSR2);
    check(!pthread_sigmask(SIG_BLOCK,&block,&previous)); live=true;
  }
  ~publication_guard_t() override {
    if (std::this_thread::get_id()!=worker.get_id() || !live || worker.publication_sealed() ||
        pthread_sigmask(SIG_SETMASK,&previous,nullptr)) std::abort();
    live=false; ++destroyed;
  }
};
static void test_publication_seal() {
  unsigned guard_destroyed=0, resident_destroyed=0, launches=0, allocation_failures=0;
  const auto before=rejected;
  for (unsigned trial=0;trial<32;++trial) {
    emul_driver_thread_t worker;
    std::mutex gate;
    bool live=false, capture_gone=true;
    int original_mask=-1;
    auto factory=[&]() -> std::unique_ptr<emul_driver_thread_t::resource_t> {
      return std::make_unique<publication_guard_t>(worker,gate,live,guard_destroyed);
    };
    rejects([&] { worker.seal_launch(factory); });
    worker.reserve();
    rejects([&] { worker.seal_launch(factory); }); // No staged continuation.
    worker.invoke([&] {
      sigset_t mask; check(!pthread_sigmask(SIG_SETMASK,nullptr,&mask));
      original_mask=sigismember(&mask,SIGUSR2);
      worker.retain(std::make_unique<resident_t>(worker,resident_destroyed,capture_gone));
    });
    capture_gone=false;
    auto capture=std::shared_ptr<int>(new int, [&](int *p) {
      check(std::this_thread::get_id()==worker.get_id() && resident_destroyed==trial);
      // Cancellation destroys captures before releasing publication exclusion.
      check(live==bool(trial%2)); capture_gone=true; delete p;
    });
    worker.prepare_launch([&,capture=std::move(capture)] {
      check(!live && !worker.publication_sealed() && !capture_gone);
      sigset_t mask; check(!pthread_sigmask(SIG_SETMASK,nullptr,&mask));
      check(sigismember(&mask,SIGUSR2)==original_mask);
      check(gate.try_lock()); gate.unlock(); ++launches;
    });
    rejects([&] { worker.seal_launch({}); });
    rejects([&] { worker.seal_launch([] { return std::unique_ptr<emul_driver_thread_t::resource_t>{}; }); });
    rejects([&] { worker.seal_launch([&]() -> std::unique_ptr<emul_driver_thread_t::resource_t> {
      auto guard=factory(); throw std::runtime_error("failed final validation");
    }); });
    check(!live && guard_destroyed==2*trial+1 && worker.reserved());
    // Both factory-side guard allocation and controller callable conversion
    // fail before installation. The same creator can retry either failure.
    tsi_terminal_fail_allocation_after(0);
    try { worker.seal_launch(factory); } catch(const std::bad_alloc &) { ++allocation_failures; }
    tsi_terminal_fail_allocation_after(-1);
    worker.invoke([&] { tsi_terminal_fail_allocation_after(0); });
    try { worker.seal_launch(factory); } catch(const std::bad_alloc &) { ++allocation_failures; }
    worker.invoke([&] { tsi_terminal_fail_allocation_after(-1); });
    check(worker.reserved() && !live);
    worker.invoke([&] {
      sigset_t mask; check(!pthread_sigmask(SIG_SETMASK,nullptr,&mask));
      check(sigismember(&mask,SIGUSR2)==original_mask);
    });
    worker.seal_launch(factory);
    check(worker.publication_sealed() && !worker.reserved() && live && !gate.try_lock());
    rejects([&] { worker.invoke([] {}); });
    rejects([&] { worker.prepare_launch([] {}); });
    rejects([&] { worker.launch([] {}); });
    rejects([&] { worker.seal_launch(factory); });
    rejects([&] { worker.retain({}); });
    std::thread foreign([&] {
      check(!gate.try_lock());
      rejects([&] { worker.invoke([] {}); });
      rejects([&] { worker.seal_launch(factory); });
      rejects([&] { worker.prepare_launch([] {}); });
    }); foreign.join();
    // The controller's publication/readback occurs with the creator parked,
    // the native mutex owned, and the staged continuation still dormant.
    check(launches==(trial+1)/2 && !capture_gone && worker.launch_prepared_pending());
    if (trial%2) worker.cancel_reserved();
    else {
      tsi_terminal_fail_allocation_after(0); worker.launch_prepared();
      tsi_terminal_fail_allocation_after(-1); worker.join();
    }
    check(!live && capture_gone && guard_destroyed==2*trial+2 && resident_destroyed==trial+1);
    check(gate.try_lock()); gate.unlock();
  }
  check(launches==16 && allocation_failures==64 && rejected-before==416);
  std::cout<<"DRIVER_PUBLICATION_SEAL_PASS guards=64 launches=16 cancellations=16 allocation_failures=64 rejections=416 creator_lock=1 creator_mask=1 allocation_free_commit=1 cleanup_order=1\n";
}
static int test_creator() {
  try {
    unsigned tasks = 0, failures = 0, launches = 0, cancellations = 0;
    const auto controller = std::this_thread::get_id();
    for (unsigned trial=0; trial<32; ++trial) {
      emul_driver_thread_t worker;
      rejects([&] { worker.invoke([] {}); });
      worker.reserve();
      const auto creator = worker.get_id();
      check(creator != controller && worker.reserved());
      rejects([&] { worker.reserve(); });
      rejects([&] { worker.invoke({}); });
      rejects([&] { worker.launch({}); });
      // Foreign and recursive requests must reject, never deadlock or queue.
      std::thread foreign([&] {
        rejects([&] { worker.invoke([] {}); });
        rejects([&] { worker.launch([] {}); });
        rejects([&] { worker.require_controller_if_started(); });
      });
      foreign.join();
      for (unsigned n=0; n<16; ++n) {
        std::thread::id destroyed;
        auto capture = std::shared_ptr<capture_t>(new capture_t{destroyed});
        worker.invoke([&, capture=std::move(capture)] {
          check(std::this_thread::get_id() == creator);
          rejects([&] { worker.invoke([] {}); });
          rejects([&] { worker.launch([] {}); });
          ++tasks;
        });
        check(destroyed == creator && worker.reserved());
        try {
          worker.invoke([&] {
            check(std::this_thread::get_id() == creator);
            throw std::bad_alloc();
          });
          throw std::logic_error("lost preparation exception");
        } catch (const std::bad_alloc &) { ++failures; }
        // A failed preparation leaves the same reserved worker retryable.
        worker.invoke([&] { check(std::this_thread::get_id() == creator); });
      }
      if (trial % 2) {
        ++cancellations; // Destructor joins an idle worker without launching.
      } else {
        worker.launch([&] { check(std::this_thread::get_id() == creator); ++launches; });
        worker.join();
        rejects([&] { worker.invoke([] {}); });
        rejects([&] { worker.launch([] {}); });
        rejects([&] { worker.reserve(); });
      }
    }
    // Ordinary startup remains available without reserving a creator.
    { emul_driver_thread_t worker;
      worker.launch([&] { check(std::this_thread::get_id() != controller); ++launches; });
      worker.join(); }
    check(tasks==512 && failures==512 && launches==17 && cancellations==16 && rejected==1296);
    std::cout << "DRIVER_CREATOR_PASS tasks=" << tasks << " exceptions=" << failures
              << " launches=" << launches << " cancellations=" << cancellations
              << " rejections=" << rejected << "\n";
    test_residents();
    test_prepared_launch();
    test_publication_seal();
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "DRIVER_CREATOR_ERROR " << e.what() << '\n'; return 1;
  }
}
#ifdef DRIVER_CREATOR_DPI
extern "C" int driver_creator_reservation() { return test_creator(); }
#else
int main() { return test_creator(); }
#endif
