#include "durable_restore.h"
#include <array>
#include <cerrno>
#include <cstring>
#include <cstdio>
#include <fcntl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>

durable_publication_error_t::durable_publication_error_t(bool visible, const std::string &message)
  : std::runtime_error(std::string("durable publication: ")+
      (visible ? "complete replacement visible; directory durability unconfirmed: " : "destination unchanged: ")+message),
    published(visible) {}

namespace {
struct descriptor_t {
  int value=-1;
  ~descriptor_t() { if(value>=0) close(value); }
};
void checked(bool ok, const char *operation) {
  if(!ok) throw std::runtime_error(std::string(operation)+": "+std::strerror(errno));
}
void regular_destination(int directory, const std::string &name) {
  struct stat status{};
  if(fstatat(directory,name.c_str(),&status,AT_SYMLINK_NOFOLLOW)==0) {
    if(!S_ISREG(status.st_mode)) throw std::runtime_error("destination must be a regular file");
  } else checked(errno==ENOENT,"stat destination");
}
}

void publish_durable_capture(const std::string &destination, const std::string &snapshot) {
  // Validation/encoding precede every output syscall. Never publish a partial
  // owner inventory, a high clock cut, or an incompatible target-cycle field.
  const auto image=encode_durable_capture(snapshot);
  descriptor_t directory,temporary;
  std::string pending;
  bool published=false;
  try {
    const auto slash=destination.rfind('/');
    const auto parent=slash==std::string::npos ? "." : slash==0 ? "/" : destination.substr(0,slash);
    const auto name=slash==std::string::npos ? destination : destination.substr(slash+1);
    if(name.empty() || name=="." || name==".." || destination.find('\0')!=std::string::npos)
      throw std::runtime_error("invalid destination pathname");
    directory.value=open(parent.c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    checked(directory.value>=0,"open destination directory");
    regular_destination(directory.value,name);
    checked(!fsync(directory.value),"preflight directory sync");
    std::array<unsigned char,16> random{};
    size_t offset=0;
    while(offset<random.size()) {
      const auto n=getrandom(random.data()+offset,random.size()-offset,0);
      if(n<0 && errno==EINTR) continue;
      checked(n>0,"temporary name randomness"); offset+=size_t(n);
    }
    // A bounded name also works for a destination already at NAME_MAX.
    std::string candidate=".fsckpt.pending-";
    for(auto byte:random) { candidate+="0123456789abcdef"[byte>>4]; candidate+="0123456789abcdef"[byte&15]; }
    temporary.value=openat(directory.value,candidate.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    checked(temporary.value>=0,"create temporary checkpoint");
    pending.swap(candidate); // No allocation after taking ownership of the file.
    offset=0;
    while(offset<image.size()) {
      const auto n=write(temporary.value,image.data()+offset,image.size()-offset);
      if(n<0 && errno==EINTR) continue;
      if(n==0) throw std::runtime_error("write checkpoint returned zero bytes");
      checked(n>0,"write checkpoint"); offset+=size_t(n);
    }
    checked(!fsync(temporary.value),"sync checkpoint");
    const int fd=temporary.value; temporary.value=-1;
    checked(!close(fd),"close checkpoint");
    regular_destination(directory.value,name);
    checked(!renameat(directory.value,pending.c_str(),directory.value,name.c_str()),"rename checkpoint");
    published=true; pending.clear();
    checked(!fsync(directory.value),"commit directory sync");
    const int dir=directory.value; directory.value=-1;
    checked(!close(dir),"close destination directory");
  } catch(const std::exception &error) {
    if(!pending.empty()) unlinkat(directory.value,pending.c_str(),0);
    throw durable_publication_error_t(published,error.what());
  }
}
