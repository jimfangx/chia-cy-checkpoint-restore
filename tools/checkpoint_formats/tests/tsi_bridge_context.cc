// Actual production TSI bridge with a serial MMIO device, never target RTL.
#define TSI_CONTEXT_GROUP_DPI
#include "tsi_context_group_fesvr.cc"
#include "bridges/tsibridge.h"
#include "bridges/loadmem.h"
#include "core/config.h"
#include "emul/driver_thread.h"
#include <deque>
#include <getopt.h>

simif_t::simif_t(const TargetConfig &c) : config(c) {}
simif_t::~simif_t() = default;
CPUManagedStreamIO &simif_t::get_cpu_managed_stream_io() { std::abort(); }
FPGAManagedStreamIO &simif_t::get_fpga_managed_stream_io() { std::abort(); }
int simif_t::run(simulation_t &) { std::abort(); }
void bridge_driver_t::write(size_t a, uint32_t d) { simif.write(a,d); }
uint32_t bridge_driver_t::read(size_t a) { return simif.read(a); }
midas_time_t timestamp() { return 0; }
double diff_secs(midas_time_t, midas_time_t) { return 0; }

__attribute__((constructor)) static void bridge_context_blocked_inheritance() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT,SIGTERM,SIGABRT}) sigaddset(&set,sig);
  if (pthread_sigmask(SIG_BLOCK,&set,nullptr)) std::abort();
}
static const TargetConfig bridge_fixture_config{{4,40,32},{4,40,64},1,{},{},{0,0},"tsi-bridge-component"};
struct bridge_divergence_t {};
struct bridge_parked_thread_t {
  std::promise<void> ready, release;
  std::future<void> released=release.get_future();
  std::thread worker;
  ~bridge_parked_thread_t() { if(worker.joinable()) { release.set_value(); worker.join(); } }
};
struct context_mmio_t final : simif_t {
  context_mmio_t() : simif_t(bridge_fixture_config) {}
  std::deque<uint32_t> incoming, expected;
  size_t calls=0, writes=0, words=0;
  uint32_t outgoing=0;
  size_t operation=0, packet_word=0;
  void write(size_t addr,uint32_t data) override {
    ++calls; ++writes;
    if(addr==0) outgoing=data;
    else if(addr==4) {
      require(!expected.empty(),"unexpected bridge output");
      if(expected.front()!=outgoing) {
        std::cout<<"FIRST_DIVERGENCE operation="<<operation<<" word="<<packet_word
                 <<" expected="<<expected.front()<<" actual="<<outgoing<<" acknowledged=0 fresh_context=1\n";
        throw bridge_divergence_t{};
      }
      expected.pop_front(); ++words; ++packet_word;
    } else if(addr==20) { require(!incoming.empty(),"extra input acknowledgement"); incoming.pop_front(); }
    else require(addr==32 && data==1,"bridge replayed init/reset/loadmem/step-size write");
  }
  uint32_t read(size_t addr) override {
    ++calls;
    if(addr==8) return !expected.empty();
    if(addr==12) { require(!incoming.empty(),"empty bridge input"); return incoming.front(); }
    if(addr==16) return !incoming.empty();
    if(addr==28) return 1;
    throw std::runtime_error("bridge issued unexpected MMIO read");
  }
};
// Own the actual provider and its peers across mailbox preparation and launch.
// Destruction of the first member happens last, after the provider is gone.
struct bridge_creator_session_t final : emul_driver_thread_t::resource_t {
  struct lifetime_t {
    std::thread::id creator=std::this_thread::get_id();
    bool &destroyed;
    ~lifetime_t() {
      if(std::this_thread::get_id()!=creator) std::abort();
      destroyed=true;
      std::cout<<"BRIDGE_CREATOR_DESTROYED same_thread=1 provider_destroyed=1\n";
    }
  } lifetime;
  context_mmio_t mmio;
  loadmem_t memory;
  tsibridge_t bridge;
  emul_driver_thread_t::task_t continuation;
  emul_driver_thread_t::task_t readback;
  std::unique_ptr<tsibridge_t::prepared_context_t> candidate, competitor;
  tsibridge_t::context_image_t expected;
  bool published=false;
  bool guard_live=false;
  std::mutex publication_mutex;
  fs::path out;
  bridge_creator_session_t(const std::vector<std::string> &args,bool &destroyed,const fs::path &path)
      : lifetime{std::this_thread::get_id(),destroyed},
        memory(mmio,{64,68,72,76,80,84,88,92,96},0,{},bridge_fixture_config.mem,2),
        bridge(mmio,memory,{0,4,8,12,16,20,24,28,32},0,args,true,0),out(path) {}
};
// Component exclusion only: the full simulator process policy is still pending.
struct bridge_publication_guard_t final : emul_driver_thread_t::resource_t {
  bridge_creator_session_t &session;
  std::thread::id creator=std::this_thread::get_id();
  std::unique_lock<std::mutex> lock;
  explicit bridge_publication_guard_t(bridge_creator_session_t &s)
      : session(s),lock(s.publication_mutex) { session.guard_live=true; }
  ~bridge_publication_guard_t() override {
    if(std::this_thread::get_id()!=creator || !session.guard_live) std::abort();
    session.guard_live=false;
    std::cout<<"BRIDGE_PUBLICATION_GUARD_RELEASED same_thread=1\n";
  }
};
static int bridge_context_run(const char *mode,const char *elf,const char *input,const char *metadata,
    const char *source,const char *plan,const char *destination,const char *image_path,const char *build_path) {
  try {
    const std::string action(mode); const auto context=bytes(image_path), build_bytes=bytes(build_path);
    if(action.rfind("fatal-",0)==0) std::set_terminate([] {
      std::cout<<"BRIDGE_PUBLICATION_FATAL before_acknowledgment=1\n"<<std::flush;
      std::_Exit(73);
    });
    require(build_bytes.size()==32,"need build SHA-256"); tsibridge_t::context_build_t build;
    std::copy(build_bytes.begin(),build_bytes.end(),build.begin());
    std::exception_ptr failure;
    emul_driver_thread_t creator;
    bridge_creator_session_t *session=nullptr;
    bool destroyed=false;
    creator.reserve();
    const auto creator_id=creator.get_id();
    creator.invoke([&] {
      try {
        const fs::path out(destination); fs::create_directories(out);
        std::vector<std::string> args{"+permissive","+no_hart0_msip","+idle-counts=3",
          "+checkpoint-syscall-exit","+checkpoint-terminal-input="+std::string(input)};
        if(fs::path(input).filename().string().find("flush")!=std::string::npos) args.push_back("+cflush_addr=0x20004000");
        args.insert(args.end(),{"+permissive-off",elf});
        auto owned=std::make_unique<bridge_creator_session_t>(args,destroyed,out);
        session=owned.get();
        auto &bridge=session->bridge; auto &mmio=session->mmio;
        creator.retain(std::move(owned));
        require(bridge.checkpoint_schema().empty(),"restricted restore granted aggregate admission");
        const auto pristine=bridge.control_owner().save_checkpoint();
        const auto pristine_descriptors=descriptors();
        const int saved_index=optind, saved_error=opterr, saved_option=optopt;
        char *const saved_argument=optarg;
        tsibridge_t::context_image_t image{bytes(metadata),pristine,context};
        // Bridge polling follows completed initialization and wait ticks. The
        // exact identity/configuration comes from this actual bridge instance.
        std::fill(image.control.end()-16,image.control.end(),0); image.control[image.control.size()-8]=1;
        auto unchanged=[&] {
          require(bridge.control_owner().save_checkpoint()==pristine && !mmio.calls,"bridge partially published or serviced");
          require(optind==saved_index && opterr==saved_error && optopt==saved_option && optarg==saved_argument,
                  "bridge candidate changed process argument parser globals");
          require(descriptors()==pristine_descriptors,"bridge candidate leaked/changed process descriptors");
          bool absent=false;
          try { bridge.capture_restricted_context(build); } catch(const std::runtime_error &e) {
            absent=std::string(e.what())=="TSI context capture requires an initialized bridge";
          }
          require(absent,"bridge provider published early");
        };
        if(action=="invalid") {
          bool rejected=false;
          try { auto candidate=bridge.prepare_restricted_context(image,build); candidate->commit(); }
          catch(const std::runtime_error &) { rejected=true; }
          require(rejected,"invalid context admitted by bridge"); unchanged();
          std::cout<<"BRIDGE_CONTEXT_REJECT unpublished=1 mmio=0 target_edges=0\n"; return;
        }
        if(action=="atomic") {
          size_t truncations=0,invalids=0;
          for(size_t n=0;n<image.control.size();++n) {
            auto bad=image; bad.control.resize(n); bool rejected=false;
            try { auto c=bridge.prepare_restricted_context(bad,build); c->commit(); }
            catch(const std::runtime_error &) { rejected=true; }
            require(rejected,"truncated bridge control admitted"); unchanged(); ++truncations;
          }
          for(size_t offset : {image.control.size()-16,image.control.size()-8}) {
            auto bad=image; bad.control[offset]^=1; bool rejected=false;
            try { auto c=bridge.prepare_restricted_context(bad,build); c->commit(); }
            catch(const std::runtime_error &) { rejected=true; }
            require(rejected,"inconsistent bridge phase admitted"); unchanged(); ++invalids;
          }
          long allocations=0;
          for(;;++allocations) {
            bool failed=false; tsi_terminal_fail_allocation_after(allocations);
            try { auto c=bridge.prepare_restricted_context(image,build); c->commit(); }
            catch(const std::bad_alloc &) { failed=true; }
            catch(...) { tsi_terminal_fail_allocation_after(-1); throw; }
            tsi_terminal_fail_allocation_after(-1);
            if(!failed) break; unchanged();
          }
          const auto restored=bridge.capture_restricted_context(build);
          session->expected=image; session->published=true;
          require(restored.context==image.context && restored.control==image.control && !mmio.calls,"bridge atomic readback");
          save(out/"readback.context",restored.context); save(out/"readback.control",restored.control);
          std::cout<<"BRIDGE_CONTEXT_ATOMIC truncations="<<truncations<<" cross="<<invalids
                   <<" allocations="<<allocations<<" unpublished_on_failure=1 mmio=0 target_edges=0\n"; return;
        }
        session->candidate=bridge.prepare_restricted_context(image,build);
        session->competitor=bridge.prepare_restricted_context(image,build);
        auto &candidate=session->candidate;
        auto &competitor=session->competitor;
        const bool staged=action=="restore" || action=="corrupt" || action=="cancel" ||
                          action=="cancel-prepared" || action=="cancel-sealed" || action.rfind("fatal-",0)==0;
        bridge_parked_thread_t parked_foreign;
        unchanged();
        if(action=="guard-control") {
          auto changed=image.control;
          const_cast<checkpoint_owner_t &>(bridge.control_owner()).load_checkpoint(changed);
          bool rejected=false; try { candidate->commit(); } catch(const std::runtime_error &) { rejected=true; }
          require(rejected && bridge.control_owner().save_checkpoint()==changed && !mmio.calls,
                  "late bridge control change partially published");
          const_cast<checkpoint_owner_t &>(bridge.control_owner()).load_checkpoint(pristine);
          unchanged();
          std::cout<<"BRIDGE_CONTEXT_CONTROL_GUARD unpublished=1 creator_retry=1\n";
        }
        if(action=="guard-mask") {
          sigset_t set; sigemptyset(&set); for(int sig:{SIGINT,SIGTERM,SIGABRT}) sigaddset(&set,sig);
          require(!pthread_sigmask(SIG_UNBLOCK,&set,nullptr),"unblock bridge mask");
          bool rejected=false; try { candidate->commit(); } catch(const std::runtime_error &) { rejected=true; }
          require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"repair bridge mask");
          require(rejected,"late bridge mask admitted"); unchanged();
          std::cout<<"BRIDGE_CONTEXT_LATE_GUARD unpublished=1 creator_retry=1\n";
        }
        if(action=="fatal-unsealed") candidate->publish_sealed();
        if(action=="seal-retry") {
          long allocations=0;
          for(;;++allocations) {
            bool failed=false; tsi_terminal_fail_allocation_after(allocations);
            try { candidate->seal_publication(); }
            catch(const std::bad_alloc &) { failed=true; }
            catch(...) { tsi_terminal_fail_allocation_after(-1); throw; }
            tsi_terminal_fail_allocation_after(-1);
            unchanged();
            if(!failed) break;
          }
          bool rejected=false;
          try { candidate->seal_publication(); } catch(const std::runtime_error &) { rejected=true; }
          require(rejected,"candidate sealed twice"); unchanged();
          tsi_terminal_fail_allocation_after(0); candidate->publish_sealed(); tsi_terminal_fail_allocation_after(-1);
          std::cout<<"BRIDGE_SEAL_RETRY allocations="<<allocations<<" unpublished_on_failure=1 duplicate_seal_rejected=1 allocation_free_publish=1\n";
        } else if(action=="foreign") {
          bool rejected=false;
          parked_foreign.worker=std::thread([&] {
            try { candidate->commit(); } catch(const std::runtime_error &e) {
              rejected=std::string(e.what())=="TSI access requires its live original thread";
            }
            parked_foreign.ready.set_value(); parked_foreign.released.wait();
          });
          parked_foreign.ready.get_future().wait();
          require(rejected,"foreign bridge publication admitted"); unchanged(); candidate->commit();
          std::cout<<"BRIDGE_CONTEXT_FOREIGN rejected=1 creator_retry=1\n";
        } else if(!staged) candidate->commit();
        session->expected=image;
        session->readback=[&,image,out,staged] {
        if(staged) require(session->guard_live,"TSI readback outside retained publication guard");
        const auto restored=bridge.capture_restricted_context(build);
        session->published=true;
        require(restored.context==image.context && restored.control==image.control && restored.metadata==image.metadata && !mmio.calls,
                "bridge complete zero-edge readback differs");
        save(out/"readback.context",restored.context); save(out/"readback.control",restored.control);
        size_t rejections=0;
        for(unsigned call=0;call<3;++call) {
          bool rejected=false;
          try {
            if(call==2) session->competitor->commit();
            else if(call) { auto c=bridge.prepare_restricted_context(image,build); }
            else session->candidate->commit();
          }
          catch(const std::runtime_error &) { rejected=true; }
          require(rejected && bridge.capture_restricted_context(build).context==context && !mmio.calls,"bridge republished"); ++rejections;
        }
        std::cout<<"BRIDGE_CONTEXT_READBACK owners=17 context_entries=0 mmio=0 republish_rejections="<<rejections<<" target_edges=0\n";
        };
        if(!staged) session->readback();
        if(action=="foreign") {
          bridge_parked_thread_t parked_restored; size_t denied=0;
          parked_restored.worker=std::thread([&] {
            for(unsigned call=0;call<4;++call) {
              bool rejected=false;
              try {
                if(call==0) bridge.tick();
                else if(call==1) bridge.terminate();
                else if(call==2) bridge.exit_code();
                else bridge.capture_restricted_context(build);
              } catch(const std::runtime_error &e) { rejected=std::string(e.what())=="TSI access requires its live original thread"; }
              if(rejected) ++denied;
            }
            parked_restored.ready.set_value(); parked_restored.released.wait();
          });
          parked_restored.ready.get_future().wait();
          require(denied==4 && !mmio.calls && bridge.capture_restricted_context(build).context==context,
                  "foreign restored bridge call mutated state");
          std::cout<<"BRIDGE_CONTEXT_FOREIGN_RESTORED rejected=4 mmio=0 creator_retry=1\n";
          return;
        }
        if(action=="guard-mask" || action=="guard-control" || action=="cancel" ||
           action=="cancel-prepared" || action=="cancel-sealed" || action=="seal-retry") return;
        session->continuation=[&,out,action,source=std::string(source),plan=std::string(plan)] {
        const auto cut=std::stoul(fs::path(source).filename().string().substr(4));
        std::ifstream steps(plan); std::string line; size_t op=0,operations=0,comparisons=0;
        std::ofstream records(out/"boundaries.txt");
        while(!bridge.terminate() && std::getline(steps,line)) {
          if(++op<=cut) continue;
          std::istringstream in(line); std::string kind; uint32_t n; in>>kind;
          if(kind=="SEND") { in>>n; mmio.incoming.push_back(n); continue; }
          if(kind=="PACKET") { while(in>>n) mmio.expected.push_back(n); }
          else require(kind=="TICK","unknown bridge operation");
          mmio.operation=op; mmio.packet_word=0;
          try { bridge.tick(); }
          catch(const bridge_divergence_t &) { require(action=="corrupt","unexpected semantic divergence"); return; }
          require(mmio.incoming.empty() && mmio.expected.empty(),"bridge did not consume complete boundary");
          const auto after=bridge.capture_restricted_context(build);
          save(out/("operation-"+std::to_string(op)+".context"),after.context);
          records<<op<<'\n'; ++operations; comparisons+=17;
        }
        require(action!="corrupt" && bridge.terminate(),"bridge did not terminate or missed semantic corruption");
        std::cout<<"BRIDGE_CONTEXT_CONTINUED operations="<<operations<<" comparisons="<<comparisons
                 <<" words="<<mmio.words<<" exit="<<bridge.exit_code()<<" startup_replays=0 target_edges=0\n";
        };
      } catch(...) { tsi_terminal_fail_allocation_after(-1); failure=std::current_exception(); }
    });
    auto continuation=[&] {
      require(std::this_thread::get_id()==creator_id,"creator reservation changed thread");
      try {
        require(!destroyed && session,"creator lost prepared resource");
        require(!session->guard_live,"publication guard survived launch");
        if(session->published) {
          const auto restored=session->bridge.capture_restricted_context(build);
          require(restored.context==session->expected.context && restored.control==session->expected.control &&
                  restored.metadata==session->expected.metadata && !session->mmio.calls,
                  "live provider changed across launch");
          save(session->out/"launch-readback.context",restored.context);
          save(session->out/"launch-readback.control",restored.control);
          std::cout<<"BRIDGE_CREATOR_LIVE_READBACK owners=17 mmio=0 same_thread=1 target_edges=0\n";
        }
        if(!failure && session->continuation) session->continuation();
      } catch(...) { failure=std::current_exception(); }
    };
    const bool staged=!failure && (action=="restore" || action=="corrupt" || action=="cancel" ||
                                  action=="cancel-prepared" || action=="cancel-sealed" || action.rfind("fatal-",0)==0);
    if(staged) {
      require(session && !session->published && !session->mmio.calls,"TSI published during preparation");
      creator.prepare_launch(continuation);
      creator.prepare_publication([&] {
        require(session->guard_live && !session->published,"unguarded/early TSI publication");
        if(action=="fatal-foreign") {
          std::thread foreign([&] { session->candidate->publish_sealed(); }); foreign.join();
        }
        if(action=="fatal-destination")
          const_cast<checkpoint_owner_t &>(session->bridge.control_owner()).load_checkpoint(session->expected.control);
        // The actual pointer/control publication must succeed with no allocation.
        tsi_terminal_fail_allocation_after(0);
        session->candidate->publish_sealed();
        if(action=="fatal-repeat") session->candidate->publish_sealed();
        tsi_terminal_fail_allocation_after(-1);
        session->readback();
        std::cout<<"BRIDGE_SEALED_PUBLICATION owners=17 same_thread=1 allocation_free=1 guarded=1 target_edges=0\n";
      });
      if(action!="cancel-prepared") {
        creator.seal_launch([&] {
          auto guard=std::make_unique<bridge_publication_guard_t>(*session);
          session->candidate->seal_publication();
          require(!session->published && !session->mmio.calls,"sealing published TSI");
          std::cout<<"BRIDGE_CANDIDATE_SEALED unpublished=1 mmio=0 same_thread=1 target_edges=0\n";
          return guard;
        });
        if(action!="cancel-sealed") creator.publish_prepared();
      }
      const bool cancelled=action=="cancel" || action=="cancel-prepared" || action=="cancel-sealed";
      if(cancelled) {
        const bool published=session->published;
        creator.cancel_reserved();
        require(destroyed,"cancel did not destroy live provider/candidate");
        std::cout<<"BRIDGE_RESERVED_CREATOR_CANCEL same_thread=1 service_calls=0 target_edges=0\n";
        std::cout<<"BRIDGE_STAGED_CANCEL published="<<published<<" provider_destroyed=1 target_edges=0\n";
        return 0;
      }
      require(session->guard_live && session->published,"TSI guard released before controller readback");
      std::cout<<"BRIDGE_CONTROLLER_READBACK guarded=1 owners=17 target_edges=0\n";
      creator.launch_prepared();
    } else creator.launch(continuation);
    creator.join();
    require(destroyed,"provider not destroyed before join");
    if(failure) std::rethrow_exception(failure);
    std::cout<<"BRIDGE_RESERVED_CREATOR same_thread=1 preparation_complete=1 target_edges=0\n";
    return 0;
  } catch(const std::exception &e) { std::cerr<<"FAIL "<<e.what()<<'\n'; return 2; }
}
#ifdef TSI_BRIDGE_CONTEXT_DPI
extern "C" int tsi_bridge_context(const char *m,const char *e,const char *i,const char *b,const char *s,
    const char *p,const char *d,const char *v,const char *h) { return bridge_context_run(m,e,i,b,s,p,d,v,h); }
#else
int main(int argc,char **argv) {
  return argc==10 ? bridge_context_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7],argv[8],argv[9]) : 2;
}
#endif
