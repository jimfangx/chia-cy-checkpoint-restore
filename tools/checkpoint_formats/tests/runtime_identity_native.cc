#include "../runtime_identity.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <dlfcn.h>

int main(int argc, char **argv) {
  if (argc<4) return 2;
  std::string mode=argv[1];
  const std::string filename=argv[2], preload=argv[3];
  void *library=nullptr;
  if (preload!="-" && mode!="late-add") {
    library=dlopen(preload.c_str(),RTLD_NOW|RTLD_LOCAL); if(!library) return 3;
  }
  try {
    if(mode.rfind("warm-",0)==0) {
      mode=mode.substr(5);
      checkpoint_vcs_runtime_warmup();
      checkpoint_vcs_runtime_warmup(); // Repeated entry keeps the same handles.
    }
    runtime_identity_t owner({argv+4,argv+argc});
    auto initial=owner.save_checkpoint();
    if(mode=="late-add" || mode=="late-remove") {
      if(mode=="late-add") {
        library=dlopen(preload.c_str(),RTLD_NOW|RTLD_LOCAL); if(!library) return 3;
      } else if(dlclose(library)) return 3;
      try { owner.save_checkpoint(); return 8; }
      catch(const std::runtime_error &error) {
        const std::string message=error.what();
        if(message.find(mode=="late-add" ? "added ELF: " : "removed ELF: ")==std::string::npos ||
           message.find(preload)==std::string::npos) return 9;
        std::cout<<"REJECT changed ELF inventory "<<message<<'\n'; return 0;
      }
    }
    if (mode=="save") {
      std::ofstream output(filename,std::ios::binary);
      output.write(reinterpret_cast<const char *>(initial.data()),initial.size());
      output.close();if(!output) return 4;
    } else {
      std::ifstream file(filename,std::ios::binary);
      const std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
      try {
        owner.validate_checkpoint(bytes);owner.load_checkpoint(bytes);
        if(mode=="reject") return 5;
      } catch (const std::exception &error) {
        if(mode!="reject") throw;
        if(owner.save_checkpoint()!=initial) return 6;
        std::cout<<"REJECT unchanged_owner=1 "<<error.what()<<'\n';return 0;
      }
      if(owner.save_checkpoint()!=initial) return 7;
    }
    std::cout<<"PASS immutable runtime identity\n";return 0;
  } catch(const std::exception &error) {
    std::cout<<"ENTRY_ERROR "<<error.what()<<'\n';return mode=="bad-args" ? 0 : 1;
  }
}
