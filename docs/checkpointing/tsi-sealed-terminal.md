# Sealed terminal component state

Iteration 116 added an opt-in production BCD terminal owner. Iteration 117
binds that owner into startup metadata and the suspended polling audit.
Complete Rocket Level-1 continuation and captured Level-2 readback/replay remain
pending.

Iteration 118 adds `firesim_tsi_bcd_t::load_sealed_checkpoint`, a transaction
over the ordered `terminal` and `bcd` component images. It uses the terminal
already bound to the destination device. Both parsers validate the entire
image, check supported/idle service boundaries and allocate replacement storage
before either owner changes. Publication consists only of statically checked
nonthrowing swaps and cursor assignment. A second allocation failure after a
terminal load can no longer leave the pair partially restored. Individual
component image formats and normal device execution remain unchanged.

This is a component transaction, not the complete HTIF aggregate. The polling
response queue, startup metadata, syscall state, signals, stop/exit and caller
reconstruction still require their own coherent restoration. Complete CPU
admission remains disabled. Ordered peer membership rejects missing, extra,
duplicate, unknown and reordered owners. It does not certify that independently
supplied valid images came from a single CPU cut.

Native ASan/UBSan and VCS DPI verification now exercise the production
transaction for every fresh paired continuation. A test-only thread-local
allocator fails each successive allocation in the transaction; each failure
must preserve both complete destination images and issue no services. Both
destinations intentionally differ from the source, so partial publication
cannot pass through equal pristine values. The allocator is disabled during
simulator startup, file I/O and independent readback. Diagnostic evidence and
exact commands for this iteration are indexed in the CPU matrix.

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
and the original BCD component interface remain compatible. Sealed startup metadata uses revision 4 and binds the terminal
configuration and pristine image as its eighth peer. Ordinary live-mode
metadata retains its revision-3 bytes. The terminal accessor is for inspection;
complete HTIF/device/caller/aggregate restoration is still disabled. Syscall
descriptors, process signals, live terminal/termios state and stop/exit state
remain separate pending owners. The sealed stream does not model timed input
arrival; it represents an input file whose bytes are available from startup.
In sealed mode, `inspect_polling_cut()` now includes BCD and terminal alongside
the eight protocol owners. Each image is validated and saved again to check
stability. This ten-component audit still cannot establish a complete HTIF or
CPU cut: syscall, signal, stop/exit and coherent caller restoration remain pending. The sealed
input service applies to the owned default BCD route; configured installed HTIF
routes remain outside this component's checkpoint scope.

## Iteration 117: metadata binding and complete known-peer inspection

Diagnostic root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration117/`.
`terminal/invocation-vszs_4d9/summary.json` retains the native sanitizer and VCS
DPI checks, exact argv, source snapshots and every image/readback. The independent
Python oracle checks revision-4 bytes, ordered owner membership, ELF metadata,
required XLEN, arguments and sealed input. Eight fresh metadata preparations
read back metadata and all eight pristine peers before services or context entry.
Replacing the original terminal file after construction does not affect the
prepared state. All 16,004 malformed images and 16 incompatible configurations
(live mode, different input, omitted terminal, reordered peers) reject before
peer or mailbox mutation. Three guards per valid preparation prevent entering
the caller, duplicate preparation or inspecting a nonexistent polling context.

Two real TSI transport runs audit all ten owners at first poll, after consuming
all input and after writing output (60 complete component images). Their
startup metadata remains identical across terminal progress. The original
52 paired terminal/BCD restores, 312 host events, 568 malformed rejections,
four incompatible inputs, eight incomplete pairs, 28 service guards and four
first response divergences remain covered. These are host component events;
no semantic CPU target-cycle or whole-runtime continuation is claimed.

Reproduce with the command below, changing the output to
`automations/checkpoint_loop/runs/m11-iteration117-controller-rechecks/terminal`.
Audit the new retained invocation with `--audit` and its absolute summary path.
See the CPU matrix for the full exact-recipe workload controls and ordinary
RTL diagnostic. Complete aggregate restoration remains pending.

## Iteration 116 native verification (historical)

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
