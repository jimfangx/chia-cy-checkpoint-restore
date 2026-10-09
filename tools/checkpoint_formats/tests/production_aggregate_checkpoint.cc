// Test-only checkpoint capability linked to the real production entry.cc.
// Production +fs-restore remains fail closed until its durable runtime API is
// audited. This adapter exercises the real harness/DPI/dispatcher, not MMIO
// fixtures, and reserves clocks before any owner loading.
#include "core/simulation.h"
#include "core/checkpoint_entry.h"
#include "entry.h"
#include "emul/simif_emul.h"
#include "../aggregate_restore.h"
#include "../runtime_identity.h"
#include <fstream>
#include <memory>
#include <dlfcn.h>

extern std::unique_ptr<simulation_t> simulation;
static simif_emul_t *emulator = nullptr;
static aggregate_restore_t aggregate;
static std::string bundle;
static std::string negative;
static std::string loaded_native;
static std::string extra_library;
static std::unique_ptr<runtime_identity_t> runtime_identity;
struct observed_owner_t : checkpoint_owner_t {
  checkpoint_owner_t &owner;
  size_t &loads;
  observed_owner_t(checkpoint_owner_t &owner, size_t &loads) : owner(owner), loads(loads) {}
  std::string checkpoint_schema() const override { return owner.checkpoint_schema(); }
  std::vector<uint8_t> save_checkpoint() const override { return owner.save_checkpoint(); }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override { owner.validate_checkpoint(b); }
  void load_checkpoint(const std::vector<uint8_t> &b) override { ++loads; owner.load_checkpoint(b); }
};
static aggregate_restore_t::owners_t owners() {
  auto result = emulator->checkpoint_axi_owners();
  result.push_back(emulator->checkpoint_host_timing_owner());
  auto widgets = simulation->checkpoint_widget_owners();
  auto drivers = simulation->checkpoint_driver_owners();
  result.insert(result.end(), widgets.begin(), widgets.end());
  result.insert(result.end(), drivers.begin(), drivers.end());
  result.emplace_back("runtime/compatibility", runtime_identity.get());
  return result;
}
extern "C" uint64_t generated_restore_deposit_count();
extern "C" uint64_t harness_restore_deposit_count();

class production_checkpoint_entry_t final : public checkpoint_entry_t {
public:
  explicit production_checkpoint_entry_t(const std::vector<std::string> &args) {
    runtime_identity = std::make_unique<runtime_identity_t>(args);
    for (const auto &arg : args) {
      if (arg.rfind("+test-aggregate=", 0)==0) bundle=arg.substr(16);
      if (arg.rfind("+test-negative=", 0)==0) negative=arg.substr(15);
      if (arg.rfind("+test-loaded-native=", 0)==0) loaded_native=arg.substr(20);
      if (arg.rfind("+test-extra-library=", 0)==0) extra_library=arg.substr(20);
      if (arg.rfind("+test-runtime-identity=", 0)==0) {
        const auto bytes=runtime_identity->save_checkpoint();
        std::ofstream file(arg.substr(23), std::ios::binary);
        file.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
        file.close();
        if (!file) throw std::runtime_error("runtime identity evidence write failed");
      }
    }
    if (!extra_library.empty() && (bundle.empty() || negative.empty()))
      throw std::runtime_error("unsupported test library outside a negative fresh restore");
  }
  action_t prepare(simif_t &platform, simulation_t &sim,
                   const checkpoint_request_t &request) override {
    if (request.durable())
      throw std::runtime_error("test capability cannot service public durable requests");
    emulator = dynamic_cast<simif_emul_t *>(&platform);
    if (!emulator) throw std::runtime_error("production profile requires VCS metasim");
    if (bundle.empty()) return action_t::run;
    emulator->begin_restored_load(sim);
    puts("PRODUCTION_AGGREGATE_RESERVED no_workers=1");
    return action_t::restore_reserved;
  }
};

std::unique_ptr<checkpoint_entry_t>
create_checkpoint_entry(const std::vector<std::string> &args) {
  return std::make_unique<production_checkpoint_entry_t>(args);
}

extern "C" void production_runtime_identity_verify() {
  if (!negative.empty()) return; // Expected rejection processes never resume.
  try { runtime_identity->save_checkpoint(); }
  catch (const std::exception &error) {
    fprintf(stderr, "PRODUCTION_RUNTIME_IDENTITY_ERROR: %s\n", error.what());
    std::exit(1);
  }
}

extern "C" int production_aggregate_load() {
  if (!extra_library.empty() && !dlopen(extra_library.c_str(), RTLD_NOW|RTLD_LOCAL)) {
    fprintf(stderr, "PRODUCTION_AGGREGATE_LOAD_ERROR: test library load failed\n");
    return 1;
  }
  auto list = owners();
  size_t loads = 0;
  std::vector<std::unique_ptr<observed_owner_t>> observed;
  for (auto &[name, owner] : list) {
    observed.push_back(std::make_unique<observed_owner_t>(*owner, loads));
    owner = observed.back().get();
  }
  // Snapshot native state to prove late-section failures do not mutate ANY
  // owner. Some fresh concrete adapters cannot save until loaded; those are
  // covered by zero-load/deposit counts and their component lifecycle tests.
  std::vector<std::pair<checkpoint_owner_t *, std::vector<uint8_t>>> initial;
  for (auto &[name, owner] : list) {
    try { initial.emplace_back(owner, owner->save_checkpoint()); }
    catch (const std::exception &) {}
  }
  try {
    aggregate.prepare(bundle, list);
    if (!negative.empty()) {
      fputs("PRODUCTION_AGGREGATE_INVALID_ACCEPTED\n", stderr);
      std::exit(1);
    }
    aggregate.commit_native();
    if (!loaded_native.empty()) {
      std::ofstream file(loaded_native);
      for (const auto &[name, owner] : list) {
        file << name << ' ';
        for (uint8_t byte : owner->save_checkpoint()) {
          const char *hex="0123456789abcdef";
          file << hex[byte>>4] << hex[byte&15];
        }
        file << '\n';
      }
      file.close();
      if (!file) throw std::runtime_error("native evidence write failed");
    }
    emulator->arm_restored_driver(*simulation);
    aggregate.commit_rtl();
    printf("PRODUCTION_AGGREGATE_LOADED owners=%zu target_cycle=%llu host_sample=%llu\n",
           list.size(), (unsigned long long)aggregate.target_cycle,
           (unsigned long long)aggregate.host_sample);
    return 0;
  } catch (const std::exception &error) {
    fprintf(stderr, "PRODUCTION_AGGREGATE_LOAD_ERROR: %s\n", error.what());
    if (negative.empty()) return 1;
    for (auto &[owner, bytes] : initial)
      if (owner->save_checkpoint()!=bytes) std::exit(1);
    if (loads || generated_restore_deposit_count() || harness_restore_deposit_count()) std::exit(1);
    printf("PRODUCTION_AGGREGATE_REJECTED unchanged_native=%zu native_loads=0 deposits=0\n", initial.size());
    return 2;
  }
}
