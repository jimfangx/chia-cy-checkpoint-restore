// The ordinary installed-HTIF build must link and reject the opt-in mode
// before startup, target services, session reconstruction or context entry.
#include "fesvr/firesim_tsi.h"
#include <iostream>
int main(int argc, char **argv) {
  if(argc!=3)return 2;
  try {
    std::vector<std::string> args{"provider-absent","+permissive","+checkpoint-syscall-exit",
      "+checkpoint-terminal-input="+std::string(argv[2]),"+permissive-off",argv[1]};
    std::vector<char *> values;for(auto &arg:args)values.push_back(arg.data());
    try{firesim_tsi_t tsi(values.size(),values.data(),true);}
    catch(const std::runtime_error &e){
      if(std::string(e.what())!="restricted syscall requires actual HTIF provider")throw;
      std::cout<<"ABSENT_PROVIDER_REJECTED startup=0 target_edges=0 context_entries=0\n";return 0;
    }
    throw std::runtime_error("absent provider admitted");
  }catch(const std::exception &e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
