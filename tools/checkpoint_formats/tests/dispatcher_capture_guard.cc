// Real pthread dispatcher cut guard, independent of VPI and RTL fixtures.
#define main original_dispatcher_main
#include "dispatcher_checkpoint.cc"
#undef main
#include "../cycle_schedule.h"

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
    // Public scheduling needs no diagnostic path. A missing harness callback
    // must leave the worker parked and reject rather than silently resuming.
    finished=false; restoring=false; scenario=0;
    fixture=std::make_unique<fixture_t>(0);
    auto &p=fixture->platform;
    rejects([&]{ p.schedule_checkpoint_operation(0); });
    p.schedule_checkpoint_operation(1);
    rejects([&]{ p.schedule_checkpoint_operation(1); });
    rejects([&]{ p.acknowledge_checkpoint_publication(); });
    p.start_driver(fixture->driver);
    rejects([&]{ p.schedule_checkpoint_operation(2); });
    unsigned public_cuts=0;
    while(!finished) {
      tick();
      if(p.checkpoint_pending()) {
        ++public_cuts;
        const auto ticks=p.ticks, calls=p.calls;
        const auto memory=p.slave.at(0)->save_checkpoint();
        uint32_t banks[3]={0,0,0};
        rejects([&]{ p.checkpoint_settled(67,banks); });
        check(p.checkpoint_pending() && p.ticks==ticks && p.calls==calls &&
              p.slave.at(0)->save_checkpoint()==memory);
        p.acknowledge_checkpoint_publication();
        rejects([&]{ p.acknowledge_checkpoint_publication(); });
        check(p.ticks==ticks && p.calls==calls && p.slave.at(0)->save_checkpoint()==memory);
        finished=p.checkpoint_settled(67,banks);
      }
    }
    check(public_cuts==1 && p.end()==0);
    fixture.reset();
    check(!std::filesystem::exists(output/"public-diagnostic"));
    puts("PASS: public schedule missing_callback_rejected=1 publication_acknowledged=1 added_edges=0");
    for (bool consecutive : {false,true}) {
      finished=false;
      fixture=std::make_unique<fixture_t>(0);
      auto &poll=fixture->platform;
      poll.schedule_checkpoint_polling();
      rejects([&]{ poll.schedule_checkpoint_polling(); });
      rejects([&]{ poll.schedule_checkpoint_operation(1); });
      poll.start_driver(fixture->driver);
      rejects([&]{ poll.schedule_checkpoint_polling(); });
      unsigned repeated_cuts=0;
      while(!finished) {
        if(!poll.checkpoint_pending()) tick();
        while(poll.checkpoint_pending()) {
          ++repeated_cuts;
          poll.require_settled_checkpoint_capture();
          const auto ticks=poll.ticks, calls=poll.calls;
          const auto memory=poll.slave.at(0)->save_checkpoint();
          uint32_t banks[3]={0,0,0};
          // A prior cut's acknowledgment cannot authorize this new callback.
          rejects([&]{ poll.checkpoint_settled(67,banks); });
          check(poll.checkpoint_pending() && poll.ticks==ticks && poll.calls==calls &&
                poll.slave.at(0)->save_checkpoint()==memory);
          poll.acknowledge_checkpoint_publication();
          rejects([&]{ poll.acknowledge_checkpoint_publication(); });
          if(consecutive) poll.yield=false;
          finished=poll.checkpoint_settled(67,banks);
          check(poll.ticks==ticks);
        }
      }
      check(repeated_cuts==4 && poll.end()==0);
      fixture.reset();
      printf("PASS: repeated settled callbacks cuts=%u consecutive=%u per_cut_ack=1 added_edges=0\n",
             repeated_cuts,consecutive);
    }
    checkpoint_cycle_schedule_t schedule(10,7);
    check(!schedule.due(16) && schedule.due(17) && schedule.due(17));
    schedule.committed(17); check(!schedule.due(26) && schedule.due(48));
    schedule.committed(48); check(!schedule.due(56) && schedule.due(57));
    rejects([&]{ schedule.due(56); });
    constexpr auto maximum=std::numeric_limits<uint64_t>::max();
    checkpoint_cycle_schedule_t overflow(10,maximum-10);
    check(overflow.due(maximum)); overflow.committed(maximum); check(!overflow.due(maximum));
    checkpoint_cycle_schedule_t exhausted(10,maximum-9); check(!exhausted.due(maximum));
    rejects([&]{ checkpoint_cycle_schedule_t invalid(0); });
    puts("PASS: native target deadlines restored_origin=1 skipped_deadlines=1 retry=1 overflow=1");
    return 0;
  } catch(const std::exception &error) {
    fprintf(stderr,"capture guard failure: %s\n",error.what()); std::_Exit(1);
  }
}
