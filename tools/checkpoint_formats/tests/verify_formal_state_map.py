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
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits, sha
from tools.checkpoint_formats.replay import builds, package_capture, prepare_capture
from tools.checkpoint_formats.semantic import state_id


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("fixtures") / "formal"
GENUS = "/ecad/tools/cadence/GENUS/GENUS211/bin/genus"
FORMALITY = "/ecad/tools/synopsys/fm/P-2019.03-SP2/bin/fm_shell"
VCS = "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs"


def fixture_manifest():
    state = []
    for name, kind, depth in (("held", "register", 1), ("count", "register", 1), ("ram", "memory", 4)):
        path = "Harness.dut." + name
        state.append(dict(state_id=state_id(path, kind), hierarchy=path, kind=kind, width=4, depth=depth,
                          signed=False, clock_domain="Harness.dut.clock",
                          reset="none" if kind == "memory" else "synchronous",
                          bit_order="lsb0", address_order="ascending_zero_based"))
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="Harness", dut_root="Harness.dut", clock_domain="Harness.dut.clock",
                    reference_sha256=sha((FIXTURE / "dut.v").read_bytes()),
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


def verify(out, profile="direct", duplicate_registers=False, reorder_registers=False):
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    commands = []
    cells = FIXTURE if profile == "direct" else FIXTURE / "inverted"
    sequential_cell = "CKDFF" if profile == "direct" else "CKDFFN"
    expected_gate_bits = 28 if duplicate_registers else 24
    counter_suffix = "_SYNTHESIS_SEQ_DUP_0" if duplicate_registers else ""
    slots = (2, 0, 3, 1) if reorder_registers else (0, 1, 2, 3)
    counter_name = lambda bit: f"{'gate_count' if reorder_registers else 'count'}_reg[{slots[bit]}]"
    configuration = cells / "reordered/config.tcl" if reorder_registers else cells / "config.tcl"

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
    formal_env["CHECKPOINT_DUPLICATE_REGISTERS"] = str(int(duplicate_registers))
    formal_env["CHECKPOINT_REORDER_REGISTERS"] = str(int(reorder_registers))
    invoke([GENUS, "-no_gui", "-batch", "-files", str(FIXTURE / "synth.tcl")], synth,
           synth / "synth.log", formal_env)
    require_netlist = synth / "netlist.v"
    if not require_netlist.exists():
        raise RuntimeError(f"Genus failed to write the netlist; see {synth / 'synth.log'}")

    def prove(netlist, directory, config=None):
        directory.mkdir()
        config = config or configuration
        env = dict(formal_env, CHECKPOINT_RTL=str(FIXTURE / "dut.v"),
                   CHECKPOINT_FORMAL_CONFIG=str(config),
                   CHECKPOINT_NETLIST=str(netlist), CHECKPOINT_CELLS=str(cells / "cells.v"))
        invoke([FORMALITY, "-f", str(FIXTURE / "prove.tcl")], directory, directory / "formal.log", env)
        paths = dict(rtl=FIXTURE / "dut.v", netlist=netlist, models=cells / "cells.v",
                     library=cells / "cells.lib", synthesis_script=FIXTURE / "synth.tcl",
                     synthesis_log=synth / "synth.log", formal_script=FIXTURE / "prove.tcl",
                     formal_log=directory / "formal.log", evidence=directory / "evidence.tsv",
                     formal_configuration=config,
                     blackboxes=directory / "blackboxes.rpt")
        return {role: path.read_bytes() for role, path in paths.items()}, paths

    artifacts, paths = prove(require_netlist, run / "formal")
    manifest, boundary = fixture_manifest()
    adapter = json.loads((cells / "cell-adapter.json").read_text())
    mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
    inverted = sum(g["xor"] for e in mapping["entries"] for g in e["gates"])
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
    rtl = (FIXTURE / "dut.v").read_text()
    prepare_capture(manifest, boundary, rtl, rtl + "\nStateMapDUT dut();", capture)
    (capture / "tb.sv").write_text(testbench("StateMapDUT"))
    simv = build_vcs(capture, [FIXTURE / "dut.v", capture / "capture.sv", capture / "tb.sv"])
    invoke([str(simv), f"+semantic_capture={capture / 'capture.jsonl'}"], capture, capture / "simulation.log")
    checkpoint, trace = package_capture(manifest, boundary, "formal-small-dut-v1",
                                        capture / "capture.jsonl", 17, 79, capture)
    checkpoint_data = (capture / "capture.rtlckpt").read_bytes()
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
    summary = dict(status="passed", scope="flat audited scalar-cell DUT; no retiming",
                   profile=profile, formally_proven_inverted_bits=inverted,
                   duplicate_registers=duplicate_registers, duplicated_semantic_bits=len(duplicated),
                   reorder_registers=reorder_registers, counter_bit_to_gate_slot=list(slots),
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
                             ["real merging/optimization proof cases"] +
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
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    verify(args.out, args.profile, args.duplicate_registers, args.reorder_registers)


if __name__ == "__main__":
    main()
