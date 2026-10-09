#include "durable_restore.h"
// Boost.JSON's implementation is compiled into this capability. No runtime
// Python/helper/profile file is trusted or required by the public API.
#include <boost/json/src.hpp>
#include <openssl/evp.h>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <memory>
#include <map>
#include <sstream>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>

namespace {
struct DurableEntry { const char *owner, *path; uint64_t width, depth; bool low; };
struct DurableNative { const char *owner, *schema; };
#include "durable-restore-table.h"
void require(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(std::string("durable restore: ")+message);
}
struct descriptor_t {
  int value;
  ~descriptor_t() { if(value>=0) close(value); }
};
std::string read_regular(const std::string &name) {
  descriptor_t fd{open(name.c_str(), O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK)};
  require(fd.value>=0, "cannot open regular checkpoint/executable");
  struct stat status{};
  require(!fstat(fd.value,&status) && S_ISREG(status.st_mode) && status.st_size>=0 &&
          uint64_t(status.st_size)<=256ULL*1024*1024, "unsupported file type/size for audited profile");
  std::string result(size_t(status.st_size),'\0');
  size_t offset=0;
  while(offset<result.size()) {
    const auto n=read(fd.value,result.data()+offset,result.size()-offset);
    if(n<0 && errno==EINTR) continue;
    require(n>0, "truncated/unreadable file"); offset+=size_t(n);
  }
  char extra;
  require(read(fd.value,&extra,1)==0, "file grew during read");
  return result;
}
std::string sha256(std::string_view bytes) {
  std::array<unsigned char,32> digest{}; unsigned size=0;
  require(EVP_Digest(bytes.data(),bytes.size(),digest.data(),&size,EVP_sha256(),nullptr)==1 &&
          size==digest.size(), "SHA256 failure");
  return {reinterpret_cast<const char *>(digest.data()),digest.size()};
}
std::string hex(std::string_view bytes) {
  std::string result; result.reserve(bytes.size()*2);
  for(unsigned char byte:bytes) { result.push_back("0123456789abcdef"[byte>>4]); result.push_back("0123456789abcdef"[byte&15]); }
  return result;
}
const boost::json::object &object(const boost::json::value &v) {
  require(v.is_object(), "expected object"); return v.as_object();
}
void keys(const boost::json::object &v, std::initializer_list<const char *> names) {
  require(v.size()==names.size(), "missing/extra object keys");
  for(const auto *name:names) require(v.contains(name), "missing object key");
  std::string_view previous;
  for(const auto &row:v) {
    const std::string_view key{row.key().data(),row.key().size()};
    require(previous.empty() || previous<key, "noncanonical key order"); previous=key;
  }
}
std::string_view string(const boost::json::value &v) {
  require(v.is_string(), "expected string"); return {v.as_string().data(),v.as_string().size()};
}
uint64_t natural(const boost::json::value &v) {
  require(v.is_uint64() || (v.is_int64() && v.as_int64()>=0), "expected unsigned integer");
  return v.is_uint64()?v.as_uint64():uint64_t(v.as_int64());
}
uint64_t scalar(std::string_view value) {
  require(value.size()<=16, "scalar overflow"); uint64_t result=0;
  for(char c:value) result=(result<<4)|(c<='9'?c-'0':c-'a'+10);
  return result;
}
using rows_t=std::map<std::string_view,const boost::json::object *>;
const boost::json::object &record(const rows_t &rows, const std::string &owner) {
  auto it=rows.find(owner); require(it!=rows.end(), "missing manifested owner"); return *it->second;
}
std::string_view value(const rows_t &rows, const std::string &owner) {
  return string(record(rows,owner).at("value"));
}
void entry(const rows_t &rows, const DurableEntry &e, bool packed) {
  const auto &r=record(rows,e.owner); const auto v=string(r.at("value"));
  const uint64_t digits=(e.width+3)/4;
  require(natural(r.at("width"))==(packed?4*digits*e.depth:e.width), "changed entry shape");
  require(v.size()==digits*e.depth, "incomplete entry");
  // Check the padding of EVERY memory word, even when the record's aggregate
  // width happens to be nibble aligned. Clock outputs must remain low.
  for(size_t i=0;i<v.size();i+=digits)
    require(e.width%4==0 || scalar(v.substr(i,1))<(1ULL<<(e.width%4)), "nonzero word padding");
  require(!e.low || v.find_first_not_of('0')==std::string_view::npos, "high clock/reset/finish cut");
}
}

