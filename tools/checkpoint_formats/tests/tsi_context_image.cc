// Bound, immutable context images; all TSI work executes on its fresh creator.
#define TSI_CONTEXT_GROUP_DPI
#include "tsi_context_group_fesvr.cc"
#include "fesvr/tsi_context_image.h"

__attribute__((constructor)) static void image_blocked_inheritance() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
  if (pthread_sigmask(SIG_BLOCK, &set, nullptr)) std::abort();
}

static int image_run(const char *mode, const char *elf, const char *input,
                     const char *metadata, const char *source, const char *plan,
                     const char *destination, const char *image_path, const char *build_path) {
  try {
    const std::string action(mode);
    const auto transport = action == "capture" ? std::vector<uint8_t>{} : bytes(image_path);
    const auto build_bytes = bytes(build_path);
    require(build_bytes.size() == 32, "need exact build SHA-256");
    firesim_tsi_context_image_t::build_t build;
    std::copy(build_bytes.begin(), build_bytes.end(), build.begin());
    std::exception_ptr failure;
    // The VCS/DPI caller transfers only immutable image/build bytes. Neither
    // source nor destination TSI objects live on the VCS calling thread.
    std::thread creator([&] {
      try {
        const fs::path out(destination); fs::create_directories(out);
        std::vector<std::string> args{"syscall-polling", "+permissive", "+no_hart0_msip", "+idle-counts=3",
          "+checkpoint-syscall-exit", "+checkpoint-terminal-input="+std::string(input)};
        if (fs::path(input).filename().string().find("flush") != std::string::npos)
          args.push_back("+cflush_addr=0x20004000");
        args.insert(args.end(), {"+permissive-off", elf});
        std::vector<char *> argv; for (auto &arg : args) argv.push_back(arg.data());
        firesim_tsi_t tsi(argv.size(), argv.data(), true);
        context_group_t group(tsi); firesim_tsi_context_image_t bound(tsi, build);
        const auto cut = std::stoul(fs::path(source).filename().string().substr(4));
        const auto expected = load_context(source);
        std::ifstream steps(plan); require(bool(steps), "missing image operation plan");
        size_t operations = 0, op = 0;
        auto step = [&](const std::string &line, bool live) {
          std::istringstream in(line); std::string kind; uint32_t n; in >> kind;
          if (kind == "TICK") { if (live) tsi.tick(); else group.resume(); }
          else if (kind == "SEND") { in >> n; tsi.send_word(n); }
          else if (kind == "PACKET") {
            size_t word = 0;
            while (in >> n) {
              require(tsi.data_available(), "missing image output packet");
              const auto actual = tsi.in_bits();
              if (actual != n) {
                require(action == "corrupt" && tsi.in_bits() == actual, "unexpected image divergence");
                std::cout << "FIRST_DIVERGENCE operation=" << op << " word=" << word
                          << " expected=" << n << " actual=" << actual
                          << " acknowledged=0 fresh_context=1\n";
                return false;
              }
              require(tsi.recv_word() == n, "image output changed"); ++word;
            }
          } else throw std::runtime_error("unknown image operation");
          return true;
        };
        if (action == "capture") {
          syscall_startup(tsi);
          std::string line;
          while (op < cut && std::getline(steps, line)) { ++op; require(step(line, true), "source divergence"); }
          require(op == cut && group.inspect() == expected, "live image source differs from retained oracle");
          save(out/"source", group.inspect()); save(image_path, bound.capture());
          require(group.inspect_startup_metadata() == bytes(metadata), "source image metadata differs");
          std::cout << "CONTEXT_IMAGE_CAPTURE owners=16 live=1 cut=" << cut << " target_edges=0\n";
          return;
        }
        tsi.prepare_startup_metadata(bytes(metadata));
        const auto before = context_unprepared(tsi);
        auto unchanged = [&] {
          require(context_unprepared(tsi) == before && !group.native_context_initialized(),
                  "bound image partially published or entered context");
          bool absent = false; try { tsi.htif_poll_owner(); } catch (const std::runtime_error &) { absent = true; }
          require(absent, "bound image published child");
        };
        if (action == "invalid") {
          bool bad = false;
          try { auto candidate = bound.prepare(transport); candidate.commit(); }
          catch (const std::runtime_error &) { bad = true; }
          require(bad, "invalid bound image admitted"); unchanged();
          std::cout << "CONTEXT_IMAGE_REJECT unpublished=1 context_entries=0 target_edges=0\n";
          return;
        }
        if (action == "atomic") {
          size_t truncated = 0;
          for (size_t size = 0; size < transport.size(); ++size) {
            const std::vector<uint8_t> bad(transport.begin(), transport.begin()+size);
            bool rejected = false;
            try { auto next = bound.prepare(bad); next.commit(); }
            catch (const std::runtime_error &) { rejected = true; }
            require(rejected, "truncated bound image admitted"); unchanged(); ++truncated;
          }
          long allocations = 0;
          for (;; ++allocations) {
            bool failed = false;
            tsi_terminal_fail_allocation_after(allocations);
            try { auto next = bound.prepare(transport); next.commit(); }
            catch (const std::bad_alloc &) { failed = true; }
            catch (...) { tsi_terminal_fail_allocation_after(-1); throw; }
            tsi_terminal_fail_allocation_after(-1);
            if (!failed) break;
            unchanged();
          }
          require(group.inspect() == expected && !group.native_context_initialized(), "atomic image readback differs");
          save(out/"preedge", group.inspect());
          std::cout << "CONTEXT_IMAGE_ATOMIC truncations=" << truncated << " allocation_failures=" << allocations
                    << " unchanged_on_failure=1 owners=16 context_entries=0 target_edges=0\n";
          return;
        }
        auto owned = transport;
        auto next = bound.prepare(owned);
        auto competitor = bound.prepare(owned);
        owned.clear(); // Candidates must own every input, including metadata.
        struct parked_thread_t {
          std::promise<void> ready, release;
          std::future<void> released = release.get_future();
          std::thread worker;
          ~parked_thread_t() { if (worker.joinable()) { release.set_value(); worker.join(); } }
        } parked_foreign;
        if (action == "foreign") {
          size_t rejections = 0;
          parked_foreign.worker = std::thread([&] {
            for (unsigned call = 0; call < 4; ++call) {
              bool bad = false;
              try {
                if (call == 0) bound.capture();
                else if (call == 1) { auto candidate = bound.prepare(transport); }
                else if (call == 2) { auto candidate = bound.prepare({}); }
                else next.commit();
              } catch (const std::runtime_error &e) {
                bad = std::string(e.what()) == "TSI access requires its live original thread";
              }
              if (bad) ++rejections;
            }
            parked_foreign.ready.set_value(); parked_foreign.released.wait();
          });
          parked_foreign.ready.get_future().wait(); require(rejections == 4, "foreign image operation admitted"); unchanged();
          std::cout << "CONTEXT_IMAGE_FOREIGN rejected=4 creator_retry=1\n";
        }
        if (action == "guard-mask") {
          sigset_t set; sigemptyset(&set);
          for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
          require(!pthread_sigmask(SIG_UNBLOCK, &set, nullptr), "unblock image guard");
          bool rejected = false; try { next.commit(); } catch (const std::runtime_error &) { rejected = true; }
          require(!pthread_sigmask(SIG_BLOCK, &set, nullptr), "reblock image guard");
          require(rejected, "late image mask guard admitted"); unchanged();
          std::cout << "CONTEXT_IMAGE_LATE_GUARD unpublished=1 creator_retry=1\n";
        }
        next.commit();
        require(group.inspect() == expected && !group.native_context_initialized(), "bound image preedge readback differs");
        for (unsigned call = 0; call < 2; ++call) {
          bool bad = false;
          try { if (call) competitor.commit(); else next.commit(); }
          catch (const std::runtime_error &) { bad = true; }
          require(bad && group.inspect() == expected, "bound image republished");
        }
        save(out/"preedge", group.inspect());
        require(bound.capture() == transport, "canonical image recapture differs");
        std::cout << "CONTEXT_IMAGE_READBACK owners=16 services=0 context_entries=0 target_edges=0 republish_rejections=2\n";
        if (action == "corrupt")
          const_cast<checkpoint_owner_t &>(tsi.syscall_exit_owner()).load_checkpoint(bytes(std::string(source)+".fault"));
        std::ofstream continued(out/"continuation.bin", std::ios::binary);
        std::string line;
        while (std::getline(steps, line)) {
          if (++op <= cut) continue;
          if (!step(line, false)) return;
          for (const auto &[name, payload] : group.inspect())
            continued.write(reinterpret_cast<const char *>(payload.data()), payload.size());
          ++operations;
        }
        require(action != "corrupt" && tsi.done() && tsi.host_wrapper_owner().save_checkpoint().at(40) == 2,
                "bound image did not reach tail");
        for (unsigned i = 0; i < 3; ++i) {
          const auto old = group.inspect(); group.resume(); require(group.inspect() == old, "bound image tail serviced");
        }
        std::cout << "CONTEXT_IMAGE_CONTINUED operations=" << operations << " owners=16 startup_replays=0 tail_ticks=3 return="
                  << tsi.exit_code() << " target_edges=0\n";
      } catch (...) { tsi_terminal_fail_allocation_after(-1); failure = std::current_exception(); }
    });
    creator.join(); if (failure) std::rethrow_exception(failure);
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_CONTEXT_IMAGE_DPI
extern "C" int tsi_context_image(const char *m, const char *e, const char *i, const char *b,
    const char *s, const char *p, const char *d, const char *v, const char *h) { return image_run(m,e,i,b,s,p,d,v,h); }
#else
int main(int argc, char **argv) {
  return argc == 10 ? image_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7],argv[8],argv[9]) : 2;
}
#endif
