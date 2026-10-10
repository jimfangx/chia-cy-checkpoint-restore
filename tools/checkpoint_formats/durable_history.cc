#include "durable_history.h"
#include "durable_restore.h"
#include <boost/json.hpp>
#include <openssl/evp.h>
#include <array>
#include <cerrno>
#include <charconv>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <iomanip>
#include <set>
#include <sstream>
#include <sys/file.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

durable_history_error_t::durable_history_error_t(bool visible, const std::string &message)
  : std::runtime_error("durable history: index_committed="+std::to_string(visible)+": "+message),
    committed(visible) {}

namespace {
constexpr const char *schema="firesim.rolling.native.level1.v1";
constexpr const char *index_name="history.json";
struct fd_t {
  int value=-1;
  ~fd_t() { if(value>=0) close(value); }
};
struct close_dir_t { void operator()(DIR *dir) const { closedir(dir); } };
void require(bool ok, const char *message) {
  if(!ok) throw std::runtime_error(message);
}
void checked(bool ok, const char *operation) {
  if(!ok) throw std::runtime_error(std::string(operation)+": "+std::strerror(errno));
}
std::string sha(std::string_view bytes) {
  std::array<unsigned char,32> digest{}; unsigned length=0;
  require(EVP_Digest(bytes.data(),bytes.size(),digest.data(),&length,EVP_sha256(),nullptr)==1 &&
          length==digest.size(), "SHA256 failure");
  std::string result;
  for(auto byte:digest) { result+="0123456789abcdef"[byte>>4]; result+="0123456789abcdef"[byte&15]; }
  return result;
}
void keys(const boost::json::object &value, std::initializer_list<const char *> names) {
  require(value.size()==names.size(), "missing/extra history fields");
  for(auto name:names) require(value.contains(name), "missing history field");
  std::string previous;
  for(const auto &row:value) {
    const std::string key(row.key());
    require(previous.empty() || previous<key, "noncanonical history keys"); previous=key;
  }
}
uint64_t number(const boost::json::value &value) {
  require(value.is_uint64() || (value.is_int64() && value.as_int64()>=0), "invalid history number");
  return value.is_uint64()?value.as_uint64():uint64_t(value.as_int64());
}
std::string text(const boost::json::value &value) {
  require(value.is_string(), "invalid history string"); return std::string(value.as_string());
}
uint64_t cycle_of(const std::string &snapshot) {
  std::istringstream input(snapshot); std::string magic,hash; uint64_t cycle=0;
  require(bool(input>>magic>>hash>>cycle) && magic=="FSAGG1", "invalid validated snapshot header");
  return cycle;
}
struct lock_t {
  fd_t fd;
  explicit lock_t(int directory) {
    fd.value=openat(directory,".history.lock",O_RDWR|O_CREAT|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC,0600);
    checked(fd.value>=0,"open history lock");
    struct stat state{};
    require(!fstat(fd.value,&state) && S_ISREG(state.st_mode), "history lock must be regular");
    int result;
    do { result=flock(fd.value,LOCK_EX); } while(result<0 && errno==EINTR);
    checked(result==0,"lock history");
  }
};
}

struct durable_history_t::impl_t {
  fd_t directory;
  uint64_t retention;
  std::string binding,prefix;

