// Component checks of the production pointer-free TSI read owner. External
// queues below are a separate fixture owner, never a complete CPU checkpoint.
#include "fesvr/loadmem_read.h"
#include <deque>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <cstdlib>

namespace fs = std::filesystem;
using reader_t = firesim_loadmem_read_t;
static uint64_t checks = 0;
static void require(bool test, const char *message) {
  if (!test) throw std::runtime_error(message);
}
template <class F> static void rejects(F action) {
  bool failed = false;
  try { action(); } catch (const std::exception &) { failed = true; }
  require(failed, "expected rejection"); ++checks;
}
static void store(const fs::path &path, const std::vector<uint8_t> &bytes) {
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char *>(bytes.data()), bytes.size());
  require(bool(out), "cannot write owner");
}
static std::vector<uint8_t> read(const fs::path &path) {
  std::ifstream in(path, std::ios::binary);
  require(bool(in), "missing owner");
  return {std::istreambuf_iterator<char>(in), {}};
}
static uint32_t response(uint64_t index) {
  return index % 3 == 0 ? 0 : uint32_t(0xf0000000ULL + index * 0x10203ULL);
}
struct fixture_t final : reader_t::services_t {
  uint64_t op = 0, writes = 2, issued = 0, supplied = 0;
  std::deque<uint32_t> responses;
  std::vector<std::string> calls;
  bool writes_pending() override {
    calls.push_back("PENDING " + std::to_string(writes)); return writes != 0;
  }
  void issue(uint64_t address, uint64_t bytes) override {
    calls.push_back("ISSUE " + std::to_string(address) + " " + std::to_string(bytes));
    require(!issued, "duplicate request"); issued = 1;
  }
  bool receive(uint32_t &word) override {
    if (responses.empty()) { calls.push_back("EMPTY"); return false; }
    word = responses.front(); responses.pop_front();
    calls.push_back("WORD " + std::to_string(word)); return true;
  }
  std::vector<uint8_t> save() const {
    widget_checkpoint_config_t config(15, {op, writes, issued, supplied, responses.size()});
    for (auto word : responses) config.word(word);
    return config.bytes;
  }
  void load(const std::vector<uint8_t> &bytes) {
    auto get = [&](size_t offset) {
      uint64_t value = 0;
      for (unsigned i=0;i<8;++i) value |= uint64_t(bytes.at(offset+i))<<(8*i);
      return value;
    };
    require(get(0)==0x3154504b43474457ULL && get(8)==1 && get(16)==15 && get(24)==5,
            "bad separate fixture owner");
    op=get(32); writes=get(40); issued=get(48); supplied=get(56);
    const auto count=get(64);
    require(count <= 3 && bytes.size()==72+count*8, "invalid fixture queue");
    responses.clear();
    for (uint64_t i=0;i<count;++i) responses.push_back(get(72+i*8));
  }
};

