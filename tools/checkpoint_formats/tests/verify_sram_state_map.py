"""Original flat RTL -> synthesized SRAM architecture -> complete VCS replay.

Source Chipyard, FireSim and vcs-env.sh LAST before invoking. Diagnostic work
belongs under the loop runs directory. This uses artificial functional cells.
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
from tools.checkpoint_formats.relational_state import SCRIPT, miter
from tools.checkpoint_formats.replay import builds, package_capture, prepare_capture, prepare_replay
from tools.checkpoint_formats.semantic import state_id
from .verify_formal_state_map import FIXTURE, GENUS, JASPER, ROOT, VCS, fixture_manifest, testbench


SRAM = FIXTURE / "sram"
SHAPES = (("held", 4, 1, "register"), ("count", 4, 1, "register"),
          ("ram", 4, 4, "memory"), ("addr_q", 2, 1, "register"),
          ("write_q", 1, 1, "register"), ("data_q", 4, 1, "register"),
          ("read_q", 4, 1, "register"))
MACRO_STORAGE = (("contents", "ram", 4, 4, "memory"),
                 ("port_address", "addr_q", 2, 1, "register"),
                 ("port_write", "write_q", 1, 1, "register"),
                 ("port_data", "data_q", 4, 1, "register"),
                 ("pipeline", "read_q", 4, 1, "register"))


def verify(out, profile="direct"):
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    scalar = FIXTURE if profile == "direct" else FIXTURE / "inverted"
    macro = SRAM / ("macro.v" if profile == "direct" else "macro-inverted.v")
    models = run / "models.v"
    models.write_bytes((scalar / "cells.v").read_bytes() + macro.read_bytes())
    adapter = json.loads((scalar / "cell-adapter.json").read_text())
    adapter.update(adapter_version=2, models_sha256=sha(models.read_bytes()))
    for cell in adapter["cells"].values():
        for storage in cell["storage"]:
            storage.update(width=1, depth=1, kind="register")
    adapter["cells"]["CKSRAM"] = dict(storage=[
        dict(rtl_path=name, formal_path=name + "_reg", xor=0, width=width, depth=depth, kind=kind)
        for name, _, width, depth, kind in MACRO_STORAGE])
    rtl = SRAM / "dut.v"
    manifest, boundary = fixture_manifest(rtl)
    manifest["state"] = []
    for name, width, depth, kind in SHAPES:
        path = "Harness.dut." + name
        manifest["state"].append(dict(state_id=state_id(path, kind), hierarchy=path,
            width=width, depth=depth, kind=kind, signed=False,
            clock_domain="Harness.dut.clock", reset="synchronous" if name in ("held", "count") else "none",
            bit_order="lsb0", address_order="ascending_zero_based"))
    manifest["state"].sort(key=lambda entry: entry["state_id"])
    parity = int(profile == "inverted")
    rows = [dict(original_rtl=f"{name}[{bit}]", gate=f"{name}_reg[{bit}].state", xor=parity)
            for name in ("held", "count") for bit in range(4)]
    for name, original, width, depth, kind in MACRO_STORAGE:
        for address in range(depth):
            word = f"[{address}]" if kind == "memory" else ""
            for bit in range(width):
                suffix = f"[{bit}]" if width > 1 else ""
                rows.append(dict(original_rtl=original + word + suffix,
                                 gate="memory." + name + word + suffix, xor=parity))
    spec = dict(relation_version=1, top="StateMapDUT", relations=rows)
    commands = []
    cad_env = dict(os.environ)
    cad_env.pop("LD_LIBRARY_PATH", None)

    def invoke(argv, directory, name, env=None, expected=0):
        argv = list(map(str, argv))
        log = directory / name
        with log.open("w") as output:
            result = subprocess.run(argv, cwd=directory, env=env, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=300)
        commands.append(dict(cwd=str(directory.relative_to(ROOT)), argv=argv,
                             log=str(log), exit_code=result.returncode))
        (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        assert result.returncode == expected, str(log)
        return log.read_text()

    synth = run / "synthesis"
    synth.mkdir()
    env = dict(cad_env, CHECKPOINT_RTL=str(rtl), CHECKPOINT_IMPLEMENTATION_RTL=str(SRAM / "implementation.v"),
               CHECKPOINT_MACRO_STUB=str(SRAM / "macro-stub.v"), CHECKPOINT_LIBRARY=str(scalar / "cells.lib"))
    invoke([GENUS, "-no_gui", "-batch", "-files", SRAM / "synth.tcl"], synth, "synth.log", env)
    netlist = synth / "netlist.v"

    def prove(directory, candidate=spec, model=models):
        directory.mkdir()
        (directory / "spec.json").write_text(json.dumps(candidate, indent=2) + "\n")
        (directory / "miter.sv").write_bytes(miter(candidate, rtl.read_text(), netlist.read_text()))
        (directory / "prove.tcl").write_text(SCRIPT)
        env = dict(cad_env, CHECKPOINT_RTL=str(rtl), CHECKPOINT_NETLIST=str(netlist),
            CHECKPOINT_CELLS=str(model), CHECKPOINT_RELATION_SPEC=str(directory / "spec.json"),
            CHECKPOINT_RELATION_MITER=str(directory / "miter.sv"), CHECKPOINT_RELATION_SCRIPT=str(directory / "prove.tcl"))
        invoke([JASPER, "-allow_unsupported_OS", "-batch", "-tcl", directory / "prove.tcl"], directory, "jasper.log", env)
        paths = dict(rtl=rtl, netlist=netlist, models=model, library=scalar / "cells.lib",
            implementation_rtl=SRAM / "implementation.v", macro_stub=SRAM / "macro-stub.v",
            synthesis_script=SRAM / "synth.tcl", synthesis_log=synth / "synth.log",
            relation_spec=directory / "spec.json", relation_miter=directory / "miter.sv",
            relation_script=directory / "prove.tcl", relation_log=directory / "jasper.log",
            relation_results=directory / "relation-results.tsv")
        return {role: path.read_bytes() for role, path in paths.items()}, paths

    artifacts, paths = prove(run / "relation")
    mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
    assert mapping["map_version"] == 8 and mapping["semantic_bits"] == mapping["gate_storage_bits"] == 35
    for name, value in (("asic_state_map.json", mapping), ("manifest.json", manifest),
                        ("boundary.json", boundary), ("cell-adapter.json", adapter),
                        ("inputs.json", {role: str(path) for role, path in paths.items()})):
        (run / name).write_text(json.dumps(value, indent=2) + "\n")

    def build(directory, sources):
        text = invoke([VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-debug_access+all",
            "-CFLAGS", "-std=c++11", "-cc", os.environ["VCS_CC"], *sources,
            ROOT / "tools/checkpoint_formats/semantic_restore.cc", "-o", directory / "simv"], directory, "compile.log")
        assert "Y-2026.03-SP1" in text
        return directory / "simv"

    capture = run / "reference"
    capture.mkdir()
    prepare_capture(manifest, boundary, rtl.read_text(), rtl.read_text() + "\nStateMapDUT dut();", capture)
    (capture / "tb.sv").write_text(testbench("StateMapDUT"))
    simv = build(capture, [rtl, capture / "capture.sv", capture / "tb.sv"])
    invoke([simv, f"+semantic_capture={capture / 'capture.jsonl'}"], capture, "simulation.log")
    checkpoint, trace = package_capture(manifest, boundary, "formal-sram-dut-v1", capture / "capture.jsonl", 17, 79, capture)
    data = (capture / "capture.rtlckpt").read_bytes()
    expected_build = builds(manifest, boundary, "formal-sram-dut-v1")[0]
    cycle, deposits = gate_deposits(mapping, manifest, adapter, artifacts, data, expected_build, "tb.dut")
    assert cycle == 17 and len(deposits) == 16 and sum(width for _, width, _ in deposits) == 35
    restore = run / "restore.txt"
    restore.write_text("".join(f"{path} {width} {value}\n" for path, width, value in deposits))
    gate = run / "gate-restored"
    gate.mkdir()
    (gate / "tb.sv").write_text(testbench("StateMapDUT", start=cycle, trace=trace, deposits=(restore, len(deposits))))
    simv = build(gate, [netlist, models, gate / "tb.sv"])
    log = invoke([simv], gate, "simulation.log")
    assert "GATE_ZERO_EDGE_READBACK cycle=17 bits=16 edges=0" in log
    assert log.count("GATE_MATCH cycle=") == 79 and "GATE_END cycle=96 edges=79" in log
    replay = run / "rtl-restored"
    prepare_replay(manifest, boundary, "formal-sram-dut-v1", data,
                   (capture / "capture.trace").read_bytes(), replay)
    clean = build(replay, [rtl, replay / "replay.sv"])
    clean_log = invoke([clean, f"+restore={replay / 'restore.txt'}", f"+waveform={replay / 'replay.vcd'}"], replay, "simulation.log")
    assert "PASS: fresh clean RTL replay" in clean_log

    uninterrupted = run / "gate-uninterrupted"
    uninterrupted.mkdir()
    prefix = testbench("StateMapDUT").split("for (c=0;")[0]
    prefix += "for (c=0; c<17; c=c+1) begin\n" + \
        "reset = (c == 0); enable = (c % 3 != 1); write = (c < 4 || c % 5 != 2);\n" + \
        "address = c % 4; data = (c * 7 + 3) % 16; #1; clock=1; #1; clock=0; #1; end\n"
    continuation = testbench("StateMapDUT", start=17, trace=trace).split("initial begin\n#1;\n", 1)[1]
    (uninterrupted / "tb.sv").write_text(prefix + continuation.replace("edges != 79", "edges != 96"))
    un_simv = build(uninterrupted, [netlist, models, uninterrupted / "tb.sv"])
    un_log = invoke([un_simv], uninterrupted, "simulation.log")
    assert [line for line in un_log.splitlines() if line.startswith("GATE_MATCH")] == \
           [line for line in log.splitlines() if line.startswith("GATE_MATCH")]

    loader_failures = {}
    for name in ("missing-word", "missing-pipeline", "width", "duplicate", "unknown-value", "incomplete"):
        bad = [f"{path} {width} {value}" for path, width, value in deposits]
        path, width, value = deposits[0]
        bad[0] = f"{path} {width} {int(value, 16) ^ 1:x}"
        index = next(n for n, (path, _, _) in enumerate(deposits) if "memory.contents[3]" in path)
        path, width, value = deposits[index]
        if name == "missing-word": bad[index] = "tb.dut.memory.contents[4] 4 0"
        elif name == "missing-pipeline": bad = [row for row in bad if "memory.pipeline" not in row]
        elif name == "width": bad[index] = f"{path} 3 {value}"
        elif name == "duplicate": bad[index] = bad[0]
        elif name == "unknown-value": bad[index] = f"{path} {width} x"
        else: bad.pop()
        filename = gate / (name + ".txt")
        filename.write_text("\n".join(bad) + "\n")
        rejected = invoke([simv, f"+invalid_restore={filename}"], gate, name + ".log")
        assert "INVALID_GATE_LOAD_REJECTED edges=0 unchanged=16" in rejected and "GATE_END cycle=96 edges=79" in rejected
        loader_failures[name] = "rejected atomically; all 35 bits unchanged; continuation matches"

    faults = {}
    for name, storage in (("contents", "contents[0][0]"), ("address", "port_address[0]"),
                          ("enable", "port_write"), ("data", "port_data[0]"), ("pipeline", "pipeline[0]")):
        directory = run / ("fault-" + name)
        directory.mkdir()
        (directory / "tb.sv").write_text(testbench("StateMapDUT", start=cycle, trace=trace,
            deposits=(restore, len(deposits)), fault_storage="dut.memory." + storage))
        fault_simv = build(directory, [netlist, models, directory / "tb.sv"])
        faulty = invoke([fault_simv, "+fault_gate=1"], directory, "simulation.log", expected=1)
        mismatch = re.search(r"GATE_MISMATCH cycle=(\d+) signal=read_out", faulty)
        assert mismatch and 29 <= int(mismatch[1]) < 96
        faults[name] = int(mismatch[1])

    proof_failures = {}
    for name in ("wrong-polarity", "missing-memory-bit", "changed-write", "changed-pipeline"):
        candidate = copy.deepcopy(spec)
        model = models
        if name == "wrong-polarity": candidate["relations"][8]["xor"] ^= 1
        elif name == "missing-memory-bit": candidate["relations"].pop(8)
        else:
            model = run / (name + ".v")
            source = models.read_text()
            if name == "changed-write":
                token = "if (port_write)" if profile == "direct" else "if (~port_write)"
                source = source.replace(token, "if (1'b0)")
            else:
                token = "pipeline <= contents[port_address];" if profile == "direct" else "pipeline <= contents[~port_address];"
                source = source.replace(token, "pipeline <= port_data;")
            assert source != models.read_text()
            model.write_text(source)
        negative, _ = prove(run / name, candidate, model)
        assert "\tassert\tcex\n" in negative["relation_results"].decode()
        assert "A counterexample (cex)" in negative["relation_log"].decode()
        negative_adapter = copy.deepcopy(adapter)
        negative_adapter["models_sha256"] = sha(model.read_bytes())
        try:
            export_state_map(manifest, "StateMapDUT", negative_adapter, negative)
        except FormatError as error:
            proof_failures[name] = str(error)
        else:
            raise AssertionError("unproven SRAM state accepted")

    summary = dict(status="passed", profile=profile, semantic_bits=35, gate_storage_bits=35,
        macro_storage_bits=27, macro_words=4, initialized_words=16, restore_cycle=17,
        restored_edges=79, compared_output_values=237, end_cycle=96, retiming=False,
        pending_write=int(next(r for r in checkpoint["records"] if r["state_id"] == state_id("Harness.dut.write_q", "register"))["values"][0], 16),
        loader_rejections=loader_failures, actual_state_fault_cycles=faults, real_counterexample_rejections=proof_failures,
        automatic_SRAM_inference=False, process_ASIC_or_power_validated=False, physical_fpga_validated=False)
    assert summary["pending_write"] == 1
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(run=str(run), **summary), indent=2))
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=("direct", "inverted"), default="direct")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    verify(args.out, args.profile)


if __name__ == "__main__":
    main()
