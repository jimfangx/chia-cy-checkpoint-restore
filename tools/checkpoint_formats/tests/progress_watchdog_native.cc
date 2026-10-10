#include "progress_watchdog.h"
#include "core/checkpoint_entry.h"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <functional>
#include <string>
#include <thread>
#include <fcntl.h>
#include <unistd.h>

using namespace std::chrono_literals;
void reject(const std::function<void()> &f) {
  bool failed=false; try { f(); } catch(const std::exception &) { failed=true; } assert(failed);
}
int main(int argc,char **argv) {
  const std::string mode=argc>1 ? argv[1] : "policy";
  if(mode=="policy") {
    checkpoint_progress_policy_t p(10,20,100);
    assert(!p.failure(0)); reject([&]{ p.begin_capture(0); });
    p.sample(1,600000); assert(!p.failure(10));
    assert(std::string(p.failure(11))=="host_progress_stall");
    checkpoint_progress_policy_t c(0,20,100);
    c.sample(1,600000); c.sample(11,600000); assert(!c.failure(20));
    c.begin_capture(20); assert(!c.failure(119));
    c.end_capture(119); assert(!c.failure(119));
    assert(std::string(c.failure(120))=="target_cycle_stall");
    checkpoint_progress_policy_t cap(10,20,100);
    cap.sample(1,7); cap.begin_capture(2);
    reject([&]{cap.begin_capture(3);}); reject([&]{cap.sample(4,7);});
    assert(!cap.failure(101)); assert(std::string(cap.failure(102))=="capture_stall");
    reject([&]{cap.end_capture(102);});
    checkpoint_progress_policy_t regress(10,20,100);
    regress.sample(10,7); reject([&]{regress.sample(11,6);});
    reject([&]{regress.failure(9);}); reject([&]{regress.end_capture(12);});
    reject([]{checkpoint_progress_policy_t invalid(0,0,100);});
    reject([]{checkpoint_progress_policy_t invalid(10,0,0);});
    // Public parsing before platform construction, including unsupported use.
    const std::vector<std::string> restore={"+fs-restore=image","+fs-checkpoint-host-timeout-ms=100",
                                           "+fs-checkpoint-capture-timeout-ms=1000"};
    assert(checkpoint_request_t::parse(restore).watchdog());
    unsigned rejected=0;
    for(const auto &key:{"host","cycle","capture"}) {
      const auto prefix=std::string("+fs-checkpoint-")+key+"-timeout-ms=";
      for(const auto &value:{"","0","-1","+1","1x","9223372036855","18446744073709551616"}) {
        auto args=restore;
        args.erase(args.begin()+1,args.end());
        args.push_back(prefix+value);
        reject([&]{checkpoint_request_t::parse(args);}); ++rejected;
      }
      auto args=restore; args.push_back(prefix+"100");
      if(std::string(key)=="cycle") args.push_back(prefix+"100");
      reject([&]{checkpoint_request_t::parse(args);}); ++rejected;
    }
    for(const auto &args:std::vector<std::vector<std::string>>{
      {"+fs-restore=image","+fs-checkpoint-host-timeout-ms=1"},
      {"+fs-restore=image","+fs-checkpoint-capture-timeout-ms=1"},
      {"+fs-checkpoint-host-timeout-ms=1","+fs-checkpoint-capture-timeout-ms=100"},
      {"+fs-restore=image","+fs-checkpoint-host-timeout-ms-typo=1","+fs-checkpoint-capture-timeout-ms=100"}}) {
      reject([&]{checkpoint_request_t::parse(args);}); ++rejected;
    }
    printf("PASS: policy boundaries capture_exclusion_preserves_age=1 parser_rejections=%u\n",rejected);
    return 0;
  }
  const bool cycle=mode=="cycle";
  checkpoint_progress_watchdog_t watchdog(cycle?0:100,cycle?100:0,500);
  if(mode=="sample-lock") {
    // Block stdio in the sampling critical section. The monitor must keep
    // aging its last coherent copy without waiting on that held mutex.
    int pipefd[2]; assert(pipe(pipefd)==0);
    assert(fcntl(pipefd[1],F_SETFL,O_NONBLOCK)==0);
    char bytes[4096]{}; while(write(pipefd[1],bytes,sizeof(bytes))>0) {}
    assert(fcntl(pipefd[1],F_SETFL,0)==0); assert(dup2(pipefd[1],STDOUT_FILENO)>=0);
    std::thread blocked([&]{watchdog.sample(600000);});
    std::this_thread::sleep_for(800ms); blocked.join();
    return 2;
  }
  watchdog.sample(600000);
  if(mode=="healthy" || mode=="capture") {
    watchdog.begin_capture(); std::this_thread::sleep_for(mode=="capture"?800ms:250ms);
    watchdog.end_capture();
    watchdog.sample(600001);
    for(unsigned i=0;i<20;++i) { std::this_thread::sleep_for(5ms); watchdog.sample(600002+i); }
    puts("PASS: real independent monitor capture_longer_than_progress_timeout=1 clean_shutdown=1");
  } else if(cycle) {
    for(unsigned i=0;i<100;++i) { std::this_thread::sleep_for(5ms); watchdog.sample(600000); }
  } else std::this_thread::sleep_for(800ms);
}
