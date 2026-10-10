// Test-only syscall wrappers. The production runtime has no fault controls.
#include "../durable_history.h"
#include "../durable_restore.h"
#include "core/checkpoint_entry.h"
#include <algorithm>
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
#include <unistd.h>

static std::string fault;
static bool armed=false,committed=false;
static int temporary=-1,temporaries=0,dirsyncs=0,writes=0;
static bool failed(const char *name) {
  if(armed && fault==name) { errno=EIO; return true; } return false;
}
static void killed(const char *name) { if(armed && fault==name) kill(getpid(),SIGKILL); }
extern "C" int __real_openat(int,const char *,int,...);
extern "C" int __wrap_openat(int dir,const char *name,int flags,...) {
  const std::string path(name);
  if(armed && path=="history.json" && committed && failed("index-readback")) return -1;
  const bool pending=(flags&O_CREAT) && path.rfind(".history.pending-",0)==0;
  if(pending && failed(temporaries ? "index-open" : "image-open")) return -1;
  const auto fd=__real_openat(dir,name,flags,0600);
  if(armed && pending && fd>=0) { temporary=fd; ++temporaries; }
  return fd;
}
extern "C" ssize_t __real_write(int,const void *,size_t);
extern "C" ssize_t __wrap_write(int fd,const void *bytes,size_t count) {
  if(armed && fd==temporary) {
    ++writes;
    if(failed("write")) return -1;
    if(fault=="zero-write") return 0;
    if(fault=="eintr-short-write" && writes==1) { errno=EINTR; return -1; }
    if(fault=="partial-error" && writes>1) { errno=ENOSPC; return -1; }
    const auto n=__real_write(fd,bytes,(fault=="eintr-short-write" || fault=="partial-error" ||
                                      fault=="kill-partial") ? std::min(count,size_t(37)) : count);
    killed("kill-partial"); return n;
  }
  return __real_write(fd,bytes,count);
}
extern "C" int __real_fsync(int);
extern "C" int __wrap_fsync(int fd) {
  if(armed) {
    if(fd==temporary && failed(temporaries==1 ? "image-sync" : "index-sync")) return -1;
    struct stat state{};
    if(!fstat(fd,&state) && S_ISDIR(state.st_mode)) {
      ++dirsyncs;
      if(failed(dirsyncs==1 ? "preflight-sync" : dirsyncs==2 ? "image-directory-sync" :
                dirsyncs==3 ? "index-directory-sync" : "retention-sync")) return -1;
    }
  }
  const auto result=__real_fsync(fd);
  if(armed && fd==temporary) killed(temporaries==1 ? "kill-image-sync" : "kill-index-sync");
  return result;
}
extern "C" int __real_close(int);
extern "C" int __wrap_close(int fd) {
  const bool error=armed && fd==temporary && failed(temporaries==1 ? "image-close" : "index-close");
  const auto result=__real_close(fd);
  if(fd==temporary) temporary=-1;
  if(error) { errno=EIO; return -1; } return result;
}
extern "C" int __real_linkat(int,const char *,int,const char *,int);
extern "C" int __wrap_linkat(int a,const char *b,int c,const char *d,int flags) {
  if(failed("image-link")) return -1;
  const auto result=__real_linkat(a,b,c,d,flags);
  if(!result && fault=="image-readback") {
    const int fd=__real_openat(c,d,O_WRONLY,0600);
    char byte='x'; pwrite(fd,&byte,1,40); __real_close(fd);
  }
  killed("kill-image-link"); return result;
}
extern "C" int __real_renameat(int,const char *,int,const char *);
extern "C" int __wrap_renameat(int a,const char *b,int c,const char *d) {
  if(failed("index-rename")) return -1;
  killed("kill-before-index");
  const auto result=__real_renameat(a,b,c,d);
  if(armed && !result) committed=true;
  killed("kill-after-index"); return result;
}
extern "C" int __real_unlinkat(int,const char *,int);
extern "C" int __wrap_unlinkat(int dir,const char *name,int flags) {
  if(armed && std::string(name).rfind("snapshot-",0)==0) {
    if(failed("prune")) return -1;
    killed("kill-prune");
  }
  return __real_unlinkat(dir,name,flags);
}

int main(int argc,char **argv) {
  if(argc>1 && (std::string(argv[1])=="parse" || std::string(argv[1])=="parse-disabled")) {
    try {
      auto request=checkpoint_request_t::parse(std::vector<std::string>(argv+2,argv+argc));
      // A capability which did not explicitly authorize public periodic state
      // must reject it, exactly as an ordinary no-capability entry does.
      if(std::string(argv[1])=="parse-disabled") {
        struct unaudited_t : checkpoint_entry_t {
          action_t prepare(simif_t &,simulation_t &,const checkpoint_request_t &) override { return action_t::run; }
        } unaudited;
        unaudited.authorize_request(request);
      }
      std::cout<<"PARSED periodic="<<request.periodic()<<" durable="<<request.durable()<<'\n';
      return 0;
    } catch(const std::exception &error) { std::cout<<"REJECT parser "<<error.what()<<'\n'; return 1; }
  }
  if(argc!=6) return 2;
  try {
    durable_history_t history(argv[2],std::stoull(argv[3]));
    fault=argv[4]; armed=true;
    if(std::string(argv[5])=="recover") { puts("RECOVERED"); return 0; }
    if(std::string(argv[5])=="pin") {
      const std::string path=argv[2];
      if(rename(path.c_str(),(path+"-pinned").c_str()) || mkdir(path.c_str(),0700)) return 2;
    }
    std::ifstream input(argv[1],std::ios::binary);
    const std::string snapshot((std::istreambuf_iterator<char>(input)),{});
    if(!input) return 2;
    history.publish(snapshot);
    puts("PUBLISHED index_committed=1"); return 0;
  } catch(const durable_history_error_t &error) {
    std::cerr<<"REJECT index_committed="<<error.committed<<' '<<error.what()<<'\n'; return error.committed?3:1;
  } catch(const std::exception &error) { std::cerr<<"REJECT initialization "<<error.what()<<'\n'; return 1; }
}
