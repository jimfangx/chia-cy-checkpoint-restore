// No durable-file parser: aggregate.py verifies FSCKPT integrity, executable,
// configuration and complete manifest before creating this local staging.
// Native validators and BOTH compiled VPI tables run before the first load.
#include "aggregate_restore.h"
#include <fstream>
#include <sstream>
#include <set>

extern "C" int generated_restore_prepare_text(const char *);
extern "C" int harness_restore_prepare_text(const char *);
extern "C" int generated_restore_commit();
extern "C" int generated_restore_check_target_cycle(const char *, uint64_t);
extern "C" int harness_restore_commit();
namespace {
struct NativeIdentity { const char *owner, *schema; };
#include "aggregate-restore-table.h"
void require(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(message);
}
uint64_t number(const std::string &text) {
  require(!text.empty() && text.find_first_not_of("0123456789") == std::string::npos,
          "invalid aggregate number");
  size_t used=0; const auto value=std::stoull(text, &used);
  require(used==text.size(), "invalid aggregate number"); return value;
}
std::string section(std::istream &input, const char *expected) {
  std::string line, kind, length, extra;
  require(bool(std::getline(input,line)), "missing aggregate section");
  std::istringstream row(line);
  require(bool(row>>kind>>length) && !(row>>extra) && kind==expected, "wrong aggregate section");
  const auto n=number(length);
  // Read from the immutable in-memory bundle, with length bounded by bytes
  // actually present, rather than allocating according to an untrusted count.
  const auto start=input.tellg(); input.seekg(0,std::ios::end); const auto end=input.tellg(); input.seekg(start);
  require(start>=0 && end>=start && n<=uint64_t(end-start), "truncated aggregate section");
  std::string text(size_t(n),'\0'); input.read(text.data(),text.size());
  require(bool(input) && text.find('\0')==std::string::npos, "invalid aggregate section bytes");
  return text;
}
}

void aggregate_restore_t::prepare(const std::string &filename, const owners_t &list) {
  try {
    require(phase==phase_t::fresh, "aggregate destination already consumed");
    std::ifstream file(filename,std::ios::binary); require(bool(file), "cannot open aggregate staging");
    const std::string bytes{std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
    require(file.eof() || !file.fail(), "cannot read aggregate staging");
    prepare_text(bytes, list);
  } catch (...) {
    phase=phase_t::poisoned; // Includes allocation and interrupted-file errors.
    throw;
  }
}

void aggregate_restore_t::prepare_text(const std::string &bytes, const owners_t &list) {
  const auto previous=phase;
  phase=phase_t::poisoned; // Any validation/load interruption is terminal.
  require(previous==phase_t::fresh, "aggregate destination already consumed");
  require(list.size()==std::size(native_identities), "changed native inventory");
  std::set<checkpoint_owner_t *> pointers;
  for(size_t i=0;i<list.size();++i) {
    require(list[i].first==native_identities[i].owner && list[i].second &&
            list[i].second->checkpoint_schema()==native_identities[i].schema &&
            pointers.insert(list[i].second).second, "unsupported/changed native owner or schema");
  }
  std::istringstream input(bytes);
  std::string line, magic, hash, cycle, sample, count, extra;
  require(bool(std::getline(input,line)), "missing aggregate header");
  std::istringstream header(line);
  require(bool(header>>magic>>hash>>cycle>>sample>>count) && !(header>>extra) &&
          magic=="FSAGG1" && hash==aggregate_manifest_hash && number(count)==list.size(),
          "incompatible aggregate header");
  target_cycle=number(cycle); host_sample=number(sample);
  std::vector<std::vector<uint8_t>> next;
  for(size_t i=0;i<list.size();++i) {
    require(bool(std::getline(input,line)), "missing aggregate native owner");
    std::istringstream row(line); std::string kind, owner, schema, size, hex;
    require(bool(row>>kind>>owner>>schema>>size>>hex) && !(row>>extra) && kind=="HOST" &&
            owner==native_identities[i].owner && schema==native_identities[i].schema,
            "changed aggregate native membership/schema");
    require(!hex.empty() && hex.size()%2==0 && number(size)==hex.size()/2 &&
            hex.find_first_not_of("0123456789abcdef")==std::string::npos, "invalid aggregate native bytes");
    std::vector<uint8_t> b(hex.size()/2);
    auto nibble=[](char c){return c<='9'?c-'0':c-'a'+10;};
    for(size_t j=0;j<b.size();++j) b[j]=(nibble(hex[2*j])<<4)|nibble(hex[2*j+1]);
    list[i].second->validate_checkpoint(b); next.push_back(std::move(b));
  }
  const auto generated=section(input,"GENERATED"), harness=section(input,"HARNESS");
  require(input.peek()==std::char_traits<char>::eof(), "trailing aggregate bytes");
  require(!generated_restore_prepare_text(generated.c_str()), "aggregate generated validation failed");
  require(!harness_restore_prepare_text(harness.c_str()), "aggregate harness validation failed");
#ifdef AGGREGATE_TARGET_CYCLE_PATH
  require(!generated_restore_check_target_cycle(AGGREGATE_TARGET_CYCLE_PATH, target_cycle),
          "aggregate target cycle validation failed");
#endif
  owners=list; payloads.swap(next); phase=phase_t::prepared;
}

void aggregate_restore_t::commit_native() {
  const auto previous=phase;
  phase=phase_t::poisoned;
  require(previous==phase_t::prepared, "aggregate native commit without preparation");
  for(size_t i=0;i<owners.size();++i) { ++native_loads; owners[i].second->load_checkpoint(payloads[i]); }
  for(size_t i=0;i<owners.size();++i)
    require(owners[i].second->save_checkpoint()==payloads[i], "aggregate native readback mismatch");
  phase=phase_t::native_loaded;
}

void aggregate_restore_t::commit_rtl() {
  const auto previous=phase;
  phase=phase_t::poisoned;
  require(previous==phase_t::native_loaded, "aggregate RTL commit without native load");
  require(!harness_restore_commit() && !generated_restore_commit(), "aggregate RTL commit failed");
  phase=phase_t::rtl_loaded; // Caller must still settle/verify both before bootstrap.
}
