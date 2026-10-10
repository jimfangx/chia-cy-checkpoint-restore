// Explicitly linked public restore capability for the audited FCFS/FASED VCS
// profile. Public capture uses completed-operation scheduling at a settled cut.
#include "core/checkpoint_entry.h"
#include "core/simulation.h"
#include "emul/simif_emul.h"
#include "aggregate_restore.h"
#include "durable_restore.h"
#include "durable_capture.h"
#include "cycle_schedule.h"
#include "durable_history.h"
#include "progress_watchdog.h"
#include "core/driver_boundary_diagnostic.h"
#include "runtime_identity.h"
#include "shadow_controls.h"
#include <fstream>
#include <memory>
extern "C" uint64_t generated_restore_deposit_count();
extern "C" uint64_t harness_restore_deposit_count();

namespace {
class durable_restore_entry_t final : public checkpoint_entry_t {
  simif_emul_t *emulator=nullptr;
  simulation_t *simulation=nullptr;
  std::unique_ptr<runtime_identity_t> identity;
  mutable std::string staging;
  aggregate_restore_t aggregate;
  std::string loaded_native;
  std::string live_capture;
  bool public_capture=false;
  bool captured=false;
  bool consumed=false;
  // Host policy is independent of the checkpointed simulator state.
  std::string periodic_prefix;
  uint64_t periodic_interval=0;
  std::unique_ptr<durable_history_t> history;
  std::unique_ptr<checkpoint_cycle_schedule_t> periodic_schedule;
  checkpoint_request_t watchdog_configuration;
  std::unique_ptr<checkpoint_progress_watchdog_t> watchdog;
  aggregate_restore_t::owners_t owners() {
    auto result=emulator->checkpoint_axi_owners();
    result.push_back(emulator->checkpoint_host_timing_owner());
    for(const auto &list:{simulation->checkpoint_widget_owners(),simulation->checkpoint_driver_owners()})
      result.insert(result.end(),list.begin(),list.end());
    result.emplace_back("runtime/compatibility",identity.get()); return result;
  }
public:
  explicit durable_restore_entry_t(const std::vector<std::string> &args) {
    const auto request=checkpoint_request_t::parse(args);
    const auto shadow=checkpoint_shadow_controls_t::parse(args, request.kind==checkpoint_request_t::kind_t::restore);
    watchdog_configuration=request;
    if(request.kind==checkpoint_request_t::kind_t::capture) {
      if(!request.operation)
        throw std::runtime_error("public capture requires +fs-checkpoint-operation=N");
      live_capture=request.path;
      public_capture=true;
    }
    std::vector<std::string> configuration;
    for(const auto &arg:args) {
      if(shadow.contains(arg)) continue; // Validated, restore-only observer controls.
      if(arg.rfind("+fs-restore=",0)==0) continue; // Already parsed by entry.
      if(arg.rfind("+fs-checkpoint=",0)==0 || arg.rfind("+fs-checkpoint-operation=",0)==0) continue;
      if(arg.rfind("+fs-checkpoint-directory=",0)==0 || arg.rfind("+fs-checkpoint-interval=",0)==0 ||
         arg.rfind("+fs-checkpoint-retention=",0)==0 || arg=="+fs-checkpoint-level=1") continue;
      if(arg.rfind("+fs-checkpoint-target-timeout-cycles=",0)==0 ||
         arg.rfind("+fs-checkpoint-host-timeout-ms=",0)==0 ||
         arg.rfind("+fs-checkpoint-cycle-timeout-ms=",0)==0 ||
         arg.rfind("+fs-checkpoint-capture-timeout-ms=",0)==0) continue;
      if(arg.rfind("+test-live-periodic",0)==0) {
        const std::string prefix="+test-live-periodic=";
        if(arg.rfind(prefix,0)!=0 || arg.size()==prefix.size() || !periodic_prefix.empty())
          throw std::runtime_error("invalid/duplicate periodic capture destination");
        periodic_prefix=arg.substr(prefix.size()); continue;
      }
      if(arg.rfind("+test-live-interval",0)==0) {
        const std::string prefix="+test-live-interval=";
        if(arg.rfind(prefix,0)!=0 || periodic_interval)
          throw std::runtime_error("invalid/duplicate target interval");
        const auto value=arg.substr(prefix.size());
        const auto parsed=std::from_chars(value.data(),value.data()+value.size(),periodic_interval);
        if(parsed.ec!=std::errc{} || parsed.ptr!=value.data()+value.size() || !periodic_interval)
          throw std::runtime_error("invalid target interval");
        continue;
      }
      if(arg.rfind("+test-live-capture",0)==0) {
        if(arg.rfind("+test-live-capture=",0)!=0 || arg.size()==19 || !live_capture.empty() ||
           request.kind!=checkpoint_request_t::kind_t::none)
          throw std::runtime_error("unsupported/duplicate live capture test control");
        live_capture=arg.substr(19); continue;
      }
      if(arg.rfind("+test-aggregate",0)==0 || arg.rfind("+test-negative",0)==0 ||
         arg.rfind("+test-extra-library",0)==0)
        throw std::runtime_error("unsupported private staging request in public capability");
      // A public restore cannot also request a diagnostic capture/driver park.
      if(request.kind==checkpoint_request_t::kind_t::restore &&
         (arg.rfind("+fs-driver-",0)==0 || arg.rfind("+settled_generated_capture",0)==0 ||
          arg.rfind("+test-runtime-identity",0)==0))
        throw std::runtime_error("unsupported capture controls during public restore");
      configuration.push_back(arg);
      if(arg.rfind("+test-loaded-native=",0)==0) loaded_native=arg.substr(20);
    }
    if(periodic_prefix.empty() != (periodic_interval==0) ||
       (!periodic_prefix.empty() && (!live_capture.empty() ||
        (request.kind!=checkpoint_request_t::kind_t::none && request.kind!=checkpoint_request_t::kind_t::restore))))
      throw std::runtime_error("periodic capture requires paired controls and no single capture/preflight");
    if(!periodic_prefix.empty()) {
      const driver_boundary_diagnostic_t cut(args);
      if(cut.requested()) throw std::runtime_error("periodic capture conflicts with diagnostic cut");
    }
    if(request.periodic()) {
      if(!periodic_prefix.empty() || periodic_interval || !live_capture.empty())
        throw std::runtime_error("public periodic history conflicts with private capture controls");
      const driver_boundary_diagnostic_t cut(args);
      if(cut.requested()) throw std::runtime_error("public periodic history conflicts with diagnostic cut");
      periodic_interval=request.interval;
    }
    if(public_capture) {
      driver_boundary_diagnostic_t cut(args);
      cut.arm_checkpoint_operation(request.operation);
    } else if(!live_capture.empty()) {
      const driver_boundary_diagnostic_t cut(args);
      if(!cut.requested() || !cut.lowclock() || !cut.settled())
        throw std::runtime_error("live capture test requires a complete settled low-clock cut");
    }
    checkpoint_vcs_runtime_warmup();
    puts("FS_VCS_DIAGNOSTICS_PINNED before_identity=1");
    identity=std::make_unique<runtime_identity_t>(configuration);
    // Constructor pins/validates/recover-prunes history before platform startup.
    // This never releases a worker or loads target state.
    if(request.periodic()) history=std::make_unique<durable_history_t>(request.directory,request.retention);
    // Diagnostic owner output is available for the uninterrupted/capture
    // verifier. It never substitutes for the durable Level-1 container.
    for(const auto &arg:args) if(arg.rfind("+test-runtime-identity=",0)==0) {
      const auto bytes=identity->save_checkpoint();
      std::ofstream file(arg.substr(23),std::ios::binary);
      file.write(reinterpret_cast<const char *>(bytes.data()),bytes.size()); file.close();
      if(!file) throw std::runtime_error("runtime identity evidence write failed");
    }
  }
  void authorize_request(const checkpoint_request_t &request) const override {
    if(request.kind==checkpoint_request_t::kind_t::restore) {
      staging=read_durable_restore(request.path);
      puts("FS_DURABLE_RESTORE_VALIDATED before_platform=1");
    } else if(request.kind!=checkpoint_request_t::kind_t::capture && !request.periodic())
      checkpoint_entry_t::authorize_request(request);
  }
  action_t prepare(simif_t &platform, simulation_t &sim, const checkpoint_request_t &request) override {
    emulator=dynamic_cast<simif_emul_t *>(&platform); simulation=&sim;
    if(!emulator) throw std::runtime_error("durable restore requires VCS metasim");
    if(public_capture) {
      emulator->schedule_checkpoint_operation(request.operation);
      puts("FS_DURABLE_CAPTURE_SCHEDULED before_run=1 units=completed_driver_operations");
    }
    if(polling_requested()) {
      emulator->schedule_checkpoint_polling();
    }
    if(request.kind!=checkpoint_request_t::kind_t::restore) return action_t::run;
    if(staging.empty()) throw std::runtime_error("missing validated durable restore image");
    emulator->begin_restored_load(sim);
    puts("PRODUCTION_AGGREGATE_RESERVED no_workers=1");
    return action_t::restore_reserved;
  }
  void verify_identity() { identity->save_checkpoint(); }
  bool public_capture_requested() const { return public_capture && !captured; }
  bool periodic_capture_requested() const { return history || !periodic_prefix.empty(); }
  bool polling_requested() const { return periodic_capture_requested() || watchdog_configuration.watchdog(); }
  int poll_periodic(uint64_t host_sample) {
    try {
      if(!emulator || !simulation)
        throw std::runtime_error("missing periodic runtime");
      emulator->require_settled_checkpoint_capture();
      const bool reset_complete=durable_capture_reset_complete();
      if(!periodic_schedule && !watchdog) {
        // The manifested FASED counter resets during the initial target reset
        // pulse. Ignore that startup epoch explicitly; later resets reject.
        if(!reset_complete) { emulator->acknowledge_checkpoint_publication(); return 0; }
        if(periodic_capture_requested())
          periodic_schedule=std::make_unique<checkpoint_cycle_schedule_t>(periodic_interval);
      } else if(!reset_complete)
        throw std::runtime_error("target reset after periodic schedule initialization");
      const auto cycle=durable_capture_target_cycle();
      if(watchdog_configuration.watchdog()) {
        if(!watchdog) watchdog=std::make_unique<checkpoint_progress_watchdog_t>(
            watchdog_configuration.host_timeout_ms,watchdog_configuration.cycle_timeout_ms,
            watchdog_configuration.capture_timeout_ms,watchdog_configuration.target_timeout_cycles);
        watchdog->sample(cycle,watchdog_configuration.target_timeout_cycles
            ? std::optional<uint64_t>(durable_capture_target_progress()) : std::nullopt);
      }
      if(periodic_schedule && periodic_schedule->due(cycle)) {
        if(watchdog) watchdog->begin_capture();
        const auto snapshot=capture_durable_snapshot(owners(),host_sample);
        if(durable_capture_target_cycle()!=cycle)
          throw std::runtime_error("target cycle changed at parked periodic cut");
        if(history) history->publish(snapshot);
        else publish_durable_capture(periodic_prefix+"."+std::to_string(cycle)+".fsckpt",snapshot);
        periodic_schedule->committed(cycle);
        if(watchdog) watchdog->end_capture();
        printf("FS_DURABLE_PERIODIC_CAPTURE_PUBLISHED target_cycle=%llu host_sample=%llu history_committed=%d\n",
               (unsigned long long)cycle,(unsigned long long)host_sample,int(bool(history)));
      }
      emulator->require_settled_checkpoint_capture();
      emulator->acknowledge_checkpoint_publication();
      return 0;
    } catch(const std::exception &error) {
      fprintf(stderr,"FS_DURABLE_PERIODIC_CAPTURE_ERROR: %s\n",error.what()); return 1;
    }
  }
  int capture(uint64_t host_sample) {
    try {
      if(live_capture.empty() || captured || consumed || !emulator || !simulation)
        throw std::runtime_error("missing/consumed live capture request");
      captured=true; // A failed capture may never be retried or published.
      emulator->require_settled_checkpoint_capture();
      const auto snapshot=capture_durable_snapshot(owners(),host_sample);
      emulator->require_settled_checkpoint_capture();
      publish_durable_capture(live_capture,snapshot);
      if(public_capture) emulator->acknowledge_checkpoint_publication();
      printf("FS_DURABLE_LIVE_CAPTURE_PUBLISHED host_sample=%llu no_loads=1 no_deposits=1\n",
             (unsigned long long)host_sample);
      return 0;
    } catch(const std::exception &error) {
      fprintf(stderr,"FS_DURABLE_LIVE_CAPTURE_ERROR: %s\n",error.what()); return 1;
    }
  }
  int load() {
    try {
      if(consumed || !emulator || !simulation || staging.empty())
        throw std::runtime_error("missing/consumed public durable restore reservation");
      consumed=true;
      auto list=owners();
      aggregate.prepare_text(staging,list);
      staging.clear(); staging.shrink_to_fit();
      aggregate.commit_native();
      if(!loaded_native.empty()) {
        std::ofstream file(loaded_native);
        for(const auto &[name,owner]:list) {
          file<<name<<' ';
          for(uint8_t byte:owner->save_checkpoint()) file<<"0123456789abcdef"[byte>>4]<<"0123456789abcdef"[byte&15];
          file<<'\n';
        }
        file.close(); if(!file) throw std::runtime_error("native evidence write failed");
      }
      emulator->arm_restored_driver(*simulation);
      aggregate.commit_rtl();
      if(polling_requested()) {
        if(!durable_capture_reset_complete())
          throw std::runtime_error("periodic restore during initial target reset is unsupported");
        if(periodic_capture_requested())
          periodic_schedule=std::make_unique<checkpoint_cycle_schedule_t>(periodic_interval,aggregate.target_cycle);
      }
      printf("PRODUCTION_AGGREGATE_LOADED owners=%zu target_cycle=%llu host_sample=%llu\n",list.size(),
             (unsigned long long)aggregate.target_cycle,(unsigned long long)aggregate.host_sample);
      return 0;
    } catch(const std::exception &error) {
      fprintf(stderr,"FS_DURABLE_RESTORE_ERROR: %s native_loads=%llu deposits=%llu\n",error.what(),
              (unsigned long long)aggregate.native_load_count(),
              (unsigned long long)(generated_restore_deposit_count()+harness_restore_deposit_count())); return 1;
    }
  }
};
durable_restore_entry_t *capability=nullptr; // Owned by production entry.
}

