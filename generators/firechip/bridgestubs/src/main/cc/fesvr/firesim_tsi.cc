// See LICENSE for license details
#include "firesim_tsi.h"
#include <inttypes.h>
#include <stdio.h>

#define fprintf(stdout, fmt, ...) (0)

static size_t idle_count(int argc, char **argv) {
  size_t result = 10;
  std::vector<std::string> args(argv + 1, argv + argc);
  for (auto &arg : args) {
    if (arg.find("+idle-counts=") == 0)
      result = atoi(arg.c_str() + 13);
  }
  return result;
}

static std::vector<firesim_tsi_init_accesses_t::access_t>
owned_accesses(const std::vector<init_access_t> &accesses) {
  std::vector<firesim_tsi_init_accesses_t::access_t> result;
  result.reserve(accesses.size());
  for (const auto &a : accesses) result.push_back({a.address, a.stdata, a.store});
  return result;
}

firesim_tsi_t::firesim_tsi_t(int argc, char **argv, bool can_have_loadmem)
    : testchip_tsi_t(argc, argv, can_have_loadmem),
      host_control(idle_count(argc, argv)),
      init_control(owned_accesses(init_accesses), write_hart0_msip) {

  // always use loadmem if the target supports it
  has_loadmem = can_have_loadmem;
}

void firesim_tsi_t::idle() {
  host_control.begin_idle();
  try {
    while (host_control.advance_idle())
      switch_to_target();
  } catch (...) {
    host_control.interrupt();
    throw;
  }
}

void firesim_tsi_t::send_loadmem_word(uint32_t word) {
  loadmem_queues.push_response(word);
}

void firesim_tsi_t::load_mem_write(addr_t addr,
                                   size_t nbytes,
                                   const void *src) {
  fprintf(stdout,
          "firesim_tsi_t::load_mem_write addr: %" PRIx64 " nbytes: %" PRIu64
          "\n",
          addr,
          nbytes);
  fflush(stdout);

  loadmem_queues.enqueue_write(addr, nbytes, src);
}

void firesim_tsi_t::load_mem_read(addr_t addr, size_t nbytes, void *dst) {
  fprintf(stdout,
          "firesim_tsi_t::load_mem_read addr: %" PRIx64 " nbytes: %" PRIu64
          "\n",
          addr,
          nbytes);
  fflush(stdout);

  // The response cursor and data no longer live only on a suspended stack.
  // The caller/destination still belongs to HTIF's unsupported coroutine; do
  // not infer a complete TSI owner from this component's serializable state.
  class services_t final : public firesim_loadmem_read_t::services_t {
  public:
    explicit services_t(firesim_loadmem_queues_t &queues) : queues(queues) {}
    bool writes_pending() override { return queues.writes_pending(); }
    void issue(uint64_t address, uint64_t bytes) override {
      queues.enqueue_read(address, bytes);
    }
    bool receive(uint32_t &word) override {
      return queues.pop_response(word);
    }
  private:
    firesim_loadmem_queues_t &queues;
  } services(loadmem_queues);
  loadmem_read.begin(addr, nbytes);
  for (;;) {
    const auto progress = loadmem_read.advance(services);
    if (progress == firesim_loadmem_read_t::result_t::complete)
      break;
    if (progress == firesim_loadmem_read_t::result_t::blocked)
      switch_to_target();
  }
  const auto &words = loadmem_read.result();
  std::copy(words.begin(), words.end(), static_cast<uint32_t *>(dst));
  loadmem_read.finish();
}

void firesim_tsi_t::tick() { switch_to_host(); }

void firesim_tsi_t::reset() {
  // after program loading, this function is called and spins until the target
  // thread/bridge has synced/drained all in-flight fesvr xacts
  host_control.begin_reset();
  try {
    while (host_control.advance_reset())
      switch_to_target();
    fprintf(
        stdout,
        "firesim_tsi_t::reset done loading program. sending reset signal(s)\n");
    fflush(stdout);
    perform_owned_init_accesses();
    host_control.finish_reset();
  } catch (...) {
    init_control.interrupt();
    host_control.interrupt();
    throw;
  }
}

void firesim_tsi_t::perform_owned_init_accesses() {
  // Same TestChip order/routing and MSIP policy, with the current access and
  // read destination owned independently of the suspended reset stack.
  using phase_t = firesim_tsi_init_accesses_t::phase_t;
  init_control.begin();
  for (;;) {
    const auto phase = init_control.select();
    if (phase == phase_t::complete) return;
    if (phase == phase_t::read_child) {
      (fprintf)(stderr, "Reading %" PRIx64 " ...", init_control.address());
      read_chunk(init_control.address(), sizeof(uint32_t), init_control.read_destination());
    } else {
      if (phase == phase_t::write_child)
        (fprintf)(stderr, "Writing %" PRIx64 " with %x\n", init_control.address(), *init_control.write_source());
      write_chunk(init_control.address(), sizeof(uint32_t), init_control.write_source());
    }
    init_control.child_returned();
    if (phase == phase_t::read_child)
      (fprintf)(stderr, " got %x\n", init_control.read_result());
    else if (phase == phase_t::write_child)
      (fprintf)(stderr, "Done writing %" PRIx64 " with %x\n", init_control.address(), init_control.write_result());
    init_control.retire();
    if (phase == phase_t::msip_child) return;
  }
}

bool firesim_tsi_t::has_loadmem_reqs() {
  return loadmem_queues.requests_pending();
}

bool firesim_tsi_t::recv_loadmem_write_req(firesim_loadmem_t &loadmem) {
  firesim_loadmem_queues_t::request_t request;
  if (!loadmem_queues.pop_write(request))
    return false;
  loadmem.addr = request.address;
  loadmem.size = request.bytes;
  return true;
}

bool firesim_tsi_t::recv_loadmem_read_req(firesim_loadmem_t &loadmem) {
  firesim_loadmem_queues_t::request_t request;
  if (!loadmem_queues.pop_read(request))
    return false;
  loadmem.addr = request.address;
  loadmem.size = request.bytes;
  return true;
}

void firesim_tsi_t::recv_loadmem_data(void *buf, size_t len) {
  loadmem_queues.pop_write_data(buf, len);
}

// re-enable fprintfs in file
#undef fprintf

// try to catch exceptions in the htif thread (specifically from program
// loading)
// TODO: ideally you override the htif_t::run function but currently
// un-overrideable
void firesim_tsi_t::load_program() {
  try {
    testchip_tsi_t::load_program();
  } catch (std::exception &e) {
    fprintf(stderr,
            "Caught Exception headed for the simulator (in TSI thread): %s.\n",
            e.what());
    throw std::runtime_error(
        e.what()); // runtime_error used here to throw exception in main thread
  } catch (...) {
    // seriously, VCS will give you an unhelpful message if you let an exception
    // propagate catch it here and if we hit this, I can go remember how to
    // unwind the stack to print a trace
    fprintf(
        stderr,
        "Caught non std::exception headed for the simulator (in TSI thread)\n");
    throw std::runtime_error(
        "unknown"); // runtime_error used here to throw exception in main thread
  }
}
