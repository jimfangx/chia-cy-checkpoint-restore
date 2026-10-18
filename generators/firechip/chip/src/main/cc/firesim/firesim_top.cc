// See LICENSE for license details

#include "bridges/clock.h"
#include "bridges/fased_memory_timing_model.h"
#include "bridges/heartbeat.h"
#include "bridges/peek_poke.h"
#include "core/bridge_driver.h"
#include "core/simif.h"
#include "core/simulation.h"
#include "core/systematic_scheduler.h"
#include "core/bridge_run_loop.h"
#include "core/checkpoint_publication.h"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>

class firesim_top_t : public systematic_scheduler_t, public simulation_t,
                      private bridge_run_loop_t::services_t {
public:
  firesim_top_t(simif_t &simif,
                widget_registry_t &registry,
                const std::vector<std::string> &args);

  int simulation_run() override;
  bool simulation_supports_steps() const override { return true; }
  bool simulation_run_step() override {
    widget_checkpoint_state_t::call_t call(checkpoint_state);
    if (finalized)
      throw std::runtime_error("FireSim operation after finalization");
    started = true;
    run_loop.advance(*this);
    return run_loop.finished();
  }
  int simulation_run_finalize() override;
  bool simulation_timed_out() override { return !run_loop.terminated(); }
  std::vector<std::pair<std::string, checkpoint_owner_t *>>
  checkpoint_driver_owners() override {
    auto owners = simulation_t::checkpoint_driver_owners();
    owners.front().second = &driver_checkpoint;
    auto scheduler_owners = systematic_scheduler_t::checkpoint_owners();
    owners.insert(owners.end(), scheduler_owners.begin(), scheduler_owners.end());
    owners.emplace_back("runtime/simulation/firesim-run-loop", &run_loop);
    return owners;
  }

private:
  // A separate adapter avoids overriding the scheduler's checkpoint virtuals
  // through this multiply inherited driver.
  class concrete_checkpoint_t final : public checkpoint_owner_t {
  public:
    explicit concrete_checkpoint_t(firesim_top_t &driver) : driver(driver) {}
    std::string checkpoint_schema() const override {
      return "firesim.simulation.bridge-driver.v1";
    }
    std::vector<uint8_t> save_checkpoint() const override {
      driver.checkpoint_state.require_idle();
      if (!driver.started || driver.finalized)
        throw std::runtime_error("FireSim checkpoint requires an unfinished running driver");
      return driver.checkpoint_state.save(driver.checkpoint_configuration(), 1);
    }
    void validate_checkpoint(const std::vector<uint8_t> &payload) const override {
      driver.checkpoint_state.require_idle();
      if (driver.finalized)
        throw std::runtime_error("FireSim restore after finalization");
      if (driver.checkpoint_state.validate(payload, driver.checkpoint_configuration(), 1) != 1)
        throw std::runtime_error("FireSim checkpoint is not a running driver");
    }
    void load_checkpoint(const std::vector<uint8_t> &payload) override {
      validate_checkpoint(payload);
      require_fresh();
      publication.changed();
      driver.started = true;
    }
    std::unique_ptr<prepared_checkpoint_t>
    prepare_checkpoint_publication(const std::vector<uint8_t> &payload) override {
      return std::make_unique<restore_t>(*this, payload);
    }
  private:
    void require_fresh() const {
      driver.checkpoint_state.require_idle();
      if (driver.started || driver.finalized)
        throw std::runtime_error("FireSim restore requires a fresh driver");
    }
    std::vector<uint8_t> destination_stamp() const {
      require_fresh();
      // Source capture requires a running driver. Stamp the fresh destination
      // separately, including the complete registry/configuration binding.
      return driver.checkpoint_state.save(driver.checkpoint_configuration(), 0);
    }
    class restore_t final : public prepared_checkpoint_t {
      concrete_checkpoint_t &owner;
      checkpoint_publication_t::guard_t guard;
      const std::vector<uint8_t> expected;
    public:
      restore_t(concrete_checkpoint_t &owner, const std::vector<uint8_t> &payload)
          : owner(owner), guard(owner.publication), expected(owner.destination_stamp()) {
        owner.validate_checkpoint(payload);
      }
      void seal() override {
        guard.require_unsealed(); // Check lifetime/thread/generation before owner access.
        if (owner.destination_stamp() != expected)
          throw std::runtime_error("FireSim checkpoint destination changed");
        guard.seal();
      }
      void publish() noexcept override {
        guard.publish();
        owner.driver.started = true;
      }
    };
    firesim_top_t &driver;
    checkpoint_publication_t publication;
  } driver_checkpoint{*this};
  widget_checkpoint_config_t checkpoint_configuration() const;
  simif_t &simif;
  /// Reference to the peek-poke bridge.
  peek_poke_t &peek_poke;
  std::optional<uint64_t> profile_interval;
  std::vector<bridge_driver_t *> bridges;
  bridge_run_loop_t run_loop;
  widget_checkpoint_state_t checkpoint_state;
  bool started = false;
  bool finalized = false;
  void record_tsi_host_audit(uint64_t credit, const std::string &directory);
  bool horizon_reached() override { return finished_scheduled_tasks(); }
  void run_tasks() override { run_scheduled_tasks(); }
  void issue_step() override { peek_poke.step(get_largest_stepsize(), false); }
  bool step_done() override { return peek_poke.is_done(); }
  void tick_bridge(uint64_t index) override { bridges.at(index)->tick(); }
  bool bridge_terminated(uint64_t index) override { return bridges.at(index)->terminate(); }
  int bridge_exit_code(uint64_t index) override { return bridges.at(index)->exit_code(); }
};

