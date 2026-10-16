// Twelve-owner preparation failures and semantic faults at active HTIF dispatch.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
namespace fs = std::filesystem;
using images_t = firesim_tsi_t::polling_cut_t;
static const std::array<const char *,12> names{{"poll","program","init","host","read","serial",
  "loadmem-read","loadmem-queues","bcd","terminal","identity","write"}};
static void require(bool ok,const char *s){if(!ok)throw std::runtime_error(s);}
static auto bytes(const fs::path &p){std::ifstream f(p,std::ios::binary);require(bool(f),"missing image");return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});}
static auto load(const fs::path &p){images_t out;for(auto n:names)out.emplace_back(n,bytes(p.string()+"."+n));return out;}
static uint64_t word(const std::vector<uint8_t> &b,size_t at){uint64_t n=0;for(unsigned i=0;i<8;++i)n|=uint64_t(b.at(at+i))<<(8*i);return n;}
static void put(std::vector<uint8_t> &b,size_t at,uint64_t n){for(unsigned i=0;i<8;++i)b.at(at+i)=n>>(8*i);}
static auto peers(const firesim_tsi_t &t){images_t out;for(const auto &[n,o]:std::vector<std::pair<std::string,const checkpoint_owner_t *>>{
  {"program",&t.program_loader_owner()},{"init",&t.init_accesses_owner()},{"host",&t.host_control_owner()},
  {"read",&t.serial_read_owner()},{"serial",&t.serial_queue_owner()},{"loadmem-read",&t.loadmem_read_owner()},
  {"loadmem-queues",&t.loadmem_queue_owner()},{"terminal",&t.terminal_owner()},
  {"identity",&t.bcd_identity_owner()},{"write",&t.memif_write_owner()}})out.emplace_back(n,o->save_checkpoint());return out;}
