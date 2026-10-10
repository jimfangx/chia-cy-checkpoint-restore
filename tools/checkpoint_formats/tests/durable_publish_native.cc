// Faults live only in this test executable's linker wrappers, never in the
// runtime publisher. Each invocation exercises the real filesystem syscalls.
#include "../durable_restore.h"
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
#include <unistd.h>

static std::string fault;
static int directory=-1,temporary=-1,syncs=0,writes=0;
static bool injected=false;
static bool fail(const char *name) {
  if(fault!=name || injected) return false;
  injected=true; errno=EIO; return true;
}
static void killed(const char *name) { if(fault==name) raise(SIGKILL); }
extern "C" int __real_open(const char *,int,...);
extern "C" int __wrap_open(const char *path,int flags,...) {
  if(flags&O_DIRECTORY) {
    if(fail("directory-open")) return -1;
    return directory=__real_open(path,flags);
  }
  return __real_open(path,flags);
}
extern "C" int __real_openat(int,const char *,int,...);
extern "C" int __wrap_openat(int dir,const char *path,int flags,...) {
  if(fail("temporary-open")) return -1;
  return temporary=__real_openat(dir,path,flags,0600);
}
extern "C" ssize_t __real_write(int,const void *,size_t);
extern "C" ssize_t __wrap_write(int fd,const void *bytes,size_t size) {
  if(fd==temporary) {
    if(fail("write")) return -1;
    if(fault=="zero-write") return 0;
    if(fault=="partial-write-error" && writes++) { errno=ENOSPC; return -1; }
    if(fault=="eintr-short-write" && !injected) { injected=true; errno=EINTR; return -1; }
    const auto n=__real_write(fd,bytes,(fault=="partial-write-error" || fault=="kill-partial" || fault=="eintr-short-write") ? std::min(size,size_t(37)) : size);
    killed("kill-partial"); return n;
  }
  return __real_write(fd,bytes,size);
}
extern "C" int __real_fsync(int);
extern "C" int __wrap_fsync(int fd) {
  if(fd==temporary && fail("file-sync")) return -1;
  if(fd==directory && fail(syncs++ ? "directory-sync" : "preflight-sync")) return -1;
  const auto result=__real_fsync(fd);
  if(fd==temporary) killed("kill-file-sync");
  return result;
}
extern "C" int __real_close(int);
extern "C" int __wrap_close(int fd) {
  // Linux closes the descriptor even when reporting a delayed I/O error.
  const bool error=(fd==temporary && fail("file-close")) || (fd==directory && fail("directory-close"));
  const auto result=__real_close(fd);
  if(fd==temporary) temporary=-1;
  if(fd==directory) directory=-1;
  if(error) { errno=EIO; return -1; }
  return result;
}
extern "C" int __real_renameat(int,const char *,int,const char *);
extern "C" int __wrap_renameat(int a,const char *b,int c,const char *d) {
  if(fail("rename")) return -1;
  const auto result=__real_renameat(a,b,c,d); killed("kill-rename"); return result;
}
int main(int argc,char **argv) {
  if(argc!=4) return 2;
  fault=argv[3];
  std::ifstream input(argv[1],std::ios::binary);
  std::string snapshot((std::istreambuf_iterator<char>(input)),{});
  if(!input || (!fault.empty() && fault!="none" && fault!="eintr-short-write" && fault.rfind("kill-",0)!=0 &&
      fault!="directory-open" && fault!="temporary-open" && fault!="write" && fault!="zero-write" &&
      fault!="partial-write-error" && fault!="file-sync" && fault!="file-close" && fault!="rename" &&
      fault!="preflight-sync" && fault!="directory-sync" && fault!="directory-close")) return 2;
  try { publish_durable_capture(argv[2],snapshot); puts("PUBLISHED durable=1"); return 0; }
  catch(const durable_publication_error_t &error) {
    std::cerr<<"REJECT published="<<error.published<<" "<<error.what()<<'\n'; return error.published?3:1;
  } catch(const std::exception &error) { std::cerr<<"REJECT validation=1 "<<error.what()<<'\n'; return 1; }
}
