// Process-local context lifetime checks, also executed from native VCS DPI.
#include <fesvr/context.h>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <thread>

namespace {
constexpr size_t stack_bytes = 1024 * 1024;
std::atomic<int> live{0}, allocated{0}, released{0};
std::atomic<bool> fail_allocation{false};
// Test-only allocation interception; production has no testing entry points.
void *stacks[128]{};
void check(bool ok) { if (!ok) throw std::runtime_error("context oracle mismatch"); }
}
void *operator new[](size_t bytes) {
  if (bytes == stack_bytes && fail_allocation.exchange(false)) throw std::bad_alloc();
  void *p = std::malloc(bytes);
  if (!p) throw std::bad_alloc();
  if (bytes == stack_bytes) {
    bool found = false;
    for (auto &slot : stacks) if (!slot) { slot = p; found = true; break; }
    if (!found) std::abort();
    ++live; ++allocated;
  }
  return p;
}
void operator delete[](void *p) noexcept {
  for (auto &slot : stacks) if (p && slot == p) {
    slot = nullptr; --live; ++released; break;
  }
  std::free(p);
}
void operator delete[](void *p, size_t) noexcept { operator delete[](p); }

namespace {
struct task_t {
  context_t child;
  context_t *parent = context_t::current();
  int step = 0;
  int rounds = 0;
  bool finish = false;
  static void body(void *arg) {
    auto &task = *static_cast<task_t *>(arg);
    volatile unsigned char values[4096];
    for (size_t i = 0; i < sizeof(values); ++i) values[i] = i % 251;
    for (int round = 0;; ++round) {
      check(context_t::current() == &task.child);
      for (size_t i = 0; i < sizeof(values); ++i) check(values[i] == i % 251);
      ++task.step;
      if (task.finish && round == task.rounds) return;
      task.parent->switch_to();
    }
  }
};
// Model metasim's intentionally retained registry. Keep the object reachable
// while checking that thread teardown releases its suspended stack allocation.
task_t *retained_task = nullptr;
template<class F> void rejected(F f) {
  bool caught = false;
  try { f(); } catch (const std::runtime_error &) { caught = true; }
  check(caught);
}
struct nesting_t {
  context_t parent;
  task_t *inner = nullptr;
  context_t *root = context_t::current();
  static void body(void *arg) {
    auto &n = *static_cast<nesting_t *>(arg);
    // Keep the child on the heap so the death test can deliberately try
    // destroying its creator. The ordinary test deletes child first.
    n.inner = new task_t;
    n.inner->child.init(task_t::body, n.inner);
    n.inner->child.switch_to();
    n.root->switch_to();
    n.inner->child.switch_to();
    check(n.inner->step == 2);
    delete n.inner;
    n.inner = nullptr;
    n.root->switch_to();
  }
};
int run_checks(const char *mode) {
  if (!std::strcmp(mode, "stack-leak")) {
    for (int i = 0; i < 2; ++i) {
      task_t task;
      task.child.init(task_t::body, &task);
      task.child.switch_to();
      check(task.step == 1);
    }
    std::cout << "STACK_LIFETIME allocated=" << allocated << " released=" << released
              << " live=" << live << std::endl;
    return live == 0 ? 0 : 2;
  }
  if (!std::strcmp(mode, "active-destroy")) {
    context_t::current()->~context_t();
    return 1;
  }
  if (!std::strcmp(mode, "active-exit")) {
    context_t child;
    child.init([](void *) { std::exit(17); }, nullptr);
    child.switch_to();
    return 1;
  }
  if (!std::strcmp(mode, "creator-destroy")) {
    auto *n = new nesting_t;
    n->parent.init(nesting_t::body, n);
    n->parent.switch_to();
    delete n;
    return 1;
  }
  check(!std::strcmp(mode, "checks"));
  context_t *root = context_t::current();
  check(live == 0);
  { context_t fresh;
    rejected([&] { fresh.switch_to(); });
    rejected([&] { fresh.init(nullptr, nullptr); });
    rejected([&] { root->switch_to(); });
    rejected([&] { root->init(task_t::body, nullptr); });
  }
  int suspended = 0, returned = 0, switches = 0;
  for (int index = 0; index < 256; ++index) {
    const int before = live;
    {
      task_t task;
      task.finish = index % 2;
      task.rounds = index % 7;
      task.child.init(task_t::body, &task);
      check(task.step == 0 && live == before + 1);
      rejected([&] { task.child.init(task_t::body, &task); });
      for (int round = 0; round <= task.rounds; ++round) {
        task.child.switch_to(); ++switches;
        check(task.step == round + 1 && context_t::current() == root);
      }
      if (task.finish) { ++returned; rejected([&] { task.child.switch_to(); }); }
      else ++suspended;
    }
    check(live == before);
  }
  // Interleaved siblings retain separate stack-local data.
  {
    task_t first, second;
    first.child.init(task_t::body, &first);
    second.child.init(task_t::body, &second);
    for (int i = 0; i < 64; ++i) {
      second.child.switch_to(); first.child.switch_to();
      check(first.step == i + 1 && second.step == i + 1);
    }
  }
  check(live == 0);
  {
    nesting_t n;
    n.parent.init(nesting_t::body, &n);
    n.parent.switch_to(); check(live == 2 && n.inner->step == 1);
    n.parent.switch_to(); check(live == 1 && n.inner == nullptr);
  }
  check(live == 0);
  // A failed stack allocation must leave the child fresh and retryable.
  {
    task_t task;
    fail_allocation = true;
    bool caught = false;
    try { task.child.init(task_t::body, &task); } catch (const std::bad_alloc &) { caught = true; }
    check(caught && live == 0 && task.step == 0);
    task.child.init(task_t::body, &task);
    task.child.switch_to(); check(task.step == 1);
  }
  check(live == 0);
  // Root allocation and current() are thread-local and cleaned at thread exit.
  for (int i = 0; i < 16; ++i) {
    std::thread worker([&] {
      check(context_t::current() != root);
      rejected([&] { root->switch_to(); });
      task_t task;
      task.child.init(task_t::body, &task);
      task.child.switch_to(); check(task.step == 1);
    });
    worker.join(); check(live == 0 && context_t::current() == root);
  }
  std::thread retained_worker([] {
    retained_task = new task_t;
    retained_task->child.init(task_t::body, retained_task);
    retained_task->child.switch_to();
    check(retained_task->step == 1 && live == 1);
  });
  retained_worker.join();
  check(retained_task && live == 0 && context_t::current() == root);
  check(allocated == released && live == 0);
  std::cout << "CONTEXT suspended=" << suspended << " returned=" << returned
            << " switches=" << switches << " allocated=" << allocated
            << " released=" << released << " live=" << live << "\n";
  return 0;
}
} // namespace

extern "C" int fesvr_context_lifetime(const char *mode) {
  try { return run_checks(mode); }
  catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
#ifndef FESVR_CONTEXT_DPI
int main(int argc, char **argv) { return fesvr_context_lifetime(argc == 2 ? argv[1] : "checks"); }
#endif
