// See LICENSE for license details

#include "tsibridge.h"
#include "bridges/loadmem.h"
#include "core/simif.h"
#include "fesvr/firesim_tsi.h"
#include "fesvr/loadmem_read_transport.h"

#include <cassert>
#include <gmp.h>

char tsibridge_t::KIND;

tsibridge_t::tsibridge_t(simif_t &simif,
                         loadmem_t &loadmem_widget,
                         const TSIBRIDGEMODULE_struct &mmio_addrs,
                         int tsino,
                         const std::vector<std::string> &args,
                         bool has_mem,
                         int64_t mem_host_offset)
    : bridge_driver_t(simif, &KIND), mmio_addrs(mmio_addrs),
      loadmem_widget(loadmem_widget), has_mem(has_mem),
      mem_host_offset(mem_host_offset) {

  const std::string num_equals = std::to_string(tsino) + std::string("=");
  const std::string prog_arg = std::string("+prog") + num_equals;
  std::vector<std::string> args_vec;
  args_vec.push_back("firesim_tsi");

  // This particular selection is vestigial. You may change it freely.
  uint32_t step_size = 2004765L;

  // During the initial program phase speed up when FESVR is called
  // (i.e. speed up program loading when loadmem isn't/can't be used)
  // (disabled by default)
  bool fast_fesvr = false;

  // This particular selection is correlated to the amount of reset cycles.
  // It should be larger than the reset period.
  uint32_t wait_ticks = 8;

  // This particular selection is vestigial. You may change it freely.
  // This * wait_ticks is should be larger than the reset period.
  const uint32_t loading_step_size = fast_fesvr ? 8 : step_size;

  for (auto &arg : args) {
    if (arg.find("+fesvr-step-size=") == 0) {
      step_size = atoi(arg.c_str() + 17);
    }
    if (arg.find("+fesvr-enable-early-fast") == 0) {
      fast_fesvr = true;
    }
    if (arg.find("+fesvr-wait-ticks=") == 0) {
      wait_ticks = atoi(arg.c_str() + 18);
    }
    if (arg.find(prog_arg) == 0) {
      std::string clean_target_args =
          const_cast<char *>(arg.c_str()) + prog_arg.length();

      std::istringstream ss(clean_target_args);
      std::string token;
      while (std::getline(ss, token, ' ')) {
        args_vec.push_back(token);
      }
    } else if (arg.find(std::string("+prog")) == 0) {
      // Eliminate arguments for other fesvrs
    } else {
      args_vec.push_back(arg);
    }
  }

  int argc_count = args_vec.size() - 1;
  tsi_argv = new char *[args_vec.size()];
  for (size_t i = 0; i < args_vec.size(); ++i) {
    tsi_argv[i] = new char[args_vec[i].size() + 1];
    std::strcpy(tsi_argv[i], args_vec[i].c_str());
  }

  // debug for command line arguments
  printf("command line for program %d. argc=%d:\n", tsino, argc_count);
  for (int i = 0; i < argc_count; i++) {
    printf("%s ", tsi_argv[i + 1]);
  }
  printf("\n");

  tsi_argc = argc_count + 1;

  // Bind the selected bridge, every MMIO address, memory transport and the
  // exact per-TSI argv. Parent build/workload identity remains independently
  // required by the future aggregate coordinator.
  widget_checkpoint_config_t identity(17, {
      uint64_t(tsino), mmio_addrs.in_bits, mmio_addrs.in_valid,
      mmio_addrs.in_ready, mmio_addrs.out_bits, mmio_addrs.out_valid,
      mmio_addrs.out_ready, mmio_addrs.step_size, mmio_addrs.done,
      mmio_addrs.start, uint64_t(has_mem), uint64_t(mem_host_offset),
      loadmem_widget.get_mem_data_chunk(), uint64_t(tsi_argc)});
  for (const auto &arg : args_vec)
    identity.text(arg);
  control = std::make_unique<tsi_bridge_state_t>(
      std::move(identity), step_size, loading_step_size, wait_ticks, fast_fesvr);
}

tsibridge_t::~tsibridge_t() {
  if (fesvr)
    delete fesvr;
  if (tsi_argv) {
    for (int i = 0; i < tsi_argc; ++i) {
      if (tsi_argv[i])
        delete[] tsi_argv[i];
    }
    delete[] tsi_argv;
  }
}

