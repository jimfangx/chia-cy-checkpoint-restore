// Foreign-thread aggregate/transport entries must reject before owner access.
#define TSI_CONTEXT_GROUP_DPI
#include "tsi_context_group_fesvr.cc"
#include "fesvr/tsi_polling_lifecycle.h"
#include <functional>

__attribute__((constructor)) static void access_blocked_inheritance() {
  sigset_t set; sigemptyset(&set);
  for (int sig : {SIGINT, SIGTERM, SIGABRT}) sigaddset(&set, sig);
  if (pthread_sigmask(SIG_BLOCK, &set, nullptr)) std::abort();
}

static int access_run(const char *operation, const char *elf, const char *input,
                      const char *metadata, const char *source, const char *destination) {
  try {
    const std::string op(operation); const fs::path out(destination);
    fs::create_directories(out);
    std::vector<std::string> args{"thread-access", "+permissive", "+no_hart0_msip", "+idle-counts=3",
      "+checkpoint-syscall-exit", "+checkpoint-terminal-input="+std::string(input), "+permissive-off", elf};
    std::vector<char *> argv; for (auto &s : args) argv.push_back(s.data());
    firesim_tsi_t tsi(argv.size(), argv.data(), true); context_group_t group(tsi);
    tsi.prepare_startup_metadata(bytes(metadata)); const auto good = load_context(source);
    auto candidate = group.prepare(good);
    // Capture fixed owner views before aggregate publication. Optional owners
    // become observable only once their real slots have been published.
    const checkpoint_owner_t *retained_serial=&tsi.serial_queue_owner();
    const checkpoint_owner_t *retained_terminal=&tsi.terminal_owner();
    const bool pristine = op.find("prepare") != std::string::npos || op.find("commit") != std::string::npos;
    if (!pristine) { candidate.commit(); if (op == "context-resume-live") group.resume(); }
    const auto before = context_unprepared(tsi);
    const auto initialized = group.native_context_initialized();
    save(out/"before", before);
    if (!pristine) save(out/"aggregate-before", group.inspect());
    const checkpoint_owner_t *retained=nullptr;
    std::string retained_method, retained_schema;
    std::vector<uint8_t> retained_image;
    if(op.rfind("retained-",0)==0) {
      const auto split=op.find('-',9); require(split!=std::string::npos,"missing retained method");
      const auto name=op.substr(9,split-9); retained_method=op.substr(split+1);
      const std::vector<std::pair<std::string,const checkpoint_owner_t *>> owners{
        {"poll",&tsi.htif_poll_owner()}, {"program",&tsi.program_loader_owner()},
        {"init",&tsi.init_accesses_owner()}, {"host",&tsi.host_control_owner()},
        {"read",&tsi.serial_read_owner()}, {"serial",retained_serial},
        {"loadread",&tsi.loadmem_read_owner()}, {"queues",&tsi.loadmem_queue_owner()},
        {"bcd",&tsi.bcd_owner()}, {"terminal",retained_terminal},
        {"identity",&tsi.bcd_identity_owner()}, {"write",&tsi.memif_write_owner()},
        {"memread",&tsi.memif_read_owner()}, {"syscall",&tsi.syscall_exit_owner()},
        {"outer",&tsi.host_execution_owner()}, {"wrapper",&tsi.host_wrapper_owner()}};
      for(const auto &[key,owner]:owners)if(key==name)retained=owner;
      require(retained,"unknown retained owner");
      require(retained_serial==&tsi.serial_queue_owner() && retained_terminal==&tsi.terminal_owner(),
              "view identity changed across publication");
      retained_schema=retained->checkpoint_schema(); retained_image=retained->save_checkpoint();
      save(out/"retained.image",retained_image);
    }
    const images_t host_images(good.begin(), good.begin()+15), syscall_images(good.begin(),good.begin()+14),
                   polling_images(good.begin(),good.begin()+12);
    using host_candidate_t = firesim_tsi_host_group_t::prepared_t;
    using syscall_candidate_t = firesim_tsi_polling_syscall_t::prepared_t;
    using polling_candidate_t = firesim_tsi_t::prepared_polling_components_t;
    // Destinations outlive their prepared candidates, including after commit.
    std::unique_ptr<firesim_tsi_t> host_destination, syscall_destination;
    std::unique_ptr<firesim_tsi_t> ordinary_source, ordinary_destination;
    std::unique_ptr<host_candidate_t> host_candidate;
    std::unique_ptr<syscall_candidate_t> syscall_candidate;
    std::unique_ptr<polling_candidate_t> polling_candidate;
    images_t host_before, syscall_before, syscall_supported;
    if (op == "host-commit") {
      host_destination = std::make_unique<firesim_tsi_t>(argv.size(), argv.data(), true);
      host_destination->prepare_startup_metadata(bytes(metadata));
      host_before = context_unprepared(*host_destination); save(out/"host-before", host_before);
      save(out/"host-source", host_images);
      host_candidate.reset(new host_candidate_t(firesim_tsi_host_group_t(*host_destination).prepare(host_images)));
    }
    if (op == "syscall-commit") {
      // The fourteen-owner API excludes completed stop/return state. Its own
      // prepared candidate uses the supported execution cut at both outer
      // boundaries, rather than weakening that parent admission rule.
      const auto execution = load_context(fs::path(source).parent_path()/"cut-6");
      syscall_supported.assign(execution.begin(), execution.begin()+14);
      syscall_destination = std::make_unique<firesim_tsi_t>(argv.size(), argv.data(), true);
      syscall_destination->prepare_startup_metadata(bytes(metadata));
      syscall_before = context_unprepared(*syscall_destination); save(out/"syscall-before", syscall_before);
      save(out/"syscall-source", syscall_supported);
      syscall_candidate.reset(new syscall_candidate_t(firesim_tsi_polling_syscall_t(*syscall_destination).prepare(syscall_supported)));
    }
    // The public twelve-owner candidate deliberately excludes restricted
    // syscall mode. Exercise its real commit on a separate ordinary sealed
    // source/destination, preserving that production admission rule.
    images_t ordinary_images, ordinary_before;
    if (op == "polling-commit") {
      auto ordinary_args = args;
      ordinary_args.erase(std::find(ordinary_args.begin(), ordinary_args.end(), "+checkpoint-syscall-exit"));
      std::vector<char *> ordinary_argv; for (auto &s : ordinary_args) ordinary_argv.push_back(s.data());
      ordinary_source = std::make_unique<firesim_tsi_t>(ordinary_argv.size(), ordinary_argv.data(), true);
      syscall_startup(*ordinary_source);
      ordinary_images = ordinary_source->inspect_polling_cut();
      ordinary_destination = std::make_unique<firesim_tsi_t>(ordinary_argv.size(), ordinary_argv.data(), true);
      ordinary_destination->prepare_startup_metadata(ordinary_source->save_startup_metadata());
      ordinary_before = peers(*ordinary_destination);
      save(out/"ordinary-before", ordinary_before); save(out/"ordinary-source", ordinary_images);
      polling_candidate.reset(new polling_candidate_t(ordinary_destination->prepare_polling_components_candidate(ordinary_images)));
    }
    std::string reason;
    auto action = [&] {
      firesim_loadmem_t request; uint64_t value = 0;
      if(retained) {
        if(retained_method=="schema")retained->checkpoint_schema();
        else if(retained_method=="save")retained->save_checkpoint();
        else if(retained_method=="validate")retained->validate_checkpoint(retained_image);
        else if(retained_method=="load")const_cast<checkpoint_owner_t *>(retained)->load_checkpoint(retained_image);
        else if(retained_method=="invalid-load")const_cast<checkpoint_owner_t *>(retained)->load_checkpoint({});
        else throw std::runtime_error("unknown retained checkpoint method");
      }
      else if (op == "context-prepare") { auto next = group.prepare(good); }
      else if (op == "context-prepare-invalid") { auto next = group.prepare({}); }
      else if (op == "context-commit") candidate.commit();
      else if (op == "context-capture") group.inspect();
      else if (op == "context-initialized") group.native_context_initialized();
      else if (op == "context-resume-fresh" || op == "context-resume-live") group.resume();
      else if (op == "host-prepare") { auto next = firesim_tsi_host_group_t(tsi).prepare(host_images); }
      else if (op == "host-commit") host_candidate->commit();
      else if (op == "host-capture") firesim_tsi_host_group_t(tsi).inspect();
      else if (op == "host-advance") firesim_tsi_host_group_t(tsi).advance();
      else if (op == "syscall-prepare") { auto next = firesim_tsi_polling_syscall_t(tsi).prepare(syscall_images); }
      else if (op == "syscall-commit") syscall_candidate->commit();
      else if (op == "syscall-capture") firesim_tsi_polling_syscall_t(tsi).inspect();
      else if (op == "syscall-advance") firesim_tsi_polling_syscall_t(tsi).advance();
      else if (op == "polling-prepare") { auto next = tsi.prepare_polling_components_candidate(polling_images); }
      else if (op == "polling-commit") polling_candidate->commit();
      else if (op == "polling-capture") tsi.inspect_prepared_polling_components();
      else if (op == "polling-advance") tsi.advance_prepared_polling_components();
      else if (op == "exit-prepare") { auto next = firesim_tsi_polling_lifecycle_t(tsi).prepare({}); }
      else if (op == "exit-capture") firesim_tsi_polling_lifecycle_t(tsi).inspect();
      else if (op == "exit-completed") firesim_tsi_polling_lifecycle_t(tsi).inspect_completed_exit();
      else if (op == "serial-send") tsi.send_word(0xface);
      else if (op == "serial-recv") tsi.recv_word();
      else if (op == "serial-front") tsi.in_bits();
      else if (op == "serial-available") tsi.data_available();
      else if (op == "serial-valid") tsi.in_valid();
      else if (op == "serial-ready") tsi.out_ready();
      else if (op == "serial-owner") tsi.serial_queue_owner();
      else if (op == "wrapper-owner") tsi.host_wrapper_owner();
      else if (op == "host-tick") tsi.tick();
      else if (op == "host-switch") tsi.switch_to_host();
      else if (op == "host-busy") tsi.busy();
      else if (op == "host-loaded") tsi.loaded_in_host();
      else if (op == "host-set-loaded") tsi.set_loaded_in_target(true);
      else if (op == "loadmem-send") tsi.send_loadmem_word(0xface);
      else if (op == "loadmem-read-request") tsi.recv_loadmem_read_req(request);
      else if (op == "loadmem-write-request") tsi.recv_loadmem_write_req(request);
      else if (op == "loadmem-data") tsi.recv_loadmem_data(&value, sizeof(value));
      else if (op == "loadmem-available") tsi.has_loadmem_reqs();
      else if (op == "memory-read") tsi.read_chunk(0, sizeof(value), &value);
      else if (op == "memory-write") tsi.write_chunk(0, sizeof(value), &value);
      else if (op == "memory-interface") tsi.memif();
      else if (op == "metadata-save") tsi.save_startup_metadata();
      else if (op == "metadata-prepare") tsi.prepare_startup_metadata({});
      else throw std::runtime_error("unknown thread access operation");
    };
    // The foreign thread stays parked through creator readback and retry.
    // Its entry must fail using immutable ownership before touching any owner.
    std::promise<void> parked, release; auto done = release.get_future();
    std::thread worker([&] {
      try { action(); } catch (const std::runtime_error &e) { reason = e.what(); }
      parked.set_value(); done.wait();
    });
    parked.get_future().wait();
    try {
      require(reason == "TSI access requires its live original thread", ("foreign access was not rejected before owner access: "+reason).c_str());
      require(context_unprepared(tsi) == before && group.native_context_initialized() == initialized,
              "foreign access changed owners/context");
      save(out/"after", context_unprepared(tsi));
      if (host_candidate) {
        require(context_unprepared(*host_destination) == host_before, "foreign host commit changed peers");
        save(out/"host-after", context_unprepared(*host_destination)); host_candidate->commit();
        require(firesim_tsi_host_group_t(*host_destination).inspect() == host_images, "original host candidate retry differs");
        save(out/"host-retry", firesim_tsi_host_group_t(*host_destination).inspect());
      }
      if (syscall_candidate) {
        require(context_unprepared(*syscall_destination) == syscall_before, "foreign syscall commit changed peers");
        save(out/"syscall-after", context_unprepared(*syscall_destination)); syscall_candidate->commit();
        require(firesim_tsi_polling_syscall_t(*syscall_destination).inspect() == syscall_supported,
                "original syscall candidate retry differs");
        save(out/"syscall-retry", firesim_tsi_polling_syscall_t(*syscall_destination).inspect());
      }
      if (polling_candidate) {
        require(peers(*ordinary_destination) == ordinary_before, "foreign polling commit changed ordinary peers");
        save(out/"ordinary-after", peers(*ordinary_destination));
        polling_candidate->commit();
        require(ordinary_destination->inspect_prepared_polling_components() == ordinary_images,
                "original ordinary polling candidate retry differs");
        save(out/"ordinary-retry", ordinary_destination->inspect_prepared_polling_components());
      }
      if (pristine) { candidate.commit(); require(group.inspect() == good, "creator commit retry differs"); }
      else {
        save(out/"aggregate-after", group.inspect());
        if(retained) {
          require(retained->checkpoint_schema()==retained_schema && retained->save_checkpoint()==retained_image,
                  "foreign retained access changed owner");
          if(retained_method=="invalid-load") {
            bool rejected=false;try{action();}catch(const std::runtime_error &){rejected=true;}
            require(rejected,"creator accepted invalid retained image");
          } else action();
          require(group.inspect()==good,"retained creator retry changed aggregate");
          save(out/"retained-retry.image",retained->save_checkpoint());
        }
        if (op == "context-resume-fresh" || op == "context-resume-live") group.resume();
      }
      save(out/"retry", group.inspect());
    } catch (...) { release.set_value(); worker.join(); throw; }
    release.set_value(); worker.join();
    std::ofstream(out/"rejection.txt") << reason << '\n';
    std::cout << "THREAD_ACCESS operation=" << op << " rejected=1 unchanged=1 retry=1 initialized=" << initialized
              << " foreign_services=0 target_edges=0\n";
    return 0;
  } catch (const std::exception &e) { std::cerr << "FAIL " << e.what() << '\n'; return 2; }
}
#ifdef TSI_THREAD_ACCESS_DPI
extern "C" int tsi_thread_access(const char *o, const char *e, const char *i,
  const char *m, const char *s, const char *d) { return access_run(o,e,i,m,s,d); }
#else
int main(int argc, char **argv) { return argc == 7 ? access_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6]) : 2; }
#endif
