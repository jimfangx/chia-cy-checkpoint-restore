#include "runtime_identity.h"
#include <array>
#include <charconv>
#include <cstdlib>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <limits>
#include <link.h>
#include <memory>
#include <map>
#include <openssl/evp.h>
#include <set>

namespace {
void require(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(std::string("runtime identity: ") + message);
}
void append(std::vector<uint8_t> &out, uint64_t value) {
  for (unsigned i=0; i<8; ++i) out.push_back(value >> (8*i));
}
void append(std::vector<uint8_t> &out, const std::string &value) {
  append(out, value.size()); out.insert(out.end(), value.begin(), value.end());
}
uint64_t number(const std::string &value, uint64_t maximum) {
  uint64_t result=0;
  auto parsed=std::from_chars(value.data(), value.data()+value.size(), result);
  require(parsed.ec==std::errc{} && parsed.ptr==value.data()+value.size() && result<=maximum,
          "invalid audited numeric argument");
  return result;
}
struct loaded_t { std::vector<std::string> files; std::exception_ptr error; };
int loaded(struct dl_phdr_info *info, size_t, void *data) noexcept {
  auto &result=*static_cast<loaded_t *>(data);
  try {
    const std::string path=info->dlpi_name;
    // The vDSO is kernel-generated and has no file-backed simulator state.
    if (path=="linux-vdso.so.1") return 0;
    result.files.push_back(path.empty() ? "/proc/self/exe" : path);
    return 0;
  } catch (...) { result.error=std::current_exception(); return 1; }
}
std::array<uint8_t,32> sha256(const std::string &path) {
  std::ifstream file(path, std::ios::binary);
  require(bool(file), "missing loaded ELF file");
  const auto size=std::filesystem::file_size(path);
  const auto time=std::filesystem::last_write_time(path);
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> hash(EVP_MD_CTX_new(), EVP_MD_CTX_free);
  require(hash && EVP_DigestInit_ex(hash.get(), EVP_sha256(), nullptr)==1, "SHA256 initialization failed");
  std::array<char,65536> buffer{};
  while (file.read(buffer.data(), buffer.size()) || file.gcount())
    require(EVP_DigestUpdate(hash.get(), buffer.data(), file.gcount())==1, "SHA256 update failed");
  require(file.eof() && !file.bad() && size==std::filesystem::file_size(path) &&
          time==std::filesystem::last_write_time(path), "loaded ELF changed during hashing");
  std::array<uint8_t,32> result{}; unsigned length=0;
  require(EVP_DigestFinal_ex(hash.get(), result.data(), &length)==1 && length==result.size(),
          "SHA256 finalization failed");
  return result;
}
// Decode only our own freshly built compatibility identities for diagnostics.
// This never admits a changed ELF set or changes the serialized owner schema.
std::map<std::string,std::array<uint8_t,32>> elf_records(const std::vector<uint8_t> &bytes,size_t offset) {
  auto integer=[&] {
    require(offset<=bytes.size() && bytes.size()-offset>=8,"invalid internal ELF identity");
    uint64_t value=0;
    for(unsigned i=0;i<8;++i) value|=uint64_t(bytes[offset++])<<(8*i);
    return value;
  };
  const auto count=integer();
  std::map<std::string,std::array<uint8_t,32>> result;
  for(uint64_t i=0;i<count;++i) {
    const auto size=integer();
    require(offset<=bytes.size() && size<=bytes.size()-offset && bytes.size()-offset-size>=32,
            "invalid internal ELF record");
    std::string path(bytes.begin()+offset,bytes.begin()+offset+size); offset+=size;
    std::array<uint8_t,32> hash{};
    for(auto &byte:hash) byte=bytes[offset++];
    require(result.emplace(path,hash).second,"duplicate internal ELF record");
  }
  require(offset==bytes.size(),"trailing internal ELF identity"); return result;
}
}

void checkpoint_vcs_runtime_warmup() {
  const char *home=std::getenv("VCS_HOME");
  require(home && (std::string(home)=="/ecad/tools/synopsys/vcs/Y-2026.03-SP1" ||
                   std::string(home)=="/tools/Synopsys/vcs/Y-2026.03-SP2"),
          "unsupported VCS_HOME for diagnostic warmup");
  static const std::string release=home;
  require(std::string(home)==release, "unsupported VCS_HOME for diagnostic warmup");
  // VCS opens these tables on its first diagnostic (including healthy $finish).
  // Load exact absolute files, never an environment-selected search-path alias.
  // Do not close them: capture and fresh restore must retain the same ELF set
  // through finalization. current_identity() hashes both files and dependencies;
  // no library is excluded and no identity is refreshed after construction.
  static const auto handles=[] {
    std::array<void *,2> result{};
    unsigned i=0;
    for(const char *name:{"liberrindex.so", "libsystemcerror.so"}) {
      const std::string path=std::string(release)+"/linux64/lib/"+name;
      result[i]=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);
      if(!result[i]) {
        const char *error=dlerror();
        throw std::runtime_error("runtime identity: VCS diagnostic warmup failed: "+path+
                                 ": "+(error ? error : "unknown loader error"));
      }
      ++i;
    }
    return result;
  }();
  (void)handles;
}

