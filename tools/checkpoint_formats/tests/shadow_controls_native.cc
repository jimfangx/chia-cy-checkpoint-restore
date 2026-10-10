#include "../shadow_controls.h"
#include <iostream>

int main(int argc, char **argv) {
  try {
    if (argc < 2) return 2;
    const auto controls = checkpoint_shadow_controls_t::parse({argv + 2, argv + argc}, std::string(argv[1]) == "restore");
    std::cout << "PASS: controls=" << controls.values.size() << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cout << "REJECT: " << error.what() << '\n';
    return 1;
  }
}
