// Actual installed HTIF metadata reconstruction without target services.
#include "tsi_polling_cut_checks.h"
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
static int run(const char *mode,const char *source,const char *image,const char *destination) {
  try {
    std::filesystem::path out(destination);std::filesystem::create_directories(out);
    std::string operation(mode);
    std::vector<std::string> args{"metadata","+permissive","+no_hart0_msip","+permissive-off",source};
    if(operation=="wrong-args")args.push_back("changed-target-argument");
    if(operation.rfind("unsupported-",0)==0) {
      const std::string suffix=operation.substr(12);
      args.insert(args.begin()+3,suffix=="long" ? "--signature=unused" : "+"+suffix+"=unused");
    }
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
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
      write_file(out/"startup.metadata",tsi.save_startup_metadata());
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
    if(operation=="invalid") {
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
