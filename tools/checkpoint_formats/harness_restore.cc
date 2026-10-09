// Fresh harness component loader. This does not reconstruct the driver/DPI
// continuation. The coordinator must load generated/native owners separately.
// Hold clocks low and verify readback before permitting the first edge.
#include <sv_vpi_user.h>
#define RESTORE_TABLE "harness-restore-table.h"
#define RESTORE_MAGIC "FSHRNS1"
#define RESTORE_PHASE "settled_host_negedge"
#define RESTORE_LOG "HARNESS_RESTORE"
#define RESTORE_ACCEPTED_TYPE(entry, type) \
  ((type) == ((entry).clock_output ? vpiBitVar : vpiStructVar))
#define generated_restore harness_restore_deposit
#define generated_restore_verify harness_restore_readback
#define generated_restore_fail harness_restore_fail
#define generated_restore_prepare_text harness_restore_prepare_impl
#define generated_restore_commit harness_restore_commit_impl
#define generated_restore_deposit_count harness_restore_deposit_count
#include "generated_restore.cc"
#undef generated_restore
#undef generated_restore_verify
#undef generated_restore_prepare_text
#undef generated_restore_commit

namespace {
bool armed = false, advanced = false, loaded = false, poisoned = false;
s_vpi_value clock_value{};
s_vpi_time clock_time{};
s_cb_data clock_callback{};
vpiHandle clock_subscription = nullptr;
PLI_INT32 clock_changed(p_cb_data) {
  if (!low_clock()) advanced = true;
  return 0;
}
}

extern "C" int harness_restore_initialize() {
  s_vpi_time time{};
  time.type = vpiSimTime;
  vpi_get_time(nullptr, &time);
  if (armed || time.high || time.low || !low_clock())
    return fail("initialize at fresh time zero with clock low", clock_path);
  for (const auto *path : unsupported_paths)
    if (vpi_handle_by_name(const_cast<char *>(path), nullptr))
      return fail("unsupported debug/gate-level harness state", path);
  clock_value.format = vpiVectorVal;
  clock_time.type = vpiSuppressTime;
  clock_callback.reason = cbValueChange;
  clock_callback.cb_rtn = clock_changed;
  clock_callback.obj = vpi_handle_by_name(const_cast<char *>(clock_path), nullptr);
  clock_callback.value = &clock_value;
  clock_callback.time = &clock_time;
  clock_subscription = vpi_register_cb(&clock_callback);
  if (!clock_subscription) return fail("cannot guard first clock edge", clock_path);
  armed = true;
  return 0;
}

extern "C" int harness_restore(const char *filename) {
  if (!armed || advanced || loaded || poisoned)
    return fail("requires unused fresh armed harness before first edge", clock_path);
  const int result = harness_restore_deposit(filename);
  if (!result) loaded = true;
  return result;
}

extern "C" int harness_restore_prepare_text(const char *text) {
  if (!armed || advanced || loaded || poisoned)
    return fail("requires unused fresh armed harness before first edge", clock_path);
  return harness_restore_prepare_impl(text);
}

extern "C" int harness_restore_commit() {
  if (!armed || advanced || loaded || poisoned)
    return fail("requires unused fresh armed harness before first edge", clock_path);
  const int result = harness_restore_commit_impl();
  if (!result) loaded = true;
  return result;
}

extern "C" int harness_restore_verify() {
  if (!armed || advanced || poisoned) {
    if (loaded) poisoned = true;
    return fail("clock advanced or failed verification", clock_path);
  }
  const int result = harness_restore_readback();
  if (result && loaded) poisoned = true;
  return result;
}
