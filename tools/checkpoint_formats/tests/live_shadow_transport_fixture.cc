#include <cstdio>
#include <cstring>

extern "C" void shadow_open(const char *, int, const char *, unsigned long long, const char *);
extern "C" void shadow_send(const char *);
extern "C" const char *shadow_receive();
extern "C" void shadow_close();

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  const bool server = std::strcmp(argv[1], "server") == 0;
  shadow_open(argv[2], server, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 42, "1 9");
  if (server) {
    const char *rows[] = {"DATA 42 1 101", "DATA 43 0 1ff", "END 44"};
    const char *acks[] = {"ACK 42", "ACK 43", "ACK 44"};
    for (unsigned i = 0; i < 3; ++i) {
      if (std::strcmp(shadow_receive(), rows[i]) != 0) return 3;
      shadow_send(acks[i]);
    }
  } else {
    shadow_send("DATA 42 1 101");
    if (std::strcmp(shadow_receive(), "ACK 42") != 0) return 3;
    shadow_send("DATA 43 0 1ff");
    if (std::strcmp(shadow_receive(), "ACK 43") != 0) return 3;
    shadow_send("END 44");
    if (std::strcmp(shadow_receive(), "ACK 44") != 0) return 3;
  }
  shadow_close();
  std::puts("PASS: live transport lockstep");
}