class tsibridge_t::services_t final : public tsi_bridge_state_t::services_t {
public:
  explicit services_t(tsibridge_t &bridge) : bridge(bridge) {}
  void create() override {
    // Create ucontext on the execution thread, as in the original bridge.
    bridge.fesvr = new firesim_tsi_t(bridge.tsi_argc, bridge.tsi_argv, bridge.has_mem);
  }
  void write_step(uint32_t step) override { bridge.write(bridge.mmio_addrs.step_size, step); }
  void loaded_in_target() override { bridge.fesvr->set_loaded_in_target(true); }
  void go() override { bridge.go(); }
  bool done() override { return bridge.read(bridge.mmio_addrs.done); }
  void receive() override { bridge.recv(); }
  bool data_available() override { return bridge.fesvr->data_available(); }
  void advance() override { bridge.fesvr->tick(); }
  bool requests_pending() override { return bridge.fesvr->has_loadmem_reqs(); }
  void bypass() override { bridge.tsi_bypass_via_loadmem(); }
  bool terminated() override { return bridge.fesvr->done(); }
  void send() override { bridge.send(); }
  bool loaded_in_host() override { return bridge.fesvr->loaded_in_host(); }
private:
  tsibridge_t &bridge;
};

void tsibridge_t::init() {
  services_t services(*this);
  control->initialize(services);
}

void tsibridge_t::go() { write(mmio_addrs.start, 1); }

void tsibridge_t::send() {
  while (fesvr->data_available() && read(mmio_addrs.in_ready)) {
    write(mmio_addrs.in_bits, fesvr->recv_word());
    write(mmio_addrs.in_valid, 1);
  }
}

void tsibridge_t::recv() {
  while (read(mmio_addrs.out_valid)) {
    fesvr->send_word(read(mmio_addrs.out_bits));
    write(mmio_addrs.out_ready, 1);
  }
}

void tsibridge_t::handle_loadmem_read(firesim_loadmem_t loadmem) {
  if (!has_mem)
    throw std::runtime_error("TSI loadmem read without a memory widget");
  firesim_read_loadmem(loadmem_widget, loadmem.addr, loadmem.size, mem_host_offset,
                       [this](uint32_t word) { fesvr->send_loadmem_word(word); });
  // Switch back to fesvr for it to process read data
  fesvr->tick();
}

void tsibridge_t::handle_loadmem_write(firesim_loadmem_t loadmem) {
  assert(loadmem.size <= 4096);
  assert(has_mem);
  static char buf[4096]; // size chosen empirically based on chunk sizes
  fesvr->recv_loadmem_data(buf, loadmem.size);
  mpz_t data;
  mpz_init(data);
  mpz_import(data,
             (loadmem.size + sizeof(uint32_t) - 1) / sizeof(uint32_t),
             -1,
             sizeof(uint32_t),
             0,
             0,
             buf);
  loadmem_widget.write_mem_chunk(
      loadmem.addr + mem_host_offset, data, loadmem.size);
  mpz_clear(data);
}

void tsibridge_t::tsi_bypass_via_loadmem() {
  firesim_loadmem_t loadmem;
  while (fesvr->has_loadmem_reqs()) {
    // Check for reads first as they preceed a narrow write;
    if (fesvr->recv_loadmem_read_req(loadmem))
      handle_loadmem_read(loadmem);
    if (fesvr->recv_loadmem_write_req(loadmem))
      handle_loadmem_write(loadmem);
  }
}

void tsibridge_t::tick() {
  services_t services(*this);
  control->tick(services);
}

bool tsibridge_t::terminate() { return control->query([this] { return fesvr->done(); }); }
int tsibridge_t::exit_code() { return control->query([this] { return fesvr->exit_code(); }); }

std::vector<std::pair<std::string, std::vector<uint8_t>>>
tsibridge_t::inspect_host_components() const {
  control->save_checkpoint(); // Reject inspection inside an active bridge call.
  if (!fesvr) throw std::runtime_error("TSI polling audit: FESVR has not been created");
  return fesvr->inspect_polling_cut();
}
