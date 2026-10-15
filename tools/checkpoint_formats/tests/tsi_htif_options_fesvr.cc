// Installed getopt_long abbreviations must retain the configured HTIF loop.
#include "fesvr/firesim_tsi.h"
#include <iostream>
static int run(const char *option) {
  try {
    std::vector<std::string> args{"options-fesvr","+permissive","+idle-counts=1"};
    const bool expected=std::string(option)=="default";
    if (!expected) args.push_back(option);
    args.push_back("+permissive-off");args.push_back("none");
    std::vector<char *> argv;for(auto &arg:args)argv.push_back(arg.data());
    firesim_tsi_t tsi(argv.size(),argv.data(),true);tsi.tick();
    bool owned=false;
    try { tsi.htif_poll_owner().save_checkpoint();owned=true; }
    catch(const std::runtime_error &) {}
    if (owned!=expected || tsi.done() || tsi.busy()) throw std::runtime_error("configured HTIF route was bypassed");
    std::cout<<"REAL_HTIF_OPTION option="<<option<<" owned_default="<<owned<<" contexts=1 cpu_edges=0\n";return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef TSI_HTIF_OPTIONS_DPI
extern "C" int tsi_htif_options(const char *o) {return run(o);}
extern "C" void tsi_htif_options_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=2)return 2;return run(argv[1]);}
#endif
