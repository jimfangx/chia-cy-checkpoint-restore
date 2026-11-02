# Source-bound regional FAME freeze projection

Iteration 9796 adds an explicit original-source projection for FAME roles in
native regional banks. Ordinary `FAMEClockProgressBindings.resolve` retains its
strict uninstrumented contract. Only construction and validation paths carrying
the original executable `CircuitState` may use `resolveFrozen`.

The projection checks the original role contract and the complete identity set,
concrete execution paths, types and storage kinds. It compares every original
statement in each role-owning module against the permitted bank self-hold,
reset lowering, physical root-clock and native BUFGCE mask rewrites. Original
ports, logical enables, observer arithmetic, pending flags, output drivers and
clocked effects remain bound to their source equations. Unselected role owners
must preserve their original equations. No serialized annotation or rehashed
manifest grants an exception.

This is a local equation proof. Complete native in-place/regional regeneration
separately authenticates the selected execution and ancestor sideband routes.
The projection supplies no physical owner acknowledgement, global target-time
authority, production memory/host/transport owner, restore mapping or image
admission. The existing incomplete-image guard remains required.

The directed fixture uses the real two-domain FAME transform and native bank
generator. Its arithmetic reset is performed by zero-valued target input tokens
in the original test source, with no simulator state writes. The independent
Python checker reconstructs original equations and regional freeze/mask routes
from raw FIRRTL and annotations; it does not trust producer hashes. Mutations
exercise hold/reset/clock/functional equations, native enable and role identity.

Current evidence, exact commands and failed exploratory attempts are retained
under `automations/checkpoint_loop/runs/aws-f2/iteration9796/`. Final verification
and remaining production blockers are recorded in `progress.md`. No FPGA-origin
checkpoint or CPU migration is established by this component fixture.

The actual observed Rocket diagnostic reconstructs 10,916 entries, including
six new observer registers / 321 bits. Its original test reservation has 10,910
entries and correctly refuses the mismatch. The three native gates occupy two
regional CE groups (counts two and one). The independent raw-IR audit checks all
21 roles / 323 observer-and-pending bits and all 86 original registers in the
role-owning module. This clears the earlier FAME equation rejection; refreshing
the production reservation and binding complete owners remain required before
image admission. The guard has not been overridden.