static void save(const fs::path &out,const images_t &images){for(const auto &[n,b]:images){std::ofstream f(out.string()+"."+n,std::ios::binary);f.write(reinterpret_cast<const char *>(b.data()),b.size());require(bool(f),"readback failed");}}
extern void tsi_terminal_fail_allocation_after(long);
static void atomic(firesim_tsi_t &t,const images_t &good,const fs::path &out){
  const auto before=peers(t);const auto metadata=t.save_startup_metadata();
  auto unchanged=[&]{require(peers(t)==before && t.save_startup_metadata()==metadata && !t.done(),"partial polling publication");
    for(unsigned i=0;i<2;++i){bool absent=false;try{if(i)t.bcd_owner();else t.htif_poll_owner();}catch(const std::runtime_error &){absent=true;}require(absent,"published parent/device after rejection");}};
  size_t membership=0,malformed=0,cross=0;
  auto reject=[&](const images_t &bad){bool failed=false;try{t.prepare_polling_components(bad);}catch(const std::runtime_error &){failed=true;}require(failed,"invalid dispatch cut accepted");unchanged();};
  reject({});++membership;
  for(size_t i=0;i<good.size();++i){
    auto bad=good;bad.erase(bad.begin()+i);reject(bad);++membership;
    bad=good;bad.push_back(good[i]);reject(bad);++membership;
    bad=good;bad[i].first="unknown";reject(bad);++membership;
    bad=good;std::swap(bad[i],bad[(i+1)%good.size()]);reject(bad);++membership;
    for(size_t n=0;n<good[i].second.size();++n){bad=good;bad[i].second.resize(n);reject(bad);++malformed;}
    bad=good;bad[i].second.push_back(0);reject(bad);++malformed;
    bad=good;bad[i].second[0]^=1;reject(bad);++malformed;
  }
  require(word(good[0].second,56)==3 && word(good[10].second,72)==1,"not an active dispatch test");
  // Each parent replacement and child group below is independently parseable.
  const auto command=word(good[0].second,64);
  for(unsigned i=0;i<13;++i){auto bad=good;
    if(i==0)put(bad[0].second,64,command^1); // exact parent/caller command
    if(i==1){put(bad[10].second,80,command^1);} // copied payload/selector relation
    if(i==2){firesim_tsi_memif_write_t w;firesim_tsi_serial_state_t q;firesim_tsi_bcd_identity_t c(w,q);
      bad[10].second=c.save_checkpoint();bad[11].second=w.save_checkpoint();}
    if(i==3){put(bad[0].second,56,1);put(bad[0].second,64,0);} // reader parent with active writer
    if(i==4){auto &b=bad[4].second;put(b,64,2);put(b,72,0x80002000);put(b,80,8);} // two active readers
    if(i==5 || i==6){firesim_tsi_memif_write_t w;bad[11].second=w.save_checkpoint();put(bad[10].second,72,i==5?2:3);}
    if(i==7){firesim_tsi_memif_write_t w;firesim_tsi_serial_state_t q;firesim_tsi_bcd_identity_t c(w,q);c.begin(command);
      bad[10].second=c.save_checkpoint();bad[11].second=w.save_checkpoint();} // not yet a yield
    if(i==8)put(bad[1].second,bad[1].second.size()-8,2);
    if(i==9){put(bad[2].second,bad[2].second.size()-24,0);put(bad[2].second,bad[2].second.size()-16,0);}
    if(i==10)put(bad[3].second,bad[3].second.size()-8,2);
    if(i==11){firesim_loadmem_read_t r;r.begin(0x80000000,8);bad[6].second=r.save_checkpoint();}
    if(i==12){firesim_loadmem_queues_t q;q.push_response(3);bad[7].second=q.save_checkpoint();}
    reject(bad);++cross;
  }
  long failures=0;
  for(;;++failures){bool exhausted=false;tsi_terminal_fail_allocation_after(failures);
    try{t.prepare_polling_components(good);}catch(const std::bad_alloc &){exhausted=true;}
    catch(...){tsi_terminal_fail_allocation_after(-1);throw;}tsi_terminal_fail_allocation_after(-1);
    if(!exhausted)break;unchanged();}
  require(failures>=30 && t.inspect_prepared_polling_components()==good,"incomplete dispatch preparation");
  save(out/"preedge",t.inspect_prepared_polling_components());
  std::cout<<"DISPATCH_ATOMIC membership="<<membership<<" malformed="<<malformed<<" cross="<<cross
           <<" allocation_failures="<<failures<<" unchanged=1 owners=12 context_entries=0 target_edges=0\n";
}
static int run(const char *mode,const char *elf,const char *input,const char *metadata,const char *source,const char *plan,const char *destination){
 try{fs::path out(destination);fs::create_directories(out);
  std::vector<std::string> args{"dispatch","+permissive","+no_hart0_msip","+idle-counts=3","+checkpoint-terminal-input="+std::string(input),"+permissive-off",elf};
  std::vector<char *> argv;for(auto &a:args)argv.push_back(a.data());firesim_tsi_t t(argv.size(),argv.data(),true);
  t.prepare_startup_metadata(bytes(metadata));const auto good=load(source);
  if(std::string(mode)=="invalid"){atomic(t,good,out);return 0;}
  auto altered=good;
  if(std::string(mode)=="merge-corrupt"){
    const auto size=word(altered[11].second,88);const auto offset=104+size+96;
    require(word(altered[11].second,104+size+88)==1,"no retained merge word");
    altered[11].second.at(offset)^=1; // real preserved neighboring byte, outside copied identity
  }else if(std::string(mode)=="command-corrupt"){
    // Change command selector and the child's owned payload coherently. Image
    // remains valid; execution must expose the changed identity bytes.
    require((word(altered[10].second,80)&255)==0,"wrong selector corruption cut");
    put(altered[0].second,64,word(altered[0].second,64)^2);
    put(altered[10].second,80,word(altered[10].second,80)^2);
    for(size_t i=0;i<64;++i)altered[11].second.at(96+i)=0;
  }else throw std::runtime_error("unknown dispatch mode");
  t.prepare_polling_components(altered);require(t.inspect_prepared_polling_components()==altered,"fault load/readback differs");
  save(out/"preedge",t.inspect_prepared_polling_components());
  const auto cut=std::stoul(fs::path(source).filename().string().substr(4));
  std::ifstream steps(plan);std::string line;size_t operation=0;
  while(std::getline(steps,line)){if(++operation<=cut)continue;std::istringstream in(line);std::string op;uint64_t n;in>>op;
    if(op=="TICK")t.advance_prepared_polling_components();
    else if(op=="SEND"){in>>n;t.send_word(n);}
    else if(op=="PACKET"){size_t index=0;while(in>>n){require(t.data_available(),"missing restored request");
      if(t.in_bits()!=n){std::cout<<"FIRST_DIVERGENCE operation="<<operation<<" request_word="<<index<<" expected="<<n<<" actual="<<t.in_bits()<<" acknowledged=0 owners=12 context_entries=0\n";
        require(t.in_bits()!=n,"divergence was consumed");return 0;}
      require(t.recv_word()==n,"request changed");++index;}}
    else throw std::runtime_error("unknown plan operation");
  }throw std::runtime_error("semantic corruption did not diverge");
 }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_POLLING_PREPARE_DPI
extern "C" int tsi_polling_prepare(const char *m,const char *e,const char *i,const char *b,const char *s,const char *p,const char *d){return run(m,e,i,b,s,p,d);}
extern "C" void tsi_polling_prepare_exit(int code){std::exit(code);}
#else
int main(int argc,char **argv){if(argc!=8)return 2;return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6],argv[7]);}
#endif
