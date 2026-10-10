// Sanitized VPI adapter oracle. Real VCS live cuts are verified separately.
#include "../durable_capture.h"
#include <sv_vpi_user.h>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>

namespace {
struct Entry { const char *path; unsigned width, depth; bool memory, clock_output; };
namespace generated {
#include "generated-restore-table.h"
}
namespace harness {
#include "harness-restore-table.h"
}
struct NativeIdentity { const char *owner, *schema; };
#include "aggregate-restore-table.h"
struct Fake {
  int width, type;
  std::vector<s_vpi_vecval> bits;
  unsigned reads=0;
};
std::map<std::string, Fake> state;
std::string mode;
size_t loads=0, saves=0;
void check(bool ok) { if(!ok) throw std::logic_error("fixture assertion"); }
unsigned nibble(char c) { return c<='9' ? c-'0' : c-'a'+10; }
void add(const std::string &path, unsigned width, int type, const std::string &hex) {
  Fake fake{int(width),type,std::vector<s_vpi_vecval>((width+31ULL)/32)};
  for(size_t i=0;i<hex.size();++i)
    fake.bits[i/8].aval |= nibble(hex[hex.size()-1-i]) << (4*(i%8));
  check(state.emplace(path,std::move(fake)).second);
}
struct Native : checkpoint_owner_t {
  std::string schema;
  std::vector<uint8_t> bytes;
  mutable size_t calls=0;
  Native *previous=nullptr;
  explicit Native(const char *schema):schema(schema) {}
  std::string checkpoint_schema() const override {
    return mode=="schema-change" && calls ? "changed" : schema;
  }
  std::vector<uint8_t> save_checkpoint() const override {
    ++calls; ++saves;
    if(mode=="empty-payload") return {};
    if(mode=="native-change" && calls==2) { auto result=bytes; result[0]^=1; return result; }
    if(mode=="rtl-side-effect" && calls==2 && !previous)
      state.at("emul.Top.wide").bits[0].aval ^= 1;
    return bytes;
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override {
    check(b==bytes);
    if(mode=="validator") throw std::runtime_error("fixture semantic validator rejected");
    if(mode=="cross-owner-change" && previous) previous->bytes[0]^=1;
  }
  void load_checkpoint(const std::vector<uint8_t> &) override { ++loads; check(false); }
};
}
extern "C" vpiHandle vpi_handle_by_name(PLI_BYTE8 *path, vpiHandle) {
  if(mode==std::string("missing:")+path) return nullptr;
  auto it=state.find(path);
  return it==state.end() ? nullptr : reinterpret_cast<vpiHandle>(&it->second);
}
extern "C" PLI_INT32 vpi_get(PLI_INT32 property, vpiHandle handle) {
  auto &fake=*reinterpret_cast<Fake *>(handle);
  if(property==vpiSize) return fake.width;
  if(property==vpiType) return fake.type;
  check(false); return 0;
}
extern "C" void vpi_get_value(vpiHandle handle, p_vpi_value value) {
  check(value->format==vpiVectorVal);
  auto &fake=*reinterpret_cast<Fake *>(handle);
  ++fake.reads;
  for(const auto &[path,object]:state)
    if(&object==&fake && mode=="changed:"+path && fake.reads==2) fake.bits[0].aval^=1;
  value->value.vector=fake.bits.data();
}

int main(int argc, char **argv) {
  try {
    check(argc==4); mode=argv[3];
    const bool poll=mode.rfind("poll-",0)==0;
    if(poll) mode=mode.substr(5);
    std::ifstream input(argv[1]); check(bool(input));
    std::string line; std::getline(input,line);
    std::istringstream header(line); std::string magic,hash; uint64_t cycle,sample,count;
    check(bool(header>>magic>>hash>>cycle>>sample>>count) && count==std::size(native_identities));
    std::vector<std::unique_ptr<Native>> storage;
    aggregate_restore_t::owners_t owners;
    for(const auto &identity:native_identities) {
      std::getline(input,line); std::istringstream row(line);
      std::string kind,name,schema,hex; size_t size;
      check(bool(row>>kind>>name>>schema>>size>>hex) && name==identity.owner && schema==identity.schema);
      auto object=std::make_unique<Native>(identity.schema);
      for(size_t i=0;i<hex.size();i+=2) object->bytes.push_back((nibble(hex[i])<<4)|nibble(hex[i+1]));
      check(object->bytes.size()==size);
      if(!storage.empty()) object->previous=storage.back().get();
      owners.emplace_back(name,object.get()); storage.push_back(std::move(object));
    }
    std::getline(input,line); std::getline(input,line); // GENERATED section/header
    for(const auto &e:generated::entries) {
      std::getline(input,line); std::istringstream row(line);
      std::string path,hex; unsigned width,depth;
      check(bool(row>>path>>width>>depth>>hex) && path==e.path && width==e.width && depth==e.depth);
      const size_t digits=(width+3ULL)/4;
      for(unsigned i=0;i<depth;++i)
        add(path+(e.memory ? "["+std::to_string(i)+"]" : ""),width,
            e.memory ? vpiMemoryWord : vpiReg,hex.substr(i*digits,digits));
    }
    std::getline(input,line); std::getline(input,line); // HARNESS section/header
    for(const auto &e:harness::entries) {
      std::getline(input,line); std::istringstream row(line);
      std::string path,hex; unsigned width;
      check(bool(row>>path>>width>>hex) && path==e.path && width==e.width);
      add(path,width,e.clock_output ? vpiBitVar : vpiStructVar,hex);
    }
    for(const auto &paths:{std::vector<const char *>(std::begin(generated::clock_paths),std::end(generated::clock_paths)),
                           std::vector<const char *>(std::begin(harness::clock_paths),std::end(harness::clock_paths))})
      for(const auto *path:paths) if(!state.count(path)) add(path,1,vpiNet,"0");
    for(auto &[path,fake]:state) {
      if(mode=="width:"+path) ++fake.width;
      if(mode=="kind:"+path) fake.type=vpiNet;
      if(mode=="unknown:"+path) fake.bits[0].bval=1;
      if(mode=="padding:"+path) fake.bits.back().aval|=1u<<(fake.width%32);
      if(mode=="high:"+path) fake.bits[0].aval=1;
    }
    if(mode=="unsupported-harness") add(harness::unsupported_paths[0],1,vpiReg,"0");
    if(mode=="missing-owner") owners.pop_back();
    if(mode=="extra-owner") owners.emplace_back("unknown",storage.front().get());
    if(mode=="order") std::swap(owners.front(),owners.back());
    if(mode=="alias") owners.back().second=owners.front().second;
    if(mode=="null") owners.back().second=nullptr;
    if(mode=="schema") storage.back()->schema="unsupported";
    if(mode=="range") state.at("emul.Top.progress").bits[0].aval=10001;
    if(mode=="initialization-range") state.at("emul.Top.initialization").bits[0].aval=524289;
    if(mode=="bad-epoch") state.at("emul.Top.initialization").bits[0].aval=0;
    try {
      if(poll) {
        if(mode=="initialization") {
          state.at("emul.Top.progress").bits[0].aval=10000;
          for(const unsigned value:{0u,1u,524287u,524288u}) {
            state.at("emul.Top.initialization").bits[0].aval=value;
            check(durable_capture_target_progress()==value);
          }
          state.at("emul.Top.progress").bits[0].aval=9999;
          check(durable_capture_target_progress()==524289);
        } else check(durable_capture_target_progress()==529288 && mode=="valid");
        check(loads==0 && saves==0);
        puts("PASS: audited target-progress sampling no_loads=1 no_native_reads=1"); return 0;
      }
      const auto snapshot=capture_durable_snapshot(owners,sample);
      check(mode=="valid");
      std::ofstream output(argv[2],std::ios::binary); output.write(snapshot.data(),snapshot.size());
      output.close(); check(bool(output));
      std::cout<<"PASS live snapshot no_loads="<<loads<<"\n";
    } catch(const std::runtime_error &error) {
      if(mode=="valid") throw;
      check(loads==0);
      if(mode=="missing-owner" || mode=="extra-owner" || mode=="order" || mode=="alias" || mode=="null" || mode=="schema") check(saves==0);
      std::cout<<"REJECT "<<error.what()<<" no_loads=0\n"; return 1;
    }
    check(loads==0); return 0;
  } catch(const std::exception &error) { std::cerr<<"FIXTURE ERROR "<<error.what()<<'\n'; return 2; }
}