runtime_identity_t::runtime_identity_t(const std::vector<std::string> &args) {
  for (const auto *name : {"LD_PRELOAD", "LD_AUDIT"}) {
    const auto *value=std::getenv(name);
    require(!value || !*value, "unsupported LD_PRELOAD/LD_AUDIT library hooks");
  }
  uint64_t memory=0, horizon=0, delay=1, seed=0;
  std::set<std::string> seen;
  bool registers=false, memories=false;
  for (const auto &arg : args) {
    const auto key=arg.substr(0,arg.find('='));
    if (key=="+memsize" || key=="+max-cycles" || key=="+fuzz-host-timing" || key=="+fuzz-seed") {
      require(seen.insert(key).second && arg.find('=')!=std::string::npos,
              "duplicate/missing audited configuration argument");
      const auto value=arg.substr(arg.find('=')+1);
      if (key=="+memsize") memory=number(value, std::numeric_limits<int64_t>::max());
      if (key=="+max-cycles") horizon=number(value, std::numeric_limits<uint64_t>::max());
      if (key=="+fuzz-host-timing") delay=number(value, std::numeric_limits<int32_t>::max());
      if (key=="+fuzz-seed") seed=number(value, std::numeric_limits<uint64_t>::max());
    } else if (arg=="+vcs+initreg+0" || arg=="+vcs+initmem+0") {
      require(seen.insert(arg).second, "duplicate initialization argument");
      if (arg=="+vcs+initreg+0") registers=true; else memories=true;
    } else if (arg=="-no_save" || arg=="+fs-driver-settled" || arg=="+fs-driver-lowclock") {
      // Audited harness/test controls; they change neither the restored state
      // nor future target behavior. The cut itself is separately validated.
    } else if (key=="+fs-driver-cut" || key=="+fs-driver-diagnostic" ||
               key=="+settled_generated_capture" || key=="+target_port_trace" ||
               key=="+test-aggregate" || key=="+test-negative" ||
               key=="+test-loaded-native" || key=="+test-runtime-identity" || key=="+test-extra-library") {
      require(arg.find('=')!=std::string::npos && arg.back()!='=', "empty test control");
    } else {
      throw std::runtime_error("runtime identity: unsupported argument: "+arg);
    }
  }
  require(memory>0 && horizon>0 && delay>0 && registers && memories,
          "profile requires explicit positive memory/horizon and zero VCS initialization");
  append(configuration,"FCFS_RUNTIME1");
  for (auto value : {memory,horizon,delay,seed}) append(configuration,value);
  identity=current_identity();
}

std::vector<uint8_t> runtime_identity_t::current_identity() const {
  loaded_t loaded_files;
  dl_iterate_phdr(loaded, &loaded_files);
  if (loaded_files.error) std::rethrow_exception(loaded_files.error);
  std::set<std::string> paths;
  for (const auto &path : loaded_files.files) paths.insert(std::filesystem::canonical(path).string());
  require(!paths.empty(), "empty loaded ELF inventory");
  auto result=configuration;
  append(result,paths.size());
  for (const auto &path : paths) {
    append(result,path); const auto hash=sha256(path);
    result.insert(result.end(),hash.begin(),hash.end());
  }
  return result;
}

std::vector<uint8_t> runtime_identity_t::save_checkpoint() const {
  const auto current=current_identity();
  if(current!=identity) {
    const auto before=elf_records(identity,configuration.size()),after=elf_records(current,configuration.size());
    std::string detail;
    for(const auto &[path,hash]:before) {
      const auto found=after.find(path);
      if(found==after.end()) detail+="; removed ELF: "+path;
      else if(found->second!=hash) detail+="; changed ELF: "+path;
    }
    for(const auto &[path,hash]:after) if(!before.count(path)) detail+="; added ELF: "+path;
    throw std::runtime_error("runtime identity: configuration/loaded ELF changed after entry"+detail);
  }
  return identity;
}
void runtime_identity_t::validate_checkpoint(const std::vector<uint8_t> &bytes) const {
  require(bytes==save_checkpoint(), "incompatible configuration/executable/loaded ELF");
}
