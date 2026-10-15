// See LICENSE for license details
#include "firesim_tsi.h"
#include <inttypes.h>
#include <stdio.h>
#include <array>

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

static uint64_t cache_flush_address(int argc, char **argv) {
  uint64_t result = 0;
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg.find("+cflush_addr=0x") == 0)
      result = strtoull(arg.substr(15).c_str(), nullptr, 16);
  }
  return result;
}

static bool default_htif_devices(int argc, char **argv) {
  // Preserve installed HTIF for custom devices/chroot. Those callers remain
  // explicitly unowned; the complete CPU checkpoint profile stays disabled.
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    // getopt_long accepts abbreviations. Keep all long-option invocations on
    // the installed path so configured devices/chroot cannot be bypassed.
    if (arg.find("--") == 0) return false;
    for (const auto *option : {"+rfb", "--rfb", "+disk", "--disk", "+chroot", "--chroot"})
      if (arg.find(option) == 0) return false;
  }
  return true;
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
      owned_default_devices(default_htif_devices(argc, argv)),
      program_loader(can_have_loadmem, cache_flush_address(argc, argv)),
      host_control(idle_count(argc, argv)),
      init_control(owned_accesses(init_accesses), write_hart0_msip),
      initialization_config(22, {cache_flush_address(argc, argv)}) {

  // always use loadmem if the target supports it
  has_loadmem = can_have_loadmem;
}

