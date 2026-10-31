# Synchronous reset ownership at a common clock cut

Iteration 290 adds `CheckpointResetOwnedClockCut`, a synthesizable companion to
the existing common-source physical clock controller. Collector initialization
and functional reset are separate inputs. During ordinary execution, functional
reset retains its original wire path. At the falling edge that closes the clock
mask, the companion samples every functional reset bit. Frozen synchronous
consumers then see those held values while the collector continues on the raw
clock.

A reset-source change or missing reset writer immediately withdraws read
permission and keeps the physical clock mask closed. Positive-edge sticky
errors prevent request withdrawal, a returned reset value or restored owner
presence from repairing an invalid cut. The reset and external-owner checks
also protect the falling edge after release has already been validated. Wide
CE/cycle comparisons retain their existing registered validation path instead
of feeding a new gated-to-raw half-cycle path.

The interface supports a vector of synchronous reset sources and both internal
and externally supplied clock networks. Its live control vector is, from least
significant bits, the existing `GATES+70` physical-control bits, `RESETS` captured
reset bits, and `RESETS+1` reset-error bits. The error vector contains changed
reset bits followed by a missing-writer bit. This observation port supplies no
atomic capture or restore owner for the collector itself.

Asynchronous resets, pulses between source sampling edges, unrelated clocks
and arbitrary external writers remain unsupported. `controller_reset` belongs
to collector initialization and cannot be connected to the functional reset
writer. Production mapping must prove that every relevant synchronous reset
consumer receives `functional_reset`, bind its exact writer and complete owner
manifest, and supply separate collector capture/restore ownership. This module
does not install that mapping in the Rocket recipe or relax image guards.
The retained production gap audit names `F1Shim.reset` as an external CE-cone
input, alongside 207 distinct state owners feeding three native gates. Its
producer, consumers and synchrony still need proof; a one-cone binding or an
assumed synchronous reset cannot establish the complete production cut.

Native synthesis and EDA verification commands, immutable attempts, underlying
compiler/runtime diagnostics, vendor models and debug waves are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration290/`. The component bench uses
an independent original vendor-gate execution, both reset sources, four cuts,
backpressure and continued execution. It checks reset changes, missing writers,
owner loss, release races and the first semantic-readback mismatch.

Vivado 2025.2 synthesizes one root and three native default-SYNC BUFGCEs, with
one physical mask register and two reset-snapshot bits on the falling edge.
At the unchanged requested 140 MHz constraint, unplaced setup slack is
+2.181 ns and hold slack is -0.072 ns. Synthesis alone does not close timing;
these estimates exclude the enclosing clock source and shell I/O budgets.
Implementation of that exact DCP reaches +1.979 ns setup and +0.044 ns hold,
preserving all 242 sequential cell identities, including four BUFGCEs. All 444
routable nets complete with no routing errors or reported DRC violations.
The implemented hardware sources and synthesis inputs remain unchanged by the
later packed debug views and process-status helper changes. An explicit literal
comparison binds those changes to files not read by the synthesis Tcl.
The original implementation date and
DCP identity are retained; no full-shell timing or FPGA image is established.

Complete Rocket common-cut/reset/CE mapping, selective functional hold with an
ungated collector, native transport self-ownership and peer/reservation binding,
memory/FASED/host ownership and independent pre-FAME mapping remain required.
No checkpoint-enabled image, AFI, physical capture or paired CPU migration is
established by this component. All four required hardware cuts and finite,
live and rolling hardware acceptance remain pending.
