// See LICENSE for license details

#include "uart.h"
#include "core/simif.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <fstream>

#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE
#endif

#include <stdio.h>
#include <stdlib.h>

#ifndef _WIN32
#include <unistd.h>

char uart_t::KIND;

// name length limit for ptys
#define SLAVENAMELEN 256

/* There is no "backpressure" to the user input for sigs. only one at a time
 * non-zero value represents unconsumed special char input.
 *
 * Reset to zero once consumed.
 */

// This is fine for multiple UARTs because UARTs > uart 0 will use pty, not
// stdio
char specialchar = 0;

void sighand(int s) {
  switch (s) {
  case SIGINT:
    // ctrl-c
    specialchar = 0x3;
    break;
  default:
    specialchar = 0x0;
  }
}
#endif

/**
 * Helper class which links the UART stream to primitive streams.
 */
class uart_fd_handler : public uart_handler {
public:
  uart_fd_handler() = default;
  ~uart_fd_handler() override;

  std::optional<char> get() override;
  void put(char data) override;

protected:
  int inputfd;
  int outputfd;
  int loggingfd = 0;
};

uart_fd_handler::~uart_fd_handler() { close(this->loggingfd); }

std::optional<char> uart_fd_handler::get() {
  char inp;
  int readamt;
  if (specialchar) {
    // send special character (e.g. ctrl-c)
    // for stdin handling
    //
    // PTY should never trigger this
    inp = specialchar;
    specialchar = 0;
    readamt = 1;
  } else {
    // else check if we have input
    readamt = ::read(inputfd, &inp, 1);
  }

  if (readamt <= 0)
    return std::nullopt;
  return inp;
}

void uart_fd_handler::put(char data) {
  ::write(outputfd, &data, 1);
  if (loggingfd) {
    ::write(loggingfd, &data, 1);
  }
}

/**
 * UART handler which fetches data from stdin and outputs to stdout.
 */
class uart_stdin_handler final : public uart_fd_handler {
public:
  uart_stdin_handler() {
    // signal handler so ctrl-c doesn't kill simulation when UART is attached
    // to stdin/stdout
    struct sigaction sigIntHandler;
    sigIntHandler.sa_handler = sighand;
    sigemptyset(&sigIntHandler.sa_mask);
    sigIntHandler.sa_flags = 0;
    sigaction(SIGINT, &sigIntHandler, nullptr);
    printf("UART0 is here (stdin/stdout).\n");
    inputfd = STDIN_FILENO;
    outputfd = STDOUT_FILENO;
    // Don't block on reads if there is nothing typed in
    fcntl(inputfd, F_SETFL, fcntl(inputfd, F_GETFL) | O_NONBLOCK);
  }
};

/**
 * UART handler connected to PTY.
 */
class uart_pty_handler final : public uart_fd_handler {
public:
  uart_pty_handler(int uartno) {
    // for UARTs that are not UART0, use a PTY
    char slavename[SLAVENAMELEN];
    int ptyfd = posix_openpt(O_RDWR | O_NOCTTY);
    grantpt(ptyfd);
    unlockpt(ptyfd);
    ptsname_r(ptyfd, slavename, SLAVENAMELEN);

    // create symlink for reliable location to find uart pty
    std::string symlinkname = std::string("uartpty") + std::to_string(uartno);
    // unlink in case symlink already exists
    unlink(symlinkname.c_str());
    symlink(slavename, symlinkname.c_str());
    printf("UART%d is on PTY: %s, symlinked at %s\n",
           uartno,
           slavename,
           symlinkname.c_str());
    printf("Attach to this UART with 'sudo screen %s' or 'sudo screen %s'\n",
           slavename,
           symlinkname.c_str());
    inputfd = ptyfd;
    outputfd = ptyfd;

    // also, for these we want to log output to file here.
    std::string uartlogname = std::string("uartlog") + std::to_string(uartno);
    printf("UART logfile is being written to %s\n", uartlogname.c_str());
    this->loggingfd = open(uartlogname.c_str(), O_RDWR | O_CREAT, 0644);
    // Don't block on reads if there is nothing typed in
    fcntl(inputfd, F_SETFL, fcntl(inputfd, F_GETFL) | O_NONBLOCK);
  }
};

/**
 * UART handler connected to files.
 */
class uart_file_handler final : public uart_fd_handler {
public:
  uart_file_handler(const std::string &in_name, const std::string &out_name) {
    inputfd = open(in_name.c_str(), O_RDONLY);
    outputfd = open(out_name.c_str(), O_WRONLY | O_CREAT, 0644);
  }
};

