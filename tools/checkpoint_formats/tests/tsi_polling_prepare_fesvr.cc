// Fresh preparation of all ten known polling components. No CPU/context resume.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <fcntl.h>
#include <unistd.h>
namespace fs = std::filesystem;
using images_t = firesim_tsi_t::polling_cut_t;
static const std::array<const char *, 10> names{{"poll","program","init","host","read",
  "serial","loadmem-read","loadmem-queues","bcd","terminal"}};
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static auto bytes(const fs::path &p) {
  std::ifstream f(p,std::ios::binary); require(bool(f),"missing image");
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
}
static void save(const fs::path &p,const std::vector<uint8_t> &b) {
  std::ofstream f(p,std::ios::binary); f.write(reinterpret_cast<const char *>(b.data()),b.size());
  require(bool(f),"cannot save readback");
}
static auto load(const fs::path &p) {
  images_t result; for (auto name:names) result.emplace_back(name,bytes(p.string()+"."+name));
  return result;
}
static void save(const fs::path &p,const images_t &images) {
  for (const auto &[name,b]:images) save(p.string()+"."+name,b);
}
static auto peers(const firesim_tsi_t &tsi) {
  images_t result;
  for (const auto &[name,owner]:std::vector<std::pair<std::string,const checkpoint_owner_t *>>{
      {"program",&tsi.program_loader_owner()},{"init",&tsi.init_accesses_owner()},
      {"host",&tsi.host_control_owner()},{"read",&tsi.serial_read_owner()},
      {"serial",&tsi.serial_queue_owner()},{"loadmem-read",&tsi.loadmem_read_owner()},
      {"loadmem-queues",&tsi.loadmem_queue_owner()},{"terminal",&tsi.terminal_owner()}})
    result.emplace_back(name,owner->save_checkpoint());
  return result;
}
static void packet(firesim_tsi_t &tsi,std::initializer_list<uint32_t> expected) {
  for (auto n:expected) require(tsi.data_available() && tsi.recv_word()==n,"unexpected startup packet");
  require(!tsi.data_available(),"extra startup packet");
}
static void continue_components(firesim_tsi_t &tsi,const std::string &mode,const fs::path &source,
                                const char *plan,const fs::path &out) {
  if(mode=="unsupported" || mode=="exit-guard") {
    // At cut zero there is exactly one pending tohost request. Drain it as
    // the transport would; no unsupported command may enqueue its clear.
    while(tsi.data_available()) tsi.recv_word();
    const auto before=tsi.terminal_owner().save_checkpoint();
    if(mode=="exit-guard") tsi.htif_exit(0);
    else {
      std::ifstream f(plan);uint64_t command=0;f>>command;require(bool(f),"missing unsupported command");
      tsi.send_word(command);tsi.send_word(command>>32);
    }
    bool rejected=false;
    try {tsi.advance_prepared_polling_components();}catch(const std::runtime_error &){rejected=true;}
    require(rejected && !tsi.data_available() && tsi.terminal_owner().save_checkpoint()==before,
            "unowned command was acknowledged or changed the terminal");
    for(unsigned op=0;op<3;++op) {
      rejected=false;
      try {if(op==0)tsi.advance_prepared_polling_components();else if(op==1)tsi.tick();
        else if(mode=="unsupported")tsi.inspect_prepared_polling_components();else tsi.advance_prepared_polling_components();}
      catch(const std::runtime_error &){rejected=true;}
      require(rejected,"unowned/poisoned caller resumed");
    }
    std::cout<<"UNOWNED_REJECTED clear_packets=0 terminal_unchanged=1 reentry_guards=3 context_entries=0\n";
    return;
  }
  const auto cut=std::stoul(source.filename().string().substr(4));
  const bool corrupt=mode=="corrupt";
  if(corrupt) {
    auto image=tsi.terminal_owner().save_checkpoint();
    // The independently configured three-byte input is followed by its cursor.
    require(image.size()>=75,"missing terminal cursor");image.at(59)=1;
    const_cast<checkpoint_owner_t &>(tsi.terminal_owner()).load_checkpoint(image);
  }
  std::ofstream readbacks(out/"continuation.bin",std::ios::binary);
  std::ifstream steps(plan);require(bool(steps),"missing continuation plan");
  size_t operation=0,readback_count=0;std::string line;
  const auto metadata=tsi.save_startup_metadata();
  while(std::getline(steps,line)) {
    if(++operation<=cut)continue;
    std::istringstream in(line);std::string op;uint64_t n=0;in>>op;
    if(op=="TICK")tsi.advance_prepared_polling_components();
    else if(op=="SEND") {in>>n;tsi.send_word(n);}
    else if(op=="PACKET") {
      size_t index=0;
      while(in>>n) {
        require(tsi.data_available(),"missing continuation request");
        if(tsi.in_bits()!=n) {
          require(corrupt && operation==21 && index==5 && n==321 && tsi.in_bits()==256,
                  "unexpected first request divergence");
          const auto divergent=tsi.in_bits();
          require(tsi.in_bits()==divergent,"divergent request acknowledged");
          std::cout<<"FIRST_DIVERGENCE operation="<<operation<<" request_word="<<index
                   <<" expected="<<n<<" actual="<<divergent<<" acknowledged=0 context_entries=0\n";
          return;
        }
        require(tsi.recv_word()==n,"request changed during service");++index;
      }
    } else throw std::runtime_error("unknown continuation operation");
    const auto actual=tsi.inspect_prepared_polling_components();
    if(!corrupt)require(actual==load(source.parent_path()/("cut-"+std::to_string(operation))),
                        "continuation owner mismatch");
    require(tsi.save_startup_metadata()==metadata && !tsi.done(),"continuation changed startup/exit state");
    for(const auto &[name,image]:actual)readbacks.write(reinterpret_cast<const char *>(image.data()),image.size());
    ++readback_count;
    bool rejected=false;try {tsi.tick();}catch(const std::runtime_error &){rejected=true;}
    require(rejected && tsi.inspect_prepared_polling_components()==actual,"component enabled context entry");
  }
  require(!corrupt && bool(readbacks),"corruption was not detected or incomplete readback");
  std::cout<<"CONTINUATION operations="<<readback_count<<" complete_owner_readbacks="<<10*readback_count
           <<" startup_replays=0 target_edges=0 context_entries=0\n";
}
extern void tsi_terminal_fail_allocation_after(long);
static void rejection(firesim_tsi_t &tsi,const images_t &good,const fs::path &out) {
  const auto before=peers(tsi);
  const auto metadata=tsi.save_startup_metadata();
  auto unchanged=[&] {
    require(peers(tsi)==before && tsi.save_startup_metadata()==metadata && !tsi.done(),
            "polling preparation partially published state");
    bool absent=false; try { tsi.htif_poll_owner(); } catch(const std::runtime_error &) { absent=true; }
    require(absent,"polling preparation published a caller on failure");
  };
  size_t malformed=0,membership=0,cross=0;
  auto reject=[&](const images_t &bad) {
    bool failed=false; try { tsi.prepare_polling_components(bad); }
    catch(const std::runtime_error &) { failed=true; }
    require(failed,"invalid polling preparation accepted"); unchanged();
  };
  reject({}); ++membership;
  for(size_t i=0;i<good.size();++i) {
    auto bad=good; bad.erase(bad.begin()+i); reject(bad); ++membership;
    bad=good; bad.push_back(good[i]); reject(bad); ++membership;
    bad=good; bad[i].first="unknown"; reject(bad); ++membership;
    bad=good; bad[i]=good[(i+1)%good.size()]; reject(bad); ++membership;
    bad=good; std::swap(bad[i],bad[(i+1)%good.size()]); reject(bad); ++membership;
    for(size_t n=0;n<good[i].second.size();++n) {
      bad=good; bad[i].second.resize(n); reject(bad); ++malformed;
    }
    bad=good; bad[i].second.push_back(0); reject(bad); ++malformed;
    bad=good; bad[i].second[0]^=1; reject(bad); ++malformed;
  }
  auto put=[](std::vector<uint8_t> &b,size_t at,uint64_t n) {
    for(unsigned i=0;i<8;++i)b.at(at+i)=n>>(8*i);
  };
  // Each replacement is component-valid; the caller/child relation is not.
  for(unsigned which=0;which<11;++which) {
    auto bad=good;
    if(which==0) put(bad[1].second,bad[1].second.size()-8,2);
    if(which==1) {put(bad[2].second,bad[2].second.size()-24,0);put(bad[2].second,bad[2].second.size()-16,0);}
    if(which==2 || which==3) put(bad[3].second,bad[3].second.size()-8,which==2?2:4);
    if(which==4) put(bad[4].second,72,0x80002008);
    if(which==5) put(bad[4].second,80,16);
    if(which==6) {put(bad[0].second,56,4);put(bad[0].second,64,0);}
    if(which==7) {firesim_loadmem_read_t read;read.begin(0x80000000,8);bad[6].second=read.save_checkpoint();}
    if(which==8) {firesim_loadmem_queues_t queues;queues.push_response(23);bad[7].second=queues.save_checkpoint();}
    if(which==9) put(bad[0].second,40,0x80002010); // incompatible actual mailbox
    if(which==10) put(bad[0].second,48,8); // incompatible actual queue limit
    reject(bad); ++cross;
  }
  long failures=0;
  for(;;++failures) {
    bool exhausted=false; tsi_terminal_fail_allocation_after(failures);
    try { tsi.prepare_polling_components(good); }
    catch(const std::bad_alloc &) { exhausted=true; }
    catch(...) { tsi_terminal_fail_allocation_after(-1); throw; }
    tsi_terminal_fail_allocation_after(-1);
    if(!exhausted) break;
    unchanged();
  }
  require(failures>=30,"allocation injection missed aggregate preparation");
  require(tsi.inspect_prepared_polling_components()==good,"incomplete preparation after rejection");
  save(out/"preedge",tsi.inspect_prepared_polling_components());
  std::cout<<"PREPARATION_ATOMIC malformed="<<malformed<<" membership="<<membership<<" cross="<<cross
           <<" allocation_failures="<<failures<<" unchanged_on_failure=1 context_entries=0 target_edges=0\n";
}
static int run(const char *mode,const char *elf,const char *input,const char *metadata,
               const char *source,const char *plan,const char *destination) {
  try {
    fs::path out(destination); fs::create_directories(out);
    std::vector<std::string> args{"polling-prepare","+permissive","+no_hart0_msip","+idle-counts=3",
      "+checkpoint-terminal-input="+std::string(input),"+permissive-off",elf};
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);
    if(std::string(mode)=="capture") {
      tsi.tick();tsi.tick();firesim_loadmem_t request;std::array<uint8_t,16> data{};
      require(tsi.recv_loadmem_write_req(request) && request.addr==0x80000000 && request.size==16,"ELF write differs");
      tsi.recv_loadmem_data(data.data(),16);tsi.tick();
      require(tsi.recv_loadmem_read_req(request) && request.addr==0x80001000 && request.size==8,"ELF read differs");
      tsi.send_loadmem_word(0xaabbccdd);tsi.send_loadmem_word(0x11223344);tsi.tick();
      require(tsi.recv_loadmem_write_req(request) && request.addr==0x80001000 && request.size==8,"ELF merge differs");
      tsi.recv_loadmem_data(data.data(),8);tsi.set_loaded_in_target(true);tsi.tick();
      const auto meta=tsi.save_startup_metadata();save(out/"startup.metadata",meta);
      save(out/"cut-0",tsi.inspect_polling_cut());
      std::ifstream steps(plan);require(bool(steps),"missing capture plan");
      std::string line;size_t cut=0;
      // Keep target-visible binary output separate from diagnostic messages.
      const int previous=dup(1),fd=open((out/"output.bin").c_str(),O_CREAT|O_EXCL|O_WRONLY,0600);
      require(previous>=0 && fd>=0 && dup2(fd,1)==1,"cannot redirect source output");close(fd);
      while(std::getline(steps,line)) {
        std::istringstream in(line);std::string op;uint64_t n=0;in>>op;
        if(op=="TICK") tsi.tick();
        else if(op=="SEND") {in>>n;tsi.send_word(n);}
        else if(op=="PACKET") {while(in>>n) require(tsi.data_available() && tsi.recv_word()==n,"capture packet differs");}
        else throw std::runtime_error("unknown capture operation");
        save(out/("cut-"+std::to_string(++cut)),tsi.inspect_polling_cut());
        require(tsi.save_startup_metadata()==meta,"capture changed startup binding");
      }
      tsi.send_word(1);tsi.send_word(0);tsi.tick();packet(tsi,{1,0x80002000,0,1,0,0,0});
      require(tsi.done() && tsi.exit_code()==0,"source HTIF did not exit");
      require(dup2(previous,1)==1,"cannot restore stdout");close(previous);
      std::cout<<"CAPTURE cuts="<<cut+1<<" owners=10 source_exit=0 cpu_edges=0\n";
      return 0;
    }
    const auto good=load(source);
    const auto before=peers(tsi);
    bool rejected=false;try { tsi.prepare_polling_components(good); } catch(const std::runtime_error &) {rejected=true;}
    require(rejected && peers(tsi)==before,"unprepared metadata accepted polling state");
    tsi.prepare_startup_metadata(bytes(metadata));
    if(std::string(mode)=="invalid") {rejection(tsi,good,out);return 0;}
    tsi.prepare_polling_components(good);
    const auto actual=tsi.inspect_prepared_polling_components();
    require(actual==good && !tsi.done(),"incomplete polling component readback");
    save(out/"preedge",actual);save(out/"preedge.metadata",tsi.save_startup_metadata());
    if(std::string(mode)=="continue" || std::string(mode)=="corrupt" ||
       std::string(mode)=="unsupported" || std::string(mode)=="exit-guard") {
      continue_components(tsi,mode,source,plan,out);return 0;
    }
    size_t guards=0;
    for(unsigned op=0;op<5;++op) {
      bool failed=false;
      try {if(op==0)tsi.tick();else if(op==1)tsi.prepare_polling_components(good);
        else if(op==2)tsi.inspect_polling_cut();else if(op==3)tsi.load_initialization_checkpoint({});
        else tsi.prepare_startup_metadata(bytes(metadata));}
      catch(const std::runtime_error &) {failed=true;}
      require(failed && tsi.inspect_prepared_polling_components()==actual,"prepared caller entered or changed a peer");++guards;
    }
    std::cout<<"PREPARATION_READBACK owners=10 target_edges=0 target_services=0 context_entries=0 guards="<<guards<<'\n';
    return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_POLLING_PREPARE_DPI
extern "C" int tsi_polling_prepare(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d) {
  return run(m,e,i,b,s,p,d);
}
extern "C" void tsi_polling_prepare_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=8)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
