# Sealed terminal component state

Iteration 116 adds an opt-in production BCD terminal owner. Complete Rocket
Level-1 continuation and captured Level-2 readback/replay remain pending.

`+checkpoint-terminal-input=/absolute/path/to/input.bin`, inside the permissive
host options, captures a regular file's bytes at TSI construction. The file
descriptor closes before construction returns. Subsequent BCD reads use the
captured bytes, including NUL and 255, and deterministic EOF. The input and
output transcript each have a 1 MiB bound; unsupported input types/sizes and
output overflow fail explicitly. No FPGA bitstream or hardware is involved.

`firesim_tsi_terminal_t` owns the exact input bytes, consumption cursor and
binary output transcript. Its component image binds its version, mode, limits
and complete input. A destination must supply the same input configuration.
Loading validates the entire image and allocates the replacement transcript
before mutating either field. Loading emits no output and consumes no input;
the transcript includes output before the cut without re-emitting that prefix.
Future writes still call the destination output service at their original BCD
operation. This does not restore a host terminal or rewind external stdout.

The default live-terminal path retains canonical FESVR I/O and reports no
supported checkpoint schema. Save, validate and load reject that path. Active,
reentrant and interrupted services reject checkpoint operations. Interrupted
output and transcript overflow poison the owner rather than acknowledging an
uncertain cut. BCD still separately owns pending commands and response binding.

The production TSI lifetime owns the terminal before its BCD. Ordinary execution
and the original BCD component interface remain compatible. Startup metadata
preparation explicitly rejects the new mode: its seven-peer metadata contract
does not yet bind this additional owner. The terminal accessor is for inspection;
complete HTIF/device/caller/aggregate restoration is still disabled. Syscall
descriptors, process signals, live terminal/termios state and stop/exit state
remain separate pending owners. The sealed stream does not model timed input
arrival; it represents an input file whose bytes are available from startup.
The existing eight-component `inspect_polling_cut()` audit excludes this new
owner. Its images cannot establish a complete sealed-mode cut. The sealed
input service applies to the owned default BCD route; configured installed HTIF
routes remain outside this component's checkpoint scope.

## Native verification

The retained invocation is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration116/terminal/invocation-imxpr74q/summary.json`.
Its source snapshots, exact native argv, all images/readbacks, output suffixes,
event logs, simulator and hashes remain under that invocation. Diagnostic logs
are outside tracked documentation.

Native ASan/UBSan and Y-2026.03-SP1 VCS DPI pass all four producer/destination
backend pairings at 13 cuts, including queued input commands, consumed input,
binary output, EOF with pending requests and late output. An independent Python
byte oracle audits every terminal and BCD image, both complete readbacks before
services, every suffix event and final state. All 52 fresh continuations/312
host events match. Restored stdout emits only the suffix.

The checks reject 568 malformed images, four incompatible input configurations
and eight missing/invalid peer cases before changing either owner or issuing a
service. Four structurally valid wrong-cursor images diverge first at host event
2: the expected response contains `0x141`, the actual response `0x100`, with
the same BCD device tag. These are component events, not CPU target-cycle cuts.
Live/active/interrupted/output-limit guards pass on both backends (28 cases).

Two production TSI runs execute the installed ELF loader and actual BCD route,
consume all three captured input bytes even after replacing the source file,
send the exact serial responses, record a real stdout write, reject unbound
startup metadata and terminate successfully. These are transport fixtures;
they do not establish a complete CPU checkpoint.

Reproduce from the Chipyard root, using a new retained invocation:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration116-controller-rechecks/terminal
```

Audit the saved run independently:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration116/terminal/invocation-imxpr74q/summary.json
```

Every native compiler/simulator shell sources both repository environments and
`vcs-env.sh` last, uses system GCC/G++ 13 and VCS `-full64`. See the CPU matrix
for the exact recipe settings, full workload controls and the separate ordinary
RTL diagnostic. Neither CPU level is verified by these component results.
