// Actual VPI component loader under ASan/UBSan; handle/callback faults mocked.
#include "../harness_restore.cc"
#include <cassert>
#include <iostream>
#include <map>
namespace {
struct MockHandle { int type, width; std::vector<s_vpi_vecval> value; };
std::map<std::string, MockHandle> handles;
size_t deposit_count=0;
uint32_t now=0;
bool subscription_ok=true;
MockHandle &mock(vpiHandle h) { return *reinterpret_cast<MockHandle *>(h); }
}
extern "C" vpiHandle vpi_handle_by_name(PLI_BYTE8 *name,vpiHandle) {
 auto it=handles.find(name);return it==handles.end()?nullptr:reinterpret_cast<vpiHandle>(&it->second);
}
extern "C" PLI_INT32 vpi_get(PLI_INT32 property,vpiHandle h) {
 assert(property==vpiType || property==vpiSize);return property==vpiType?mock(h).type:mock(h).width;
}
extern "C" void vpi_get_value(vpiHandle h,p_vpi_value value) {
 assert(value->format==vpiVectorVal);value->value.vector=mock(h).value.data();
}
extern "C" vpiHandle vpi_put_value(vpiHandle h,p_vpi_value value,p_vpi_time time,PLI_INT32 flags) {
 assert(value->format==vpiVectorVal && !time && flags==vpiNoDelay);
 auto &dest=mock(h).value;dest.assign(value->value.vector,value->value.vector+dest.size());deposit_count++;return nullptr;
}
extern "C" PLI_INT32 vpi_printf(PLI_BYTE8 *,...) { return 0; }
extern "C" void vpi_get_time(vpiHandle,p_vpi_time time) { assert(time->type==vpiSimTime);time->high=0;time->low=now; }
extern "C" vpiHandle vpi_register_cb(p_cb_data cb) {
 assert(cb->reason==cbValueChange && cb->cb_rtn==clock_changed && cb->obj);
 return subscription_ok?cb->obj:nullptr;
}
int main(int argc,char **argv) {
 assert(argc==3); // independently generated all-ones non-control payload
 for (const auto &entry:entries) handles.emplace(entry.path,MockHandle{entry.clock_output?vpiBitVar:vpiStructVar,int(entry.width),std::vector<s_vpi_vecval>((entry.width+31)/32)});
 handles.emplace(clock_path,MockHandle{vpiReg,1,std::vector<s_vpi_vecval>(1)});
 std::ifstream stream(argv[1]);const std::string good{std::istreambuf_iterator<char>(stream),std::istreambuf_iterator<char>()};assert(!good.empty());
 size_t rejections=0;
 auto reject=[&](const char *path) { assert(harness_restore(path)==1 && !loaded && pending.empty() && deposit_count==0);rejections++; };
 reject(argv[1]); // not armed
 now=1;assert(harness_restore_initialize()==1);rejections++;now=0;
 subscription_ok=false;assert(harness_restore_initialize()==1);rejections++;subscription_ok=true;
 auto &clock=handles.at(clock_path);clock.value[0].aval=1;assert(harness_restore_initialize()==1);rejections++;clock.value[0].aval=0;
 for (const auto *path:unsupported_paths) {
  handles.emplace(path,MockHandle{vpiReg,1,std::vector<s_vpi_vecval>(1)});
  assert(harness_restore_initialize()==1);rejections++;handles.erase(path);
 }
 assert(harness_restore_initialize()==0);assert(harness_restore_initialize()==1);rejections++;
 if (std::string(argv[2])=="advanced") {
  clock.value[0].aval=1;clock_changed(nullptr);clock.value[0].aval=0;clock_changed(nullptr);
  reject(argv[1]);assert(harness_restore_verify()==1);rejections++;
 } else {
  std::string bad_path=std::string(argv[1])+".bad";
  for (size_t i=0;i+1<good.size();i++) { {std::ofstream bad(bad_path);bad<<good.substr(0,i);}reject(bad_path.c_str()); }
  reject("/nonexistent/harness-load");
  for (const auto &entry:entries) {
   std::string path=entry.path;const auto original=handles.at(path);
   handles.erase(path);reject(argv[1]);handles.emplace(path,original);
   handles.at(path).width++;reject(argv[1]);handles.at(path).width--;
   handles.at(path).type=vpiNet;reject(argv[1]);handles.at(path).type=original.type;
  }
  clock.value[0].bval=1;reject(argv[1]);clock.value[0].bval=0;
  assert(harness_restore_verify()==1);rejections++;
  assert(harness_restore(argv[1])==0 && loaded && deposit_count==29);
  assert(harness_restore(argv[1])==1 && deposit_count==29);rejections++;
  const std::string mode=argv[2];
  if (mode=="readback") {
   handles.at(entries[0].path).value[0].aval^=1;
   assert(harness_restore_verify()==1 && !pending.empty());rejections++;
   handles.at(entries[0].path).value[0].aval^=1;
   // Failed verification must remain terminal even if data is repaired.
   assert(harness_restore_verify()==1 && !pending.empty());rejections++;
  } else if (mode=="clock-during-load") {
   clock.value[0].aval=1;clock_changed(nullptr);clock.value[0].aval=0;clock_changed(nullptr);
   assert(harness_restore_verify()==1 && !pending.empty());rejections++;
  } else {
   assert(harness_restore_verify()==0 && pending.empty());
   for (const auto &entry:entries) {
    const auto &value=handles.at(entry.path).value;
    for (size_t i=0;i<value.size();i++) {
     const unsigned bits=std::min(32u,entry.width-32u*unsigned(i));
     assert(value[i].aval==(entry.clock_output?0u:(bits==32?UINT32_MAX:(uint32_t{1}<<bits)-1)) && value[i].bval==0);
    }
   }
  }
  assert(harness_restore(argv[1])==1 && deposit_count==29);rejections++;
 }
 std::cout<<"HARNESS_NATIVE mode="<<argv[2]<<" rejections="<<rejections<<"\n";
}
