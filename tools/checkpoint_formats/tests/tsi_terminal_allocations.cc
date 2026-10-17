// Test-only, thread-local fault injection around the production transaction.
// Disabled during simulator startup, file I/O, readback and exception reporting.
#include <cstdlib>
#include <new>

static thread_local long remaining = -1;
static thread_local std::size_t rejected_size = 0;
void tsi_terminal_fail_allocation_after(long count) { remaining = count; }
void tsi_terminal_fail_allocation_size(std::size_t size) { rejected_size = size; }
void *operator new(std::size_t size) {
  if (size == rejected_size && rejected_size) { rejected_size = 0; throw std::bad_alloc(); }
  if (remaining == 0) throw std::bad_alloc();
  if (remaining > 0) --remaining;
  if (auto p = std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