int firesim_tsi_t::run_host() {
  if (!owned_default_devices) return htif_t::run();
  // Startup/ELF/symbol and stop/signature state remain upstream, separate from
  // this resumable poll caller. Do not publish a complete TSI checkpoint.
  start();
  htif_poll = std::make_unique<firesim_tsi_htif_poll_t>(get_tohost_addr(), get_fromhost_addr());
  syscall_t syscall(this);
  bcd_t bcd;
  device_list_t devices;
  devices.register_device(&syscall); devices.register_device(&bcd);
  class services_t final : public firesim_tsi_htif_poll_t::services_t {
  public:
    services_t(firesim_tsi_t &tsi, device_list_t &devices) : tsi(tsi), devices(devices) {}
    bool exiting() override { return tsi.should_exit(); }
    bool read(uint64_t address, uint64_t &value) override {
      if (tsi.serial_read.idle()) {
        tsi.flush_program_cache_lines(address, 8);
        tsi.serial_read.begin(address, 8);
      }
      firesim_tsi_serial_read_services_t service(tsi.serial);
      for (;;) {
        auto result = tsi.serial_read.advance(service);
        if (result == firesim_tsi_serial_read_t::result_t::blocked) return false;
        if (result == firesim_tsi_serial_read_t::result_t::complete) break;
      }
      const auto &words = tsi.serial_read.result();
      // FireSim TSI's audited transport is little endian, like the installed
      // HTIF's from_target/to_target operations for these recipes.
      value = uint64_t(words.at(0)) | (uint64_t(words.at(1)) << 32);
      tsi.serial_read.finish(); return true;
    }
    void write(uint64_t address, uint64_t value) override {
      const uint32_t words[2] = {uint32_t(value), uint32_t(value >> 32)};
      tsi.write_chunk(address, 8, words);
    }
    void dispatch(uint64_t value) override {
      command_t command(tsi.memif(), value, [owner = tsi.htif_poll.get()](uint64_t response) { owner->respond(response); });
      devices.handle_command(command);
    }
    void tick_devices() override { devices.tick(); }
    bool idle() override {
      if (tsi.host_control.current_phase() == firesim_tsi_host_control_t::phase_t::ready)
        tsi.host_control.begin_idle();
      return !tsi.host_control.advance_idle();
    }
  private:
    firesim_tsi_t &tsi;
    device_list_t &devices;
  } services(*this, devices);
  for (;;) {
    const auto result = htif_poll->advance(services);
    if (result == firesim_tsi_htif_poll_t::result_t::complete) break;
    if (result == firesim_tsi_htif_poll_t::result_t::blocked) switch_to_target();
  }
  stop();
  return exit_code();
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

void firesim_tsi_t::read_chunk(addr_t address, size_t bytes, void *destination) {
  if (program_loader.loadmem_mode()) load_mem_read(address, bytes, destination);
  else {
    flush_program_cache_lines(address, bytes);
    tsi_t::read_chunk(address, bytes, destination);
  }
}

void firesim_tsi_t::write_chunk(addr_t address, size_t bytes, const void *source) {
  if (program_loader.loadmem_mode()) load_mem_write(address, bytes, source);
  else {
    flush_program_cache_lines(address, bytes);
    tsi_t::write_chunk(address, bytes, source);
  }
}

void firesim_tsi_t::flush_program_cache_lines(addr_t address, size_t bytes) {
  const auto flush = program_loader.cache_flush_address();
  if (!flush) return;
  // Same packets, cache-line walk and non-yielding order as TestChip TSI.
  for (addr_t base = address & ~addr_t(63); base < address + bytes; base += 64) {
    const uint32_t data[2] = {uint32_t(base), uint32_t(base >> 32)};
    tsi_t::write_chunk(flush, sizeof(data), data);
  }
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

void firesim_tsi_t::tick() {
  if (initialization_component_restored)
    throw std::runtime_error("HTIF/context continuation after component restore is unsupported");
  switch_to_host();
}

void firesim_tsi_t::reset() {
  // after program loading, this function is called and spins until the target
  // thread/bridge has synced/drained all in-flight fesvr xacts
  host_control.begin_reset();
  try {
    while (!advance_initialization())
      switch_to_target();
  } catch (...) {
    init_control.interrupt();
    host_control.interrupt();
    throw;
  }
}

bool firesim_tsi_t::advance_initialization() {
  // Re-entry is selected entirely by owned state, including a suspended read.
  // No local return address, destination pointer or repeated flush/issue is
  // needed in a fresh object. The caller alone performs context switches.
  using phase_t = firesim_tsi_init_accesses_t::phase_t;
  using host_phase_t = firesim_tsi_host_control_t::phase_t;
  validate_initialization(host_control, init_control, serial_read);
  if (host_control.current_phase() == host_phase_t::ready) return true;
  if (host_control.current_phase() == host_phase_t::reset_wait) {
    if (host_control.advance_reset()) return false;
    init_control.begin();
  }
  firesim_tsi_serial_read_services_t services(serial);
  for (;;) {
    auto phase = init_control.phase();
    if (phase == phase_t::complete) {
      host_control.finish_reset();
      return true;
    }
    if (phase == phase_t::ready) {
      phase = init_control.select();
      if (phase == phase_t::complete) continue;
      if (phase == phase_t::read_child) {
        (fprintf)(stderr, "Reading %" PRIx64 " ...", init_control.address());
        // Initialization runs after TestChip leaves ELF load-memory mode.
        // The original virtual read routes here through flush then serial.
        flush_program_cache_lines(init_control.address(), sizeof(uint32_t));
        serial_read.begin(init_control.address(), sizeof(uint32_t));
      }
    }
    if (phase == phase_t::read_child) {
      for (;;) {
        const auto progress = serial_read.advance(services);
        if (progress == firesim_tsi_serial_read_t::result_t::blocked) return false;
        if (progress == firesim_tsi_serial_read_t::result_t::complete) break;
      }
      *init_control.read_destination() = serial_read.result().at(0);
      serial_read.finish();
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
  }
}

void firesim_tsi_t::validate_initialization(const firesim_tsi_host_control_t &host,
                                         const firesim_tsi_init_accesses_t &init,
                                         const firesim_tsi_serial_read_t &read) {
  using hp = firesim_tsi_host_control_t::phase_t;
  using ip = firesim_tsi_init_accesses_t::phase_t;
  const auto h = host.current_phase(); const auto i = init.phase();
  const bool waiting = h == hp::reset_wait && read.idle() &&
                       (i == ip::idle || i == ip::complete);
  const bool child = h == hp::reset_child && host.loaded_in_target() &&
                     i == ip::read_child && init.pending_read_data() == 0 &&
                     read.waiting_for(init.address(), sizeof(uint32_t));
  const bool complete = h == hp::ready && i == ip::complete && read.idle();
  if (!waiting && !child && !complete)
    throw std::runtime_error("incoherent or unsupported TSI initialization owners");
}

std::vector<uint8_t> firesim_tsi_t::save_initialization_checkpoint() const {
  validate_initialization(host_control, init_control, serial_read);
  auto result = initialization_config;
  for (const checkpoint_owner_t *owner : std::array<const checkpoint_owner_t *, 4>{
         &host_control, &init_control, &serial_read, &serial}) {
    const auto bytes = owner->save_checkpoint();
    result.word(bytes.size()); result.bytes.insert(result.bytes.end(), bytes.begin(), bytes.end());
  }
  return std::move(result.bytes);
}

void firesim_tsi_t::load_initialization_checkpoint(const std::vector<uint8_t> &image) {
  // Check current usability before constructing candidates; poisoned owners
  // cannot be rehabilitated by a restore. All candidate allocations and
  // cross-owner checks finish before four noexcept state swaps commit.
  if (host_context_initialized())
    throw std::runtime_error("TSI initialization restore requires an unstarted host context");
  host_control.save_checkpoint(); init_control.save_checkpoint();
  serial_read.save_checkpoint(); serial.save_checkpoint();
  auto host = host_control; auto init = init_control;
  auto read = serial_read; auto queues = serial;
  size_t offset = initialization_config.bytes.size();
  if (image.size() < offset ||
      !std::equal(initialization_config.bytes.begin(), initialization_config.bytes.end(), image.begin()))
    throw std::runtime_error("TSI initialization bundle configuration mismatch");
  for (checkpoint_owner_t *owner : std::array<checkpoint_owner_t *, 4>{&host, &init, &read, &queues}) {
    if (image.size() - offset < 8) throw std::runtime_error("missing TSI initialization owner");
    uint64_t size = 0;
    for (unsigned i = 0; i < 8; ++i) size |= uint64_t(image[offset+i]) << (8*i);
    offset += 8;
    if (size > image.size() - offset) throw std::runtime_error("truncated TSI initialization owner");
    owner->load_checkpoint(std::vector<uint8_t>(image.begin()+offset, image.begin()+offset+size));
    offset += size;
  }
  if (offset != image.size()) throw std::runtime_error("extra TSI initialization owner bytes");
  validate_initialization(host, init, read);
  host_control.swap_state(host); init_control.swap_state(init);
  serial_read.swap_state(read); serial.swap_state(queues);
  initialization_component_restored = true;
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
    // Preserve TestChip's initial yield and its exact loading interval. The
    // routing decision is now owned instead of the base's private is_loadmem.
    program_loader.begin();
    switch_to_target();
    program_loader.enter();
    htif_t::load_program();
    program_loader.finish();
  } catch (std::exception &e) {
    program_loader.interrupt();
    fprintf(stderr,
            "Caught Exception headed for the simulator (in TSI thread): %s.\n",
            e.what());
    throw std::runtime_error(
        e.what()); // runtime_error used here to throw exception in main thread
  } catch (...) {
    program_loader.interrupt();
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
