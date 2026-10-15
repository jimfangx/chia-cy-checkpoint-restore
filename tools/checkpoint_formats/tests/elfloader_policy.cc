// Check the actual owned loader provider and sticky, scoped observer failures.
#include "fesvr/elfloader_policy.h"
#include "elfloader_resource_checks.h"
#include <iostream>
#include <thread>
#include <vector>

static void require(bool b, const char *m) { if (!b) throw std::runtime_error(m); }
template<class F> static void rejects(F f) {
  bool rejected=false;
  try { f(); } catch (const std::runtime_error &) { rejected=true; }
  require(rejected,"invalid loader provider accepted");
}
static int check(const char *path) {
  try {
    struct memory_t : memif_t {
      memory_t() : memif_t(nullptr) {}
      size_t writes=0;
      void write(addr_t,size_t,const void *) override { ++writes; }
      endianness_t get_target_endianness() const override { return endianness_little; }
    } mem;
    const auto resources=elf_snapshot_resources();
    size_t cases=0;
    for (size_t repeat=0;repeat<16;++repeat) {
      for (unsigned required : {0u,64u}) {
        reg_t entry=0;
        firesim_elfloader_policy_t policy(path,&entry,0x80000000);
        const auto symbols=load_elf(path,&mem,&entry,0x80000000,required);
        require(policy.result()==required && entry==0x80000000 && symbols.at("tohost")==0x80002000,
                "actual loader policy/metadata differs");
        ++cases;
      }
      for (const std::string mode : {"missing","path","entry","offset","null-memory","duplicate","nested","xlen-exception","thread"}) {
        reg_t entry=0,other=0;
        {
          firesim_elfloader_policy_t policy(path,&entry,0x80000000);
          if (mode=="xlen-exception") {
            bool failed=false;
            try {load_elf(path,&mem,&entry,0x80000000,32);}
            catch (const incompat_xlen &e) {failed=e.expected_xlen==32 && e.actual_xlen==64;}
            require(failed && policy.result()==32,"loader exception lost exact policy");
          } else if (mode=="thread") {
            unsigned result=99;
            std::thread worker([&] {
              reg_t e=0;
              firesim_elfloader_policy_t child(path,&e,0x80000000);
              load_elf(path,&mem,&e,0x80000000,64);
              result=child.result();
            });
            worker.join();
            require(result==64,"thread-local provider failed");
            rejects([&] {policy.result();});
          } else {
            if (mode=="nested") {
              rejects([&] {firesim_elfloader_policy_t nested(path,&entry,0x80000000);});
            } else if (mode!="missing") {
              if (mode=="duplicate")load_elf(path,&mem,&entry,0x80000000,0);
              const auto writes=mem.writes;
              rejects([&] {load_elf(mode=="path" ? "unexpected" : path,
                      mode=="null-memory" ? nullptr : &mem,mode=="entry" ? &other : &entry,
                      mode=="offset" ? 0 : 0x80000000,64);});
              require(mem.writes==writes,"unexpected provider wrote memory before rejection");
            }
            rejects([&] {policy.result();});
            // Catching an unexpected/nested call cannot salvage this scope.
            if (mode!="missing")rejects([&] {load_elf(path,&mem,&entry,0x80000000,0);});
          }
        }
        // Every exception scope releases the observer for the next real load.
        const auto symbols=load_elf(path,&mem,&entry,0x80000000,64);
        require(entry==0x80000000 && symbols.at("fromhost")==0x80002008,"observer leaked after scope exit");
        require(elf_snapshot_resources()==resources,"provider checks leaked resources");
        ++cases;
      }
    }
    std::cout<<"ELF_POLICY_PROVIDER cases="<<cases<<" repetitions=16 modes=11 sticky_rejection=1 thread_isolation=1 resources_unchanged=1\n";
    return 0;
  } catch(const std::exception &e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}
}
#ifdef ELF_POLICY_DPI
extern "C" int elf_policy_check(const char *path) {return check(path);}
extern "C" void elf_policy_exit(int code) {std::exit(code);}
#else
int main(int argc,char **argv) {return argc==2 ? check(argv[1]) : 2;}
#endif