static void atomic_checks() {
  reader_t reader;
  const auto idle = reader.save_checkpoint();
  for (auto bytes : {0ULL, 1ULL, 3ULL, 4097ULL, ~0ULL}) {
    rejects([&] { reader.begin(0x1000, bytes); });
    require(reader.save_checkpoint()==idle, "bad begin changed owner"); ++checks;
  }
  rejects([&] { reader.begin(3, 4); });
  rejects([&] { reader.begin(~3ULL, 8); });
  rejects([&] { reader.finish(); });
  rejects([&] { reader.result(); });
  reader.begin(0x123456780ULL, 8);
  const auto pending = reader.save_checkpoint();
  rejects([&] { reader.begin(0x1000, 4); });
  require(reader.save_checkpoint()==pending, "duplicate begin changed owner"); ++checks;
  for (size_t size=0;size<pending.size();++size) {
    std::vector<uint8_t> bad(pending.begin(), pending.begin()+size);
    rejects([&] { reader.validate_checkpoint(bad); });
    rejects([&] { reader.load_checkpoint(bad); });
    require(reader.save_checkpoint()==pending, "truncation changed owner"); ++checks;
  }
  auto alter = [&](size_t offset, uint64_t value) {
    auto bad=pending;
    for (unsigned i=0;i<8;++i) bad.at(offset+i)=value>>(8*i);
    rejects([&] { reader.validate_checkpoint(bad); });
    rejects([&] { reader.load_checkpoint(bad); });
    require(reader.save_checkpoint()==pending, "invalid field changed owner"); ++checks;
  };
  // Configuration, phase, alignment, bounds, response cursor and length.
  for (size_t offset : {0,8,16,24,32,40}) alter(offset, 99);
  alter(48,5); alter(56,3); alter(64,0); alter(64,4097); alter(72,1ULL<<63);
  auto trailing=pending; trailing.push_back(0);
  rejects([&] { reader.load_checkpoint(trailing); });
  require(reader.save_checkpoint()==pending, "trailing byte changed owner"); ++checks;

  struct hostile_t final : reader_t::services_t {
    reader_t &reader; bool interrupt = false;
    explicit hostile_t(reader_t &reader) : reader(reader) {}
    bool writes_pending() override {
      rejects([&] { reader.save_checkpoint(); });
      rejects([&] { reader.load_checkpoint({}); });
      rejects([&] { reader.begin(0,4); });
      rejects([&] { reader.advance(*this); });
      if (interrupt) throw std::runtime_error("interrupted callback");
      return false;
    }
    void issue(uint64_t,uint64_t) override {}
    bool receive(uint32_t &) override { return false; }
  } hostile(reader);
  require(reader.advance(hostile)==reader_t::result_t::progress, "drain failed");
  reader_t poisoned; poisoned.begin(0,4); hostile_t fault(poisoned); fault.interrupt=true;
  rejects([&] { poisoned.advance(fault); });
  rejects([&] { poisoned.save_checkpoint(); });
  rejects([&] { poisoned.validate_checkpoint(pending); });
  rejects([&] { poisoned.load_checkpoint(pending); });
  rejects([&] { poisoned.advance(fault); });

  // Loading a complete image does not issue a request or replay a dequeue.
  fixture_t io; io.writes=0;
  reader.advance(io); io.responses={0,0xffffffff};
  reader.advance(io); reader.advance(io);
  const auto complete=reader.save_checkpoint();
  reader_t fresh; fresh.load_checkpoint(complete);
  require(fresh.result()==std::vector<uint32_t>({0,0xffffffff}) && io.responses.empty(),
          "complete read changed data"); ++checks;
  fresh.finish(); require(fresh.save_checkpoint()==idle, "finish retained read state"); ++checks;
}

