// See LICENSE for license details
#include "firesim_tsi.h"
#include "tsi_polling_syscall.h"
#include "htif_dormant_proxy.h"
#include <inttypes.h>
#include <stdio.h>
#include <array>
#include <fcntl.h>
#include <sys/stat.h>
#include "elfloader_policy.h"

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

static std::unique_ptr<firesim_tsi_terminal_t> make_terminal_owner(int argc, char **argv) {
  const std::string prefix = "+checkpoint-terminal-input=";
  std::string path;
  bool requested = false;
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg.find(prefix) != 0) continue;
    if (requested) throw std::runtime_error("duplicate sealed terminal input option");
    requested = true; path = arg.substr(prefix.size());
  }
  if (!requested) return std::make_unique<firesim_tsi_terminal_t>();
  // Do not open a FIFO/device or wait for a terminal while constructing a cut.
  const int fd = open(path.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) throw std::runtime_error("cannot open sealed terminal input");
  struct close_t { int fd; ~close_t() { close(fd); } } file{fd};
  struct stat info;
  if (fstat(fd, &info) || !S_ISREG(info.st_mode) ||
      info.st_size < 0 || uint64_t(info.st_size) > firesim_tsi_terminal_t::maximum)
    throw std::runtime_error("sealed terminal input must be a bounded regular file");
  std::vector<uint8_t> input;
  std::array<uint8_t, 4096> buffer;
  for (;;) {
    const auto count = read(fd, buffer.data(), buffer.size());
    if (count < 0) {
      if (errno == EINTR) continue;
      throw std::runtime_error("cannot read sealed terminal input");
    }
    if (!count) break;
    if (input.size() + count > firesim_tsi_terminal_t::maximum)
      throw std::runtime_error("sealed terminal input grew beyond limit");
    input.insert(input.end(), buffer.begin(), buffer.begin() + count);
  }
  return std::make_unique<firesim_tsi_terminal_t>(std::move(input));
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
      runtime_memif(*this),
      owned_default_devices(default_htif_devices(argc, argv)),
      terminal(make_terminal_owner(argc, argv)),
      program_loader(can_have_loadmem, cache_flush_address(argc, argv)),
      bcd_identity(memif_write, serial),
      host_control(idle_count(argc, argv)),
      init_control(owned_accesses(init_accesses), write_hart0_msip),
      initialization_config(22, {cache_flush_address(argc, argv)}) {

  // always use loadmem if the target supports it
  has_loadmem = can_have_loadmem;
  metadata_arguments.assign(argv + 1, argv + argc);
  metadata_supported = owned_default_devices && !target_args().empty() && target_args()[0] != "none";
  for (const auto &arg : metadata_arguments)
    for (const auto *unsupported : {"+payload=", "+symbol-elf=", "+signature=", "+signature-granularity="})
      if (arg.find(unsupported) == 0) metadata_supported = false;
  bool requested = false;
  for (const auto &arg : metadata_arguments) {
    if (arg != "+checkpoint-syscall-exit") continue;
    if (requested) throw std::runtime_error("duplicate restricted syscall option");
    requested = true;
  }
  if (requested) {
    if (!metadata_supported || terminal->checkpoint_schema().empty())
      throw std::runtime_error("restricted syscall requires sealed default metadata");
    firesim_htif_require_lifecycle_api();
    syscall_exit = std::make_unique<firesim_tsi_syscall_exit_t>(*this, serial);
    firesim_htif_require_dormant_proxy_api().retire(*this);
  }
  metadata_pristine_components = metadata_components();
}

