// Real pthread dispatcher cut guard, independent of VPI and RTL fixtures.
#define main original_dispatcher_main
#include "dispatcher_checkpoint.cc"
#undef main

int main(int argc, char **argv) {
  try {
    check(argc==2);
    init({},argv[1],false,1,0,0);
    const auto initial_rejections=rejected;
    unsigned checks=0, cuts=0;
    while(!finished) {
      auto &p=fixture->platform;
      rejects([&]{ p.require_settled_checkpoint_capture(); }); ++checks;
      tick();
      if(p.checkpoint_pending()) {
        ++cuts;
        const auto ticks=p.ticks, calls=p.calls;
        const auto mmio=p.master->save_checkpoint(), memory=p.slave.at(0)->save_checkpoint();
        const auto timing=p.checkpoint_host_timing_owner().second->save_checkpoint();
        p.require_settled_checkpoint_capture();
        p.qsfp.emplace_back(nullptr);
        rejects([&]{ p.require_settled_checkpoint_capture(); }); ++checks;
        p.qsfp.pop_back();
        p.slave.resize(5);
        rejects([&]{ p.require_settled_checkpoint_capture(); }); ++checks;
        p.slave.resize(1);
        p.require_settled_checkpoint_capture();
        check(p.ticks==ticks && p.calls==calls && p.master->save_checkpoint()==mmio &&
              p.slave.at(0)->save_checkpoint()==memory &&
              p.checkpoint_host_timing_owner().second->save_checkpoint()==timing);
        settled();
        rejects([&]{ p.require_settled_checkpoint_capture(); }); ++checks;
      }
    }
    check(cuts==1 && checks==rejected-initial_rejections);
    finish();
    printf("PASS: live capture guard cuts=%u rejections=%u unchanged_native=3 added_edges=0\n",cuts,checks);
    return 0;
  } catch(const std::exception &error) {
    fprintf(stderr,"capture guard failure: %s\n",error.what()); std::_Exit(1);
  }
}