// Opt-in finite input and buffered output, with no live descriptor, signal
// latch or external cursor in a checkpoint. Output is published only at
// finish(), after which checkpointing is forbidden. A fresh restore may use
// a different output path, but must bind exactly the same input bytes.
class uart_checkpoint_file_handler final : public uart_handler {
public:
  uart_checkpoint_file_handler(const std::string &in_name,
                               const std::string &out_name) : out_name(out_name) {
    // Refuse devices/FIFOs before opening: reads must be finite and cannot
    // depend on asynchronous host input. Own the complete regular-file bytes.
    struct stat st;
    if (stat(in_name.c_str(), &st) || !S_ISREG(st.st_mode))
      throw std::runtime_error("UART checkpoint input must be a regular file");
    std::ifstream file(in_name, std::ios::binary);
    if (!file) throw std::runtime_error("UART checkpoint input open failed");
    input.assign(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
    if (file.bad()) throw std::runtime_error("UART checkpoint input read failed");
  }
  std::optional<char> get() override {
    if (position == input.size()) return std::nullopt;
    return static_cast<char>(input[position++]);
  }
  void put(char data) override { output.push_back(static_cast<uint8_t>(data)); }
  void finish() override {
    std::ofstream file(out_name, std::ios::binary | std::ios::trunc);
    file.write(reinterpret_cast<const char *>(output.data()), output.size());
    file.close();
    if (!file) throw std::runtime_error("UART checkpoint output publish failed");
  }
  std::string checkpoint_schema() const override { return "firesim.uart.buffered-file.v1"; }
  std::vector<uint8_t> save_checkpoint() const override {
    auto c = configuration();
    c.word(position); c.word(output.size());
    c.bytes.insert(c.bytes.end(), output.begin(), output.end());
    return std::move(c.bytes);
  }
  void validate_checkpoint(const std::vector<uint8_t> &b) const override { (void)decode(b); }
  void load_checkpoint(const std::vector<uint8_t> &b) override {
    auto d = decode(b); // Parsing and allocation complete before mutation.
    output.swap(d.second); position = d.first;
  }
private:
  const std::string out_name;
  std::vector<uint8_t> input, output;
  size_t position = 0;
  widget_checkpoint_config_t configuration() const {
    widget_checkpoint_config_t c(10, {input.size()});
    c.bytes.insert(c.bytes.end(), input.begin(), input.end());
    return c;
  }
  std::pair<size_t, std::vector<uint8_t>> decode(const std::vector<uint8_t> &b) const {
    const auto c = configuration();
    if (b.size() < c.bytes.size() + 16 ||
        !std::equal(c.bytes.begin(), c.bytes.end(), b.begin()))
      throw std::runtime_error("UART checkpoint handler/input mismatch");
    size_t offset = c.bytes.size();
    auto word = [&]() {
      uint64_t v = 0;
      for (unsigned i = 0; i < 8; ++i) v |= uint64_t(b[offset++]) << (8 * i);
      return v;
    };
    const auto p = word(), n = word();
    if (p > input.size() || n != b.size() - offset)
      throw std::runtime_error("UART checkpoint cursor/output length mismatch");
    return {size_t(p), std::vector<uint8_t>(b.begin() + offset, b.end())};
  }
};

static std::unique_ptr<uart_handler>
create_handler(const std::vector<std::string> &args, int uartno) {
  std::string in_arg = std::string("+uart-in") + std::to_string(uartno) + "=";
  std::string out_arg = std::string("+uart-out") + std::to_string(uartno) + "=";

  std::string in_name, out_name;
  const auto checkpoint_arg = std::string("+uart-checkpoint-file") + std::to_string(uartno);
  bool checkpoint_file = false;
  for (const auto &arg : args) {
    if (arg == checkpoint_arg) checkpoint_file = true;
    if (arg.find(in_arg) == 0) {
      in_name = const_cast<char *>(arg.c_str()) + in_arg.length();
    }
    if (arg.find(out_arg) == 0) {
      out_name = const_cast<char *>(arg.c_str()) + out_arg.length();
    }
  }

  if (checkpoint_file) {
    if (in_name.empty() || out_name.empty())
      throw std::runtime_error("UART checkpoint file mode requires input and output paths");
    return std::make_unique<uart_checkpoint_file_handler>(in_name, out_name);
  }
  if (!in_name.empty() && !out_name.empty()) {
    return std::make_unique<uart_file_handler>(in_name, out_name);
  }
  if (uartno == 0) {
    return std::make_unique<uart_stdin_handler>();
  }
  return std::make_unique<uart_pty_handler>(uartno);
}

uart_t::uart_t(simif_t &simif,
               const UARTBRIDGEMODULE_struct &mmio_addrs,
               int uartno,
               const std::vector<std::string> &args)
    : bridge_driver_t(simif, &KIND), mmio_addrs(mmio_addrs), uartno(uartno),
      handler(create_handler(args, uartno)) {}

uart_t::~uart_t() = default;

void uart_t::send() {
  if (data.in.fire()) {
    write(mmio_addrs.in_bits, data.in.bits);
    write(mmio_addrs.in_valid, data.in.valid);
  }
  if (data.out.fire()) {
    write(mmio_addrs.out_ready, data.out.ready);
  }
}

void uart_t::recv() {
  data.in.ready = read(mmio_addrs.in_ready);
  data.out.valid = read(mmio_addrs.out_valid);
  if (data.out.valid) {
    data.out.bits = read(mmio_addrs.out_bits);
  }
}

void uart_t::tick() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (finished) throw std::runtime_error("UART tick after finish");
  data.out.ready = true;
  data.in.valid = false;
  do {
    this->recv();

    if (data.in.ready) {
      if (auto bits = handler->get()) {
        data.in.bits = *bits;
        data.in.valid = true;
      }
    }

    if (data.out.fire()) {
      handler->put(data.out.bits);
    }

    this->send();
    data.in.valid = false;
  } while (data.in.fire() || data.out.fire());
}