static int run(int argc, const char **argv) {
  require(argc>=3, "mode/out required");
  std::string mode=argv[1]; fs::path out=argv[2]; fs::create_directories(out);
  if (mode=="check") { atomic_checks(); std::cout<<"ATOMIC_CHECKS "<<checks<<"\n"; return 0; }
  if (mode=="invalid") {
    require(argc==4,"invalid requires image"); reader_t reader;
    const auto before=reader.save_checkpoint(); bool failed=false;
    try { auto bytes=read(argv[3]); reader.validate_checkpoint(bytes); reader.load_checkpoint(bytes); }
    catch (const std::exception &error) { failed=true; std::cout<<"REJECT "<<error.what()<<"\n"; }
    require(failed && reader.save_checkpoint()==before,"partial restore");
    std::cout<<"UNCHANGED BEFORE_EDGES 0 BEFORE_REQUESTS 0 BEFORE_PUBLICATION 0\n"; return 0;
  }
  require(argc>=4,"length required");
  uint64_t bytes=std::stoull(argv[3]); fixture_t fixture; reader_t reader;
  std::vector<std::string> expected;
  if (mode=="reference") reader.begin(0x123456780ULL,bytes);
  else {
    require(argc>=6,"restore requires image/queue");
    auto image=read(argv[4]); auto queue=read(argv[5]);
    // Both owners validate before any externally visible restore operation.
    fixture_t validated; validated.load(queue); reader.validate_checkpoint(image);
    fixture.load(queue); reader.load_checkpoint(image);
    store(out/"initial.owner",reader.save_checkpoint());
    store(out/"initial.fixture",fixture.save());
    if (mode=="corrupt") {
      require(argc==7,"corrupt requires expected trace");
      std::ifstream lines(argv[6]); std::string line;
      while(std::getline(lines,line)) expected.push_back(line);
    }
  }
  std::ofstream trace(out/"trace"); size_t expected_cursor=0;
  auto boundary = [&](const std::vector<std::string> &lines) {
    for (auto &line:lines) {
      if (!expected.empty() && (expected_cursor>=expected.size() || line!=expected[expected_cursor])) {
        std::cout<<"FIRST_DIVERGENCE fixture_cycle="<<100+fixture.op
                 <<" acknowledged="<<fixture.op-1<<" expected="
                 <<(expected_cursor<expected.size()?expected[expected_cursor]:"END")<<" actual="<<line<<"\n";
        throw std::runtime_error("first divergent read boundary");
      }
      ++expected_cursor;
    }
    for (auto &line:lines) trace<<line<<"\n";
    trace.flush();
  };
  auto cut = [&]() {
    if(mode=="reference") {
      store(out/("cut-"+std::to_string(fixture.op)+".owner"),reader.save_checkpoint());
      store(out/("cut-"+std::to_string(fixture.op)+".fixture"),fixture.save());
    }
  };
  cut();
  // A restored completion retains a result that has not been acknowledged.
  // A restored idle image means this operation was already acknowledged.
  auto phase = [&]() { return reader.save_checkpoint().at(48); };
  if(phase()==0) return 0;
  while(phase()!=4) {
    fixture.calls.clear();
    auto result=reader.advance(fixture); ++fixture.op;
    std::vector<std::string> lines={"CALL "+std::to_string(fixture.op)+" C "+std::to_string(100+fixture.op)};
    lines.insert(lines.end(),fixture.calls.begin(),fixture.calls.end());
    if(result==reader_t::result_t::blocked) {
      lines.push_back("BLOCKED");
      if(fixture.writes) --fixture.writes;
      else {
        uint64_t count=std::min<uint64_t>(3,bytes/4-fixture.supplied);
        for(uint64_t i=0;i<count;++i) fixture.responses.push_back(response(fixture.supplied++));
      }
    } else lines.push_back(result==reader_t::result_t::complete?"COMPLETE":"PROGRESS");
    boundary(lines); cut();
  }
  ++fixture.op;
  std::vector<std::string> result={"CALL "+std::to_string(fixture.op)+" C "+std::to_string(100+fixture.op)};
  for(size_t i=0;i<reader.result().size();++i)
    result.push_back("RESULT["+std::to_string(i)+"] "+std::to_string(reader.result()[i]));
  boundary(result); reader.finish(); cut();
  require(fixture.supplied==bytes/4 && fixture.responses.empty(),"lost/duplicated queue words");
  if(!expected.empty()) require(expected_cursor==expected.size(),"missing continued boundary");
  return 0;
}

static int safe_run(int argc,const char **argv) {
  try { return run(argc,argv); }
  catch(const std::exception &error) { std::cerr<<"FAIL "<<error.what()<<"\n"; return 2; }
}
#ifdef LOADMEM_READ_CHECKPOINT_DPI
extern "C" int loadmem_read_checkpoint(const char *mode,const char *out,const char *bytes,
                                      const char *image,const char *queue,const char *expected) {
  const char *argv[]={"fixture",mode,out,bytes,image,queue,expected};
  int argc=std::string(mode)=="check"?3:std::string(mode)=="invalid"?4:
           std::string(mode)=="reference"?4:std::string(mode)=="corrupt"?7:6;
  const auto status = safe_run(argc,argv);
  // VCS defaults can give $fatal a successful process status. Keep an actual
  // nonzero native exit for failed checks/corruption, as the runner requires.
  if (status) std::exit(status);
  return status;
}
#else
int main(int argc,char **argv) { return safe_run(argc,const_cast<const char **>(argv)); }
#endif
