"""Real many-to-many Genus/Jasper/VCS state correspondence and fault checks."""

import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits
from tools.checkpoint_formats.relational_state import SCRIPT, miter
from tools.checkpoint_formats.replay import builds, package_capture, prepare_capture
from tools.checkpoint_formats.semantic import encode_semantic, state_id
from .verify_formal_state_map import FIXTURE, GENUS, JASPER, ROOT, VCS, fixture_manifest, testbench


def candidate_spec(profile, reordered):
    slots = (2, 0, 3, 1) if reordered else (0, 1, 2, 3)
    rows = []
    for name in ("held", "held_copy", "count"):
        for bit in range(4):
            gate = f"held_copy_reg[{bit}]" if name.startswith("held") else \
                   f"{'gate_count' if reordered else 'count'}_reg[{slots[bit]}]"
            for suffix in (("", "_SYNTHESIS_SEQ_DUP_0") if name == "count" else ("",)):
                rows.append(dict(original_rtl=f"{name}[{bit}]", gate=gate + suffix + ".state",
                                 xor=int(profile == "inverted")))
    for address in range(4):
        for bit in range(4):
            rows.append(dict(original_rtl=f"ram[{address}][{bit}]",
                             gate=f"ram_reg[{address}][{bit}].state", xor=int(profile == "inverted")))
    return dict(relation_version=1, top="StateMapDUT", relations=rows)