std::unique_ptr<checkpoint_entry_t> create_checkpoint_entry(const std::vector<std::string> &args) {
  auto result=std::make_unique<durable_restore_entry_t>(args); capability=result.get(); return result;
}

extern "C" void production_runtime_identity_verify() {
  try { if(!capability) throw std::runtime_error("missing durable capability"); capability->verify_identity(); }
  catch(const std::exception &error) { fprintf(stderr,"FS_DURABLE_RESTORE_IDENTITY_ERROR: %s\n",error.what()); std::exit(1); }
}
extern "C" int production_aggregate_load() {
  if(!capability) return 1;
  return capability->load();
}
// Collector shared by the verification observer and the opt-in public harness
// callback. Both enter with the worker parked at the settled low-clock cut.
extern "C" int production_durable_live_capture(uint64_t host_sample) {
  if(!capability)
    fputs("FS_DURABLE_LIVE_CAPTURE_ERROR: missing durable capability\n",stderr);
  if(!capability || capability->capture(host_sample)) {
    // The worker is still parked. VCS/exit handlers must not tear down this
    // suspended DPI execution context or run any fallback startup path.
    std::fflush(nullptr);
    std::_Exit(EXIT_FAILURE);
  }
  return 0;
}
// Called by the ordinary opt-in harness before the parked worker is released.
extern "C" void production_durable_capture_if_requested(uint64_t host_sample) {
  if(!capability) {
    fputs("FS_DURABLE_LIVE_CAPTURE_ERROR: missing durable capability\n",stderr);
    std::fflush(nullptr); std::_Exit(EXIT_FAILURE);
  }
  if(capability->public_capture_requested()) production_durable_live_capture(host_sample);
  if(capability->polling_requested() && capability->poll_periodic(host_sample)) {
    std::fflush(nullptr); std::_Exit(EXIT_FAILURE);
  }
}
