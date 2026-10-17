// Observe the real source coroutine and retain its component-only restore ban.
#define TSI_POLLING_SYSCALL_DPI
#include "tsi_polling_syscall_fesvr.cc"
static int outer_run(const char *mode,const char *elf,const char *input,const char *metadata,
                     const char *source,const char *plan,const char *destination) {
  try {
    const fs::path out(destination);fs::create_directories(out);
    sigset_t set;sigemptyset(&set);for(int sig:{SIGINT,SIGTERM,SIGABRT})sigaddset(&set,sig);
    require(!pthread_sigmask(SIG_BLOCK,&set,nullptr),"block signals");
    std::vector<std::string> args{"outer-test","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-syscall-exit","+checkpoint-terminal-input="+std::string(input)};
    const bool flush=fs::path(input).filename().string().find("flush")!=std::string::npos;
    if(flush)args.push_back("+cflush_addr=0x20004000");
    args.insert(args.end(),{"+permissive-off",elf});
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    const auto initial=tsi.host_execution_owner().save_checkpoint();save(out/"new.outer",initial);
    // Both first load-program suspensions still retain the startup stack.
    for(unsigned i=0;i<2;++i){tsi.tick();bool failed=false;
      try{tsi.host_execution_owner().save_checkpoint();}catch(const std::runtime_error &){failed=true;}
      require(failed,"startup stack accepted");}
    firesim_loadmem_t request;std::array<uint8_t,16> data{};
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"program write");
    tsi.recv_loadmem_data(data.data(),16);tsi.tick();
    require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"startup read");
    tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
    require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"startup merge");
    tsi.recv_loadmem_data(data.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
    const auto polling=tsi.host_execution_owner().save_checkpoint();save(out/"polling.outer",polling);
    size_t op=0;std::ifstream f(plan);require(bool(f),"missing plan");std::string line;
    while(std::getline(f,line)) {
      std::istringstream in(line);std::string kind;uint32_t n;in>>kind;
      if(kind=="TICK")tsi.tick();
      else if(kind=="SEND"){in>>n;tsi.send_word(n);}
      else if(kind=="PACKET")while(in>>n)
        require(tsi.data_available() && tsi.recv_word()==n,"production packet mismatch");
      else throw std::runtime_error("unknown outer plan operation");
      require(tsi.host_execution_owner().save_checkpoint()==polling,"outer left polling early");
      ++op;
    }
    require(!tsi.done(),"source stopped before final response");tsi.tick();
    std::vector<uint32_t> final;
    if(flush)final={1,0x20004000,0,1,0,0x80002000,0};
    final.insert(final.end(),{1,0x80002008,0,1,0,1,0});
    for(auto word:final)require(tsi.data_available() && tsi.recv_word()==word,"final response order");
    require(tsi.done() && !tsi.data_available(),"source completion missing");
    const auto returned=tsi.host_execution_owner().save_checkpoint();save(out/"returned.outer",returned);
    const auto life=firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint();
    for(unsigned i=0;i<3;++i){tsi.tick();require(tsi.host_execution_owner().save_checkpoint()==returned &&
        firesim_tsi_htif_lifecycle_t(tsi).save_checkpoint()==life && !tsi.data_available(),"tail repeated service");}
    // Independent metadata/protocol reconstruction keeps the outer caller at
    // startup; it cannot authorize a real context entry or erase this owner.
    firesim_tsi_t fresh(argv.size(),argv.data(),true);
    fresh.prepare_startup_metadata(bytes(metadata));syscall_group_t(fresh).load(load_syscall(source));
    const auto peers=syscall_group_t(fresh).inspect();bool rejected=false;
    try{fresh.tick();}catch(const std::runtime_error &){rejected=true;}
    require(rejected && syscall_group_t(fresh).inspect()==peers &&
      fresh.host_execution_owner().save_checkpoint()==initial,"component restored outer/context implicitly");
    std::cout<<"PRODUCTION_OUTER operations="<<op<<" startup_rejections=2 tail_ticks=3 return="<<tsi.exit_code()
      <<" component_context_rejected=1 target_edges=0\n";return 0;
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HOST_EXECUTION_FESVR_DPI
extern "C" int tsi_outer_fesvr(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return outer_run(m,e,i,b,s,p,d);}
extern "C" void tsi_outer_fesvr_exit(int c){std::exit(c);}
#else
int main(int argc,char **argv){return argc==8?outer_run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]):2;}
#endif
