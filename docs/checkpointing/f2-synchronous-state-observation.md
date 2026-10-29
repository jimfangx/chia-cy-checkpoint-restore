# Native synchronous queue state observation

Iteration 271 adds synthesized taps for the state introduced by the synchronous
native RAM adapter. The original logical StateIDs and original bank selectors
are retained. The added `ckpt_native_state` output is combinational and reaches
the enclosing root through each concrete shell's existing sideband namespace.
It introduces no storage, clock, reset, extra RAM reader or sampling edge.

The generator inventories the actual instrumented circuit, subtracts the exact
original storage mapping, and accounts for every remaining register, including
the implicit Old/read-first RAM data register that the emitter creates. The
canonical `native_state_observation` binding records each instrumented StateID,
path, expression, width, signedness, raw-clock expression and ascending bit offset.
Logical FIRRTL paths remain distinct from final emitted register paths. The
component emitter lowers the Old data owner to `ram_r_data_pipe_0`; `ram_r_data`
is a combinational memory wire. Native/EDA receipts independently bind each field
to an actual emitted register, check its width and the complete register set, and
verify that implicit data storage has the exact positive-clock sampling equation.
The native adapter's immutable source proof reconstructs the entire observation
network and schema, so recomputed hashes cannot excuse changed equations or
omitted state. Independent verification reconstructs the layout from the emitted
FIRRTL, using a separate inventory parser.

The reduced shared queue has fourteen added fields / 518 bits per selected
execution. The exact Rocket Queue_56 geometry has fourteen fields / 1,664 bits.
These include registered write-first forwarding, the public output shadow,
borrowed-reader state, both response/selector endpoints and the implicit RAM data
pipeline. Original storage remains separately banked. A manifest of original
storage alone does not include these added owners.

This is a live observation vector. Endpoint registers and borrowed RAM data can
change while functional storage is frozen. A consumer must sample the entire
vector coherently at a proven common raw-clock cut; serial multiword reads are
not an atomic checkpoint. The binding explicitly retains false atomic-snapshot,
complete-capture-owner, frozen-stability and metasim-restore flags. No checkpoint
image is admitted by this observation interface. Production still needs an
atomic snapshot/restore owner for these fields and its own staging/control state,
as well as the existing clock, memory, host, transport and pre-FAME owners.

The component checks compare every exported field against the actual emitted
registers on both clock phases, covering reset, active traffic, write-first
collisions, borrowing, reprime, response stalls, cancellation and release. Native
BLOCK/ULTRA inference and the retained regressions must also pass. Coherently
rehashed layout/equation/ownership corruptions and a compiled tap fault are
required negatives. Fresh receipts and commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration271/`; final results are recorded
in `progress.md`. Component observations do not establish physical FPGA capture,
zero-edge CPU migration, finite replay, live CPU comparison or rolling recovery.