class firesim_tsi_t::polling_services_t final : public firesim_tsi_htif_poll_t::services_t {
  public:
    polling_services_t(firesim_tsi_t &tsi, device_list_t *devices, bool completing_exit = false)
      : tsi(tsi), devices(devices), completing_exit(completing_exit) {}
    bool exiting() override {
      if (completing_exit) return tsi.should_exit();
      if (!devices && !tsi.syscall_exit && tsi.should_exit())
        throw std::runtime_error("prepared polling component cannot service HTIF exit/signal");
      return (devices || tsi.syscall_exit) ? tsi.should_exit() : false;
    }
    void validate_command(uint64_t value) override {
      if (tsi.syscall_exit) {
        // An odd direct exit or other device is not this parent's command.
        // Reject it before polling clears tohost or enters installed dispatch.
        if (!value || value >> 48 || (value & 1) || value > 0xffffffffffffULL-63)
          throw std::runtime_error("restricted polling requires syscall-93 request address");
        return;
      }
      if (devices) return;
      const auto command = (value >> 48) & 255;
      // Identity dispatch has explicit caller/write/merge-read owners. Reject
      // all other unowned commands before the caller queues tohost's clear.
      if ((value >> 56) != 1 || (command > 1 && command != 255))
        throw std::runtime_error("prepared polling component requires sealed BCD read/write or identity");
    }
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
    bool dispatch(uint64_t value) override {
      validate_command(value);
      if (tsi.syscall_exit) return tsi.dispatch_syscall_exit(value);
      if ((value >> 48) == 0x1ff) {
        return tsi.dispatch_identity(value);
      }
      command_t command(tsi.memif(), value, [owner = tsi.htif_poll.get()](uint64_t response) { owner->respond(response); });
      validate_command(value);
      if (devices && tsi.metadata_supported && !(value >> 48) && (value & 1)) {
        tsi.htif_exit_component.request(value, [&] { devices->handle_command(command); });
        tsi.htif_exit_component.validate_observed(tsi.should_exit(), tsi.done(), tsi.exit_code());
      }
      else if (devices) devices->handle_command(command);
      else tsi.bcd->handle_command(command);
      return true;
    }
    void tick_devices() override {
      if (tsi.syscall_exit) return; // restricted dispatch admits no device work
      if (devices) devices->tick(); else tsi.bcd->tick();
    }
    bool idle() override {
      if (tsi.host_control.current_phase() == firesim_tsi_host_control_t::phase_t::ready)
        tsi.host_control.begin_idle();
      return !tsi.host_control.advance_idle();
    }
  private:
    firesim_tsi_t &tsi;
    device_list_t *devices;
    const bool completing_exit;
};


int firesim_tsi_t::run_host() {
  if (metadata_prepared || metadata_poisoned)
    throw std::runtime_error("HTIF/context continuation after metadata component preparation is unsupported");
  if (!owned_default_devices) return htif_t::run();
  // Startup/ELF/symbol and stop/signature state remain upstream, separate from
  // this resumable poll caller. Do not publish a complete TSI checkpoint.
  start();
  polling_active = true;
  htif_poll = std::make_unique<firesim_tsi_htif_poll_t>(get_tohost_addr(), get_fromhost_addr());
  bcd = std::make_unique<firesim_tsi_bcd_t>(*htif_poll, 1048576, terminal.get(),
      [this](uint64_t address, const firesim_tsi_bcd_t::identity_t &bytes) { write_identity(address, bytes); });
  // Restricted dispatch owns its syscall caller and never uses a device list.
  // Do not create an unused session (and three duplicated host descriptors)
  // on the suspended outer stack. The inherited HTIF proxy remains separate.
  if (!syscall_exit) default_devices = std::make_unique<default_devices_t>(*this, *bcd);
  polling_services_t services(*this, default_devices ? &default_devices->list : nullptr);
  for (;;) {
    const auto result = htif_poll->advance(services);
    if (result == firesim_tsi_htif_poll_t::result_t::complete) break;
    if (result == firesim_tsi_htif_poll_t::result_t::blocked) switch_to_target();
  }
  polling_active = false;
  if (metadata_supported && htif_exit_component.phase() == firesim_tsi_htif_exit_t::phase_t::requested)
    htif_exit_component.stop([this] { stop(); });
  else stop();
  // Preserve the upstream return-time release as well as suspended teardown.
  default_devices.reset();
  return exit_code();
}

std::vector<uint8_t> firesim_tsi_t::save_htif_exit_component() const {
  if (!owned_default_devices || !metadata_supported)
    throw std::runtime_error("HTIF direct exit component requires default devices and no signature");
  auto &self = const_cast<firesim_tsi_t &>(*this);
  htif_exit_component.validate_observed(should_exit(), self.done(), self.exit_code());
  return htif_exit_component.save_checkpoint();
}

