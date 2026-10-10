// Host-only bounded lockstep transport for two independent VCS processes.
// It never drives RTL, deposits state, or advances a clock.
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <poll.h>
#include <unistd.h>
#include <fcntl.h>
#include <cerrno>
#include <chrono>
#include <charconv>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
int peer = -1;
bool server = false, pending = false, ended = false;
uint64_t next_cycle = 0;
std::string socket_path, received;
std::vector<unsigned> widths;
size_t maximum = 0;
constexpr int timeout_ms = 30000;
// Complete production restore/readback precedes the first boundary. It can
// exceed one cycle's ACK timeout for large memories. Keep that ACK timeout
// strict while allowing the same bounded startup as the VCS verifier.
constexpr int startup_timeout_ms = 600000;

[[noreturn]] void fail(const std::string &message) {
  std::fprintf(stderr, "SHADOW_PROTOCOL_ERROR: target_cycle=%llu pending=%u %s\n",
               static_cast<unsigned long long>(next_cycle), pending ? 1u : 0u, message.c_str());
  std::fflush(nullptr);
  // The authoritative VCS main thread can be parked while its FireSim worker
  // waits for this edge. VCS atexit teardown can then wait for that worker.
  // Flush the diagnostic and terminate without any simulator teardown/edges.
  std::_Exit(1);
}
void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}
uint64_t number(const std::string &s) {
  uint64_t value = 0;
  auto r = std::from_chars(s.data(), s.data() + s.size(), value);
  require(!s.empty() && (s == "0" || s.front() != '0') && r.ec == std::errc{} &&
          r.ptr == s.data() + s.size(), "invalid canonical integer");
  return value;
}
void wait_io(int fd, short events, Clock::time_point deadline) {
  for (;;) {
    auto left = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
    require(left > 0, "peer timeout");
    pollfd p{fd, events, 0};
    int r = poll(&p, 1, static_cast<int>(left));
    if (r < 0 && errno == EINTR) continue;
    require(r > 0, "peer timeout/poll failure");
    require(!(p.revents & (POLLERR | POLLNVAL)), "peer socket failure");
    // POLLIN with HUP must drain the final bytes, then recv reports EOF.
    require(p.revents & events, "peer disconnected");
    return;
  }
}
void write_line(const std::string &line) {
  require(line.size() <= maximum && line.find_first_of("\r\n") == std::string::npos,
          "oversized/multiline packet");
  auto deadline = Clock::now() + std::chrono::milliseconds(timeout_ms);
  const std::string bytes = line + '\n';
  size_t offset = 0;
  while (offset < bytes.size()) {
    wait_io(peer, POLLOUT, deadline);
    auto n = send(peer, bytes.data() + offset, bytes.size() - offset, MSG_NOSIGNAL);
    if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
    require(n > 0, "peer write failed");
    offset += static_cast<size_t>(n);
  }
}
std::string read_line() {
  auto deadline = Clock::now() + std::chrono::milliseconds(timeout_ms);
  std::string line;
  for (;;) {
    wait_io(peer, POLLIN, deadline);
    char byte;
    auto n = recv(peer, &byte, 1, 0);
    if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue;
    require(n == 1, "peer EOF before acknowledgment/end");
    if (byte == '\n') return line;
    require(byte != '\r' && line.size() < maximum, "oversized/malformed packet");
    line += byte;
  }
}
// Validate membership, sequence, bit widths/padding and canonical known bits
// before SV sscanf can truncate or coerce a malformed boundary value.
bool validate_data(const std::string &line) {
  std::istringstream input(line);
  std::string kind, cycle, token;
  require(static_cast<bool>(input >> kind >> cycle) && number(cycle) == next_cycle,
          "skipped/duplicated/wrong target cycle");
  require(kind == "DATA" || kind == "END", "unexpected packet kind");
  std::string canonical = kind + " " + cycle;
  if (kind == "DATA") {
    for (unsigned width : widths) {
      require(static_cast<bool>(input >> token) && token.size() == (width + 3) / 4 &&
              token.find_first_not_of("0123456789abcdef") == std::string::npos,
              "missing/unknown/reshaped boundary value");
      unsigned first = token.front() <= '9' ? token.front() - '0' : token.front() - 'a' + 10;
      require(width % 4 == 0 || first < (1u << (width % 4)), "nonzero boundary padding");
      canonical += " " + token;
    }
  }
  require(!(input >> token) && line == canonical, "extra/noncanonical packet fields");
  return kind == "END";
}
void validate_ack(const std::string &line) {
  require(line == "ACK " + std::to_string(next_cycle), "wrong/missing target acknowledgment");
}
}

