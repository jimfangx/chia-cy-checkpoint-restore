# Compiler context at the selected checkpoint widget

`NativeCheckpointWidgetGraft.connectProjected` accepts the exact inert compiler
context already validated by `NativeCheckpointInPlaceContext`. Storage contracts
still use their typed projection and circuit rename. Compiler context is checked
separately and retains its original values and historical circuit names.

Every source context annotation must occur exactly once in both the enclosing
pre-inline input and the projected host. The complete enclosing context passes
the existing compiler-context validator. The connector inserts no source context
into the host and never substitutes a selected-source driver header for the
registered host header. Missing context, conflicting or duplicate options,
changed channel ratios, output collisions and unknown owners reject. The strict
`connect` API retains its original policy. Validating the original input matters:
FIRRTL inlining can coalesce identical annotations, hiding their original
multiplicity from a check performed only after inlining.

The source-policy receipt additionally binds the original and grafted source
context, the enclosing context and both independently reconstructible context
snapshots. The independent Python auditor reconstructs these from raw annotation
files and checks both enclosing boundaries. JsonProtocol sometimes includes a
nested input-file class hint in a complete annotation list but omits it from a
context-only list. The auditor accepts only the two exact consumed-input
producers and their matching optional hints; it preserves the original files
and hashes and rejects unknown producers, mismatched hints and deleted owners.

This is compiler integration for the existing synthesized readout path. It
provides no missing capture owner or FPGA acceptance. Source/global state and
driver identity, the FASED physical CE owner, reset/external writers, functional
DRAM, timing, bridge/host and pre-FAME state remain required. Complete image
implementation/AFI, active four-hart F2 capture and paired CPU migration with
finite replay, sustained live RTL and rolling recovery remain pending.

Current diagnostic artifacts and runnable verification scripts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration252/`. Failed and superseded
attempts are retained; only explicitly pinned successful receipts establish a
component result. This document does not assert a full-image or hardware result.

Final iteration-252 validation passes 272 Scala tests across 40 suites plus twelve
preparation/directed executions, 330 Python tests, 40 loop tests, nine localhost
native scopes and nine EDA SP2 scopes. The source fixture checks seven context
kinds and eighteen connector rejections; its independent native audit rejects
34 mutations and matches 641 sources / 686 inputs. The existing connected
transport still passes 5,165 checks, four cuts, 136 words and 900 stalls, with
complete debug waves and the first compiled payload defect before release.
The exact-Rocket bank-context audit independently checks 25 annotations across
20 context kinds within 2,456 source annotations. These are compiler and
component results. Full hardware-origin CPU acceptance remains pending.
