# Native input provenance across checkpoint iterations

The polling continuation and active-dispatch checkers distinguish an inherited
build's inputs from the live inputs of a new invocation. This fixes the
iteration-134 controller failure: all continuations executed, then the final
check incorrectly compared an evolved Python preparation auditor against its
older build-time hash.

`tools/checkpoint_formats/native_input_guard.py` first validates the original
source snapshots and native evidence through `check_native_input`. It then
archives and hashes the live inputs before execution. The final check compares
against these invocation-time hashes. Editing a source during the invocation
still rejects, even when an older valid snapshot exists.

Continuation reuses the prerequisite invocation's audited native and VCS
executables, starting a fresh process for each destination. Their original
source bindings remain in `source_inputs`; the new invocation's source bindings
are recorded separately in `invocation_source_inputs`. Generated binaries,
images, traces and logs under `runs/` retain their original-path hash checks.

Active-dispatch builds new native and VCS executables. Before invoking either
compiler, it requires every inherited non-Python input to match the recorded
build bytes. This includes C++ and SystemVerilog sources, transitive headers,
libraries and environment scripts. An inherited archive cannot justify
compiling changed native sources under an old source identity. A changed input
requires a new preparation build.

Independent audits validate both generations of snapshots, exact guard
membership and equality of inherited/current native compilation identities.
The executed checker snapshot determines whether invocation guards are
required; deleting the report field cannot disable them. Historical reports
whose checkers predate these guards remain auditable.

These changes repair validation infrastructure. Complete Rocket Level-1
continuation and independently captured Level-2 replay remain pending. See
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for executable commands and
the iteration-135 results. This does not change CPU checkpoint admission.