firesim_top_t::firesim_top_t(simif_t &simif,
                             widget_registry_t &registry,
                             const std::vector<std::string> &args)
    : systematic_scheduler_t(args), simulation_t(registry, args), simif(simif),
      peek_poke(registry.get_widget<peek_poke_t>()),
      run_loop(registry.get_all_bridges().size() + 1) {

  // Cycles to advance before profiling instrumentation registers in models.
  for (auto &arg : args) {
    if (arg.find("+profile-interval=") == 0) {
      profile_interval = atoi(arg.c_str() + 18);

      if (*profile_interval == 0) {
        fprintf(stderr, "Must provide a profile interval > 0\n");
        exit(1);
      }
    }
  }

  registry.add_widget(
      new heartbeat_t(simif, registry.get_widget<clockmodule_t>(), args));
  bridges = registry.get_all_bridges();

  // Add functions you'd like to periodically invoke on a paused simulator here.
  if (profile_interval) {
    register_task(
        0, [this, interval = *profile_interval] {
          for (auto &mod : this->registry.get_bridges<FASEDMemoryTimingModel>()) {
            mod->profile();
          }
          return interval;
        });
  }

  // Optional read-only evidence for CPU owner development. Anonymous tasks
  // intentionally remain unsupported by aggregate checkpoint admission.
  std::string audit_directory, audit_cycles;
  bool have_directory = false, have_cycles = false;
  for (const auto &arg : args) {
    if (arg.rfind("+tsi-host-audit=", 0) == 0) {
      if (have_directory) throw std::runtime_error("duplicate TSI host audit directory");
      have_directory = true; audit_directory = arg.substr(16);
    }
    if (arg.rfind("+tsi-host-audit-cycles=", 0) == 0) {
      if (have_cycles) throw std::runtime_error("duplicate TSI host audit cycles");
      have_cycles = true; audit_cycles = arg.substr(23);
    }
  }
  if (have_directory != have_cycles || (have_directory && audit_directory.empty()))
    throw std::runtime_error("TSI host audit requires directory and cycles");
  if (have_directory) {
    if (std::filesystem::exists(audit_directory))
      throw std::runtime_error("TSI host audit directory already exists");
    std::vector<uint64_t> cycles;
    std::istringstream input(audit_cycles);
    std::string value;
    while (std::getline(input, value, ',')) {
      uint64_t cycle = 0;
      auto parsed = std::from_chars(value.data(), value.data() + value.size(), cycle);
      if (parsed.ec != std::errc() || parsed.ptr != value.data() + value.size() ||
          cycle == std::numeric_limits<uint64_t>::max() ||
          (!cycles.empty() && cycle <= cycles.back()))
        throw std::runtime_error("invalid TSI host audit cycle list");
      cycles.push_back(cycle);
    }
    if (cycles.empty() || audit_cycles.back() == ',')
      throw std::runtime_error("empty TSI host audit cycle");
    if (std::none_of(bridges.begin(), bridges.end(), [](const auto *bridge) {
          return bridge->host_component_scope() == "tsi-polling";
        }))
      throw std::runtime_error("TSI host audit requires a TSI bridge");
    for (auto cycle : cycles)
      register_task(cycle, [this, cycle, audit_directory] {
        record_tsi_host_audit(cycle, audit_directory);
        return std::numeric_limits<uint64_t>::max() - cycle;
      });
  }
}

