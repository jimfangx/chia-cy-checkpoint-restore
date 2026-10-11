"""Real many-to-many Genus/Jasper/VCS state correspondence and fault checks."""

import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.constant_state import SCRIPT as CONSTANT_SCRIPT, binding, validate_constants
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits
from tools.checkpoint_formats.relational_state import SCRIPT, miter
from tools.checkpoint_formats.replay import builds, package_capture, prepare_capture, prepare_replay
from tools.checkpoint_formats.semantic import encode_semantic, state_id
from .verify_formal_state_map import FIXTURE, GENUS, JASPER, ROOT, VCS, fixture_manifest, testbench


def candidate_spec(profile, reordered, optimized=False, constant=False):
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
    return dict(relation_version=3 if constant else 2 if optimized else 1, top="StateMapDUT", relations=rows,
                **(dict(unread=[f"unused[{bit}]" for bit in range(4)] if optimized else [])
                   if optimized or constant else {}),
                **(dict(constants=[dict(original_rtl=f"constant[{bit}]", value=(10 >> bit) & 1)
                                   for bit in range(4)]) if constant else {}))


def verify(out, profile="direct", reordered=False, optimized=False, constant=False):
    optimized = optimized or constant
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    cells = FIXTURE if profile == "direct" else FIXTURE / "inverted"
    rtl_path = FIXTURE / ("merged/constants/dut.v" if constant else "merged/optimized/dut.v" if optimized else "merged/dut.v")
    manifest, boundary = fixture_manifest(rtl_path, merge_registers=True, optimize_registers=optimized,
                                         constant_registers=constant)
    adapter = json.loads((cells / "cell-adapter.json").read_text())
    spec = candidate_spec(profile, reordered, optimized, constant)
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

    def prove_constants(directory, reference=rtl_path, predicates=None):
        directory.mkdir()
        predicates = predicates or dict(constant_version=1, top="StateMapDUT", bits=[
            dict(signal="constant", width=4, bit=bit, value=(10 >> bit) & 1) for bit in range(4)])
        (directory / "spec.json").write_text(json.dumps(predicates, indent=2) + "\n")
        (directory / "bind.sv").write_bytes(binding(predicates))
        (directory / "prove.tcl").write_text(CONSTANT_SCRIPT)
        env = dict(cad_env, CHECKPOINT_RTL=str(reference), CHECKPOINT_CONSTANT_TOP="StateMapDUT",
                   CHECKPOINT_CONSTANT_SPEC=str(directory / "spec.json"),
                   CHECKPOINT_CONSTANT_BIND=str(directory / "bind.sv"),
                   CHECKPOINT_CONSTANT_SCRIPT=str(directory / "prove.tcl"))
        invoke([JASPER, "-allow_unsupported_OS", "-batch", "-tcl", directory / "prove.tcl"],
               directory, "jasper.log", env)
        return dict(constant_spec=directory / "spec.json", constant_bind=directory / "bind.sv",
                    constant_script=directory / "prove.tcl", constant_log=directory / "jasper.log",
                    constant_results=directory / "constant-results.tsv")

    constant_paths = prove_constants(run / "constant-proof") if constant else {}

    def prove(directory, candidates=spec, implementation=netlist, reference=rtl_path):
        directory.mkdir()
        (directory / "spec.json").write_text(json.dumps(candidates, indent=2) + "\n")
        (directory / "miter.sv").write_bytes(miter(candidates, reference.read_text(), implementation.read_text()))
        (directory / "prove.tcl").write_text(SCRIPT)
        env = dict(cad_env, CHECKPOINT_RTL=str(reference), CHECKPOINT_NETLIST=str(implementation),
                   CHECKPOINT_CELLS=str(cells / "cells.v"), CHECKPOINT_RELATION_SPEC=str(directory / "spec.json"),
                   CHECKPOINT_RELATION_MITER=str(directory / "miter.sv"),
                   CHECKPOINT_RELATION_SCRIPT=str(directory / "prove.tcl"))
        invoke([JASPER, "-allow_unsupported_OS", "-batch", "-tcl", directory / "prove.tcl"],
               directory, "jasper.log", env)
        paths = dict(rtl=reference, netlist=implementation, models=cells / "cells.v", library=cells / "cells.lib",
                     synthesis_script=FIXTURE / "synth.tcl", synthesis_log=synth / "synth.log",
                     relation_spec=directory / "spec.json", relation_miter=directory / "miter.sv",
                     relation_script=directory / "prove.tcl", relation_log=directory / "jasper.log",
                     relation_results=directory / "relation-results.tsv")
        paths.update(constant_paths)
        return {k: p.read_bytes() for k, p in paths.items()}, paths

    artifacts, paths = prove(run / "relation")
    mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
    assert mapping["semantic_bits"] == 28 + 4 * (optimized + constant) and mapping["gate_storage_bits"] == 28
    assert mapping["map_version"] == (7 if constant else 6 if optimized else 5)
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

    constant_checks = {}
    if constant:
        for bit in range(4):
            changed = copy.deepcopy(checkpoint)
            row = next(r for r in changed["records"] if r["state_id"] == state_id("Harness.dut.constant", "register"))
            assert row["values"] == ["a"]
            row["values"] = [f"{10 ^ (1 << bit):x}"]
            payload = encode_semantic(changed, manifest)
            (run / f"conflicting-constant-{bit}.rtlckpt").write_bytes(payload)
            try: gate_deposits(mapping, manifest, adapter, artifacts, payload, expected_build, "tb.dut")
            except FormatError as error:
                assert str(error) == f"checkpoint conflicts with proven constant state: constant[{bit}]"
                constant_checks[f"checkpoint-bit-{bit}"] = str(error)
            else: raise AssertionError("conflicting constant accepted")
        early = copy.deepcopy(checkpoint)
        early["target_cycle"] = 0
        payload = encode_semantic(early, manifest)
        (run / "pre-horizon.rtlckpt").write_bytes(payload)
        try: gate_deposits(mapping, manifest, adapter, artifacts, payload, expected_build, "tb.dut")
        except FormatError as error:
            assert str(error) == "checkpoint precedes proven constant horizon"
            constant_checks["pre-horizon"] = str(error)
        else: raise AssertionError("unproven initial constant accepted")
        replay = run / "rtl-conflicting-constant"
        prepare_replay(manifest, boundary, "formal-small-dut-v1", (run / "conflicting-constant-0.rtlckpt").read_bytes(),
                       (capture / "capture.trace").read_bytes(), replay)
        bad_simv = build(replay, [rtl_path, replay / "replay.sv"])
        bad_log = invoke([bad_simv, f"+restore={replay / 'restore.txt'}",
                          f"+waveform={replay / 'replay.vcd'}"], replay, "simulation.log", expected=1)
        assert "FIRST_MISMATCH cycle=17" in bad_log and "signal=held_out" in bad_log
        wrong = json.loads(artifacts["constant_spec"])
        wrong["bits"][0]["value"] ^= 1
        conditional = run / "conditional-constant.v"
        conditional.write_text(rtl.replace("constant <= 4'b1010;", "if (enable) constant <= 4'b1010;"))
        for name, reference, predicates in (("wrong-value", rtl_path, wrong), ("conditional-update", conditional, None)):
            negative_paths = prove_constants(run / ("constant-" + name), reference, predicates)
            negative = dict(artifacts, rtl=reference.read_bytes(), **{k: p.read_bytes() for k, p in negative_paths.items()})
            assert b"\tassert\tcex\n" in negative["constant_results"]
            try: validate_constants(negative, manifest, "StateMapDUT")
            except FormatError as error: constant_checks[name] = str(error)
            else: raise AssertionError("false independent predicate accepted")
        # The conditional design preserves a guessed constant once loaded, so
        # its complete relation can PASS even though arbitrary state does not
        # converge in one edge. That relation alone must never classify state.
        conditional_artifacts, _ = prove(run / "conditional-relation", reference=conditional)
        assert b"\tcex\n" not in conditional_artifacts["relation_results"]
        from tools.checkpoint_formats.formal_state_map import flat_inventory
        from tools.checkpoint_formats.relational_state import validate_relations
        refs = {e["formal_reference"]: e for e in mapping["entries"]}
        gates = flat_inventory(netlist.read_text(), artifacts["models"].decode(), adapter, "StateMapDUT")
        try: validate_relations(conditional_artifacts, refs, gates)
        except FormatError as error:
            assert str(error) == "relational constants lack matching independent predicates"
            constant_checks["conditional-relation-only"] = str(error)
        else: raise AssertionError("complete relation PASS substituted for independent predicates")
        variants = {
            "missing-proof": {k: v for k, v in artifacts.items() if not k.startswith("constant_")},
            "missing-property": dict(artifacts, constant_results=b"\n".join(
                r for r in artifacts["constant_results"].split(b"\n") if b".constant_0\t" not in r)),
            "bounded-proof": dict(artifacts, constant_results=artifacts["constant_results"].replace(b"\tproven", b"\tbounded", 1)),
            "vacuous-proof": dict(artifacts, constant_results=artifacts["constant_results"].replace(b"\tcovered", b"\tunreachable", 1)),
            "wrong-raw-status": dict(artifacts, constant_log=artifacts["constant_log"].replace(b"\tproven", b"\tcex", 1))}
        for name in ("wrong-relation-constant", "missing-relation-constant"):
            wrong = copy.deepcopy(spec)
            if name.startswith("wrong"): wrong["constants"][0]["value"] ^= 1
            else: wrong["constants"].pop()
            variants[name] = dict(artifacts, relation_spec=(json.dumps(wrong, indent=2) + "\n").encode(),
                                  relation_miter=miter(wrong, rtl, netlist.read_text()))
        for name, negative in variants.items():
            try: export_state_map(manifest, "StateMapDUT", adapter, negative)
            except FormatError as error: constant_checks[name] = str(error)
            else: raise AssertionError(name + " accepted")
        (run / "constant-rejections.json").write_text(json.dumps(constant_checks, indent=2) + "\n")

    unread_checks = {}
    if optimized:
        altered = copy.deepcopy(checkpoint)
        unused_id = state_id("Harness.dut.unused", "register")
        unused_record = next(r for r in altered["records"] if r["state_id"] == unused_id)
        unused_record["values"][0] = f"{int(unused_record['values'][0], 16) ^ 15:x}"
        altered_data = encode_semantic(altered, manifest)
        altered_path = run / "altered-unread.rtlckpt"
        altered_path.write_bytes(altered_data)
        assert gate_deposits(mapping, manifest, adapter, artifacts, altered_data, expected_build, "tb.dut") == (cycle, deposits)
        replay = run / "rtl-altered-unread"
        replay.mkdir()
        prepare_replay(manifest, boundary, "formal-small-dut-v1", altered_data,
                       (capture / "capture.trace").read_bytes(), replay)
        replay_simv = build(replay, [rtl_path, replay / "replay.sv"])
        replay_log = invoke([replay_simv, f"+restore={replay / 'restore.txt'}",
                             f"+waveform={replay / 'replay.vcd'}"], replay, "simulation.log")
        assert "PASS: fresh clean RTL replay cycles=17..95 samples=79" in replay_log
        unread_checks["altered-checkpoint"] = "all four unread bits flipped; identical deposits and fresh RTL replay"

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
    if optimized:
        connected = run / "connected-unread.v"
        held_expression = "held & held_copy ^ constant ^ 4'b1010" if constant else "held & held_copy"
        connected.write_text(rtl.replace(f"assign held_out = {held_expression};",
                                         f"assign held_out = ({held_expression}) ^ unused;"))
        bad_artifacts, _ = prove(run / "connected-unread", reference=connected)
        assert b"\tassert\tcex\n" in bad_artifacts["relation_results"]
        assert b"checkpoint_relation_miter.output_held\tassert\tcex" in bad_artifacts["relation_results"]
        # Check the proof adapter itself; changed reference is intentionally not
        # claimed as the output of the original synthesis invocation.
        from tools.checkpoint_formats.formal_state_map import flat_inventory
        from tools.checkpoint_formats.relational_state import validate_relations
        refs = {e["formal_reference"]: e for e in mapping["entries"]}
        gates = flat_inventory(netlist.read_text(), artifacts["models"].decode(), adapter, "StateMapDUT")
        constants = validate_constants(artifacts, manifest, "StateMapDUT") if constant else {}
        try: validate_relations(bad_artifacts, refs, gates, constants)
        except FormatError as error:
            assert str(error) == "unproven or vacuous state correspondence"
            negatives["connected-unread"] = str(error)
        else: raise AssertionError("observable omitted state accepted")
        connected_next = run / "connected-unread-next.v"
        connected_next.write_text(rtl.replace("count <= count + 1'b1;", "count <= count + unused;"))
        bad_next, _ = prove(run / "connected-unread-next", reference=connected_next)
        assert any(b".step_" in row and row.endswith(b"\tassert\tcex")
                   for row in bad_next["relation_results"].splitlines())
        try: validate_relations(bad_next, refs, gates, constants)
        except FormatError as error:
            assert str(error) == "unproven or vacuous state correspondence"
            negatives["connected-unread-next"] = str(error)
        else: raise AssertionError("future observable omitted state accepted")
        for name in ("missing-unread", "wrong-unread"):
            wrong = copy.deepcopy(spec)
            if name == "missing-unread": wrong["unread"].pop()
            else: wrong["unread"][-1] = "unknown[0]"
            missing = dict(artifacts, relation_spec=(json.dumps(wrong, indent=2) + "\n").encode(),
                           relation_miter=miter(wrong, rtl, netlist.read_text()))
            try: export_state_map(manifest, "StateMapDUT", adapter, missing)
            except FormatError as error: negatives[name] = str(error)
            else: raise AssertionError(name + " accepted")
            (run / (name + "-spec.json")).write_bytes(missing["relation_spec"])
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
    summary = dict(status="passed", profile=profile, reorder_registers=reordered, map_version=mapping["map_version"],
                   merge_registers=True, duplicate_registers=True, optimize_registers=optimized,
                   constant_registers=constant, constant_semantic_bits=4 * constant, constant_rejections=constant_checks,
                   unread_semantic_bits=4 * optimized, unread_checks=unread_checks,
                   semantic_bits=28 + 4 * (optimized + constant), gate_bits=28,
                   proven_relationships=32, inverted_gate_bits=28 * int(profile == "inverted"),
                   duplicated_semantic_bits=4, merged_gate_bits=4, ram_words=4,
                   ram_implementation="synthesized flip-flops; no SRAM macro acceptance",
                   restore_cycle=17, restored_edges=79, compared_output_values=237, uninterrupted_edges=96,
                   zero_edge_readback=True, loader_rejections=failures, formal_negatives=negatives,
                   conflicting_merged_checkpoint_rejected=True, clone_fault_cycle=29, shared_fault_cycle=29,
                   initial_state="complete mapped relation; merged sources must agree",
                   remaining=["SRAM macro initialization"] + ([] if constant else ["relational constant composition"]))
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(run=str(run), **summary), indent=2))
    return run
