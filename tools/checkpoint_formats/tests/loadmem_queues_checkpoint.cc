// Production queue component. The command stream/cursor is an independent
// fixture driver, not a saved HTIF context or a Rocket target-cycle sampler.
#include "fesvr/loadmem_queues.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>

namespace fs = std::filesystem;
static void require(bool value, const std::string &message) {
  if (!value) throw std::runtime_error(message);
}
static std::vector<uint8_t> read(const fs::path &path) {
  std::ifstream file(path, std::ios::binary); require(bool(file), "missing image/input");
  return {std::istreambuf_iterator<char>(file), {}};
}
static void save(const fs::path &path, const std::vector<uint8_t> &bytes) {
  std::ofstream file(path, std::ios::binary);
  file.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(file), "cannot save readback");
}
static std::vector<std::string> lines(const char *path) {
  std::ifstream file(path); require(bool(file), "missing command/oracle file");
  std::vector<std::string> result; std::string line;
  while (std::getline(file, line)) result.push_back(line);
  return result;
}
static std::vector<uint8_t> unhex(const std::string &text) {
  require(text.size() % 2 == 0, "invalid write bytes");
  std::vector<uint8_t> result;
  for (size_t i = 0; i < text.size(); i += 2) result.push_back(std::stoul(text.substr(i,2),nullptr,16));
  return result;
}
static std::string hex(const std::vector<uint8_t> &data) {
  const char *digits="0123456789abcdef"; std::string result;
  for(auto byte:data) {result += digits[byte>>4]; result += digits[byte&15];}
  return result;
}
static std::string operation(firesim_loadmem_queues_t &owner, const std::string &command) {
  std::istringstream input(command); std::string op; input >> op;
  std::ostringstream out; out << op;
  firesim_loadmem_queues_t::request_t request{0,0};
  if(op=="WRITE") {
    uint64_t address; std::string data; input>>address>>data; auto bytes=unhex(data);
    owner.enqueue_write(address,bytes.size(),bytes.data()); out<<" "<<address<<" "<<data;
  } else if(op=="READ") {
    uint64_t address,bytes; input>>address>>bytes; owner.enqueue_read(address,bytes); out<<" "<<address<<" "<<bytes;
  } else if(op=="TAKEW" || op=="TAKER") {
    const bool valid=op=="TAKEW" ? owner.pop_write(request) : owner.pop_read(request);
    out<<" "<<valid; if(valid) out<<" "<<request.address<<" "<<request.bytes;
  } else if(op=="DATA") {
    size_t count; input>>count; std::vector<uint8_t> bytes(count);
    owner.pop_write_data(bytes.data(),count); out<<" "<<count<<" "<<hex(bytes);
  } else if(op=="PUSH") {
    uint64_t value; input>>value; require(value<=UINT32_MAX,"bad fixture response");
    owner.push_response(value); out<<" "<<value;
  } else if(op=="POP") {
    uint32_t word=0; const bool valid=owner.pop_response(word); out<<" "<<valid; if(valid) out<<" "<<word;
  } else if(op=="PENDING") out<<" "<<owner.requests_pending()<<" "<<owner.writes_pending();
  else throw std::runtime_error("unknown fixture command");
  return out.str();
}
static int run(const char *mode, const char *destination, const char *commands,
               const char *expected, const char *image, const char *cut_text) {
  try {
    fs::path out(destination); fs::create_directories(out);
    firesim_loadmem_queues_t owner;
    if(std::string(mode)=="invalid") {
      uint32_t value=0x01020304; owner.enqueue_write(0x80000000,4,&value);
      const auto before=owner.save_checkpoint(); bool rejected=false;
      try {owner.load_checkpoint(read(image));} catch(const std::exception &) {rejected=true;}
      require(rejected && before==owner.save_checkpoint(),"invalid image partially restored/accepted");
      save(out/"unchanged.owner",before); std::cout<<"REJECTED_BEFORE_MUTATION\n"; return 0;
    }
    if(std::string(mode)=="check") {
      uint32_t value=1; owner.enqueue_write(0x80000000,4,&value);
      auto valid=owner.save_checkpoint(); size_t checks=0;
      auto reject=[&](auto call) {auto before=owner.save_checkpoint(); bool failed=false;
        try {call();} catch(const std::exception &) {failed=true;}
        require(failed && before==owner.save_checkpoint(),"non-atomic invalid operation"); ++checks;};
      for(size_t n=0;n<valid.size();++n) reject([&](){owner.load_checkpoint({valid.begin(),valid.begin()+n});});
      for(auto addr:{uint64_t(1),UINT64_MAX-uint64_t(3)})
        reject([&](){owner.enqueue_read(addr,8);});
      for(auto bytes:{uint64_t(0),uint64_t(3),uint64_t(4097),UINT64_MAX})
        reject([&](){owner.enqueue_write(0,bytes,&value);});
      reject([&](){owner.pop_write_data(&value,1);});
      firesim_loadmem_queues_t::request_t request; owner.pop_write(request);
      reject([&](){owner.pop_write(request);});
      reject([&](){owner.pop_write_data(&value,5);});
      reject([&](){owner.pop_write_data(nullptr,1);});
      std::cout<<"ATOMIC_CHECKS "<<checks<<"\n"; return 0;
    }
    const auto ops=lines(commands), oracle=lines(expected);
    require(ops.size()==oracle.size(),"incomplete independent oracle");
    const size_t cut=std::stoull(cut_text); require(cut<=ops.size(),"invalid driver cursor");
    if(std::string(mode)!="reference") owner.load_checkpoint(read(image));
    const size_t first=std::string(mode)=="reference" ? 0 : cut;
    save(out/"preedge.owner",owner.save_checkpoint());
    save(out/("cut-"+std::to_string(first)+".owner"),owner.save_checkpoint());
    std::ofstream trace(out/"trace");
    size_t acknowledged=0;
    for(size_t i=first;i<ops.size();++i) {
      const auto actual="OP "+std::to_string(i+1)+" C "+std::to_string(101+i)+" "+operation(owner,ops[i]);
      if(actual!=oracle[i]) {
        std::ofstream fail(out/"first-divergence.json");
        fail<<"{\"operation\":"<<(i+1)<<",\"fixture_cycle\":"<<(101+i)
            <<",\"acknowledged\":"<<acknowledged<<",\"expected\":\""<<oracle[i]
            <<"\",\"actual\":\""<<actual<<"\"}\n";
        throw std::runtime_error("FIRST_DIVERGENCE "+actual);
      }
      trace<<actual<<"\n"; ++acknowledged;
      save(out/("cut-"+std::to_string(i+1)+".owner"),owner.save_checkpoint());
    }
    std::cout<<"COMPLETE_READBACK zero_edges=1 acknowledged="<<acknowledged<<"\n";
    return 0;
  } catch(const std::exception &error) {std::cerr<<"FAIL "<<error.what()<<"\n"; return 2;}
}
#ifdef LOADMEM_QUEUES_CHECKPOINT_DPI
extern "C" int loadmem_queues_checkpoint(const char *mode,const char *out,const char *commands,
                                          const char *expected,const char *image,const char *cut) {
  return run(mode,out,commands,expected,image,cut);
}
extern "C" void loadmem_queues_exit(int status) {std::exit(status);}
#else
int main(int argc,char **argv) {if(argc!=7) return 2; return run(argv[1],argv[2],argv[3],argv[4],argv[5],argv[6]);}
#endif
