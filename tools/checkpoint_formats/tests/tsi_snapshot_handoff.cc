// Real TSI owner bytes cross the creator/VCS thread boundary, never references.
#define TSI_CONTEXT_GROUP_DPI
#include "tsi_context_group_fesvr.cc"
#include "core/driver_boundary_diagnostic.h"
#include <condition_variable>
#include <mutex>

__attribute__((constructor)) static void snapshot_blocked_inheritance() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
  if (pthread_sigmask(SIG_BLOCK, &set, nullptr)) std::abort();
}

static int snapshot_run(const char *elf, const char *input, const char *metadata,
                        const char *source, const char *destination) {
  using diagnostic_t = driver_boundary_diagnostic_t;
  try {
    const fs::path out(destination); fs::create_directories(out);
    diagnostic_t::snapshot_t snapshot;
    diagnostic_t::owners_t borrowed;
    std::vector<std::string> schemas;
    images_t original;
    size_t allocation_failures = 0;
    std::mutex mutex; std::condition_variable condition;
    bool published = false, checked = false;
    std::exception_ptr failure;
    // Exactly the production direction: worker constructs and observes TSI,
    // main (VCS/DPI) reads the frozen records while the worker is parked.
    std::thread producer([&] {
      try {
        std::vector<std::string> args{"snapshot", "+permissive", "+no_hart0_msip", "+idle-counts=3",
          "+checkpoint-syscall-exit", "+checkpoint-terminal-input="+std::string(input), "+permissive-off", elf};
        std::vector<char *> argv; for (auto &s : args) argv.push_back(s.data());
        firesim_tsi_t tsi(argv.size(), argv.data(), true); context_group_t group(tsi);
        tsi.prepare_startup_metadata(bytes(metadata)); group.load(load_context(source));
        const auto before = group.inspect();
        borrowed = {{"poll", const_cast<checkpoint_owner_t *>(&tsi.htif_poll_owner())},
          {"program", const_cast<checkpoint_owner_t *>(&tsi.program_loader_owner())},
          {"init", const_cast<checkpoint_owner_t *>(&tsi.init_accesses_owner())},
          {"host", const_cast<checkpoint_owner_t *>(&tsi.host_control_owner())},
          {"read", const_cast<checkpoint_owner_t *>(&tsi.serial_read_owner())},
          {"serial", const_cast<checkpoint_owner_t *>(&tsi.serial_queue_owner())},
          {"loadmem-read", const_cast<checkpoint_owner_t *>(&tsi.loadmem_read_owner())},
          {"loadmem-queues", const_cast<checkpoint_owner_t *>(&tsi.loadmem_queue_owner())},
          {"bcd", const_cast<checkpoint_owner_t *>(&tsi.bcd_owner())},
          {"terminal", const_cast<checkpoint_owner_t *>(&tsi.terminal_owner())},
          {"identity", const_cast<checkpoint_owner_t *>(&tsi.bcd_identity_owner())},
          {"write", const_cast<checkpoint_owner_t *>(&tsi.memif_write_owner())},
          {"memread", const_cast<checkpoint_owner_t *>(&tsi.memif_read_owner())},
          {"syscall", const_cast<checkpoint_owner_t *>(&tsi.syscall_exit_owner())},
          {"outer", const_cast<checkpoint_owner_t *>(&tsi.host_execution_owner())},
          {"wrapper", const_cast<checkpoint_owner_t *>(&tsi.host_wrapper_owner())}};
        for (const auto &[name, owner] : borrowed) {
          schemas.push_back(owner->checkpoint_schema()); original.emplace_back(name, owner->save_checkpoint());
        }
        save(out/"original", original);
        for (long allocation = 0;; ++allocation) {
          bool failed = false;
          tsi_terminal_fail_allocation_after(allocation);
          try { snapshot = diagnostic_t::freeze(borrowed); }
          catch (const std::bad_alloc &) { failed = true; }
          catch (...) { tsi_terminal_fail_allocation_after(-1); throw; }
          tsi_terminal_fail_allocation_after(-1);
          if (!failed) break;
          ++allocation_failures;
          require(snapshot.owners().empty() && group.inspect() == before,
                  "failed snapshot allocation partially published/changed owners");
        }
        {
          std::unique_lock<std::mutex> lock(mutex);
          published = true; condition.notify_one();
          condition.wait(lock, [&] { return checked; });
        }
        require(group.inspect() == before, "snapshot foreign observation changed creator state");
        require(!group.native_context_initialized(), "snapshot entered restored context");
        for (size_t i = 0; i < borrowed.size(); ++i)
          require(borrowed[i].second->save_checkpoint() == original[i].second, "creator retry changed");
      } catch (...) {
        std::lock_guard<std::mutex> lock(mutex); failure = std::current_exception();
        published = true; condition.notify_one();
      }
    });
    {
      std::unique_lock<std::mutex> lock(mutex); condition.wait(lock, [&] { return published; });
    }
    size_t raw_rejections = 0, invalid_rejections = 0, load_rejections = 0;
    auto observe = [&](const std::string &name) {
      images_t readback; const auto owners = snapshot.owners();
      require(owners.size() == original.size() && owners.size() == 16, "snapshot membership");
      for (size_t i = 0; i < owners.size(); ++i) {
        const auto &[id, owner] = owners[i]; const auto payload = owner->save_checkpoint();
        require(id == original[i].first && owner->checkpoint_schema() == schemas[i] &&
                payload == original[i].second, "snapshot readback differs");
        owner->validate_checkpoint(payload);
        bool bad = false; try { owner->validate_checkpoint({}); } catch (const std::runtime_error &) { bad = true; }
        require(bad, "snapshot invalid bytes accepted"); ++invalid_rejections;
        bad = false; try { owner->load_checkpoint(payload); } catch (const std::runtime_error &) { bad = true; }
        require(bad, "snapshot accepted mutable restore"); ++load_rejections;
        readback.emplace_back(id, payload);
      }
      save(out/name, readback);
      auto d = diagnostic_t({"+fs-driver-cut=1", "+fs-driver-diagnostic="+(out/(name+".diag")).string()});
      d.observe(owners); d.finish();
    };
    try {
      if (failure) std::rethrow_exception(failure);
      // Witness: direct invocation on the same live borrowed production views
      // rejects. Only the frozen records may cross the boundary.
      for (const auto &[id, owner] : borrowed) {
        bool bad = false;
        try { owner->save_checkpoint(); } catch (const std::runtime_error &e) {
          bad = std::string(e.what()) == "TSI access requires its live original thread";
        }
        require(bad, "raw foreign view unexpectedly readable"); ++raw_rejections;
      }
      observe("parked");
    } catch (...) {
      { std::lock_guard<std::mutex> lock(mutex); checked = true; condition.notify_one(); }
      producer.join(); throw;
    }
    { std::lock_guard<std::mutex> lock(mutex); checked = true; condition.notify_one(); }
    producer.join(); if (failure) std::rethrow_exception(failure);
    borrowed.clear(); // The TSI and all original owner slots are now destroyed.
    auto relocated = std::move(snapshot); snapshot = std::move(relocated);
    observe("destroyed");
    std::cout << "SNAPSHOT_HANDOFF owners=16 readbacks=32 raw_rejections=" << raw_rejections
              << " invalid_rejections=" << invalid_rejections << " load_rejections=" << load_rejections
              << " allocation_failures=" << allocation_failures
              << " creator_destroyed=1 context_entries=0 target_edges=0\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_SNAPSHOT_DPI
extern "C" int tsi_snapshot(const char *e, const char *i, const char *m, const char *s, const char *d) {
  return snapshot_run(e, i, m, s, d);
}
#else
int main(int argc, char **argv) { return argc == 6 ? snapshot_run(argv[1], argv[2], argv[3], argv[4], argv[5]) : 2; }
#endif
