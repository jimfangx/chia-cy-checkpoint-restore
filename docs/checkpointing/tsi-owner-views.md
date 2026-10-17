# Retained TSI owner references

Iteration 154 closes an escape from iteration 153's creator-thread policy.
A caller could obtain a component's `checkpoint_owner_t` reference on the
creator thread and subsequently call it on a foreign thread without going
through the checked getter. The sixteen public TSI component getters now return
stable checked views. Schema, save, validation and load each check the live
creator before reading the underlying owner or optional owner slot. Malformed
images do not bypass that check. Serialized component images are unchanged.

Each view refers to its containing TSI's actual owner slot. In particular, it
does not retain a raw pointee from a `unique_ptr` that aggregate publication
can replace. An absent optional owner rejects. Views allocate no storage and
cannot be copied or moved. Their containing TSI must outlive every borrowed
reference. Component-level image loading remains available through the base
interface for the existing fault-injection checks; it enforces the same thread
policy and does not grant aggregate restore admission. Concrete-device
downcasts from observation references are no longer supported. The lifecycle
test now introduces its late terminal-cursor mutation through a validated image.

The expanded native ASan/UBSan and VCS test obtains real production owner
references before attempting foreign-thread schema/save/validate/load and
malformed-load calls. It checks every public owner at execution and returned-tail
cuts, compares complete owner bytes, preserves candidate retries and checks
creator operations against the independently executed context oracle. Fixed
serial/terminal views are borrowed before aggregate publication. The ordinary
runtime reader, which is separate from the restricted syscall's nested reader,
must retain its independently encoded pristine image. The independent auditor
retains the previous 45-entry receipt format and requires all new cases for
receipts declaring retained-view coverage.

A separate native/VCS diagnostic exercises replacement and removal of an
optional owner, creator retries, and real recycled OS-thread IDs after creator
exit. It checks that rejected operations never reach the underlying owner.
The prior-source sensitivity diagnostic compiles the same access harness with
the archived iteration-153 production sources and headers; its deliberately
failing processes demonstrate the original raw-reference gap.

This is host-component access coverage. It neither suspends VCS workers nor
coordinates process signals/actions/masks, inherited HTIF services or all
simulator state. Complete Rocket Level 1 remains disabled pending production
exclusion and coherent simulator/FAME/bridge/functional-memory publication.
Level 2 remains the independent four-cut ordinary RTL replay. BOOM and Saturn
remain pending; standalone Shuttle, physical FPGA validation and ASIC power are
outside this increment.

The next integration must respect two actual runtime threads. `tsibridge_t`'s
`services_t::create()` constructs FESVR on the driver execution thread.
`simif_emul_t::capture_driver_boundary()` runs there before parking it, whereas
the settled low-clock callback runs on the VCS thread. Consequently, passing
TSI owner references to that callback cannot authorize observation, even while
the driver is parked. Serialize supported TSI owners on their creator, hand
immutable bytes across the existing mutex/condition-variable boundary, and bind
them to the same settled simulator cut. Fresh restoration likewise needs
destination preparation/publication on the new driver creator before resuming
any target edge. This is an integration requirement, not an implemented
coordinator. The actual all-thread signal policy and every other generated,
bridge, driver and functional-memory owner still need coordinated admission.

Exact results, receipt paths and executable checks are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic files stay under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/`.
