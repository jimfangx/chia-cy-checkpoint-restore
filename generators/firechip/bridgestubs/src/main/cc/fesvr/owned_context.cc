// See LICENSE for license details.
// ABI-compatible replacement for FESVR context.cc. Keep the installed header
// and class layout; own coroutine stacks outside the opaque ucontext_t.
// This manages process-local resources, not a serializable checkpoint owner.
#include <fesvr/context.h>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <stdexcept>
#include <system_error>

#ifndef USE_UCONTEXT
#error "checkpoint FESVR context ownership requires glibc ucontext"
#endif

namespace {
constexpr size_t stack_bytes = 1024 * 1024;
struct allocation_t {
  std::unique_ptr<void*[]> stack;
  context_t *creator = nullptr;
  bool finished = false;
};
[[noreturn]] void lifetime_error(const char *message) {
  std::fprintf(stderr, "FESVR context lifetime: %s\n", message);
  std::abort();
}
struct runtime_t {
  context_t *current = nullptr;
  context_t *root = nullptr;
  bool exiting = false;
  std::map<context_t *, allocation_t> allocations;
  ~runtime_t();
};
runtime_t &runtime() {
  static thread_local runtime_t value;
  return value;
}
runtime_t::~runtime_t() {
  // std::exit from a callback runs TLS destructors on the child stack. Never
  // free that executing stack; active host termination is not an admitted cut.
  if (current && current != root)
    lifetime_error("thread exit while a child is active");
  // Metasim intentionally retains its bridge registry after the driver thread
  // returns. Release those suspended stacks at thread exit too. The retained
  // objects cannot be resumed or destroyed from a foreign thread; public
  // operations still reject them through that thread's allocation registry.
  exiting = true;
  current = nullptr;
  delete root;
  // allocations owns all remaining stacks and is destroyed next.
}
allocation_t &allocation(context_t *ctx) {
  auto &entries = runtime().allocations;
  auto it = entries.find(ctx);
  if (it == entries.end())
    throw std::runtime_error("FESVR context belongs to another thread");
  return it->second;
}
} // namespace

context_t::context_t()
    : creator(nullptr), func(nullptr), arg(nullptr), context(new ucontext_t{}) {
  runtime().allocations.emplace(this, allocation_t{});
}

context_t::~context_t() {
  auto &rt = runtime();
  if (rt.exiting) return; // Only the root is deleted by runtime_t's destructor.
  if (this == rt.current) lifetime_error("destroying the active context");
  if (!rt.allocations.count(this)) lifetime_error("destroying a foreign context");
  for (const auto &entry : rt.allocations)
    if (entry.second.creator == this)
      lifetime_error("destroying the creator of a suspended context");
  // Suspended frames are discarded, not unwound. Callers must keep resumable
  // semantic state and resource ownership outside those frames. Active service
  // cuts remain unsupported by the checkpoint admission checks.
  rt.allocations.erase(this);
}

void context_t::init(void (*f)(void *), void *a) {
  auto &owned = allocation(this);
  if (!f || owned.stack || this == runtime().root)
    throw std::runtime_error("FESVR context init requires a fresh child and callback");
  auto *parent = current();
  std::unique_ptr<void*[]> stack(new void*[stack_bytes / sizeof(void*)]);
  if (getcontext(context.get()) != 0)
    throw std::system_error(errno, std::generic_category(), "FESVR getcontext");
  context->uc_link = parent->context.get();
  context->uc_stack.ss_size = stack_bytes;
  context->uc_stack.ss_sp = stack.get();
  context->uc_stack.ss_flags = 0;
  creator = parent;
  func = f;
  arg = a;
  owned.creator = parent;
  owned.stack = std::move(stack);
#ifndef GLIBC_64BIT_PTR_BUG
  makecontext(context.get(), (void(*)(void))&context_t::wrapper, 1, this);
#else
  unsigned int hi(reinterpret_cast<unsigned long>(this) >> 32);
  unsigned int lo(reinterpret_cast<unsigned long>(this));
  makecontext(context.get(), (void(*)(void))&context_t::wrapper, 2, hi, lo);
#endif
  switch_to();
}

#ifndef GLIBC_64BIT_PTR_BUG
void context_t::wrapper(context_t *ctx) {
#else
void context_t::wrapper(unsigned int hi, unsigned int lo) {
  auto *ctx = reinterpret_cast<context_t *>(static_cast<unsigned long>(lo) |
                                            (static_cast<unsigned long>(hi) << 32));
#endif
  ctx->creator->switch_to();
  ctx->func(ctx->arg);
  // uc_link returns to the creator. Keep current() consistent with that
  // implicit transfer and reject subsequent attempts to enter a finished stack.
  auto &owned = allocation(ctx);
  owned.finished = true;
  owned.creator = nullptr;
  runtime().current = ctx->creator;
}

void context_t::switch_to() {
  auto &rt = runtime();
  auto &owned = allocation(this);
  if (!rt.current || this == rt.current || owned.finished ||
      (!owned.stack && this != rt.root))
    throw std::runtime_error("FESVR context switch requires a suspended live context");
  auto *previous = rt.current;
  rt.current = this;
  if (swapcontext(previous->context.get(), context.get()) != 0)
    lifetime_error("swapcontext failed");
}

context_t *context_t::current() {
  auto &rt = runtime();
  if (!rt.current) {
    std::unique_ptr<context_t> root(new context_t);
    if (getcontext(root->context.get()) != 0)
      throw std::system_error(errno, std::generic_category(), "FESVR root getcontext");
    rt.root = root.release();
    rt.current = rt.root;
  }
  return rt.current;
}
