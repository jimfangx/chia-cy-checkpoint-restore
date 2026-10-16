#include "checkpoint_entry_fixture.h"
#include "core/checkpoint_entry.h"
#include "entry.h"
#ifdef VCS
#include <vpi_user.h>
#endif

std::string fixture_mode;
#ifdef FIXTURE_UNOWNED_FAME_OBSERVER
// Native dispatch checks have no VPI runtime. VCS checks link the actual
// fame_capture.cc provider instead of this native-only stand-in.
extern "C" const char *firesim_fame_capture_level1_exclusion() {
  return "native dispatch observer fixture";
}
#endif
std::unique_ptr<simif_t> create_simif(const TargetConfig &, int, char **) {
  puts("FIXTURE_PLATFORM");
  return std::make_unique<simif_t>();
}
std::unique_ptr<simulation_t>
create_simulation(simif_t &, widget_registry_t &, const std::vector<std::string> &) {
  puts("FIXTURE_SIMULATION");
  return std::make_unique<simulation_t>();
}

#ifndef FIXTURE_MISSING_FACTORY
class fixture_entry_t final : public checkpoint_entry_t {
public:
  void authorize_request(const checkpoint_request_t &request) const override {
    puts("FIXTURE_AUTHORIZE");
    if (fixture_mode == "deny") checkpoint_entry_t::authorize_request(request);
    if (fixture_mode == "authorize-error") throw std::runtime_error("fixture authorize failure");
  }
  action_t prepare(simif_t &, simulation_t &, const checkpoint_request_t &request) override {
    printf("FIXTURE_PREPARE kind=%d path=%s\n", int(request.kind), request.path.c_str());
    if (fixture_mode == "prepare-error") throw std::runtime_error("fixture prepare failure");
    if (fixture_mode == "wrong-capture") return action_t::restore_reserved;
    if (fixture_mode == "wrong-restore") return action_t::run;
    return request.kind == checkpoint_request_t::kind_t::restore ?
        action_t::restore_reserved : action_t::run;
  }
};
std::unique_ptr<checkpoint_entry_t> create_checkpoint_entry(const std::vector<std::string> &) {
  puts("FIXTURE_FACTORY");
  if (fixture_mode == "factory-error") throw std::runtime_error("fixture factory failure");
  if (fixture_mode == "null") return nullptr;
  return std::make_unique<fixture_entry_t>();
}
#endif

static int invoke_entry(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    std::string arg(argv[i]);
    if (arg.rfind("+fixture-mode=", 0) == 0) fixture_mode = arg.substr(14);
  }
  const auto result = entry(argc, argv);
  printf("FIXTURE_RETURN status=%d\n", result);
  return result;
}
#ifdef VCS
extern "C" int checkpoint_entry_fixture() {
  s_vpi_vlog_info info{};
  if (!vpi_get_vlog_info(&info)) throw std::runtime_error("missing VCS arguments");
  return invoke_entry(info.argc, info.argv);
}
#else
int main(int argc, char **argv) { return invoke_entry(argc, argv); }
#endif
