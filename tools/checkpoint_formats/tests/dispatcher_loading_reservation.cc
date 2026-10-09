// Exercise fresh clock-hold reservation without ever creating a worker.
#define main original_dispatcher_checkpoint_main
#include "dispatcher_checkpoint.cc"
#undef main

int main(int argc, char **argv) {
  try {
    check(argc==2);
    for(unsigned trial=0;trial<6;++trial) {
      fixture_t f(0);auto &p=f.platform;auto &d=f.driver;
      auto *t=p.checkpoint_host_timing_owner().second;
      const auto mmio=p.master->save_checkpoint(), memory=p.slave.at(0)->save_checkpoint(), timing=t->save_checkpoint();
      uint32_t banks[3]={0,0,0};
      d.supported=false; rejects([&]{ p.begin_restored_load(d); });
      check(!p.restored_driver_pending()); d.supported=true;
      p.begin_restored_load(d); check(p.restored_driver_pending());
      driver_t other(f.registry,p,0);
      rejects([&]{ p.begin_restored_load(d); });
      rejects([&]{ p.begin_restored_load(other); });
      rejects([&]{ p.arm_restored_driver(other); });
      rejects([&]{ p.arm_restored_driver(d); }); // no owner has been loaded
      rejects([&]{ p.start_driver(d); });
      rejects([&]{ p.start_restored_driver(d,67,banks); });
      rejects([&]{ p.resume_restored_driver(67,banks); });
      rejects([&]{ p.to_sim(); });
      check(p.restored_driver_pending() && !p.calls && !p.ticks && d.index==0);
      d.require_fresh_dispatcher();
      check(p.master->save_checkpoint()==mmio && p.slave.at(0)->save_checkpoint()==memory && t->save_checkpoint()==timing);
    }
    { fixture_t f(0,{"+fs-driver-cut=1","+fs-driver-diagnostic=/unused.diag"});
      rejects([&]{ f.platform.begin_restored_load(f.driver); });check(!f.platform.restored_driver_pending()); }
    { fixture_t f(0); f.driver.base().load_checkpoint(read(std::filesystem::path(argv[1])/"base"));
      rejects([&]{ f.platform.begin_restored_load(f.driver); });check(!f.platform.restored_driver_pending()); }
    { fixture_t f(0); f.platform.slave.resize(5);
      rejects([&]{ f.platform.begin_restored_load(f.driver); });check(!f.platform.restored_driver_pending()); }
    { fixture_t f(0); f.platform.qsfp.emplace_back(nullptr);
      rejects([&]{ f.platform.begin_restored_load(f.driver); });check(!f.platform.restored_driver_pending()); }
    check(rejected==58);
    puts("PASS: loading reservation rejections=58 unchanged_owners=18 held_destinations=6 zero_workers=10 zero_edges=10");
    return 0;
  } catch(const std::exception &e) {
    fprintf(stderr,"loading reservation failure: %s\n",e.what());return 1;
  }
}
