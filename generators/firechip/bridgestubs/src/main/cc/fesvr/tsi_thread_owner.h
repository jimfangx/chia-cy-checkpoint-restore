// See LICENSE for license details.
#ifndef FIRESIM_TSI_THREAD_OWNER_H
#define FIRESIM_TSI_THREAD_OWNER_H
#include <memory>
#include <stdexcept>
#include <thread>

// Process-local access policy, never checkpoint data. A TSI's coroutine and
// protocol owners belong to the constructing OS thread. Check this before
// reading any mutable owner, including candidate consumption flags. Keeping a
// weak lifetime token also rejects a recycled std::thread::id after creator exit.
// This confines supported TSI entries; it does not freeze foreign simulator
// threads or coordinate process signals, actions or arbitrary raw owner access.
class firesim_tsi_thread_owner_t {
public:
  firesim_tsi_thread_owner_t() : creator(std::this_thread::get_id()), lifetime(token()) {}
  void require() const {
    if (std::this_thread::get_id() != creator || lifetime.expired())
      throw std::runtime_error("TSI access requires its live original thread");
  }
private:
  const std::thread::id creator;
  const std::weak_ptr<const char> lifetime;
  static const std::shared_ptr<const char> &token() {
    static thread_local const auto value = std::make_shared<const char>(0);
    return value;
  }
};
#endif
