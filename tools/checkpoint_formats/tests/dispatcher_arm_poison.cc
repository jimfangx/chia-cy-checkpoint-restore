// Reuse the audited dispatcher fixture and its independently captured owners.
// No fixture target edge or worker is allowed in these API failure checks.
#define main original_dispatcher_checkpoint_main
#include "dispatcher_checkpoint.cc"
#undef main

int main(int argc, char **argv) {
  try {
    check(argc==2);
    const std::filesystem::path input=argv[1];
    auto base=read(input/"base"), concrete=read(input/"driver");
    auto timing=read(input/"timing"), mmio=read(input/"mmio"), memory=read(input/"memory");
    for(unsigned mode=0;mode<6;++mode) {
      fixture_t f(0);auto &p=f.platform;auto &d=f.driver;
      auto *t=p.checkpoint_host_timing_owner().second;
      d.base().validate_checkpoint(base);d.validate_checkpoint(concrete);
      t->validate_checkpoint(timing);p.master->validate_checkpoint(mmio);
      p.slave.at(0)->validate_checkpoint(memory);
      d.base().load_checkpoint(base);d.load_checkpoint(concrete);
      t->load_checkpoint(timing);p.master->load_checkpoint(mmio);p.slave.at(0)->load_checkpoint(memory);
      p.arm_restored_driver(d);check(p.restored_driver_pending());
      uint32_t banks[3]={mode<3 ? 1U<<mode : 0,0,0};
      const uint32_t bits=mode==4 ? 0 : mode==5 ? 66 : 67;
      rejects([&]{ p.resume_restored_driver(bits,mode==3 ? nullptr : banks); });
      check(!p.restored_driver_pending() && !p.calls && !p.ticks);
      banks[0]=0;
      rejects([&]{ p.arm_restored_driver(d); });
      rejects([&]{ p.start_driver(d); });
      rejects([&]{ p.start_restored_driver(d,67,banks); });
      rejects([&]{ p.resume_restored_driver(67,banks); });
      rejects([&]{ p.to_sim(); });
      check(d.base().save_checkpoint()==base && d.save_checkpoint()==concrete);
      check(t->save_checkpoint()==timing && p.master->save_checkpoint()==mmio);
      check(p.slave.at(0)->save_checkpoint()==memory && !p.calls && !p.ticks);
    }
    check(rejected==36);
    puts("PASS: armed dispatcher poison rejections=36 unchanged_owners=30 zero_workers=6 zero_edges=6");
    return 0;
  } catch(const std::exception &e) {
    fprintf(stderr,"armed dispatcher poison failure: %s\n",e.what());return 1;
  }
}
