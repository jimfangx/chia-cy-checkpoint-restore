#include "fesvr/tsi_program_loader.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>

static void require(bool b) { if (!b) throw std::runtime_error("loader check failed"); }
template<class F> static void rejects(F f) {
  bool rejected=false; try { f(); } catch (const std::exception &) { rejected=true; }
  require(rejected);
}
static int run(const char *source, const char *destination, const char *phase_text) {
  try {
    size_t invalids=0, transitions=0;
    for (bool loadmem : {false,true}) for (uint64_t flush : {0ULL,0x10000100ULL}) {
      firesim_tsi_program_loader_t owner(loadmem,flush);
      for (unsigned phase=0;phase<4;++phase) {
        require(static_cast<unsigned>(owner.phase())==phase);
        require(owner.loadmem_mode()==(loadmem && phase==2));
        require(owner.cache_flush_address()==flush);
        const auto valid=owner.save_checkpoint();
        firesim_tsi_program_loader_t peer(loadmem,flush);
        peer.load_checkpoint(valid); require(peer.save_checkpoint()==valid);
        // Every malformed prefix, incompatible identity bit and extra byte.
        auto invalid = [&](const std::vector<uint8_t> &b) {
          rejects([&]{peer.validate_checkpoint(b);});
          rejects([&]{peer.load_checkpoint(b);});
          require(peer.save_checkpoint()==valid); ++invalids;
        };
        for (size_t n=0;n<valid.size();++n) invalid({valid.begin(),valid.begin()+n});
        for (size_t n=0;n<48;++n) for (unsigned bit=0;bit<8;++bit) {
          auto b=valid; b[n]^=1U<<bit; invalid(b);
        }
        auto extra=valid; extra.push_back(0); invalid(extra);
        auto bad=valid; bad[48]=4; invalid(bad);
        for (auto op : {0,1,2}) {
          const bool legal = op==0 ? (phase==0 || phase==3) : op==1 ? phase==1 : phase==2;
          auto action=[&] { if(op==0) peer.begin(); else if(op==1) peer.enter(); else peer.finish(); };
          if(legal) { action(); ++transitions; peer.load_checkpoint(valid); }
          else { rejects(action); require(peer.save_checkpoint()==valid); }
        }
        if(phase==0) owner.begin(); else if(phase==1) owner.enter(); else if(phase==2) owner.finish();
      }
      const auto before=owner.save_checkpoint(); owner.interrupt();
      rejects([&]{owner.save_checkpoint();}); rejects([&]{owner.load_checkpoint(before);});
      rejects([&]{owner.validate_checkpoint(before);}); rejects([&]{owner.loadmem_mode();});
      rejects([&]{owner.cache_flush_address();}); rejects([&]{owner.begin();});
    }
    if(std::string(source)!="self") {
      std::ifstream input(source,std::ios::binary); require(bool(input));
      std::vector<uint8_t> image{std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>()};
      firesim_tsi_program_loader_t fresh(true,0); fresh.load_checkpoint(image);
      std::ofstream out(destination,std::ios::binary);
      const auto bytes=fresh.save_checkpoint();out.write(reinterpret_cast<const char *>(bytes.data()),bytes.size());
      out.close();require(bool(out));
      const auto expected=std::stoul(phase_text);
      const auto actual=static_cast<unsigned>(fresh.phase());
      if(actual!=expected) {
        std::cerr<<"FIRST_DIVERGENCE component_operation=0 signal=loader_phase expected="<<expected
                 <<" actual="<<actual<<" acknowledged=0\n";return 3;
      }
      require(fresh.loadmem_mode()==(expected==2));
      std::cout<<"COMPLETE_PROGRAM_READBACK target_edges=0 context_entries=0 services=0 phase="<<actual<<'\n';
    }
    std::cout<<"LOADER_OWNER_CHECKS invalids="<<invalids<<" transitions="<<transitions<<" policies=4 phases=4\n";
    return 0;
  } catch(const std::exception &e) { std::cerr<<"FAIL "<<e.what()<<'\n';return 2; }
}
#ifdef TSI_PROGRAM_LOADER_DPI
extern "C" int tsi_program_loader(const char *s,const char *o,const char *p) {return run(s,o,p);}
extern "C" void tsi_program_loader_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {if(argc!=4) return 2;return run(argv[1],argv[2],argv[3]);}
#endif
