# Original physical-instance constraints

Iteration 234 extends the checked native-bank annotation translator to handle
constraints rooted directly at a shared native BUFGCE definition. Each argument
group expands over the **original** physical executions and becomes a circuit-rooted
path through the actual renamed ancestors. The added checkpoint mask gate is
excluded. Public and internal XDC keep their destinations, formats and correlated
pin groups. Unchanged siblings remain constrained. Hidden primitive state and
unsupported external definitions still reject.

Annotation translation provenance is version 2. Descriptor validation requires
the current version; older bindings must be regenerated rather than reused.
The in-place generator removes its previous primitive-local rejection only after
this checked projection is available. Bank generation performs the same
projection before clock wiring adds the mask primitive, so constraints originating
in the selected reference also keep their original execution scope.

The independent bounded auditor reconstructs the original and instrumented
instance graphs. It verifies all six emitted fixture XDC lines and rejects
fourteen annotation mutations, including local-leaf expansion onto the mask,
direct mask aliasing, mixed valid instances and loss of an original gate.
Canonical saved annotation JSON is compared independently of source ordering;
the verified, bound mapping sequence determines actual downstream XDC order.
The retained physical-gate auditor checks the new fully rooted targets, their
correlated pin tuples and the unchanged six emitted constraints.

All 248 Scala tests, 21 localhost synthesis scopes, 40 EDA scopes, 309 checkpoint
Python tests and 40 loop tests pass, including the retained ASan/UBSan, host and
FCFS regressions. The changed in-place fixture passes 6,541 fresh EDA SP2 checks
at four cuts, reading 128 words with 468 stalls through cycle 409 and retaining
six debug waveforms. It synthesizes to 884 LUTs and 590 registers, retaining all
194 raw parent/readout registers. Independent native/EDA matching binds 1,710
inputs and 41 current sources. Full-image timing closure remains pending.

Fresh run evidence and exact commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration234/`. This is annotation
integration, not complete production state ownership or FPGA capture. In-place
CE endpoint/router/widget attachment, exact stage-context projection, common
reset/external CE/functional-memory/FASED/bridge/host-owner freeze and physical CE
restore remain required. Full localhost image implementation/timing/AFI, actual
four-hart active FPGA cuts, paired zero-edge restore, finite/live RTL continuation
and rolling recovery remain pending.