def verify(out, profile="direct", reordered=False):
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    cells = FIXTURE if profile == "direct" else FIXTURE / "inverted"
    rtl_path = FIXTURE / "merged/dut.v"
    manifest, boundary = fixture_manifest(rtl_path, merge_registers=True)
    adapter = json.loads((cells / "cell-adapter.json").read_text())
    spec = candidate_spec(profile, reordered)
    slots = (2, 0, 3, 1) if reordered else (0, 1, 2, 3)
    counter = lambda bit: f"{'gate_count' if reordered else 'count'}_reg[{slots[bit]}]"
    commands = []
    cad_env = dict(os.environ)
    cad_env.pop("LD_LIBRARY_PATH", None)

    def invoke(argv, directory, name, env=None, expected=0):
        log = directory / name
        with log.open("w") as output:
            result = subprocess.run(list(map(str, argv)), cwd=directory, env=env,
                                    stdout=output, stderr=subprocess.STDOUT, timeout=300)
        commands.append(dict(cwd=str(directory.relative_to(ROOT)), argv=list(map(str, argv)),
                             log=str(log), exit_code=result.returncode))
        (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        assert result.returncode == expected, str(log)
        return log.read_text()

    synth = run / "synthesis"
    synth.mkdir()
    env = dict(cad_env, CHECKPOINT_FIXTURE=str(FIXTURE), CHECKPOINT_LIBRARY=str(cells / "cells.lib"),
               CHECKPOINT_RTL=str(rtl_path), CHECKPOINT_DUPLICATE_REGISTERS="1",
               CHECKPOINT_REORDER_REGISTERS=str(int(reordered)))
    invoke([GENUS, "-no_gui", "-batch", "-files", FIXTURE / "synth.tcl"], synth, "synth.log", env)
    netlist = synth / "netlist.v"

    def prove(directory, candidates=spec, implementation=netlist):
        directory.mkdir()
        (directory / "spec.json").write_text(json.dumps(candidates, indent=2) + "\n")
        (directory / "miter.sv").write_bytes(miter(candidates, rtl_path.read_text(), implementation.read_text()))
        (directory / "prove.tcl").write_text(SCRIPT)
        env = dict(cad_env, CHECKPOINT_RTL=str(rtl_path), CHECKPOINT_NETLIST=str(implementation),
                   CHECKPOINT_CELLS=str(cells / "cells.v"), CHECKPOINT_RELATION_SPEC=str(directory / "spec.json"),
                   CHECKPOINT_RELATION_MITER=str(directory / "miter.sv"),
                   CHECKPOINT_RELATION_SCRIPT=str(directory / "prove.tcl"))
        invoke([JASPER, "-allow_unsupported_OS", "-batch", "-tcl", directory / "prove.tcl"],
               directory, "jasper.log", env)
        paths = dict(rtl=rtl_path, netlist=implementation, models=cells / "cells.v", library=cells / "cells.lib",
                     synthesis_script=FIXTURE / "synth.tcl", synthesis_log=synth / "synth.log",
                     relation_spec=directory / "spec.json", relation_miter=directory / "miter.sv",
                     relation_script=directory / "prove.tcl", relation_log=directory / "jasper.log",
                     relation_results=directory / "relation-results.tsv")
        return {k: p.read_bytes() for k, p in paths.items()}, paths

    artifacts, paths = prove(run / "relation")
    mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
    assert mapping["semantic_bits"] == mapping["gate_storage_bits"] == 28
    assert sum(len(e["gates"]) for e in mapping["entries"]) == 32
    assert len([e for e in mapping["entries"] if len(e["gates"]) == 2]) == 4
    for filename, value in (("asic_state_map.json", mapping), ("manifest.json", manifest),
                            ("boundary.json", boundary), ("cell-adapter.json", adapter),
                            ("inputs.json", {k: str(v) for k, v in paths.items()})):
        (run / filename).write_text(json.dumps(value, indent=2) + "\n")

    def build(directory, sources):
        text = invoke([VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-debug_access+all",
                       "-CFLAGS", "-std=c++11", "-cc", os.environ["VCS_CC"], *sources,
                       ROOT / "tools/checkpoint_formats/semantic_restore.cc", "-o", directory / "simv"],
                      directory, "compile.log")
        assert "Y-2026.03-SP1" in text
        return directory / "simv"

    capture = run / "reference"
    capture.mkdir()
    rtl = rtl_path.read_text()
    prepare_capture(manifest, boundary, rtl, rtl + "\nStateMapDUT dut();", capture)
    (capture / "tb.sv").write_text(testbench("StateMapDUT"))
    simv = build(capture, [rtl_path, capture / "capture.sv", capture / "tb.sv"])
    invoke([simv, f"+semantic_capture={capture / 'capture.jsonl'}"], capture, "simulation.log")
    checkpoint, trace = package_capture(manifest, boundary, "formal-small-dut-v1", capture / "capture.jsonl", 17, 79, capture)
    data = (capture / "capture.rtlckpt").read_bytes()
    expected_build = builds(manifest, boundary, "formal-small-dut-v1")[0]
    cycle, deposits = gate_deposits(mapping, manifest, adapter, artifacts, data, expected_build, "tb.dut")
    assert cycle == 17 and len(deposits) == 28
    restore = run / "restore.txt"
    restore.write_text("".join(f"{p} {w} {v}\n" for p, w, v in deposits))
    gate = run / "gate-restored"
    gate.mkdir()
    clone = counter(0) + "_SYNTHESIS_SEQ_DUP_0"
    (gate / "tb.sv").write_text(testbench("StateMapDUT", start=cycle, trace=trace, deposits=(restore, 28),
                                         fault_storage=f"dut.\\{clone} .state"))
    simv = build(gate, [netlist, cells / "cells.v", gate / "tb.sv"])
    text = invoke([simv], gate, "simulation.log")
    assert "GATE_ZERO_EDGE_READBACK cycle=17 bits=28 edges=0" in text
    assert text.count("GATE_MATCH cycle=") == 79 and "GATE_END cycle=96 edges=79" in text
    failures = {}
    for name in ("missing", "width", "duplicate", "unknown-value", "incomplete", "missing-copy"):
        rows = [f"{p} {w} {v}" for p, w, v in deposits]
        p, w, v = deposits[0]
        rows[0] = f"{p} {w} {1-int(v)}"
        p, w, v = deposits[-1]
        if name == "missing": rows[-1] = "tb.dut.missing.state 1 0"
        elif name == "width": rows[-1] = f"{p} 2 {v}"
        elif name == "duplicate": rows[-1] = rows[0]
        elif name == "unknown-value": rows[-1] = f"{p} {w} x"
        elif name == "missing-copy": rows = [r for r in rows if clone not in r]
        else: rows.pop()
        path = gate / (name + ".txt")
        path.write_text("\n".join(rows) + "\n")
        log = invoke([simv, f"+invalid_restore={path}"], gate, name + ".log")
        assert "INVALID_GATE_LOAD_REJECTED edges=0 unchanged=28" in log and "GATE_END cycle=96 edges=79" in log
        failures[name] = "atomic rejection; 28 unchanged bits; matched continuation"
    fault = invoke([simv, "+fault_gate=1"], gate, "fault.log", expected=1)
    assert "GATE_MISMATCH cycle=29 signal=count_out" in fault and fault.count("GATE_MATCH cycle=") == 12
    shared = run / "gate-shared-fault"
    shared.mkdir()
    (shared / "tb.sv").write_text(testbench("StateMapDUT", start=cycle, trace=trace, deposits=(restore, 28),
                                           fault_storage="dut.\\held_copy_reg[0] .state"))
    shared_simv = build(shared, [netlist, cells / "cells.v", shared / "tb.sv"])
    fault = invoke([shared_simv, "+fault_gate=1"], shared, "fault.log", expected=1)
    assert "GATE_MISMATCH cycle=29 signal=held_out" in fault and fault.count("GATE_MATCH cycle=") == 12
    uninterrupted = run / "gate-uninterrupted"
    uninterrupted.mkdir()
    prefix = testbench("StateMapDUT").split("for (c=0;")[0]
    prefix += "for (c=0; c<17; c=c+1) begin\n" + \
              "reset = (c == 0); enable = (c % 3 != 1); write = (c < 4 || c % 5 != 2);\n" + \
              "address = c % 4; data = (c * 7 + 3) % 16; #1; clock=1; #1; clock=0; #1; end\n"
    continuation = testbench("StateMapDUT", start=17, trace=trace).split("initial begin\n#1;\n", 1)[1]
    (uninterrupted / "tb.sv").write_text(prefix + continuation.replace("edges != 79", "edges != 96"))
    un_simv = build(uninterrupted, [netlist, cells / "cells.v", uninterrupted / "tb.sv"])
    un_log = invoke([un_simv], uninterrupted, "simulation.log")
    assert [l for l in un_log.splitlines() if l.startswith("GATE_MATCH")] == \
           [l for l in text.splitlines() if l.startswith("GATE_MATCH")]
    conflicting = copy.deepcopy(checkpoint)
    alias = next(r for r in conflicting["records"] if r["state_id"] == state_id("Harness.dut.held_copy", "register"))
    alias["values"][0] = f"{int(alias['values'][0], 16) ^ 1:x}"
    conflicting_data = encode_semantic(conflicting, manifest)
    (run / "inconsistent-merged.rtlckpt").write_bytes(conflicting_data)
    try:
        gate_deposits(mapping, manifest, adapter, artifacts, conflicting_data, expected_build, "tb.dut")
    except FormatError as error:
        assert str(error).startswith("inconsistent merged semantic state")
    else:
        raise AssertionError("inconsistent checkpoint accepted")

    # Each adversarial candidate is proved against the same actual RTL/netlist.
    negatives = {}
    for name in ("wrong-polarity", "wrong-alias", "wrong-permutation"):
        wrong = copy.deepcopy(spec)
        for row in wrong["relations"]:
            if name == "wrong-polarity": row["xor"] ^= 1
            elif name == "wrong-alias" and row["original_rtl"] == "held[0]": row["original_rtl"] = "held[1]"
            elif name == "wrong-permutation" and row["original_rtl"] in ("count[0]", "count[1]"):
                row["original_rtl"] = "count[1]" if row["original_rtl"] == "count[0]" else "count[0]"
        bad_artifacts, _ = prove(run / name, wrong)
        assert b"\tcex\n" in bad_artifacts["relation_results"], name
        try: export_state_map(manifest, "StateMapDUT", adapter, bad_artifacts)
        except FormatError as error: negatives[name] = str(error)
        else: raise AssertionError(name + " accepted")
    for name, instance in (("changed-clone-D", clone), ("changed-shared-D", "held_copy_reg[0]")):
        bad = re.sub(rf"(\bCKDFFN?\s+\\{re.escape(instance)}\s*\([^;]*?\.D\s*\()[^)]*(\))",
                     r"\g<1>1'b0\2", netlist.read_text(), count=1)
        assert bad != netlist.read_text()
        path = run / (name + ".v")
        path.write_text(bad)
        bad_artifacts, _ = prove(run / name, implementation=path)
        assert b"\tcex\n" in bad_artifacts["relation_results"], name
        negatives[name] = "real Jasper counterexample on changed synthesized D connection"
    impossible = copy.deepcopy(spec)
    impossible["relations"] += [
        dict(original_rtl="held[0]", gate="held_copy_reg[1].state", xor=int(profile == "inverted")),
        dict(original_rtl="held[1]", gate="held_copy_reg[0].state", xor=int(profile != "inverted"))]
    vacuous, _ = prove(run / "vacuous-relation", impossible)
    assert b"\tunreachable\n" in vacuous["relation_results"]
    try: export_state_map(manifest, "StateMapDUT", adapter, vacuous)
    except FormatError as error:
        assert str(error) == "unproven or vacuous state correspondence"
        negatives["vacuous-relation"] = str(error)
    else: raise AssertionError("impossible relation accepted through vacuous assertions")
    for name, original, gate_name in (("missing-alias", "held[0]", None), ("missing-copy", None, clone + ".state")):
        missing = dict(artifacts)
        omitted = copy.deepcopy(spec)
        omitted["relations"] = [r for r in omitted["relations"] if not
                                (r["original_rtl"] == original or r["gate"] == gate_name)]
        missing["relation_spec"] = (json.dumps(omitted, indent=2) + "\n").encode()
        missing["relation_miter"] = miter(omitted, rtl, netlist.read_text())
        try: export_state_map(manifest, "StateMapDUT", adapter, missing)
        except FormatError as error: negatives[name] = str(error)
        else: raise AssertionError(name + " accepted")
        (run / (name + "-spec.json")).write_bytes(missing["relation_spec"])
    summary = dict(status="passed", profile=profile, reorder_registers=reordered, map_version=5,
                   merge_registers=True, duplicate_registers=True, semantic_bits=28, gate_bits=28,
                   proven_relationships=32, inverted_gate_bits=28 * int(profile == "inverted"),
                   duplicated_semantic_bits=4, merged_gate_bits=4, ram_words=4,
                   ram_implementation="synthesized flip-flops; no SRAM macro acceptance",
                   restore_cycle=17, restored_edges=79, compared_output_values=237, uninterrupted_edges=96,
                   zero_edge_readback=True, loader_rejections=failures, formal_negatives=negatives,
                   conflicting_merged_checkpoint_rejected=True, clone_fault_cycle=29, shared_fault_cycle=29,
                   initial_state="complete mapped relation; merged sources must agree",
                   remaining=["SRAM macro initialization", "relational unread/constant composition"])
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(run=str(run), **summary), indent=2))
    return run
