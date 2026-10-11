"""Real Genus/Formality/ordinary-VCS mapping and gate initialization check.

Run with Chipyard env.sh, FireSim env.sh, then vcs-env.sh sourced LAST.
Diagnostic tool work is isolated under --out (normally the loop runs directory).
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.constant_state import SCRIPT, binding, validate_constants
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits, sha
from tools.checkpoint_formats.replay import builds, package_capture, prepare_capture, prepare_replay
from tools.checkpoint_formats.semantic import encode_semantic, state_id


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("fixtures") / "formal"
GENUS = "/ecad/tools/cadence/GENUS/GENUS211/bin/genus"
FORMALITY = "/ecad/tools/synopsys/fm/P-2019.03-SP2/bin/fm_shell"
VCS = "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs"
JASPER = "/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg"


def fixture_manifest(rtl_path=FIXTURE / "dut.v", merge_registers=False, optimize_registers=False,
                     constant_registers=False):
    state = []
    for name, kind, depth in (("held", "register", 1), ("count", "register", 1), ("ram", "memory", 4)) + \
                            ((("held_copy", "register", 1),) if merge_registers else ()) + \
                            ((("unused", "register", 1),) if optimize_registers else ()) + \
                            ((("constant", "register", 1),) if constant_registers else ()):
        path = "Harness.dut." + name
        state.append(dict(state_id=state_id(path, kind), hierarchy=path, kind=kind, width=4, depth=depth,
                          signed=False, clock_domain="Harness.dut.clock",
                          reset="none" if kind == "memory" or name == "constant" else "synchronous",
                          bit_order="lsb0", address_order="ascending_zero_based"))
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="Harness", dut_root="Harness.dut", clock_domain="Harness.dut.clock",
                    reference_sha256=sha(rtl_path.read_bytes()),
                    state=sorted(state, key=lambda e: e["state_id"]))
    boundary = dict(boundary_version=1, dut_module="StateMapDUT", dut_root="Harness.dut", clock="clock",
                    sample_phase="before_rising_edge", ports=[dict(name=n, direction=d, width=w) for n, d, w in (
                        ("clock", "input", 1), ("reset", "input", 1), ("enable", "input", 1),
                        ("write", "input", 1), ("address", "input", 2), ("data", "input", 4),
                        ("held_out", "output", 4), ("count_out", "output", 4), ("read_out", "output", 4))])
    return manifest, boundary


def testbench(module, start=0, trace=None, deposits=None, fault_storage=None):
    lines = ["`timescale 1ns/1ps", "module tb;", "reg clock = 0;",
             "reg reset, enable, write; reg [1:0] address; reg [3:0] data;",
             "wire [3:0] held_out, count_out, read_out;",
             f"{module} dut(.*);", "integer c; integer edges = 0; string invalid_restore; integer inject_fault = 0;",
             'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
             'import "DPI-C" context function int semantic_verify(input string path, input int unsigned words);',
             'import "DPI-C" context function void semantic_fail(input string message);',
             "always @(posedge clock) edges = edges + 1;", "initial begin", "#1;"]
    if deposits:
        path, words = deposits
        lines += [f'if (semantic_restore("{path}", {words})) semantic_fail("GATE_RESTORE_FAILED");',
                  "#1;", 'if (edges != 0) semantic_fail("GATE_RESTORE_ADVANCED_TIME");',
                  f'if (semantic_verify("{path}", {words})) semantic_fail("GATE_READBACK_FAILED");',
                  f'$display("GATE_ZERO_EDGE_READBACK cycle={start} bits={words} edges=%0d", edges);',
                  'if ($value$plusargs("invalid_restore=%s", invalid_restore)) begin',
                  f'if (!semantic_restore(invalid_restore, {words})) semantic_fail("INVALID_GATE_LOAD_ACCEPTED");',
                  f'if (semantic_verify("{path}", {words})) semantic_fail("PARTIAL_GATE_LOAD_MUTATION");',
                  'if (edges != 0) semantic_fail("INVALID_GATE_LOAD_ADVANCED_TIME");',
                  f'$display("INVALID_GATE_LOAD_REJECTED edges=0 unchanged={words}");', 'end']
    if fault_storage:
        lines += ['if ($value$plusargs("fault_gate=%d", inject_fault)) begin end']
    if trace:
        # Finite replay uses only the independent trace and a validated map.
        for record in trace["records"]:
            cycle = record["cycle"]
            for name, value in record["inputs"].items():
                lines.append(f"{name} = {value['width']}'h{value['value']};")
            lines += ["#1;"]
            if fault_storage and cycle == 29:
                lines += [f"if (inject_fault) begin {fault_storage} = ~{fault_storage}; #1; end"]
            for name, value in record["outputs"].items():
                lines.append(f"if ({name} !== {value['width']}'h{value['value']}) "
                             f'semantic_fail("GATE_MISMATCH cycle={cycle} signal={name}");')
            lines += [f'$display("GATE_MATCH cycle={cycle} held=%h count=%h ram=%h", held_out, count_out, read_out);',
                      "clock = 1; #1; clock = 0; #1;"]
        lines += [f'if (edges != {len(trace["records"])}) semantic_fail("GATE_EDGE_COUNT");',
                  f'$display("GATE_END cycle={trace["target_cycle"] + len(trace["records"])} edges=%0d", edges);']
    else:
        lines += ["for (c=0; c<96; c=c+1) begin",
                  "reset = (c == 0 || c == 37); enable = (c % 3 != 1);",
                  "write = (c < 4 || c % 5 != 2); address = c % 4; data = (c * 7 + 3) % 16;",
                  "#1; clock = 1; #1; clock = 0; #1;", "end"]
    lines += ["$finish;", "end", "endmodule"]
    return "\n".join(lines) + "\n"


def verify(out, profile="direct", duplicate_registers=False, reorder_registers=False, merge_registers=False,
           optimize_registers=False, constant_registers=False):
    optimize_registers = optimize_registers or constant_registers
    if merge_registers and duplicate_registers:
        raise ValueError("combined merging and duplication requires a separate proof adapter")
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    commands = []
    cells = FIXTURE if profile == "direct" else FIXTURE / "inverted"
    sequential_cell = "CKDFF" if profile == "direct" else "CKDFFN"
    expected_gate_bits = 28 if duplicate_registers else 24
    counter_suffix = "_SYNTHESIS_SEQ_DUP_0" if duplicate_registers else ""
    slots = (2, 0, 3, 1) if reorder_registers else (0, 1, 2, 3)
    counter_name = lambda bit: f"{'gate_count' if reorder_registers else 'count'}_reg[{slots[bit]}]"
    configuration = cells / "reordered/config.tcl" if reorder_registers else cells / "config.tcl"
    rtl_path = FIXTURE / ("merged/dut.v" if merge_registers else "dut.v")
    if optimize_registers:
        rtl_path = FIXTURE / "optimized/dut.v"
    if constant_registers:
        rtl_path = FIXTURE / "constants/dut.v"
    if merge_registers:
        if optimize_registers:
            rtl_path = FIXTURE / "merged" / ("constants" if constant_registers else "optimized") / "dut.v"
        configuration = FIXTURE / "merged" / profile / ("reordered/config.tcl" if reorder_registers else "config.tcl")

    def invoke(argv, cwd, log, env=None, timeout=240, expected=0):
        with open(log, "w") as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        commands.append(dict(cwd=str(Path(cwd).relative_to(ROOT)), argv=list(map(str, argv)),
                             log=str(log), exit_code=result.returncode))
        (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode != expected:
            raise RuntimeError(f"exit {result.returncode} from {argv[0]}; see {log}")

    synth = run / "synthesis"
    synth.mkdir()
    formal_env = dict(os.environ)
    formal_env.pop("LD_LIBRARY_PATH", None)  # Isolate CAD tools from the Conda ICU/libc libraries.
    formal_env["CHECKPOINT_FIXTURE"] = str(FIXTURE)
    formal_env["CHECKPOINT_LIBRARY"] = str(cells / "cells.lib")
    formal_env["CHECKPOINT_RTL"] = str(rtl_path)
    formal_env["CHECKPOINT_DUPLICATE_REGISTERS"] = str(int(duplicate_registers))
    formal_env["CHECKPOINT_REORDER_REGISTERS"] = str(int(reorder_registers))
    invoke([GENUS, "-no_gui", "-batch", "-files", str(FIXTURE / "synth.tcl")], synth,
           synth / "synth.log", formal_env)
    require_netlist = synth / "netlist.v"
    if not require_netlist.exists():
        raise RuntimeError(f"Genus failed to write the netlist; see {synth / 'synth.log'}")

    constant_paths = {}

    def prove_constants(directory, reference=rtl_path, spec=None):
        directory.mkdir()
        spec = spec or dict(constant_version=1, top="StateMapDUT", bits=[
            dict(signal="constant", width=4, bit=bit, value=(10 >> bit) & 1) for bit in range(4)])
        directory.joinpath("spec.json").write_text(json.dumps(spec, indent=2) + "\n")
        directory.joinpath("bind.sv").write_bytes(binding(spec))
        directory.joinpath("prove.tcl").write_text(SCRIPT)
        env = dict(formal_env, CHECKPOINT_RTL=str(reference), CHECKPOINT_CONSTANT_TOP="StateMapDUT",
                   CHECKPOINT_CONSTANT_SPEC=str(directory / "spec.json"),
                   CHECKPOINT_CONSTANT_SCRIPT=str(directory / "prove.tcl"),
                   CHECKPOINT_CONSTANT_BIND=str(directory / "bind.sv"))
        invoke([JASPER, "-allow_unsupported_OS", "-batch", "-tcl", str(directory / "prove.tcl")],
               directory, directory / "jasper.log", env)
        return dict(constant_spec=directory / "spec.json", constant_bind=directory / "bind.sv",
                    constant_script=directory / "prove.tcl", constant_log=directory / "jasper.log",
                    constant_results=directory / "constant-results.tsv")

    if constant_registers:
        constant_paths = prove_constants(run / "constant-proof")

    def prove(netlist, directory, config=None, reference=None):
        directory.mkdir()
        config = config or configuration
        reference = reference or rtl_path
        env = dict(formal_env, CHECKPOINT_RTL=str(reference),
                   CHECKPOINT_FORMAL_CONFIG=str(config),
                   CHECKPOINT_NETLIST=str(netlist), CHECKPOINT_CELLS=str(cells / "cells.v"))
        invoke([FORMALITY, "-f", str(FIXTURE / "prove.tcl")], directory, directory / "formal.log", env)
        paths = dict(rtl=reference, netlist=netlist, models=cells / "cells.v",
                     library=cells / "cells.lib", synthesis_script=FIXTURE / "synth.tcl",
                     synthesis_log=synth / "synth.log", formal_script=FIXTURE / "prove.tcl",
                     formal_log=directory / "formal.log", evidence=directory / "evidence.tsv",
                     formal_configuration=config,
                     blackboxes=directory / "blackboxes.rpt")
        if paths["evidence"].read_bytes().startswith(b"FORMAT\tformality-state-v3\n"):
            paths["optimization_report"] = directory / "optimized-unread.rpt"
        paths.update(constant_paths)
        return {role: path.read_bytes() for role, path in paths.items()}, paths

    artifacts, paths = prove(require_netlist, run / "formal")
    manifest, boundary = fixture_manifest(rtl_path, merge_registers, optimize_registers, constant_registers)
    adapter = json.loads((cells / "cell-adapter.json").read_text())
    mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
    inverted = len({g["formal_implementation"] for e in mapping["entries"] for g in e["gates"] if g["xor"]})
    assert inverted == (expected_gate_bits if profile == "inverted" else 0), "profile did not exercise expected polarity"
    assert mapping["gate_storage_bits"] == expected_gate_bits
    duplicated = [e for e in mapping["entries"] if len(e["gates"]) > 1]
    assert len(duplicated) == (4 if duplicate_registers else 0)
    for entry in duplicated:
        assert entry["original_rtl"] == f"count[{entry['bit']}]"
        assert len(entry["gates"]) == 2
        assert {g["instance"] for g in entry["gates"]} == {
            counter_name(entry["bit"]), counter_name(entry["bit"]) + "_SYNTHESIS_SEQ_DUP_0"}
    counter_entries = [e for e in mapping["entries"] if e["original_rtl"].startswith("count[")]
    assert len(counter_entries) == 4
    for entry in counter_entries:
        assert {g["instance"] for g in entry["gates"]} == {
            counter_name(entry["bit"]) + suffix for suffix in
            (("", "_SYNTHESIS_SEQ_DUP_0") if duplicate_registers else ("",))}
    assert all(g["cell"] == sequential_cell for e in mapping["entries"] for g in e["gates"])
    assert mapping["semantic_bits"] == 24 + 4 * (merge_registers + optimize_registers + constant_registers)
    unread_entries = [e for e in mapping["entries"] if e.get("optimization", {}).get("kind") == "unread"]
    assert len(unread_entries) == (4 if optimize_registers else 0)
    for entry in unread_entries:
        assert entry["original_rtl"] == f"unused[{entry['bit']}]"
        assert entry["optimization"] == dict(kind="unread", proof_status="tool_classified", report="optimization_report")
    shared = {}
    for entry in mapping["entries"]:
        for gate in entry["gates"]:
            shared.setdefault(gate["formal_implementation"], []).append(entry["original_rtl"])
    merged = {gate: sources for gate, sources in shared.items() if len(sources) > 1}
    assert len(merged) == (4 if merge_registers else 0)
    for gate, sources in merged.items():
        bit = re.search(r"held_copy_reg\[(\d)\]", gate)[1]
        assert set(sources) == {f"held[{bit}]", f"held_copy[{bit}]"}
    (run / "cell-adapter.json").write_text(json.dumps(adapter, indent=2) + "\n")
    (run / "asic_state_map.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (run / "boundary.json").write_text(json.dumps(boundary, indent=2) + "\n")
    (run / "inputs.json").write_text(json.dumps({k: str(v) for k, v in paths.items()}, indent=2) + "\n")

    def build_vcs(directory, sources):
        directory.mkdir(exist_ok=True)
        invoke([VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-debug_access+all",
                "-CFLAGS", "-std=c++11", "-cc", os.environ["VCS_CC"],
                *map(str, sources), str(ROOT / "tools/checkpoint_formats/semantic_restore.cc"),
                "-o", str(directory / "simv")], directory, directory / "compile.log")
        if "Y-2026.03-SP1" not in (directory / "compile.log").read_text():
            raise RuntimeError("VCS release was not pinned")
        return directory / "simv"

    capture = run / "reference"
    capture.mkdir()
    rtl = rtl_path.read_text()
    prepare_capture(manifest, boundary, rtl, rtl + "\nStateMapDUT dut();", capture)
    (capture / "tb.sv").write_text(testbench("StateMapDUT"))
    simv = build_vcs(capture, [rtl_path, capture / "capture.sv", capture / "tb.sv"])
    invoke([str(simv), f"+semantic_capture={capture / 'capture.jsonl'}"], capture, capture / "simulation.log")
    checkpoint, trace = package_capture(manifest, boundary, "formal-small-dut-v1",
                                        capture / "capture.jsonl", 17, 79, capture)
    checkpoint_data = (capture / "capture.rtlckpt").read_bytes()
    optimization_rejections = {}
    if optimize_registers:
        # Explicit unread classification permits arbitrary values only for
        # these bits. Retain an independent clean-RTL replay with all four
        # unread bits changed, and compare against the same recorded oracle.
        altered = copy.deepcopy(checkpoint)
        record = next(r for r in altered["records"] if r["state_id"] == state_id("Harness.dut.unused", "register"))
        record["values"][0] = f"{int(record['values'][0], 16) ^ 15:x}"
        altered_data = encode_semantic(altered, manifest)
        (run / "altered-unread.rtlckpt").write_bytes(altered_data)
        build = builds(manifest, boundary, "formal-small-dut-v1")[0]
        assert gate_deposits(mapping, manifest, adapter, artifacts, altered_data, build, "tb.dut") == \
               gate_deposits(mapping, manifest, adapter, artifacts, checkpoint_data, build, "tb.dut")
        replay = run / "rtl-altered-unread"
        prepare_replay(manifest, boundary, "formal-small-dut-v1", altered_data,
                       (capture / "capture.trace").read_bytes(), replay)
        simv = build_vcs(replay, [rtl_path, replay / "replay.sv"])
        invoke([str(simv), f"+restore={replay / 'restore.txt'}", f"+waveform={replay / 'replay.vcd'}"],
               replay, replay / "simulation.log")
        assert "PASS: fresh clean RTL replay cycles=17..95 samples=79" in (replay / "simulation.log").read_text()
        # Mutating actual original connectivity must remove the unread
        # classification and fail output equivalence against the real netlist.
        observed = run / "observed-unread.v"
        observed.write_text(rtl_path.read_text().replace("assign held_out = held", "assign held_out = held ^ unused"))
        bad_artifacts, _ = prove(require_netlist, run / "formal-observed-unread", reference=observed)
        assert b"Verification FAILED" in bad_artifacts["formal_log"]
        assert not any(line.startswith(b"OPTIMIZED\tunread\t") for line in bad_artifacts["evidence"].splitlines())
        semantic_side = "i" if merge_registers else "r"
        unread_point = f"{semantic_side}:/WORK/StateMapDUT/unused_reg[0]".encode()
        variants = {
            "missing-classification": artifacts["evidence"].replace(
                b"OPTIMIZED\tunread\t" + unread_point + b"\n", b""),
            "unsupported-constant": artifacts["evidence"].replace(b"OPTIMIZED\tunread", b"OPTIMIZED\tconst0", 1),
            "live-state-classified-unread": artifacts["evidence"].replace(
                b"OPTIMIZED\tunread\t" + unread_point,
                f"OPTIMIZED\tunread\t{semantic_side}:/WORK/StateMapDUT/count_reg[0]".encode()),
            "wrong-semantic-side": artifacts["evidence"].replace(
                b"OPTIMIZED\tunread\t" + unread_point,
                b"OPTIMIZED\tunread\t" + (b"r" if merge_registers else b"i") + unread_point[1:]),
        }
        for name, evidence in variants.items():
            (run / (name + "-evidence.tsv")).write_bytes(evidence)
            try:
                export_state_map(manifest, "StateMapDUT", adapter, dict(artifacts, evidence=evidence))
            except FormatError as error:
                optimization_rejections[name] = str(error)
            else:
                raise AssertionError(f"unsupported optimization evidence accepted: {name}")
    inconsistent_merge_rejection = None
    constant_rejections = {}
    if constant_registers:
        constant_entries = [e for e in mapping["entries"] if e.get("optimization", {}).get("kind") == "constant"]
        assert len(constant_entries) == 4 and mapping["map_version"] == 4
        for entry in constant_entries:
            assert entry["original_rtl"] == f"constant[{entry['bit']}]"
            assert entry["optimization"]["value"] == (10 >> entry["bit"]) & 1
            assert not entry["gates"]
        build = builds(manifest, boundary, "formal-small-dut-v1")[0]
        for bit in range(4):
            conflicting = copy.deepcopy(checkpoint)
            row = next(r for r in conflicting["records"] if r["state_id"] == state_id("Harness.dut.constant", "register"))
            assert row["values"] == ["a"]
            row["values"][0] = f"{10 ^ (1 << bit):x}"
            payload = encode_semantic(conflicting, manifest)
            (run / f"conflicting-constant-{bit}.rtlckpt").write_bytes(payload)
            try:
                gate_deposits(mapping, manifest, adapter, artifacts, payload, build, "tb.dut")
            except FormatError as error:
                constant_rejections[f"checkpoint-bit-{bit}"] = str(error)
            else:
                raise AssertionError("conflicting observable constant checkpoint accepted")
        early = copy.deepcopy(checkpoint)
        early["target_cycle"] = 0
        early_data = encode_semantic(early, manifest)
        (run / "pre-horizon.rtlckpt").write_bytes(early_data)
        try:
            gate_deposits(mapping, manifest, adapter, artifacts, early_data, build, "tb.dut")
        except FormatError as error:
            constant_rejections["pre-horizon"] = str(error)
        else:
            raise AssertionError("unproven initial constant state accepted")
        # Fresh ordinary RTL must expose the semantic error before any edge.
        replay = run / "rtl-conflicting-constant"
        prepare_replay(manifest, boundary, "formal-small-dut-v1",
                       (run / "conflicting-constant-0.rtlckpt").read_bytes(),
                       (capture / "capture.trace").read_bytes(), replay)
        simv = build_vcs(replay, [rtl_path, replay / "replay.sv"])
        invoke([str(simv), f"+restore={replay / 'restore.txt'}", f"+waveform={replay / 'replay.vcd'}"],
               replay, replay / "simulation.log", expected=1)
        assert "cycle=17" in (replay / "simulation.log").read_text()
        wrong_spec = json.loads(artifacts["constant_spec"])
        wrong_spec["bits"][0]["value"] ^= 1
        conditional = run / "conditional-constant.v"
        conditional.write_text(rtl.replace("constant <= 4'b1010;", "if (enable) constant <= 4'b1010;"))
        assert conditional.read_text() != rtl
        for case, reference, spec in (("wrong-value", rtl_path, wrong_spec),
                                      ("conditional-update", conditional, None)):
            negative_paths = prove_constants(run / ("constant-" + case), reference, spec)
            negative = dict(artifacts, rtl=reference.read_bytes(),
                            **{k: p.read_bytes() for k, p in negative_paths.items()})
            try:
                validate_constants(negative, manifest, "StateMapDUT")
            except FormatError as error:
                constant_rejections[case] = str(error)
            else:
                raise AssertionError("false constant predicate accepted")
            assert b"\tassert\tcex\n" in negative["constant_results"]
        variants = {
            "missing-proof": {k: v for k, v in artifacts.items() if not k.startswith("constant_")},
            "missing-property": dict(artifacts, constant_results=b"\n".join(
                line for line in artifacts["constant_results"].split(b"\n") if not
                (line.startswith(b"PROPERTY\t") and line.endswith(b"\tassert\tproven") and b"constant_0\t" in line))),
            "bounded-proof": dict(artifacts, constant_results=artifacts["constant_results"].replace(
                b"\tassert\tproven", b"\tassert\tbounded_proven", 1)),
            "vacuous-proof": dict(artifacts, constant_results=artifacts["constant_results"].replace(
                b"\tcover\tcovered", b"\tcover\tunreachable", 1)),
            "wrong-raw-status": dict(artifacts, constant_log=artifacts["constant_log"].replace(
                b"\tassert\tproven", b"\tassert\tcex", 1)),
        }
        for case, negative in variants.items():
            try:
                export_state_map(manifest, "StateMapDUT", adapter, negative)
            except FormatError as error:
                constant_rejections[case] = str(error)
            else:
                raise AssertionError(f"unsupported constant evidence accepted: {case}")
        (run / "constant-rejections.json").write_text(json.dumps(constant_rejections, indent=2) + "\n")
    if merge_registers:
        inconsistent = copy.deepcopy(checkpoint)
        record = next(r for r in inconsistent["records"] if r["state_id"] == state_id("Harness.dut.held_copy", "register"))
        record["values"][0] = f"{int(record['values'][0], 16) ^ 1:x}"
        inconsistent_data = encode_semantic(inconsistent, manifest)
        (run / "inconsistent-merged.rtlckpt").write_bytes(inconsistent_data)
        try:
            gate_deposits(mapping, manifest, adapter, artifacts, inconsistent_data,
                          builds(manifest, boundary, "formal-small-dut-v1")[0], "tb.dut")
        except FormatError as error:
            inconsistent_merge_rejection = str(error)
        else:
            raise AssertionError("inconsistent merged semantic values accepted")
        assert inconsistent_merge_rejection.startswith("inconsistent merged semantic state")
    swapped_map_rejection = None
    if reorder_registers:
        guessed = copy.deepcopy(mapping)
        count_entries = sorted((e for e in guessed["entries"] if e["original_rtl"].startswith("count[")),
                               key=lambda e: e["bit"])
        count_entries[0]["gates"], count_entries[1]["gates"] = count_entries[1]["gates"], count_entries[0]["gates"]
        (run / "swapped-destinations-map.json").write_text(json.dumps(guessed, indent=2) + "\n")
        try:
            gate_deposits(guessed, manifest, adapter, artifacts, checkpoint_data,
                          builds(manifest, boundary, "formal-small-dut-v1")[0], "tb.dut")
        except FormatError as error:
            swapped_map_rejection = str(error)
        else:
            raise AssertionError("swapped destination map accepted before translation")
        assert swapped_map_rejection == "ASIC map or build/proof identity mismatch"
    cycle, deposits = gate_deposits(mapping, manifest, adapter, artifacts, checkpoint_data,
                                    builds(manifest, boundary, "formal-small-dut-v1")[0], "tb.dut")
    restore = run / "restore.txt"
    restore.write_text("".join(f"{p} {w} {v}\n" for p, w, v in deposits))
    gate = run / "gate-restored"
    gate.mkdir()
    (gate / "tb.sv").write_text(testbench("StateMapDUT", start=cycle, trace=trace,
                                         deposits=(restore, len(deposits)),
                                         fault_storage=f"dut.\\{counter_name(0)}{counter_suffix} .state"))
    simv = build_vcs(gate, [require_netlist, cells / "cells.v", gate / "tb.sv"])
    invoke([str(simv)], gate, gate / "simulation.log")
    text = (gate / "simulation.log").read_text()
    assert f"GATE_ZERO_EDGE_READBACK cycle={cycle} bits={expected_gate_bits} edges=0" in text
    assert "GATE_END cycle=96 edges=79" in text
    assert text.count("GATE_MATCH cycle=") == 79
    # Earlier rows would change stored state if the loader wrote eagerly.
    invalid_cases = {}
    for name in ("missing", "width", "duplicate", "unknown-value", "incomplete") + (("missing-copy",) if duplicate_registers else ()):
        rows = [f"{p} {w} {v}" for p, w, v in deposits]
        p, w, v = deposits[0]
        rows[0] = f"{p} {w} {1 - int(v)}"
        if name == "missing":
            rows[-1] = "tb.dut.missing.state 1 0"
        elif name == "width":
            p, _, v = deposits[-1]
            rows[-1] = f"{p} 2 {v}"
        elif name == "duplicate":
            rows[-1] = rows[0]
        elif name == "unknown-value":
            p, w, _ = deposits[-1]
            rows[-1] = f"{p} {w} x"
        elif name == "missing-copy":
            rows = [row for row in rows if counter_name(0) + "_SYNTHESIS_SEQ_DUP_0" not in row]
        else:
            rows.pop()
        bad_restore = gate / (name + ".txt")
        bad_restore.write_text("\n".join(rows) + "\n")
        log = gate / (name + ".log")
        invoke([str(simv), f"+invalid_restore={bad_restore}"], gate, log)
        assert f"INVALID_GATE_LOAD_REJECTED edges=0 unchanged={expected_gate_bits}" in log.read_text()
        assert "GATE_END cycle=96 edges=79" in log.read_text()
        invalid_cases[name] = f"rejected before writes; all {expected_gate_bits} bits unchanged; continuation matched"
    invoke([str(simv), "+fault_gate=1"], gate, gate / "fault.log", expected=1)
    fault_log = (gate / "fault.log").read_text()
    assert "GATE_MISMATCH cycle=29 signal=count_out" in fault_log
    assert fault_log.count("GATE_MATCH cycle=") == 12

    # Also check an actual uninterrupted gate run against the *same* original
    # RTL oracle at each pre-edge boundary, including the post-cut reset edge.
    uninterrupted = run / "gate-uninterrupted"
    uninterrupted.mkdir()
    prefix = testbench("StateMapDUT").split("for (c=0;")[0]
    prefix += "for (c=0; c<17; c=c+1) begin\n" + \
              "reset = (c == 0); enable = (c % 3 != 1); write = (c < 4 || c % 5 != 2);\n" + \
              "address = c % 4; data = (c * 7 + 3) % 16; #1; clock=1; #1; clock=0; #1; end\n"
    continuation = testbench("StateMapDUT", start=17, trace=trace).split("initial begin\n#1;\n", 1)[1]
    continuation = continuation.replace("edges != 79", "edges != 96")
    (uninterrupted / "tb.sv").write_text(prefix + continuation)
    simv = build_vcs(uninterrupted, [require_netlist, cells / "cells.v", uninterrupted / "tb.sv"])
    invoke([str(simv)], uninterrupted, uninterrupted / "simulation.log")
    assert "GATE_END cycle=96 edges=96" in (uninterrupted / "simulation.log").read_text()
    matched = lambda p: [line for line in p.read_text().splitlines() if line.startswith("GATE_MATCH ")]
    assert matched(uninterrupted / "simulation.log") == matched(gate / "simulation.log")

    # A fresh formal run on a real faulty implementation must fail closed;
    # no stale successful map is accepted or published for it.
    bad_netlist = run / "bad-netlist.v"
    bad = re.sub(rf"(\b{sequential_cell}\s+\\{re.escape(counter_name(3))}{counter_suffix}\s*\([^;]*?\.D\s*\()[^)]*(\))",
                 r"\g<1>1'b0\2", require_netlist.read_text(), count=1)
    assert bad != require_netlist.read_text()
    bad_netlist.write_text(bad)
    bad_artifacts, _ = prove(bad_netlist, run / "formal-fault")
    try:
        export_state_map(manifest, "StateMapDUT", adapter, bad_artifacts)
    except FormatError as error:
        rejection = str(error)
    else:
        raise AssertionError("faulty gate implementation accepted")
    assert b"Verification FAILED" in bad_artifacts["formal_log"]
    opposite = FIXTURE / "inverted" if profile == "direct" else FIXTURE
    opposite_config = opposite / ("reordered/config.tcl" if reorder_registers else "config.tcl")
    if merge_registers:
        opposite_config = FIXTURE / "merged" / ("inverted" if profile == "direct" else "direct") / \
                          ("reordered/config.tcl" if reorder_registers else "config.tcl")
    wrong_artifacts, _ = prove(require_netlist, run / "formal-wrong-polarity", opposite_config)
    try:
        export_state_map(manifest, "StateMapDUT", adapter, wrong_artifacts)
    except FormatError as error:
        wrong_polarity_rejection = str(error)
    else:
        raise AssertionError("unproven polarity hypothesis accepted")
    assert b"Verification FAILED" in wrong_artifacts["formal_log"]
    wrong_permutation_rejection = None
    if reorder_registers:
        # Deliberately pair gate slots by their numeric index instead of the
        # actual permutation. A fresh proof must reject this plausible guess.
        wrong_config = run / "wrong-permutation.tcl"
        wrong_config.write_text("set checkpoint_candidate_polarity " +
                                ("-inverted" if profile == "inverted" else "-noninverted") +
                                "\nset checkpoint_candidate_names [dict create " +
                                " ".join(f"{{gate_count_reg[{b}]}} {{count_reg[{b}]}}" for b in range(4)) + "]\n")
        if merge_registers:
            with wrong_config.open("a") as output:
                output.write(configuration.read_text().split("# Symmetric equivalence:", 1)[1].split("\n", 1)[1])
        wrong_artifacts, _ = prove(require_netlist, run / "formal-wrong-permutation", wrong_config)
        try:
            export_state_map(manifest, "StateMapDUT", adapter, wrong_artifacts)
        except FormatError as error:
            wrong_permutation_rejection = str(error)
        else:
            raise AssertionError("unproven destination permutation accepted")
        assert b"Verification FAILED" in wrong_artifacts["formal_log"]
    missing_copy_rejection = None
    if duplicate_registers:
        # A global successful equivalence result is insufficient when one copy's
        # individual passing relationship is missing. Keep the real tool evidence
        # intact and retain this isolated rejected export as a diagnostic artifact.
        missing = dict(artifacts)
        omitted = (counter_name(0) + "_SYNTHESIS_SEQ_DUP_0/state_reg").encode()
        missing["evidence"] = b"\n".join(row for row in artifacts["evidence"].split(b"\n")
                                            if not (row.startswith(b"PROVEN\t") and omitted in row))
        (run / "missing-copy-evidence.tsv").write_bytes(missing["evidence"])
        try:
            export_state_map(manifest, "StateMapDUT", adapter, missing)
        except FormatError as error:
            missing_copy_rejection = str(error)
        else:
            raise AssertionError("unproven synthesized copy accepted")
        assert missing_copy_rejection == "unproven or unmappable gate state"
    missing_alias_rejection = None
    wrong_alias_rejection = None
    if merge_registers:
        missing = dict(artifacts)
        omitted = b"\ti:/WORK/StateMapDUT/held_reg[0]"
        missing["evidence"] = b"\n".join(row for row in artifacts["evidence"].split(b"\n")
                                       if not (row.startswith(b"PROVEN\t") and row.endswith(omitted)))
        (run / "missing-alias-evidence.tsv").write_bytes(missing["evidence"])
        try:
            export_state_map(manifest, "StateMapDUT", adapter, missing)
        except FormatError as error:
            missing_alias_rejection = str(error)
        else:
            raise AssertionError("unproven merged alias accepted despite global PASS")
        assert missing_alias_rejection == "unproven or unmappable semantic state"
        wrong_config = run / "wrong-alias.tcl"
        # Preserve all inventories and compare point membership; swap held aliases.
        text = configuration.read_text().replace("{held_reg[0]}", "{held_reg[999]}")
        text = text.replace("{held_reg[1]}", "{held_reg[0]}").replace("{held_reg[999]}", "{held_reg[1]}")
        wrong_config.write_text(text)
        wrong_artifacts, _ = prove(require_netlist, run / "formal-wrong-alias", wrong_config)
        try:
            export_state_map(manifest, "StateMapDUT", adapter, wrong_artifacts)
        except FormatError as error:
            wrong_alias_rejection = str(error)
        else:
            raise AssertionError("unproven merged alias hypothesis accepted")
        assert b"Verification FAILED" in wrong_artifacts["formal_log"]
    summary = dict(status="passed", scope="flat audited scalar-cell DUT; no retiming",
                   profile=profile, formally_proven_inverted_bits=inverted,
                   optimize_registers=optimize_registers, unread_semantic_bits=len(unread_entries),
                   altered_unread_rtl_replayed=optimize_registers,
                   observed_unread_formal_failed=optimize_registers,
                   optimization_evidence_rejections=optimization_rejections,
                   constant_registers=constant_registers, constant_semantic_bits=4 if constant_registers else 0,
                   constant_rejections=constant_rejections,
                   duplicate_registers=duplicate_registers, duplicated_semantic_bits=len(duplicated),
                   reorder_registers=reorder_registers, counter_bit_to_gate_slot=list(slots),
                   merge_registers=merge_registers, merged_gate_bits=len(merged),
                   merged_semantic_sources=merged,
                   inconsistent_merge_rejected=inconsistent_merge_rejection,
                   missing_alias_proof_rejected=missing_alias_rejection,
                   wrong_alias_formal_rejected=wrong_alias_rejection,
                   reordered_semantic_bits=4 if reorder_registers else 0,
                   wrong_permutation_rejected=wrong_permutation_rejection,
                   swapped_destination_map_rejected=swapped_map_rejection,
                   missing_copy_proof_rejected=missing_copy_rejection,
                   semantic_bits=mapping["semantic_bits"], gate_bits=mapping["gate_storage_bits"],
                   ram_words=4, restore_cycle=cycle, restored_edges=79, uninterrupted_edges=96,
                   compared_output_values=79 * 3, zero_edge_readback=True,
                   gate_fault_first_mismatch_cycle=29, gate_fault_edges=12,
                   gate_loader_rejections=invalid_cases,
                   faulty_netlist_rejected=rejection, faulty_netlist_formal_failed=True,
                   wrong_polarity_rejected=wrong_polarity_rejection, wrong_polarity_formal_failed=True,
                   remaining=(["real polarity proof case"] if profile == "direct" else []) +
                             ([] if merge_registers else ["real merging proof case"]) +
                             (["real unread-state proof case"] if not optimize_registers else []) +
                             ([] if constant_registers else ["proven constant propagation"]) +
                             ([] if reorder_registers else ["real indexed destination permutation proof case"]) +
                             ([] if duplicate_registers else ["real duplication proof case"]) + [
                              "audited SRAM macro initialization interface"])
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(run=str(run), **summary), indent=2))
    return run


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=("direct", "inverted"), default="direct")
    parser.add_argument("--duplicate-registers", action="store_true")
    parser.add_argument("--reorder-registers", action="store_true")
    parser.add_argument("--merge-registers", action="store_true")
    parser.add_argument("--optimize-registers", action="store_true")
    parser.add_argument("--constant-registers", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    verify(args.out, args.profile, args.duplicate_registers, args.reorder_registers, args.merge_registers,
           args.optimize_registers, args.constant_registers)


if __name__ == "__main__":
    main()