void uart_t::finish() {
  widget_checkpoint_state_t::call_t call(checkpoint_state);
  if (!finished) { handler->finish(); finished = true; }
}

void uart_t::require_checkpointable() const {
  checkpoint_state.require_idle();
  if (finished || handler->checkpoint_schema() != "firesim.uart.buffered-file.v1")
    throw std::runtime_error("unsupported UART external input/output or finished lifecycle");
}

widget_checkpoint_config_t uart_t::checkpoint_config() const {
  return widget_checkpoint_config_t(9, {uint64_t(uartno), mmio_addrs.out_bits,
      mmio_addrs.out_valid, mmio_addrs.out_ready, mmio_addrs.in_bits,
      mmio_addrs.in_valid, mmio_addrs.in_ready});
}

std::vector<uint8_t> uart_t::save_checkpoint() const {
  require_checkpointable();
  auto c = checkpoint_config();
  // Preserve stale data as well as handshake flags. Object padding and signed
  // char representation are never serialized through an object-layout cast.
  c.word(static_cast<uint8_t>(data.in.bits)); c.word(data.in.valid); c.word(data.in.ready);
  c.word(static_cast<uint8_t>(data.out.bits)); c.word(data.out.valid); c.word(data.out.ready);
  const auto h = handler->save_checkpoint();
  c.word(h.size()); c.bytes.insert(c.bytes.end(), h.begin(), h.end());
  (void)decode_checkpoint(c.bytes);
  return std::move(c.bytes);
}

uart_t::decoded_checkpoint_t uart_t::decode_checkpoint(const std::vector<uint8_t> &b) const {
  require_checkpointable();
  const auto c = checkpoint_config();
  if (b.size() < c.bytes.size() + 56 || !std::equal(c.bytes.begin(), c.bytes.end(), b.begin()))
    throw std::runtime_error("UART checkpoint configuration/incomplete state mismatch");
  size_t offset = c.bytes.size();
  auto word = [&]() {
    uint64_t v = 0;
    for (unsigned i = 0; i < 8; ++i) v |= uint64_t(b[offset++]) << (8 * i);
    return v;
  };
  auto byte = [&]() {
    const auto v = word();
    if (v > 255) throw std::runtime_error("UART invalid data byte");
    return static_cast<char>(v);
  };
  auto boolean = [&]() {
    const auto v = word();
    if (v > 1) throw std::runtime_error("UART invalid handshake boolean");
    return bool(v);
  };
  decoded_checkpoint_t d{};
  d.data.in.bits = byte(); d.data.in.valid = boolean(); d.data.in.ready = boolean();
  d.data.out.bits = byte(); d.data.out.valid = boolean(); d.data.out.ready = boolean();
  if (d.data.in.valid || (d.data.out.valid && d.data.out.ready))
    throw std::runtime_error("UART checkpoint is not a completed tick");
  const auto handler_size = word();
  if (handler_size != b.size() - offset) throw std::runtime_error("UART incomplete/trailing handler state");
  d.handler.assign(b.begin() + offset, b.end());
  handler->validate_checkpoint(d.handler);
  return d;
}

void uart_t::validate_checkpoint(const std::vector<uint8_t> &b) const { (void)decode_checkpoint(b); }
void uart_t::load_checkpoint(const std::vector<uint8_t> &b) {
  const auto d = decode_checkpoint(b);
  // The concrete handler also parses and allocates before committing. The
  // remaining handshake assignments cannot throw; no MMIO/file writes occur.
  handler->load_checkpoint(d.handler);
  data = d.data;
}
