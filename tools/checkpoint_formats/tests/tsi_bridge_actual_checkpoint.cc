// Fresh restore of the actual production bridge-control image. This does not
// restore FESVR/HTIF, generated bridge RTL or the external loadmem widget.
#include "bridges/tsi_bridge_state.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>
static int restore(const char *image,const char *out,const char *elf,const char *chunk_text) {
  try {
    const unsigned chunk=std::stoul(chunk_text);
    if(chunk!=1 && chunk!=2) throw std::runtime_error("invalid actual bridge beat width");
    std::vector<std::string> args{"firesim_tsi","+permissive","+fesvr-wait-ticks=0",
                                  "+fesvr-step-size=128","+permissive-off",elf};
    widget_checkpoint_config_t config(17,{0,1024,1028,1032,1036,1040,1044,1048,1052,1056,
                                         1,uint64_t(-0x80000000LL),chunk,args.size()});
    for(const auto &arg:args) config.text(arg);
    tsi_bridge_state_t owner(std::move(config),128,2004765,0,false);
    std::ifstream source(image,std::ios::binary);
    if(!source) throw std::runtime_error("missing actual bridge image");
    std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(source),{}};
    const auto sentinel=owner.save_checkpoint();
    try {
      owner.validate_checkpoint(bytes);owner.load_checkpoint(bytes);
    } catch(const std::exception &) {
      if(owner.save_checkpoint()!=sentinel) throw std::runtime_error("partial actual bridge restore");
      throw;
    }
    // No services object exists in this process: restoration cannot perform
    // FESVR construction, MMIO, queue operations, callbacks or target edges.
    const auto readback=owner.save_checkpoint();
    if(readback!=bytes) throw std::runtime_error("incomplete actual bridge zero-edge readback");
    std::filesystem::create_directories(out);
    std::ofstream file(std::filesystem::path(out)/"preedge.owner",std::ios::binary);
    file.write(reinterpret_cast<const char *>(readback.data()),readback.size());
    if(!file) throw std::runtime_error("cannot write actual bridge readback");
    std::cout<<"ACTUAL_BRIDGE_CONTROL_RESTORE words=2 zero_edges=1 service_calls=0\n";return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_BRIDGE_ACTUAL_DPI
extern "C" int tsi_bridge_actual(const char *image,const char *out,const char *elf,const char *chunk) {
  return restore(image,out,elf,chunk);
}
extern "C" void tsi_bridge_actual_exit(int status) {std::exit(status);}
#else
int main(int argc,char **argv) {if(argc!=5) return 2;return restore(argv[1],argv[2],argv[3],argv[4]);}
#endif
