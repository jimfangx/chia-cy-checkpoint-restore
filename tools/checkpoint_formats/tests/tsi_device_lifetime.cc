// Actual production HTIF device resources at suspended host coroutine cuts.
// This checks process-local lifetime, not semantic CPU checkpoint admission.
#include "fesvr/firesim_tsi.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <fcntl.h>
#include <unistd.h>

static void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}

static std::map<int, std::string> descriptors() {
  std::map<int, std::string> result;
  const auto directory = "/proc/" + std::to_string(getpid()) + "/fd";
  for (const auto &entry : std::filesystem::directory_iterator(directory)) {
    const auto target = std::filesystem::read_symlink(entry.path()).string();
    if (target != directory) result.emplace(std::stoi(entry.path().filename()), target);
  }
  return result;
}

static void packet(firesim_tsi_t &tsi, const std::vector<uint32_t> &expected) {
  for (auto word : expected)
    require(tsi.data_available() && tsi.recv_word() == word, "production device packet differs");
  require(!tsi.data_available(), "extra production device serial word");
}

static void start(firesim_tsi_t &tsi) {
  tsi.tick(); tsi.tick();
  firesim_loadmem_t request;
  std::array<uint8_t, 16> bytes{};
  require(tsi.recv_loadmem_write_req(request) && request.addr == 0x80000000 && request.size == 16,
          "wrong ELF initial write");
  tsi.recv_loadmem_data(bytes.data(), 16); tsi.tick();
  require(tsi.recv_loadmem_read_req(request) && request.addr == 0x80001000 && request.size == 8,
          "wrong ELF partial read");
  tsi.send_loadmem_word(0xaabbccdd); tsi.send_loadmem_word(0x11223344); tsi.tick();
  require(tsi.recv_loadmem_write_req(request) && request.addr == 0x80001000 && request.size == 8,
          "wrong ELF merged write");
  tsi.recv_loadmem_data(bytes.data(), 8); tsi.set_loaded_in_target(true); tsi.tick();
  packet(tsi, {0, 0x80002000, 0, 1, 0});
}

static void cut(firesim_tsi_t &tsi, const std::string &name) {
  if (name == "pristine") return;
  if (name == "loader") { tsi.tick(); return; }
  start(tsi);
  if (name == "poll") return;
  if (name == "poll-partial") { tsi.send_word(0); tsi.tick(); return; }
  if (name == "idle") {
    tsi.send_word(0); tsi.send_word(0); tsi.tick();
    require(!tsi.busy(), "idle host remained busy");
    return;
  }
  if (name == "bcd-pending") {
    tsi.send_word(0); tsi.send_word(0x01000000); tsi.tick();
    packet(tsi, {1, 0x80002000, 0, 1, 0, 0, 0, 0, 0x80002000, 0, 1, 0});
    widget_checkpoint_config_t expected(26, {1, 1048576});
    expected.word(1); expected.word(uint64_t(1) << 56);
    require(tsi.bcd_owner().save_checkpoint() == expected.bytes, "missing pending BCD command");
    return;
  }
  if (name == "syscall-pending" || name == "syscall-partial" || name == "syscall-returned") {
    tsi.send_word(0x80003000); tsi.send_word(0); tsi.tick();
    packet(tsi, {1, 0x80002000, 0, 1, 0, 0, 0, 0, 0x80003000, 0, 15, 0});
    if (name == "syscall-pending") return;
    tsi.send_word(93); tsi.tick();
    if (name == "syscall-partial") return;
    for (unsigned i = 1; i < 16; ++i) tsi.send_word(0);
    tsi.tick();
    std::vector<uint32_t> expected{1, 0x80003000, 0, 15, 0}; expected.resize(21, 0);
    expected.insert(expected.end(), {0, 0x80002008, 0, 1, 0}); packet(tsi, expected);
    // Installed sys_exit has returned; its response still awaits fromhost.
    require(!tsi.done() && tsi.exit_code() == 0, "sys_exit caller did not suspend before response");
    return;
  }
  require(name == "pass" || name == "fail", "unknown device lifetime cut");
  tsi.send_word(name == "pass" ? 1 : 3); tsi.send_word(0); tsi.tick();
  packet(tsi, {1, 0x80002000, 0, 1, 0, 0, 0});
  require(tsi.done() && tsi.exit_code() == (name == "pass" ? 0 : 1), "installed stop/exit differs");
}

static int run(const char *source, const char *destination) {
  try {
    const std::filesystem::path out(destination); std::filesystem::create_directories(out);
    // Use a deterministic empty terminal. No pending input is consumed or serialized.
    const auto input = out / "input.bin";
    { std::ofstream file(input, std::ios::binary); require(bool(file), "cannot write terminal input"); }
    const int fd = ::open(input.c_str(), O_RDONLY);
    require(fd >= 0 && ::dup2(fd, 0) == 0, "cannot bind terminal input"); ::close(fd);
    const auto baseline = descriptors();
    size_t instances = 0, suspended = 0, returned = 0;
    for (const std::string name : {"pristine", "loader", "poll", "poll-partial", "idle", "bcd-pending",
                                   "syscall-pending", "syscall-partial", "syscall-returned", "pass", "fail"}) {
      for (unsigned repetition = 0; repetition < 16; ++repetition) {
        std::vector<std::string> args{"device-lifetime", "+permissive", "+no_hart0_msip", "+permissive-off", source};
        std::vector<char *> argv; for (auto &arg : args) argv.push_back(arg.data());
        {
          firesim_tsi_t tsi(argv.size(), argv.data(), true);
          require(descriptors().size() == baseline.size() + 3, "installed HTIF descriptor initialization differs");
          cut(tsi, name);
          const bool complete = name == "pass" || name == "fail";
          const bool session = name != "pristine" && name != "loader" && !complete;
          require(descriptors().size() == baseline.size() + (session ? 6 : 3), "running device descriptor ownership differs");
          if (complete) ++returned;
          else if (name != "pristine") ++suspended;
        }
        const auto after = descriptors();
        if (after != baseline) {
          std::cerr << "DEVICE_RESOURCE_LEAK cut=" << name << " repetition=" << repetition
                    << " leaked_descriptors=" << (after.size() - baseline.size()) << '\n';
          return 3;
        }
        ++instances;
      }
      std::cout << "DEVICE_CUT cut=" << name << " repetitions=16 unchanged_descriptors=1\n";
    }
    require(instances == 176 && suspended == 128 && returned == 32, "incomplete lifetime coverage");
    std::cout << "DEFAULT_DEVICE_LIFETIME instances=" << instances << " suspended=" << suspended
              << " returned=" << returned << " leaked_descriptors=0 cpu_edges=0\n";
    return 0;
  } catch (const std::exception &error) { std::cerr << "FAIL " << error.what() << '\n'; return 2; }
}

#ifdef TSI_DEVICE_LIFETIME_DPI
extern "C" int tsi_device_lifetime(const char *source, const char *destination) { return run(source, destination); }
extern "C" void tsi_device_lifetime_exit(int code) { std::exit(code); }
#else
int main(int argc, char **argv) { if (argc != 3) return 2; return run(argv[1], argv[2]); }
#endif