std::string read_durable_restore(const std::string &filename) {
  // One immutable file image feeds integrity, schema and native preparation.
  auto bytes=read_regular(filename);
  require(bytes.size()>=48 && bytes.compare(0,8,std::string("FSCKPT\0\1",8))==0, "wrong magic/type/version");
  uint64_t size=0; for(size_t i=8;i<16;++i) size=(size<<8)|uint8_t(bytes[i]);
  require(size==bytes.size()-48, "container size mismatch");
  require(sha256(std::string_view(bytes).substr(0,bytes.size()-32))==bytes.substr(bytes.size()-32), "checksum mismatch");
  const std::string_view payload{bytes.data()+16,size_t(size)};
  boost::json::parse_options options; options.max_depth=8;
  auto doc=boost::json::parse(payload,{},options);
  // Re-serialization rejects whitespace, duplicate keys, escaped alternatives,
  // and noncanonical numbers. Every object below also requires sorted keys.
  require(boost::json::serialize(doc)==payload, "noncanonical/duplicate JSON");
  bytes.clear(); bytes.shrink_to_fit();
  const auto &root=object(doc);
  keys(root,{"build","checkpoint_type","format_version","records","target_clock_phase","target_cycle"});
  require(natural(root.at("format_version"))==1 && string(root.at("checkpoint_type"))=="fsckpt" &&
          string(root.at("target_clock_phase"))=="before_rising_edge", "unsupported checkpoint contract");
  const auto cycle=natural(root.at("target_cycle"));
  const auto &build=object(root.at("build"));
  keys(build,{"golden_gate_build_hash","rtl_build_hash","simulator_build_hash","state_manifest_hash","target_configuration"});
  // /proc/self/exe is resolved only for this regular-file read, never by an
  // untrusted container. All other identities are immutable compiled tables.
  std::array<char,4096> executable_path{};
  const auto path_size=readlink("/proc/self/exe",executable_path.data(),executable_path.size());
  require(path_size>0 && size_t(path_size)<executable_path.size(), "cannot resolve executable");
  const auto executable=read_regular(std::string(executable_path.data(),path_size));
  require(string(build.at("golden_gate_build_hash"))==durable_build_hash &&
          string(build.at("rtl_build_hash"))==durable_rtl_hash &&
          string(build.at("state_manifest_hash"))==durable_runtime_hash &&
          string(build.at("target_configuration"))==durable_profile &&
          string(build.at("simulator_build_hash"))==hex(sha256(executable)), "incompatible build/manifest/executable");
  require(root.at("records").is_array(), "expected record array");
  const auto &records=root.at("records").as_array();
  require(records.size()==1+std::size(durable_generated)+std::size(durable_harness)+std::size(durable_native),
          "incomplete record membership");
  rows_t rows; std::string_view previous;
  for(const auto &r:records) {
    const auto &o=object(r); keys(o,{"owner","value","width"});
    const auto owner=string(o.at("owner")), v=string(o.at("value")); const auto width=natural(o.at("width"));
    require(!owner.empty() && (previous.empty() || previous<owner), "duplicate/unsorted owner"); previous=owner;
    require(width>0 && width/4+(width%4!=0)==v.size() && !v.empty() &&
            v.find_first_not_of("0123456789abcdef")==std::string_view::npos, "invalid bit vector");
    require(width%4==0 || scalar(v.substr(0,1))<(1ULL<<(width%4)), "nonzero record padding");
    rows.emplace(owner,&o);
  }
  require(natural(record(rows,"cut/host_sample").at("width"))==64, "invalid host sample width");
  const auto sample=scalar(value(rows,"cut/host_sample"));
  for(const auto &e:durable_generated) entry(rows,e,true);
  for(const auto &e:durable_harness) entry(rows,e,false);
  require(cycle==scalar(value(rows,durable_target_cycle_owner)), "target cycle disagrees with bound counter");
  std::ostringstream result;
  result<<"FSAGG1 "<<durable_runtime_hash<<' '<<cycle<<' '<<sample<<' '<<std::size(durable_native)<<'\n';
  for(const auto &e:durable_native) {
    const std::string owner=std::string("host/")+e.owner; const auto &r=record(rows,owner); const auto v=string(r.at("value"));
    require(natural(r.at("width"))%8==0, "invalid opaque native bytes");
    result<<"HOST "<<e.owner<<' '<<e.schema<<' '<<v.size()/2<<' '<<v<<'\n';
  }
  std::ostringstream g,h; uint64_t words=0; for(const auto &e:durable_generated) words+=e.depth;
  g<<"FSGRTL2 "<<durable_generated_hash<<' '<<durable_build_hash<<" settled_host_negedge "<<words<<'\n';
  for(const auto &e:durable_generated) g<<e.path<<' '<<e.width<<' '<<e.depth<<' '<<value(rows,e.owner)<<'\n';
  h<<"FSHRNS1 "<<durable_harness_hash<<' '<<durable_harness_source_hash<<" settled_host_negedge "<<std::size(durable_harness)<<'\n';
  for(const auto &e:durable_harness) h<<e.path<<' '<<e.width<<' '<<value(rows,e.owner)<<'\n';
  for(const auto &[name,text]:{std::pair{"GENERATED",g.str()},std::pair{"HARNESS",h.str()}})
    result<<name<<' '<<text.size()<<'\n'<<text;
  return result.str();
}