std::map<std::string, uint64_t> firesim_tsi_t::load_payload(
    const std::string &payload, reg_t *entry, reg_t offset) {
  if (!metadata_supported || payload != target_args().at(0))
    return htif_t::load_payload(payload, entry, offset);
  // Preserve installed HTIF's path-search behavior for ordinary execution.
  // Such a load cannot supply this explicit-path metadata component.
  if (!preparing_metadata && access(payload.c_str(), F_OK) != 0) {
    metadata_supported = false;
    return htif_t::load_payload(payload, entry, offset);
  }
  auto bytes = preparing_metadata ? startup_metadata.elf : firesim_tsi_elf_bytes(payload);
  firesim_tsi_elf_snapshot_t snapshot(bytes);
  auto symbols = htif_t::load_payload(snapshot.path(), entry, offset);
  startup_metadata = {std::move(bytes), *entry, symbols};
  return symbols;
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::metadata_components() const {
  if (syscall_exit && syscall_exit->current.phase != firesim_tsi_syscall_exit_t::phase_t::idle)
    throw std::runtime_error("TSI metadata has an active syscall parent");
  if (!memif_read.idle()) throw std::runtime_error("TSI metadata has an active generic memif reader");
  if (!bcd_identity.idle()) throw std::runtime_error("TSI metadata has an active BCD identity caller");
  if (!memif_write.idle()) throw std::runtime_error("TSI metadata has an active memif write child");
  polling_cut_t result;
  for (const auto &[name, owner] : std::array<std::pair<const char *, const checkpoint_owner_t *>, 7>{{
      {"program", &program_loader}, {"init", &init_control}, {"host", &host_control},
      {"read", &serial_read}, {"serial", &serial}, {"loadmem-read", &loadmem_read},
      {"loadmem-queues", &loadmem_queues}}})
    result.emplace_back(name, owner->save_checkpoint());
  if (!terminal->checkpoint_schema().empty())
    result.emplace_back("terminal", terminal->save_checkpoint());
  return result;
}

std::vector<uint8_t> firesim_tsi_t::metadata_configuration(unsigned required_xlen) const {
  auto &self = const_cast<firesim_tsi_t &>(*this);
  widget_checkpoint_config_t config(25, {metadata_revision(), uint64_t(has_loadmem),
      uint64_t(self.get_target_endianness()), self.chunk_align(), self.chunk_max_size(), required_xlen});
  config.word(metadata_pristine_components.size());
  for (const auto &[name, bytes] : metadata_pristine_components) {
    config.word(name.size()); config.bytes.insert(config.bytes.end(), name.begin(), name.end());
    config.word(bytes.size()); config.bytes.insert(config.bytes.end(), bytes.begin(), bytes.end());
  }
  return std::move(config.bytes);
}

unsigned firesim_tsi_t::preflight_startup_metadata(const firesim_tsi_startup_metadata_t &candidate) {
  // Use the actual installed HTIF's expected_xlen, including changes through
  // an htif_t reference. A shadow of its nonvirtual setter would miss those.
  // Qualified load_payload changes only its local entry/symbol results; the
  // preloaded guard suppresses every target write, including partial writes.
  firesim_tsi_elf_snapshot_t snapshot(candidate.elf);
  reg_t entry = 0;
  firesim_elfloader_policy_t policy(snapshot.path(), &entry, 0x80000000);
  preparing_metadata = true;
  try {
    auto symbols = htif_t::load_payload(snapshot.path(), &entry, 0x80000000);
    preparing_metadata = false;
    if (entry != candidate.entry || symbols != candidate.symbols)
      throw std::runtime_error("TSI installed loader metadata differs from probe");
    return policy.result();
  } catch (...) {
    preparing_metadata = false;
    throw;
  }
}

void firesim_tsi_t::check_startup_metadata() const {
  // Installed HTIF's read-only getters lack const qualifiers.
  auto &self = const_cast<firesim_tsi_t &>(*this);
  if (!metadata_supported || metadata_poisoned || startup_metadata.elf.empty())
    throw std::runtime_error("unsupported or incomplete TSI startup metadata");
  const auto &symbols = startup_metadata.symbols;
  auto expected = [&](const char *name) { auto p = symbols.find(name); return p == symbols.end() ? 0 : p->second; };
  const bool mailboxes = symbols.count("tohost") && symbols.count("fromhost");
  if (self.get_entry_point() != startup_metadata.entry ||
      self.get_tohost_addr() != (mailboxes ? expected("tohost") : 0) ||
      self.get_fromhost_addr() != (mailboxes ? expected("fromhost") : 0))
    throw std::runtime_error("TSI startup entry/mailbox readback differs");
  std::map<uint64_t, std::string> canonical;
  for (const auto &[name, address] : symbols) canonical.emplace(address, name);
  for (const auto &[address, name] : canonical) {
    const char *actual = self.get_symbol(address);
    if (!actual || name != actual) throw std::runtime_error("TSI startup symbol readback differs");
  }
}

std::vector<uint8_t> firesim_tsi_t::save_startup_metadata() const {
  if (syscall_exit && (polling_active || polling_components_prepared))
    firesim_tsi_polling_syscall_t(const_cast<firesim_tsi_t &>(*this)).inspect();
  else if (!metadata_prepared) inspect_polling_cut();
  else if (polling_components_prepared) inspect_prepared_polling_components();
  else if (host_context_initialized() || metadata_components() != metadata_pristine_components)
    throw std::runtime_error("metadata-only preparation changed a caller component");
  check_startup_metadata();
  const auto xlen = const_cast<firesim_tsi_t &>(*this).preflight_startup_metadata(startup_metadata);
  return startup_metadata.image(metadata_arguments, metadata_configuration(xlen), metadata_revision());
}

void firesim_tsi_t::prepare_startup_metadata(const std::vector<uint8_t> &image) {
  if (!metadata_supported || metadata_prepared || metadata_poisoned || host_context_initialized() ||
      !startup_metadata.elf.empty() || metadata_components() != metadata_pristine_components ||
      should_exit() || done())
    throw std::runtime_error("TSI metadata preparation requires a pristine supported caller");
  auto candidate = firesim_tsi_startup_metadata_t::probe(firesim_tsi_elf_bytes(target_args().at(0)));
  const auto xlen = preflight_startup_metadata(candidate);
  if (candidate.image(metadata_arguments, metadata_configuration(xlen), metadata_revision()) != image)
    throw std::runtime_error("TSI startup metadata ELF/arguments/complete image mismatch");
  startup_metadata = std::move(candidate);
  preparing_metadata = true;
  try {
    // Bypass TestChip/FireSim load_program's yield and program-loader phases.
    // Installed load_payload sees all bytes as preloaded, so neither memif
    // read/modify/write nor target reset/initialization can be reissued.
    htif_t::load_program();
    preparing_metadata = false;
    check_startup_metadata();
    if (metadata_components() != metadata_pristine_components || host_context_initialized())
      throw std::runtime_error("metadata preparation entered target services");
    metadata_prepared = true;
  } catch (...) {
    preparing_metadata = false; metadata_poisoned = true; throw;
  }
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::inspect_polling_cut() const {
  if (htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::running ||
      should_exit() || const_cast<firesim_tsi_t &>(*this).done())
    throw std::runtime_error("TSI polling audit lacks HTIF exit/signal/stop owners");
  return inspect_live_polling_protocol();
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::inspect_live_polling_protocol() const {
  if (syscall_exit)
    throw std::runtime_error("TSI polling audit lacks the restricted syscall parent");
  // The generic syscall parent is still on the installed stack. Its reader
  // is inspectable separately, never part of the sealed polling aggregate.
  if (!memif_read.idle()) throw std::runtime_error("TSI polling audit lacks the generic memif caller");
  // Unsealed inspection still exposes only its historical eight owners. It
  // must never admit an active identity whose two owners it does not return.
  if (terminal->checkpoint_schema().empty() && (!bcd_identity.idle() || !memif_write.idle()))
    throw std::runtime_error("TSI unsealed polling audit lacks identity/write owners");
  if (!owned_default_devices)
    throw std::runtime_error("TSI polling audit: installed custom/long-option HTIF path");
  if (!polling_active || !htif_poll)
    throw std::runtime_error("TSI polling audit: startup has not returned or polling has ended");
  if (!host_context_suspended())
    throw std::runtime_error("TSI polling audit: host context is not suspended at target");
  validate_polling_components(*htif_poll, program_loader, init_control, host_control,
                              serial_read, loadmem_read, loadmem_queues, bcd_identity, memif_write);
  return polling_components();
}

void firesim_tsi_t::write_identity(uint64_t address, const firesim_tsi_bcd_t::identity_t &bytes) {
  class services_t final : public firesim_tsi_memif_write_t::services_t {
  public:
    explicit services_t(firesim_tsi_t &tsi) : tsi(tsi) {}
    void issue(uint64_t address, uint64_t bytes) override {
      tsi.flush_program_cache_lines(address, bytes);
      tsi.serial.issue_read(address, bytes);
    }
    bool receive(uint32_t &word) override {
      if (!tsi.serial.response_available()) return false;
      word = tsi.serial.pop_response(); return true;
    }
    void write(uint64_t address, size_t bytes, const uint32_t *words) override {
      tsi.write_chunk(address, bytes, words);
    }
  private:
    firesim_tsi_t &tsi;
  } services(*this);
  memif_write.begin(address, {bytes.begin(), bytes.end()});
  try {
    for (;;) {
      const auto result = memif_write.advance(services);
      if (result == firesim_tsi_memif_write_t::result_t::complete) break;
      if (result == firesim_tsi_memif_write_t::result_t::blocked) switch_to_target();
    }
    memif_write.finish();
  } catch (...) { memif_write.interrupt(); throw; }
}

bool firesim_tsi_t::dispatch_identity(uint64_t command) {
  class services_t final : public firesim_tsi_bcd_identity_t::services_t {
  public:
    explicit services_t(firesim_tsi_t &tsi) : tsi(tsi) {}
    void issue(uint64_t address, uint64_t bytes) override {
      tsi.flush_program_cache_lines(address, bytes); tsi.serial.issue_read(address, bytes);
    }
    bool receive(uint32_t &word) override {
      if (!tsi.serial.response_available()) return false;
      word = tsi.serial.pop_response(); return true;
    }
    void write(uint64_t address, size_t bytes, const uint32_t *words) override {
      tsi.write_chunk(address, bytes, words);
    }
    void respond(uint64_t value) override { tsi.htif_poll->respond(value); }
  private:
    firesim_tsi_t &tsi;
  } services(*this);
  if (bcd_identity.idle()) bcd_identity.begin(command);
  else if (!bcd_identity.pending_for(command))
    throw std::runtime_error("HTIF dispatch/BCD identity command mismatch");
  for (;;) {
    const auto result = bcd_identity.advance(services);
    if (result == firesim_tsi_bcd_identity_t::result_t::complete) break;
    // Propagate the yield through the parent service. run_host switches only
    // after both explicit owner guards have returned.
    if (result == firesim_tsi_bcd_identity_t::result_t::blocked) return false;
  }
  bcd_identity.finish();
  return true;
}

bool firesim_tsi_t::dispatch_syscall_exit(uint64_t command) {
  class services_t final : public firesim_tsi_syscall_exit_t::services_t {
  public:
    explicit services_t(firesim_tsi_t &tsi) : tsi(tsi) {}
    void issue(uint64_t address, uint64_t bytes) override {
      tsi.flush_program_cache_lines(address, bytes); tsi.serial.issue_read(address, bytes);
    }
    bool receive(uint32_t &word) override {
      if (!tsi.serial.response_available()) return false;
      word = tsi.serial.pop_response(); return true;
    }
    void write(uint64_t address, size_t bytes, const uint32_t *words) override {
      tsi.write_chunk(address, bytes, words);
    }
    void respond(uint64_t value) override { tsi.htif_poll->respond(value); }
  private:
    firesim_tsi_t &tsi;
  } services(*this);
  auto &caller = *syscall_exit;
  if (caller.current.phase == firesim_tsi_syscall_exit_t::phase_t::idle) caller.begin(command);
  else if (caller.current.command != command)
    throw std::runtime_error("HTIF polling/syscall command mismatch");
  for (;;) {
    const auto result = caller.advance(services);
    if (result == firesim_tsi_syscall_exit_t::result_t::complete) return true;
    // Both caller guards unwind before run_host switches to the target.
    if (result == firesim_tsi_syscall_exit_t::result_t::blocked) return false;
  }
}

void firesim_tsi_t::validate_polling_components(const firesim_tsi_htif_poll_t &poll,
    const firesim_tsi_program_loader_t &program, const firesim_tsi_init_accesses_t &init,
    const firesim_tsi_host_control_t &host, const firesim_tsi_serial_read_t &reader,
    const firesim_loadmem_read_t &loadread, const firesim_loadmem_queues_t &queues,
    const firesim_tsi_bcd_identity_t &identity, const firesim_tsi_memif_write_t &writer,
    bool completed_exit, bool syscall) {
  // phase() also rejects an active or interrupted device/memif service.
  const auto phase = poll.phase();
  using pp = firesim_tsi_htif_poll_t::phase_t;
  using hp = firesim_tsi_host_control_t::phase_t;
  const bool read = (phase == pp::tohost_read || phase == pp::fromhost_read) &&
                    host.current_phase() == hp::ready &&
                    reader.pending_for(poll.pending_read_address(), 8);
  const bool idle = phase == pp::idle && host.current_phase() == hp::idle &&
                    !host.busy() && reader.idle();
  // pending_for validates the copied writer address/payload against the raw
  // identity command. The independent mailbox reader cannot also be active.
  const bool inactive = identity.idle() && writer.idle();
  const bool dispatch = phase == pp::dispatch && host.current_phase() == hp::ready && reader.idle() &&
      (syscall ? inactive : identity.blocked_for(poll.pending_dispatch_command()));
  const bool complete = completed_exit && phase == pp::complete &&
                        host.current_phase() == hp::ready && reader.idle();
  if ((!dispatch && (!(read || idle || complete) || !inactive)) ||
      program.phase() != firesim_tsi_program_loader_t::phase_t::complete ||
      init.phase() != firesim_tsi_init_accesses_t::phase_t::complete ||
      !host.loaded_in_host() || !host.loaded_in_target() ||
      !loadread.idle() || !queues.empty())
    throw std::runtime_error("TSI polling audit: incoherent or active startup/child owners");
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::polling_components() const {
  std::vector<std::pair<const char *, const checkpoint_owner_t *>> owners{
      {"poll", htif_poll.get()}, {"program", &program_loader}, {"init", &init_control},
      {"host", &host_control}, {"read", &serial_read}, {"serial", &serial},
      {"loadmem-read", &loadmem_read}, {"loadmem-queues", &loadmem_queues}};
  if (!terminal->checkpoint_schema().empty()) {
    if (!bcd) throw std::runtime_error("TSI sealed polling audit: missing BCD owner");
    owners.emplace_back("bcd", bcd.get());
    owners.emplace_back("terminal", terminal.get());
    owners.emplace_back("identity", &bcd_identity);
    owners.emplace_back("write", &memif_write);
  }
  polling_cut_t result;
  for (const auto &[name, owner] : owners) {
    auto image = owner->save_checkpoint();
    owner->validate_checkpoint(image);
    result.emplace_back(name, std::move(image));
  }
  for (size_t i = 0; i < owners.size(); ++i)
    if (owners[i].second->save_checkpoint() != result[i].second)
      throw std::runtime_error("TSI polling audit: component changed during inspection");
  return result;
}

void firesim_tsi_t::require_pristine_polling_destination() {
  if (!metadata_prepared || metadata_poisoned || polling_components_prepared ||
      host_context_initialized() || polling_active || htif_poll || bcd || default_devices ||
      !owned_default_devices || terminal->checkpoint_schema().empty() ||
      should_exit() || done() || metadata_components() != metadata_pristine_components)
    throw std::runtime_error("TSI polling preparation requires pristine sealed metadata-only caller");
  check_startup_metadata();
}

struct firesim_tsi_t::prepared_polling_components_t::state_t {
  firesim_tsi_t &tsi;
  firesim_tsi_program_loader_t program;
  firesim_tsi_init_accesses_t init;
  firesim_tsi_host_control_t host;
  firesim_tsi_serial_read_t reader;
  firesim_tsi_serial_state_t transport;
  firesim_loadmem_read_t loadread;
  firesim_tsi_memif_write_t writer;
  firesim_tsi_bcd_identity_t identity;
  firesim_loadmem_queues_t queues;
  std::unique_ptr<firesim_tsi_htif_poll_t> poll;
  std::unique_ptr<firesim_tsi_bcd_t> device;
  std::unique_ptr<firesim_tsi_bcd_t::prepared_polling_t> devices;
  bool consumed = false;

  state_t(firesim_tsi_t &tsi, const polling_cut_t &images, bool completed_exit, bool syscall)
      : tsi(tsi), program(tsi.program_loader), init(tsi.init_control), host(tsi.host_control),
        reader(tsi.serial_read), transport(tsi.serial), loadread(tsi.loadmem_read),
        identity(writer, transport) {
    tsi.require_pristine_polling_destination();
    static const std::array<const char *, 12> names{{"poll", "program", "init", "host", "read",
        "serial", "loadmem-read", "loadmem-queues", "bcd", "terminal", "identity", "write"}};
    if (images.size() != names.size())
      throw std::runtime_error("TSI polling preparation requires all twelve ordered components");
    for (size_t i = 0; i < names.size(); ++i)
      if (images[i].first != names[i])
        throw std::runtime_error("TSI polling preparation component membership/order mismatch");
    // Candidates carry destination configuration and bindings. No callback,
    // pointer, process context or input-image storage is copied from the cut.
    poll = std::make_unique<firesim_tsi_htif_poll_t>(tsi.get_tohost_addr(), tsi.get_fromhost_addr());
    device = std::make_unique<firesim_tsi_bcd_t>(*poll, 1048576, tsi.terminal.get(),
        [&tsi](uint64_t address, const firesim_tsi_bcd_t::identity_t &bytes) { tsi.write_identity(address, bytes); });
    std::array<checkpoint_owner_t *, 8> candidates{{poll.get(), &program, &init, &host,
        &reader, &transport, &loadread, &queues}};
    for (size_t i = 0; i < candidates.size(); ++i)
      candidates[i]->load_checkpoint(images[i].second);
    writer.load_checkpoint(images[11].second);
    identity.load_checkpoint(images[10].second);
    validate_polling_components(*poll, program, init, host, reader, loadread, queues, identity, writer,
                                completed_exit, syscall);
    // Parse and allocate the remaining three replacements without changing
    // the actual terminal. The temporary ordered image list also precedes
    // publication. Its destruction cannot affect the owned replacements.
    devices = std::make_unique<firesim_tsi_bcd_t::prepared_polling_t>(
        *device, firesim_tsi_bcd_t::sealed_checkpoint_t{images[0], images[9], images[8]});
  }

  void publish() noexcept {
    devices->publish();
    tsi.program_loader.swap_state(program); tsi.init_control.swap_state(init);
    tsi.host_control.swap_state(host); tsi.serial_read.swap_state(reader); tsi.serial.swap_state(transport);
    tsi.loadmem_read.swap_state(loadread); tsi.loadmem_queues.swap_state(queues);
    static_assert(std::is_nothrow_move_assignable<firesim_tsi_memif_write_t>::value,
                  "polling write publication must not allocate");
    tsi.memif_write = std::move(writer);
    tsi.bcd_identity.swap_state(identity);
    tsi.htif_poll.swap(poll); tsi.bcd.swap(device);
    tsi.polling_components_prepared = true;
    consumed = true;
  }
};

firesim_tsi_t::prepared_polling_components_t::prepared_polling_components_t(
    firesim_tsi_t &tsi, const polling_cut_t &images, bool completed_exit, bool syscall)
    : state(std::make_unique<state_t>(tsi, images, completed_exit, syscall)) {}
firesim_tsi_t::prepared_polling_components_t::~prepared_polling_components_t() = default;
void firesim_tsi_t::prepared_polling_components_t::commit() {
  recheck();
  publish();
}
void firesim_tsi_t::prepared_polling_components_t::recheck() {
  if (state->consumed) throw std::runtime_error("TSI polling candidate already committed");
  state->tsi.require_pristine_polling_destination();
}
void firesim_tsi_t::prepared_polling_components_t::publish() noexcept {
  state->publish();
}
void firesim_tsi_t::prepared_polling_components_t::require_exit_boundary(
    firesim_tsi_htif_exit_t::phase_t phase) const {
  if (state->tsi.syscall_exit) throw std::runtime_error("direct exit group excludes restricted syscall mode");
  using ep = firesim_tsi_htif_exit_t::phase_t;
  if ((phase == ep::stopped &&
       state->poll->phase() != firesim_tsi_htif_poll_t::phase_t::complete) || (phase == ep::requested &&
      state->poll->phase() != firesim_tsi_htif_poll_t::phase_t::fromhost_read))
    throw std::runtime_error("TSI aggregate lacks this exit/stop parent boundary");
}
void firesim_tsi_t::validate_syscall_boundary(const firesim_tsi_htif_poll_t &poll,
    const firesim_tsi_syscall_exit_t &caller, firesim_htif_lifecycle_state_t provider) {
  caller.boundary.require_idle();
  firesim_tsi_syscall_exit_t::validate(caller.current, provider);
  using sp = firesim_tsi_syscall_exit_t::phase_t;
  using pp = firesim_tsi_htif_poll_t::phase_t;
  const auto phase = poll.phase();
  const bool idle = caller.current.phase == sp::idle &&
      (phase == pp::tohost_read || phase == pp::idle) && poll.responses_empty();
  const bool dispatch = phase == pp::dispatch && caller.current.phase != sp::idle &&
      caller.current.phase != sp::complete && poll.responses_empty() &&
      caller.current.command == poll.pending_dispatch_command();
  const bool complete = caller.current.phase == sp::complete &&
      ((phase == pp::fromhost_read && poll.response_is(1)) ||
       (phase == pp::complete && poll.responses_empty()));
  if (!(idle || dispatch || complete))
    throw std::runtime_error("TSI polling/syscall parent/response boundary mismatch");
}
void firesim_tsi_t::prepared_polling_components_t::require_syscall_boundary(
    const firesim_tsi_syscall_exit_t &caller, firesim_htif_lifecycle_state_t provider) const {
  firesim_tsi_t::validate_syscall_boundary(*state->poll, caller, provider);
}
firesim_tsi_t::prepared_polling_components_t firesim_tsi_t::prepare_polling_components_candidate(
    const polling_cut_t &images) {
  if (syscall_exit) throw std::runtime_error("twelve-owner preparation excludes restricted syscall mode");
  return prepared_polling_components_t(*this, images);
}
void firesim_tsi_t::prepare_polling_components(const polling_cut_t &images) {
  auto next = prepare_polling_components_candidate(images);
  next.commit();
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::inspect_prepared_polling_components() const {
  if (syscall_exit) throw std::runtime_error("twelve-owner inspection excludes restricted syscall mode");
  if (htif_exit_component.phase() != firesim_tsi_htif_exit_t::phase_t::running ||
      should_exit() || const_cast<firesim_tsi_t &>(*this).done())
    throw std::runtime_error("prepared polling audit lacks HTIF exit/signal/stop owners");
  return inspect_fresh_polling_protocol();
}

firesim_tsi_t::polling_cut_t firesim_tsi_t::inspect_fresh_polling_protocol(bool completed_exit) const {
  if (!polling_components_prepared || !metadata_prepared || metadata_poisoned ||
      host_context_initialized() || polling_active || !htif_poll || !bcd || default_devices ||
      prepared_polling_service_active || prepared_polling_service_poisoned)
    throw std::runtime_error("TSI polling components have not been prepared in a fresh caller");
  validate_polling_components(*htif_poll, program_loader, init_control, host_control,
                              serial_read, loadmem_read, loadmem_queues, bcd_identity, memif_write,
                              completed_exit);
  return polling_components();
}

void firesim_tsi_t::advance_prepared_syscall_components() {
  prepared_polling_service_active = true;
  try {
    polling_services_t services(*this, nullptr);
    for (;;) {
      const auto result = htif_poll->advance(services);
      // Stop/return/session teardown belong to an independent outer caller.
      if (result != firesim_tsi_htif_poll_t::result_t::progress) break;
    }
    prepared_polling_service_active = false;
  } catch (...) {
    prepared_polling_service_active = false;
    prepared_polling_service_poisoned = true;
    throw;
  }
}

bool firesim_tsi_t::advance_prepared_exit_components() {
  // The lifecycle group has inspected the complete provider/protocol state,
  // including signal/signature guards, before entering this private service.
  // Only finish the outstanding fromhost transaction and the loop condition.
  // This never reconstructs or dispatches the installed syscall session.
  prepared_polling_service_active = true;
  try {
    polling_services_t services(*this, nullptr, true);
    for (;;) {
      using pp = firesim_tsi_htif_poll_t::phase_t;
      const auto phase = htif_poll->phase();
      if (phase != pp::fromhost_read && phase != pp::fromhost_write && phase != pp::ready)
        throw std::runtime_error("prepared exit reached an unowned caller phase");
      const auto result = htif_poll->advance(services);
      if (result == firesim_tsi_htif_poll_t::result_t::blocked) {
        prepared_polling_service_active = false;
        return false;
      }
      if (result == firesim_tsi_htif_poll_t::result_t::complete) {
        // Signature mode was rejected by the actual provider guard. The
        // installed no-signature stop writes only the owned stopped field.
        htif_exit_component.stop([this] { stop(); });
        prepared_polling_service_active = false;
        return true;
      }
    }
  } catch (...) {
    prepared_polling_service_active = false;
    prepared_polling_service_poisoned = true;
    throw;
  }
}

void firesim_tsi_t::advance_prepared_polling_components() {
  // Reconstruct the executable polling caller from explicit child phases;
  // never initialize a coroutine or call start/load_program/reset/stop.
  inspect_prepared_polling_components();
  if (should_exit() || done())
    throw std::runtime_error("prepared polling component cannot service HTIF exit/signal");
  prepared_polling_service_active = true;
  try {
    polling_services_t services(*this, nullptr);
    for (;;) {
      const auto result = htif_poll->advance(services);
      if (result == firesim_tsi_htif_poll_t::result_t::complete)
        throw std::runtime_error("prepared polling component reached unowned HTIF stop");
      if (result == firesim_tsi_htif_poll_t::result_t::blocked) break;
    }
    prepared_polling_service_active = false;
    validate_polling_components(*htif_poll, program_loader, init_control, host_control,
                                serial_read, loadmem_read, loadmem_queues, bcd_identity, memif_write);
  } catch (...) {
    prepared_polling_service_active = false;
    prepared_polling_service_poisoned = true;
    throw;
  }
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
  if (preparing_metadata) throw std::runtime_error("metadata preparation attempted a target read");
  if (program_loader.loadmem_mode()) load_mem_read(address, bytes, destination);
  else {
    flush_program_cache_lines(address, bytes);
    tsi_t::read_chunk(address, bytes, destination);
  }
}

void firesim_tsi_t::runtime_memif_t::read(addr_t address, size_t bytes, void *destination) {
  // ELF/startup loadmem is a different transport with independent owners.
  // Its installed head/tail/body caller must not issue serial/cache packets.
  if (tsi.program_loader.loadmem_mode()) memif_t::read(address, bytes, destination);
  else tsi.read_runtime_memif(address, bytes, destination);
}

void firesim_tsi_t::read_runtime_memif(addr_t address, size_t bytes, void *destination) {
  if (preparing_metadata || metadata_prepared || metadata_poisoned)
    throw std::runtime_error("runtime memif read during metadata preparation/restore");
  if (bytes && !destination) throw std::runtime_error("missing memif read destination");
  firesim_tsi_memif_read_services_t services(serial, program_loader.cache_flush_address());
  memif_read.begin(address, bytes);
  try {
    for (;;) {
      const auto result = memif_read.advance(services);
      if (result == firesim_tsi_memif_read_t::result_t::complete) break;
      // advance has left every component guard before a host context yield.
      if (result == firesim_tsi_memif_read_t::result_t::blocked) switch_to_target();
    }
    const auto &data = memif_read.result();
    if (bytes) std::copy(data.begin(), data.end(), static_cast<uint8_t *>(destination));
    memif_read.finish();
  } catch (...) { memif_read.interrupt(); throw; }
}

void firesim_tsi_t::write_chunk(addr_t address, size_t bytes, const void *source) {
  if (preparing_metadata) throw std::runtime_error("metadata preparation attempted a target write");
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
  if (metadata_prepared || metadata_poisoned)
    throw std::runtime_error("HTIF/context continuation after metadata component preparation is unsupported");
  if (initialization_component_restored)
    throw std::runtime_error("HTIF/context continuation after component restore is unsupported");
  switch_to_host();
}

void firesim_tsi_t::reset() {
  if (preparing_metadata) throw std::runtime_error("metadata preparation attempted target reset");
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
  if (host_context_initialized() || polling_components_prepared)
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
