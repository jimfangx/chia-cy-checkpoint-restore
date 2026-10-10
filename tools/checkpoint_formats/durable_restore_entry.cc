// Explicitly linked public restore capability for the audited FCFS/FASED VCS
// profile. Capture publication is not enabled by this restore-only factory.
#include "core/checkpoint_entry.h"
#include "core/simulation.h"
#include "emul/simif_emul.h"
#include "aggregate_restore.h"
#include "durable_restore.h"
#include "durable_capture.h"
#include "core/driver_boundary_diagnostic.h"
#include "runtime_identity.h"
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
  bool captured=false;
  bool consumed=false;
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
    if(request.kind==checkpoint_request_t::kind_t::capture)
      throw std::runtime_error("unsupported public durable capture publication");
    std::vector<std::string> configuration;
    for(const auto &arg:args) {
      if(arg.rfind("+fs-restore=",0)==0) continue; // Already parsed by entry.
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
    if(!live_capture.empty()) {
      const driver_boundary_diagnostic_t cut(args);
      if(!cut.requested() || !cut.lowclock() || !cut.settled())
        throw std::runtime_error("live capture test requires a complete settled low-clock cut");
    }
    identity=std::make_unique<runtime_identity_t>(configuration);
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
    } else checkpoint_entry_t::authorize_request(request);
  }
  action_t prepare(simif_t &platform, simulation_t &sim, const checkpoint_request_t &request) override {
    emulator=dynamic_cast<simif_emul_t *>(&platform); simulation=&sim;
    if(!emulator) throw std::runtime_error("durable restore requires VCS metasim");
    if(request.kind!=checkpoint_request_t::kind_t::restore) return action_t::run;
    if(staging.empty()) throw std::runtime_error("missing validated durable restore image");
    emulator->begin_restored_load(sim);
    puts("PRODUCTION_AGGREGATE_RESERVED no_workers=1");
    return action_t::restore_reserved;
  }
  void verify_identity() { identity->save_checkpoint(); }
  int capture(uint64_t host_sample) {
    try {
      if(live_capture.empty() || captured || consumed || !emulator || !simulation)
        throw std::runtime_error("missing/consumed live capture test request");
      captured=true; // A failed capture may never be retried or published.
      emulator->require_settled_checkpoint_capture();
      const auto snapshot=capture_durable_snapshot(owners(),host_sample);
      emulator->require_settled_checkpoint_capture();
      publish_durable_capture(live_capture,snapshot);
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
// Verification-only entry to the collector, called by a context DPI observer
// at checkpoint_settled_event. Public +fs-checkpoint remains fail closed.
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