  std::string read(const std::string &name, bool missing=false) {
    fd_t fd;
    fd.value=openat(directory.value,name.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd.value<0 && missing && errno==ENOENT) return {};
    checked(fd.value>=0,"open history input");
    struct stat state{};
    require(!fstat(fd.value,&state) && S_ISREG(state.st_mode) && state.st_size>=0 &&
            uint64_t(state.st_size)<=256ULL*1024*1024, "invalid history input type/size");
    std::string bytes(size_t(state.st_size),'\0'); size_t offset=0;
    while(offset<bytes.size()) {
      const auto n=::read(fd.value,bytes.data()+offset,bytes.size()-offset);
      if(n<0 && errno==EINTR) continue;
      require(n>0,"truncated history input"); offset+=size_t(n);
    }
    char extra; ssize_t n;
    do { n=::read(fd.value,&extra,1); } while(n<0 && errno==EINTR);
    require(n==0,"history input grew");
    // Distinguish a present empty index from ENOENT.
    require(!bytes.empty(),"empty history input"); return bytes;
  }
  std::string name(uint64_t cycle, const std::string &hash) {
    std::ostringstream out; out<<prefix<<std::setw(20)<<std::setfill('0')<<cycle<<'-'<<hash<<".fsckpt";
    return out.str();
  }
  std::string image(const boost::json::object &record) {
    keys(record,{"bytes","name","sha256","target_cycle"});
    const auto cycle=number(record.at("target_cycle"));
    const auto hash=text(record.at("sha256")), filename=text(record.at("name"));
    require(hash.size()==64 && hash.find_first_not_of("0123456789abcdef")==std::string::npos &&
            filename==name(cycle,hash), "invalid history filename/hash");
    auto bytes=read(filename);
    require(bytes.size()==number(record.at("bytes")) && sha(bytes)==hash, "retained image integrity failure");
    require(cycle_of(validate_durable_restore(bytes))==cycle, "retained image cycle mismatch");
    return bytes;
  }
  boost::json::object index() {
    const auto bytes=read(index_name,true);
    if(bytes.empty()) return {{"binding",binding},{"records",boost::json::array{}},
                             {"retention",retention},{"schema",schema}};
    boost::json::parse_options options; options.max_depth=4;
    const auto parsed=boost::json::parse(bytes,{},options);
    require(parsed.is_object() && boost::json::serialize(parsed)==bytes, "noncanonical/duplicate history index");
    const auto &doc=parsed.as_object(); keys(doc,{"binding","records","retention","schema"});
    require(text(doc.at("binding"))==binding && text(doc.at("schema"))==schema &&
            number(doc.at("retention"))==retention && doc.at("records").is_array(), "incompatible history binding");
    const auto &records=doc.at("records").as_array();
    require(!records.empty() && records.size()<=retention, "invalid retained history count");
    bool first=true; uint64_t previous=0;
    for(const auto &r:records) {
      require(r.is_object(), "invalid history record"); image(r.as_object());
      const auto cycle=number(r.as_object().at("target_cycle"));
      require(first || cycle>previous, "history cycles must increase"); first=false; previous=cycle;
    }
    return doc;
  }
  std::string write(const std::string &bytes) {
    std::array<unsigned char,16> random{}; size_t offset=0;
    while(offset<random.size()) {
      const auto n=getrandom(random.data()+offset,random.size()-offset,0);
      if(n<0 && errno==EINTR) continue;
      checked(n>0,"history temporary randomness"); offset+=size_t(n);
    }
    std::string pending=".history.pending-";
    for(auto byte:random) { pending+="0123456789abcdef"[byte>>4]; pending+="0123456789abcdef"[byte&15]; }
    fd_t fd;
    fd.value=openat(directory.value,pending.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    checked(fd.value>=0,"create history temporary");
    try {
      offset=0;
      while(offset<bytes.size()) {
        const auto n=::write(fd.value,bytes.data()+offset,bytes.size()-offset);
        if(n<0 && errno==EINTR) continue;
        require(n!=0,"history write returned zero"); checked(n>0,"write history temporary"); offset+=size_t(n);
      }
      checked(!fsync(fd.value),"sync history temporary");
      const int closing=fd.value; fd.value=-1; checked(!close(closing),"close history temporary");
    } catch(...) { unlinkat(directory.value,pending.c_str(),0); throw; }
    return pending;
  }
  void prune(const boost::json::object &doc) {
    std::set<std::string> retained;
    for(const auto &r:doc.at("records").as_array()) retained.insert(text(r.as_object().at("name")));
    fd_t listing;
    listing.value=openat(directory.value,".",O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    checked(listing.value>=0,"open pinned history listing");
    std::unique_ptr<DIR,close_dir_t> stream(fdopendir(listing.value));
    checked(bool(stream),"list pinned history directory");
    listing.value=-1;
    std::vector<std::string> obsolete;
    errno=0;
    while(auto *entry=readdir(stream.get())) {
      const std::string filename=entry->d_name;
      // Foreign and pending files survive; only this build's complete canonical
      // immutable namespace can be reclaimed. Validate ALL before any deletion.
      if(filename.rfind(prefix,0)==0 && !retained.count(filename)) {
        const auto rest=filename.substr(prefix.size());
        if(rest.size()!=20+1+64+7 || rest[20]!='-' || rest.substr(85)!=".fsckpt" ||
           rest.substr(0,20).find_first_not_of("0123456789")!=std::string::npos) continue;
        uint64_t cycle=0;
        const auto parsed=std::from_chars(rest.data(),rest.data()+20,cycle);
        require(parsed.ec==std::errc{} && parsed.ptr==rest.data()+20,"invalid orphan cycle");
        const auto bytes=read(filename);
        image({{"bytes",bytes.size()},{"name",filename},{"sha256",rest.substr(21,64)},{"target_cycle",cycle}});
        obsolete.push_back(filename);
      }
      errno=0;
    }
    checked(errno==0,"read history directory");
    for(const auto &filename:obsolete) checked(!unlinkat(directory.value,filename.c_str(),0),"prune old history image");
    checked(!fsync(directory.value),"sync history retention");
  }
  impl_t(const std::string &path, uint64_t count) : retention(count), binding(sha(durable_build_identity_json())),
      prefix("snapshot-"+binding+"-") {
    require(retention>0 && path.find('\0')==std::string::npos,"invalid history configuration");
    directory.value=open(path.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    checked(directory.value>=0,"open private history directory");
    lock_t lock(directory.value);
    const auto doc=index();
    if(!doc.at("records").as_array().empty()) {
      checked(!fsync(directory.value),"recover history commit"); prune(doc);
    }
  }
  void publish(const std::string &snapshot) {
    // Complete validation precedes output access. Membership and native state
    // stability come from the live collector, not from host metadata.
    const auto bytes=encode_durable_capture(snapshot);
    const auto cycle=cycle_of(snapshot);
    const auto hash=sha(bytes);
    const boost::json::object record{{"bytes",bytes.size()},{"name",name(cycle,hash)},
                                    {"sha256",hash},{"target_cycle",cycle}};
    bool committed=false; std::string pending;
    try {
      lock_t lock(directory.value);
      auto doc=index(); auto &records=doc.at("records").as_array();
      require(records.empty() || cycle>number(records.back().as_object().at("target_cycle")),
              "new snapshot must advance target cycles");
      records.push_back(record);
      if(records.size()>retention) records.erase(records.begin());
      checked(!fsync(directory.value),"preflight history directory sync");
      pending=write(bytes); const auto filename=text(record.at("name"));
      if(linkat(directory.value,pending.c_str(),directory.value,filename.c_str(),0)) {
        checked(errno==EEXIST,"publish immutable history image");
        require(image(record)==bytes,"conflicting immutable history image");
      }
      checked(!unlinkat(directory.value,pending.c_str(),0),"unlink image temporary"); pending.clear();
      checked(!fsync(directory.value),"sync immutable history image");
      require(image(record)==bytes,"immutable history image readback changed");
      const auto encoded=boost::json::serialize(doc); pending=write(encoded);
      struct stat state{};
      if(!fstatat(directory.value,index_name,&state,AT_SYMLINK_NOFOLLOW))
        require(S_ISREG(state.st_mode),"history index must be regular");
      else checked(errno==ENOENT,"stat history index");
      checked(!renameat(directory.value,pending.c_str(),directory.value,index_name),"commit history index");
      committed=true; pending.clear();
      checked(!fsync(directory.value),"sync committed history index");
      require(boost::json::serialize(index())==encoded,"committed history readback changed");
      prune(doc);
    } catch(const std::exception &error) {
      if(!pending.empty()) unlinkat(directory.value,pending.c_str(),0);
      throw durable_history_error_t(committed,error.what());
    }
  }
};

durable_history_t::durable_history_t(const std::string &directory, uint64_t retention)
  : impl(std::make_unique<impl_t>(directory,retention)) {}
durable_history_t::~durable_history_t() = default;
void durable_history_t::publish(const std::string &snapshot) { impl->publish(snapshot); }
