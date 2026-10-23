// Process failure status only. No state access, simulation control or backdoor.
#include <cstdlib>
extern "C" void checkpoint_network_fail() { std::exit(1); }
