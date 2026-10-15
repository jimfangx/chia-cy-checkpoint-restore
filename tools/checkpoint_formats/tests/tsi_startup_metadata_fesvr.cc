// Actual installed HTIF metadata reconstruction without target services.
#include "tsi_polling_cut_checks.h"
#include "elfloader_resource_checks.h"
#include <array>
static void require(bool b, const char *m) { if (!b) throw std::runtime_error(m); }
static std::vector<uint8_t> read_file(const std::filesystem::path &p) {
  std::ifstream f(p,std::ios::binary);require(bool(f),"missing test image");
  return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
static void write_file(const std::filesystem::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"write failed");
}
static auto peers(firesim_tsi_t &tsi) {
  firesim_tsi_t::polling_cut_t result;
  for (const auto &[name, owner]:std::vector<std::pair<std::string,const checkpoint_owner_t *>>{
    {"program",&tsi.program_loader_owner()},{"init",&tsi.init_accesses_owner()},
    {"host",&tsi.host_control_owner()},{"read",&tsi.serial_read_owner()},
    {"serial",&tsi.serial_queue_owner()},{"loadmem-read",&tsi.loadmem_read_owner()},
    {"loadmem-queues",&tsi.loadmem_queue_owner()}}) result.emplace_back(name,owner->save_checkpoint());
  return result;
}
static void packet(firesim_tsi_t &tsi,std::vector<uint32_t> expected) {
  for (auto word:expected) require(tsi.data_available() && tsi.recv_word()==word,"wrong actual load/poll packet");
  require(!tsi.data_available(),"extra actual packet");
}
static void loader_resources(const char *source) {
  const auto bytes=read_file(source);
  const auto resources=elf_snapshot_resources();
  const auto descriptors=elf_process_descriptors();
  struct memory_t : memif_t {
    memory_t() : memif_t(nullptr) {}
    size_t fail_write=0;
    std::vector<std::pair<addr_t,std::vector<uint8_t>>> writes;
    endianness_t endian=endianness_little;
    void write(addr_t address,size_t size,const void *src) override {
      const auto *p=static_cast<const uint8_t *>(src);
      writes.emplace_back(address,std::vector<uint8_t>(p,p+size));
      if (fail_write==writes.size()) throw std::runtime_error("injected memif write exception");
    }
    endianness_t get_target_endianness() const override { return endian; }
  };
  size_t cases=0;
  for (size_t repetition=0;repetition<32;++repetition) {
    for (const std::string mode : {"xlen32","xlen128","endian","write1","write2","empty","missing","directory","success0","success64","bss"}) {
      {
        auto candidate=mode=="empty" ? std::vector<uint8_t>{} : bytes;
        if (mode=="bss") candidate.at(104)=24; // first PT_LOAD: 16 data bytes, eight zero bytes
        firesim_tsi_elf_snapshot_t snapshot(candidate);
        memory_t mem;
        if (mode=="endian") mem.endian=endianness_big;
        if (mode=="write1") mem.fail_write=1;
        if (mode=="write2") mem.fail_write=2;
        unsigned xlen=mode=="xlen32" ? 32 : mode=="xlen128" ? 128 : mode=="success0" ? 0 : 64;
        reg_t entry=0;
        bool rejected=false;
        const auto path=mode=="missing" ? "/proc/self/fd/not-an-elf-descriptor" : mode=="directory" ? "/proc/self/fd" : snapshot.path();
        try {
          const auto symbols=load_elf(path.c_str(),&mem,&entry,0x80000000,xlen);
          require(entry==0x80000000 && symbols.at("tohost")==0x80002000 && symbols.at("fromhost")==0x80002008,
                  "loader success changed metadata");
          auto expected=std::vector<std::pair<addr_t,std::vector<uint8_t>>>{
            {0x80000000,{0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}}};
          if (mode=="bss") expected.push_back({0x80000010,std::vector<uint8_t>(8,0)});
          expected.push_back({0x80001004,{0x44,0x55,0x66,0x77}});
          require(mem.writes==expected,"loader changed target writes");
        } catch (const incompat_xlen &e) {
          require((mode=="xlen32" || mode=="xlen128") && e.expected_xlen==xlen && e.actual_xlen==64,
                  "loader changed XLEN exception");rejected=true;
        } catch (const std::invalid_argument &) {
          require(mode=="empty" || mode=="missing" || mode=="directory" || mode=="endian","unexpected loader resource error");
          rejected=true;
        } catch (const std::runtime_error &e) {
          require((mode=="write1" || mode=="write2") && std::string(e.what())=="injected memif write exception",
                  "loader swallowed/changed memory exception");rejected=true;
        }
        require(rejected==(mode!="success0" && mode!="success64" && mode!="bss"),"loader wrong error/success outcome");
        if (mode.rfind("xlen",0)==0 || mode=="endian") require(mem.writes.empty(),"loader wrote before compatibility rejection");
      }
      require(elf_snapshot_resources()==resources && elf_process_descriptors()==descriptors,
              "ELF loader leaked descriptor or mapping");
      ++cases;
    }
  }
  std::cout<<"ELF_LOADER_RESOURCES cases="<<cases<<" modes=11 repetitions=32 leaked_descriptors=0 leaked_mappings=0 exact_metadata=1 exact_writes=1\n";
}
static int run(const char *mode,const char *source,const char *image,const char *destination) {
  try {
    std::filesystem::path out(destination);std::filesystem::create_directories(out);
    std::string operation(mode);
    if (operation=="loader-resources") { loader_resources(source); return 0; }
    std::vector<std::string> args{"metadata","+permissive","+no_hart0_msip","+permissive-off",source};
    if(operation=="wrong-args")args.push_back("changed-target-argument");
    if(operation.rfind("unsupported-",0)==0) {
      const std::string suffix=operation.substr(12);
      args.insert(args.begin()+3,suffix=="long" ? "--signature=unused" : "+"+suffix+"=unused");
    }
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),operation!="wrong-loadmem");
    // Exercise the real, nonvirtual installed setter through the base type.
    htif_t &installed = tsi;
    if(operation=="capture") {
      tsi.tick();tsi.tick();
      firesim_loadmem_t request;std::array<uint8_t,16> bytes{};
      require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"wrong ELF write");
      tsi.recv_loadmem_data(bytes.data(),16);tsi.tick();
      require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"wrong ELF merge read");
      tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
      require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"wrong ELF merge write");
      tsi.recv_loadmem_data(bytes.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
      packet(tsi,{0,0x80002000,0,1,0});
      polling_cut_check(tsi,out,"first-poll",true);
      const auto before=tsi.inspect_polling_cut();
      const auto captured=tsi.save_startup_metadata();
      write_file(out/"startup.metadata",captured);
      installed.set_expected_xlen(32);
      const auto resources=elf_snapshot_resources();
      for (size_t i=0;i<32;++i) {
        bool rejected=false;
        try {tsi.save_startup_metadata();} catch(const incompat_xlen &e) {rejected=e.expected_xlen==32 && e.actual_xlen==64;}
        require(rejected && tsi.inspect_polling_cut()==before,"capture missed installed XLEN or changed peers");
        require(elf_snapshot_resources()==resources,"capture XLEN rejection leaked ELF resources");
      }
      installed.set_expected_xlen(64);
      require(tsi.save_startup_metadata()==captured,"compatible installed XLEN changed metadata");
      std::cout<<"INSTALLED_XLEN_CAPTURE_REJECTION expected=32 actual=64 recovered=64 unchanged_components=8\n";
      std::cout<<"ELF_RESOURCE_ATOMIC_REJECTIONS count=32 leaked_descriptors=0 leaked_mappings=0\n";
      require(tsi.inspect_polling_cut()==before,"metadata capture changed caller");
      // Real default syscall PASS, complete through installed HTIF stop().
      tsi.send_word(1);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002000,0,1,0,0,0});
      require(tsi.done() && tsi.exit_code()==0,"actual source did not pass");
      std::cout<<"ACTUAL_METADATA_CAPTURE polling_components=8 source_exit=0\n";
      return 0;
    }
    const auto before=peers(tsi);const auto original=read_file(image);
    auto reject=[&](const std::vector<uint8_t> &candidate) {
      bool failed=false;try {tsi.prepare_startup_metadata(candidate);}catch(const std::runtime_error &){failed=true;}
      require(failed,"invalid metadata admitted");
      require(peers(tsi)==before && tsi.get_tohost_addr()==0 && tsi.get_fromhost_addr()==0 && !tsi.done() && tsi.exit_code()==0,
              "invalid metadata partially restored");
    };
    if(operation=="xlen-recovery") {
      installed.set_expected_xlen(32);
      const auto resources=elf_snapshot_resources();
      for (size_t i=0;i<32;++i) {
        bool rejected=false;
        try {tsi.prepare_startup_metadata(original);}catch(const incompat_xlen &e) {rejected=e.expected_xlen==32 && e.actual_xlen==64;}
        require(rejected && peers(tsi)==before && tsi.get_tohost_addr()==0 && tsi.get_fromhost_addr()==0 && !tsi.done() && tsi.exit_code()==0,
                "installed XLEN rejection partially restored");
        require(elf_snapshot_resources()==resources,"prepare XLEN rejection leaked ELF resources");
      }
      installed.set_expected_xlen(64);
      std::cout<<"ATOMIC_INSTALLED_XLEN_REJECTION expected=32 actual=64 recovered=64 unchanged_components=7 mailboxes=0\n";
      std::cout<<"ELF_RESOURCE_ATOMIC_REJECTIONS count=32 leaked_descriptors=0 leaked_mappings=0\n";
    } else if(operation=="invalid") {
      size_t cases=0;
      for(size_t i=0;i<original.size();++i) {auto bad=original;bad[i]^=1;reject(bad);++cases;}
      for(size_t n=0;n<original.size();++n) {reject({original.begin(),original.begin()+n});++cases;}
      auto bad=original;bad.push_back(0);reject(bad);++cases;
      std::cout<<"ATOMIC_METADATA_REJECTIONS count="<<cases<<" unchanged_components=7 mailboxes=0 context_entries=0\n";
    } else if(operation!="prepare") {
      reject(original);std::cout<<"INCOMPATIBLE_METADATA_REJECTION mode="<<operation<<" unchanged_components=7 mailboxes=0\n";return 0;
    }
    tsi.prepare_startup_metadata(original);
    require(peers(tsi)==before && tsi.get_tohost_addr()==0x80002000 && tsi.get_fromhost_addr()==0x80002008 && !tsi.done() && tsi.exit_code()==0,
            "metadata preparation changed caller/termination");
    const auto readback=tsi.save_startup_metadata();require(readback==original,"incomplete fresh metadata readback");
    write_file(out/"preedge.metadata",readback);
    for (const auto &[name,bytes]:before)write_file(out/("preedge."+name),bytes);
    size_t guards=0;
    try {tsi.tick();}catch(const std::runtime_error &){++guards;}
    try {tsi.prepare_startup_metadata(original);}catch(const std::runtime_error &){++guards;}
    try {tsi.inspect_polling_cut();}catch(const std::runtime_error &){++guards;}
    require(guards==3 && tsi.save_startup_metadata()==original && peers(tsi)==before,"component-only guard failed");
    std::cout<<"COMPLETE_STARTUP_METADATA_READBACK target_edges=0 target_services=0 context_entries=0 unchanged_components=7 guards=3\n";
    return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_METADATA_DPI
extern "C" int tsi_startup_metadata(const char *m,const char *s,const char *i,const char *o) {return run(m,s,i,o);}
extern "C" void tsi_startup_metadata_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=5)return 2;return run(argv[1],argv[2],argv[3],argv[4]);}
#endif
