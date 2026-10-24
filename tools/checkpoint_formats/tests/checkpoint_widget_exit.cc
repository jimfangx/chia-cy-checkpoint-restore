// Preserve a nonzero process status AFTER $finish closes VCS debug outputs.
// No RTL state access, simulation control, backdoor or target-edge operations.
#include <cstdlib>
extern "C" void checkpoint_widget_failed() {
  static bool registered = false;
  if (!registered) {
    if (std::atexit([]() { std::_Exit(EXIT_FAILURE); }) != 0)
      std::exit(EXIT_FAILURE);
    registered = true;
  }
}
