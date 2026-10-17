// Mailbox lifecycle and creator identity, including teardown and exceptions.
#include "emul/driver_thread.h"
#include <atomic>
#include <iostream>
#include <memory>

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
