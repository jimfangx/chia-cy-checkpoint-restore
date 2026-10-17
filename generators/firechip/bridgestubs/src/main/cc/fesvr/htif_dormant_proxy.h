// See LICENSE for license details.
#ifndef FIRESIM_HTIF_DORMANT_PROXY_H
#define FIRESIM_HTIF_DORMANT_PROXY_H
#include <stdexcept>
class htif_t;

// Only the restricted FireSim caller may retire the inherited, unused proxy.
// Fresh construction reconstructs immutable registrations and owner pointers;
// no host descriptor number, function pointer or resource enters an image.
// This is an absent-resource invariant, not general syscall session restore.
struct firesim_htif_dormant_proxy_api_t {
  void (*retire)(htif_t &);
  void (*validate)(const htif_t &);
};
extern "C" const firesim_htif_dormant_proxy_api_t *firesim_htif_dormant_proxy_api() __attribute__((weak));
inline const firesim_htif_dormant_proxy_api_t &firesim_htif_require_dormant_proxy_api() {
  if (!firesim_htif_dormant_proxy_api)
    throw std::runtime_error("restricted syscall requires dormant proxy provider");
  const auto *api = firesim_htif_dormant_proxy_api();
  if (!api || !api->retire || !api->validate)
    throw std::runtime_error("incomplete dormant proxy provider interface");
  return *api;
}
#endif
