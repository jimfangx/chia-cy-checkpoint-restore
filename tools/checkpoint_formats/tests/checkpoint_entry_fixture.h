// Dispatch fixture only. The production entry translation unit is compiled
// unchanged, with platform/registry/driver declarations replaced by these
// no-clock observers. Full generated-state continuation is verified separately.
#pragma once
#define __CORE_CONFIG_H
#define __SIMIF_H
#define __SIMULATION_H
#define __LOADMEM_H
#include "core/checkpoint.h"
#include <cstdio>
#include <memory>
#include <utility>

extern std::string fixture_mode;
struct TargetConfig {};
class widget_registry_t {
public:
  widget_registry_t() { puts("FIXTURE_REGISTRY"); }
  void note_constructor() { puts("FIXTURE_WIDGET"); }
  void checkpoint_preflight() const {
    puts("FIXTURE_PREFLIGHT");
    if (fixture_mode == "widget")
      throw std::runtime_error("unsupported fixture widget");
  }
};
class fixture_owner_t : public checkpoint_owner_t {
public:
  std::string checkpoint_schema() const override {
    return fixture_mode == "driver" ? "" : "fixture.dispatch-only.v1";
  }
};
class simulation_t {
  fixture_owner_t owner;
public:
  std::vector<std::pair<std::string, checkpoint_owner_t *>> checkpoint_driver_owners() {
    puts("FIXTURE_DRIVER_INVENTORY");
    if (fixture_mode == "empty-driver") return {};
    return {{"runtime/simulation", fixture_mode == "null-driver" ? nullptr : &owner}};
  }
};
class simif_t {
public:
  virtual ~simif_t() = default;
  int run(simulation_t &) { puts("FIXTURE_RUN mmio=1 native_ticks=1 target_edges=1"); return 0; }
};