extern "C" void shadow_open(const char *path, int is_server, const char *identity,
                            unsigned long long first_cycle, const char *shape) {
  try {
    require(peer == -1 && (is_server == 0 || is_server == 1), "duplicate/invalid endpoint");
    require(identity && std::strlen(identity) == 64 &&
            std::strspn(identity, "0123456789abcdef") == 64, "invalid session identity");
    require(path && *path && std::strlen(path) < sizeof(sockaddr_un{}.sun_path), "invalid socket path");
    std::istringstream input(shape);
    std::string token;
    maximum = 160;
    while (input >> token) {
      auto width = number(token);
      require(width > 0 && width <= 1048576, "unsupported boundary width");
      widths.push_back(static_cast<unsigned>(width));
      maximum += (width + 3) / 4 + 1;
    }
    require(!widths.empty() && maximum <= 1048576, "unsupported boundary size");
    server = is_server;
    next_cycle = first_cycle;
    socket_path = path;
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::strcpy(address.sun_path, path);
    peer = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    require(peer >= 0, "socket creation failed");
    auto deadline = Clock::now() + std::chrono::milliseconds(startup_timeout_ms);
    if (server) {
      require(bind(peer, reinterpret_cast<sockaddr *>(&address), sizeof(address)) == 0,
              "socket bind failed (existing paths are never replaced)");
      require(chmod(path, 0600) == 0 && listen(peer, 1) == 0, "socket setup failed");
      wait_io(peer, POLLIN, deadline);
      int connected = accept4(peer, nullptr, nullptr, SOCK_NONBLOCK | SOCK_CLOEXEC);
      require(connected >= 0, "accept failed");
      close(peer);
      peer = connected;
    } else {
      while (connect(peer, reinterpret_cast<sockaddr *>(&address), sizeof(address)) != 0) {
        require(errno == ENOENT || errno == ECONNREFUSED, "connect failed");
        require(Clock::now() < deadline, "connect timeout");
        poll(nullptr, 0, 10);
      }
    }
    const std::string hello = "HELLO " + std::string(identity) + " " + std::to_string(next_cycle);
    if (server) {
      require(read_line() == hello, "incompatible session/checkpoint/origin");
      write_line("READY");
    } else {
      write_line(hello);
      require(read_line() == "READY", "peer did not accept session");
    }
  } catch (const std::exception &e) { fail(e.what()); }
}

// Explicit simulator errors must use the same bounded termination as transport
// errors: a parked FireSim worker cannot participate in VCS atexit teardown.
extern "C" void shadow_fail(const char *message) { fail(message); }

extern "C" void shadow_send(const char *message) {
  try {
    require(peer >= 0 && !ended, "send outside live session");
    if (server) {
      require(pending, "acknowledgment without boundary");
      validate_ack(message);
      write_line(message);
      pending = false;
      ended = received.rfind("END ", 0) == 0;
      if (!ended) { require(next_cycle != UINT64_MAX, "target cycle overflow"); ++next_cycle; }
    } else {
      require(!pending, "advance before acknowledgment");
      validate_data(message);
      write_line(message);
      received = message;
      pending = true;
    }
  } catch (const std::exception &e) { fail(e.what()); }
}

extern "C" const char *shadow_receive() {
  try {
    require(peer >= 0 && !ended, "receive outside live session");
    if (server) {
      require(!pending, "new boundary before acknowledgment");
      received = read_line();
      validate_data(received);
      pending = true;
    } else {
      require(pending, "acknowledgment without boundary");
      const auto acknowledgment = read_line();
      validate_ack(acknowledgment);
      pending = false;
      ended = received.rfind("END ", 0) == 0;
      if (!ended) { require(next_cycle != UINT64_MAX, "target cycle overflow"); ++next_cycle; }
      received = acknowledgment;
    }
    return received.c_str();
  } catch (const std::exception &e) { fail(e.what()); }
}

extern "C" void shadow_close() {
  try {
    require(peer >= 0 && ended && !pending, "close without acknowledged end");
    close(peer);
    peer = -1;
    if (server) require(unlink(socket_path.c_str()) == 0, "socket removal failed");
  } catch (const std::exception &e) { fail(e.what()); }
}