void firesim_top_t::record_tsi_host_audit(uint64_t credit, const std::string &directory) {
  // Credit and clock-token count are distinct labels. Neither asserts that
  // a semantic DUT edge or memory transaction completed at this boundary.
  std::ostringstream out;
  out << "{\"format\":\"firesim-tsi-host-audit-v1\",\"master_credit\":" << credit
      << ",\"clock_tokens_enqueued\":" << registry.get_widget<clockmodule_t>().tcycle()
      << ",\"level1_verified\":false,\"level2_verified\":false,\"bridges\":[";
  bool first = true;
  for (auto *bridge : bridges) {
    if (bridge->host_component_scope() != "tsi-polling") continue;
    if (!first) out << ',';
    first = false;
    std::vector<std::pair<std::string, std::vector<uint8_t>>> images;
    std::string rejection;
    try { images = bridge->inspect_host_components(); }
    catch (const std::runtime_error &error) { rejection = error.what(); }
    out << "{\"rejection\":" << std::quoted(rejection) << ",\"components\":{";
    bool first_component = true;
    for (const auto &[name, image] : images) {
      if (!first_component) out << ',';
      first_component = false;
      out << std::quoted(name) << ":\"";
      for (auto byte : image)
        out << std::hex << std::setfill('0') << std::setw(2) << unsigned(byte);
      out << std::dec << '"';
    }
    out << "}}";
  }
  out << "]}\n";
  std::filesystem::create_directories(directory);
  auto destination = std::filesystem::path(directory) / (std::to_string(credit) + ".json");
  auto temporary = destination.string() + ".tmp";
  if (std::filesystem::exists(destination) || std::filesystem::exists(temporary))
    throw std::runtime_error("TSI host audit destination already exists");
  std::ofstream file(temporary, std::ios::binary);
  file << out.str(); file.close();
  if (!file) throw std::runtime_error("TSI host audit write failed");
  std::filesystem::rename(temporary, destination);
}

int firesim_top_t::simulation_run() {
  while (!simulation_run_step())
    ;
  return simulation_run_finalize();
}

int firesim_top_t::simulation_run_finalize() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (finalized || !run_loop.finished())
    throw std::runtime_error("FireSim repeated or premature finalization");
  finalized = true;
  return run_loop.exit_code();
}

widget_checkpoint_config_t firesim_top_t::checkpoint_configuration() const {
  widget_checkpoint_config_t config(
      13, {profile_interval.has_value(), profile_interval.value_or(0)});
  const auto owners = registry.checkpoint_owners();
  const auto identity = [&](checkpoint_owner_t *owner) {
    const auto it = std::find_if(owners.begin(), owners.end(),
                                [&](const auto &entry) { return entry.second == owner; });
    if (it == owners.end())
      throw std::runtime_error("FireSim owner missing from registry");
    config.text(it->first);
    config.text(owner->checkpoint_schema());
  };
  identity(&peek_poke);
  if (bridges != registry.get_all_bridges())
    throw std::runtime_error("FireSim registry changed after construction");
  config.word(bridges.size());
  for (auto *bridge : bridges)
    identity(bridge);
  return config;
}

std::unique_ptr<simulation_t>
create_simulation(simif_t &simif,
                  widget_registry_t &registry,
                  const std::vector<std::string> &args) {
  return std::make_unique<firesim_top_t>(simif, registry, args);
}
