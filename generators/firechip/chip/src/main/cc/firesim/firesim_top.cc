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
      if (driver.started)
        throw std::runtime_error("FireSim restore requires a fresh driver");
      driver.started = true;
    }
  private:
    firesim_top_t &driver;
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
