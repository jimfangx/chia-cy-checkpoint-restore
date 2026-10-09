// Software-owner diagnostics: failure must leave no published partial file.
#include "core/driver_boundary_diagnostic.h"
#include "core/stepped_run_loop.h"
#include "core/systematic_scheduler.h"
#include "emul/host_timing.h"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>

namespace {
void check(bool ok) {
  if (!ok)
    throw std::runtime_error("test assertion");
}
unsigned rejected = 0;
void rejects(const std::function<void()> &call) {
  try {
    call();
  } catch (const std::runtime_error &) {
    ++rejected;
    return;
  }
  throw std::runtime_error("expected rejection");
}
struct owner_t : checkpoint_owner_t {
  mutable unsigned saves = 0;
  bool bad = false, moving = false, changing = false;
  std::function<void()> hook;
  std::string checkpoint_schema() const override {
    return changing && saves ? "other" : "test.owner.v1";
  }
  std::vector<uint8_t> save_checkpoint() const override {
    ++saves;
    if (hook)
      hook();
    return {uint8_t(moving ? saves : 42)};
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override {
    if (bad || b.size() != 1)
      throw std::runtime_error("bad payload");
  }
};
} // namespace
int main(int argc, char **argv) {
  try {
    check(argc == 2);
    const std::filesystem::path out(argv[1]);
    // Remove only this test's generated files so repeated verification still
    // exercises destination refusal within the run, rather than old fixtures.
    for (const auto *name :
         {"good.diag", "components.diag", "existing.diag.tmp"})
      std::filesystem::remove(out / name);
    for (const auto &args : std::vector<std::vector<std::string>>{
             {"+fs-driver-cut=1"},
             {"+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=0", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=-1", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=+1", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=1x", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=18446744073709551616", "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=1", "+fs-driver-cut=2",
              "+fs-driver-diagnostic=x"},
             {"+fs-driver-cut=1", "+fs-driver-diagnostic=x",
              "+fs-driver-diagnostic=y"},
             {"+fs-driver-cut=1", "+fs-driver-diagnostic="}})
      rejects([&] { driver_boundary_diagnostic_t diagnostic(args); });
    auto make = [&](const std::string &name, uint64_t cut = 1) {
      return driver_boundary_diagnostic_t(
          {"+fs-driver-cut=" + std::to_string(cut),
           "+fs-driver-diagnostic=" + (out / name).string()});
    };
    owner_t owner, second;
    checkpoint_owner_t unsupported;
    driver_boundary_diagnostic_t unused({});
    unused.observe({});
    unused.finish();
    auto good = make("good.diag", 2);
    check(!good.due());
    good.observe({});
    check(good.due());
    good.observe({{"test/a", &owner},
                  {"test/unsupported", &unsupported},
                  {"test/missing", nullptr}});
    good.finish();
    check(owner.saves == 2 && std::filesystem::exists(out / "good.diag"));
    good.observe({});
    good.finish();
    check(owner.saves == 2);
    auto late = make("late.diag", 2);
    late.observe({});
    rejects([&] { late.finish(); });
    for (unsigned scenario = 0; scenario < 10; ++scenario) {
      owner_t a, b;
      auto path = "negative-" + std::to_string(scenario) + ".diag";
      auto d = make(path);
      driver_boundary_diagnostic_t::owners_t owners{{"a", &a}, {"b", &b}};
      if (scenario == 0)
        owners.clear();
      if (scenario == 1)
        owners[1].first = "a";
      if (scenario == 2)
        owners[1].second = &a;
      if (scenario == 3)
        owners[1].first = "";
      if (scenario == 4)
        b.bad = true;
      if (scenario == 5)
        b.moving = true;
      if (scenario == 6)
        b.changing = true;
      if (scenario == 7)
        b.hook = [&] { d.observe(owners); };
      if (scenario == 8)
        b.hook = [&] { a.moving = true; };
      if (scenario == 9)
        b.hook = [&] { d.finish(); };
      rejects([&] { d.observe(owners); });
      rejects([&] { d.observe(owners); });
      rejects([&] { d.finish(); });
      check(!std::filesystem::exists(out / path) &&
            !std::filesystem::exists(out / (path + ".tmp")));
    }
    // The serializer must not turn a component's suspended call into a cut.
    host_timing_t timing;
    auto suspended = make("suspended.diag");
    rejects([&] {
      timing.run_delay([&] { suspended.observe({{"timing", &timing}}); });
    });
    check(!std::filesystem::exists(out / "suspended.diag"));
    // Real production component payloads stay byte-identical across saves.
    systematic_scheduler_t scheduler({"+max-cycles=17"});
    stepped_run_loop_t loop(3);
    host_timing_t stable_timing(7, 18446744073709551615ULL);
    auto components = make("components.diag");
    components.observe({{"scheduler", &scheduler},
                        {"loop", &loop},
                        {"timing", &stable_timing}});
    components.finish();
    auto blocked = make("no-directory/failed.diag");
    rejects([&] { blocked.observe({{"a", &owner}}); });
    rejects([&] { blocked.finish(); });
    auto existing = make("good.diag");
    const auto size = std::filesystem::file_size(out / "good.diag");
    rejects([&] { existing.observe({{"a", &owner}}); });
    check(std::filesystem::file_size(out / "good.diag") == size);
    std::ofstream(out / "existing.diag.tmp") << "retain";
    auto temporary = make("existing.diag");
    rejects([&] { temporary.observe({{"a", &owner}}); });
    check(std::filesystem::file_size(out / "existing.diag.tmp") == 6);
    std::cout << "PASS: " << rejected
              << " diagnostic/configuration/suspended/reentrant rejections\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
