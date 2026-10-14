"""Reproducible M2 VCS metasim -> fresh ordinary RTL replay acceptance check.

Run from Chipyard root after sourcing env.sh, sims/firesim/env.sh, and
automations/checkpoint_loop/vcs-env.sh LAST. All diagnostics go under --out.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from tools.checkpoint_formats.codec import FormatError, encode, require
from tools.checkpoint_formats.replay import (
    package_capture, prepare_capture, prepare_replay, read_json,
)


ROOT = Path(__file__).resolve().parents[3]


def invalidate_stale_driver_objects(generated, log):
    """VCS's cached external-C makefile can ignore compiler header dependencies.

    Remove only generated objects whose recorded source/header is newer, so
    these checks actually exercise the current driver ABI on reused builds.
    """
    removed = []
    for dependency_file in generated.glob("*.csrc/*.d"):
        obj = dependency_file.with_suffix(".o")
        if not obj.exists():
            continue
        dependencies = shlex.split(dependency_file.read_text().replace("\\\n", " ").partition(":")[2])
        stale = [str(path) for token in dependencies
                 if (path := Path(token)).is_file() and path.stat().st_mtime_ns > obj.stat().st_mtime_ns]
        if stale:
            obj.unlink()
            removed.append(dict(object=str(obj), newer_dependencies=stale))
    log.write_text(json.dumps(removed, indent=2) + "\n")


def run(argv, log, cwd=ROOT, expected=0):
    with log.open("w") as output:
        output.write(f"cwd={cwd}\nargv={json.dumps([str(a) for a in argv])}\n")
        output.flush()
        process = subprocess.Popen([str(a) for a in argv], cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        output.write(f"fresh_process_pid={process.pid}\n")
        output.flush()
        try:
            code = process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        output.write(f"exit={code}\n")
    require(code == expected if expected is not None else code != 0,
            f"unexpected process exit {code}; see {log}")
    return log.read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--forwarded-clocks", action="store_true",
                        help="Also exercise nested/sibling forwarded clocks at the bridge-extracted boundary.")
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    require(str(vcs) == "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs", "source vcs-env.sh LAST")
    design = "ForwardedClockInventoryFixture" if args.forwarded_clocks else "InventoryFixture"
    root_option = "SEMANTIC_BRIDGE_CHECKPOINT_ROOT" if args.forwarded_clocks else "SEMANTIC_CHECKPOINT_ROOT"
    configuration = design + "-NoConfig-DefaultF2Config"
    make = ["make", f"DESIGN={design}", "TARGET_CONFIG=NoConfig", "PLATFORM_CONFIG=DefaultF2Config",
            f"{root_option}={design}.dut", f"BUILD_DIR={build}"]
    if args.forwarded_clocks:
        driver_dir = ROOT / 'sims/firesim/sim/src/main/cc/midasexamples'
        make += [f"DRIVER_CC={driver_dir / 'TestInventoryFixture.cc'} {driver_dir / 'TestHarness.cc'}"]
    sim_dir = ROOT / "sims/firesim/sim"
    run(make + ["verilog"], out / "fixture-verilog.log", sim_dir)
    generated = build / ("f2/f2-midasexamples-" + configuration)
    base = generated / "FireSim-generated"
    manifest, boundary = read_json(str(base) + ".semantic-state.json"), read_json(str(base) + ".semantic-boundary.json")
    clean = Path(str(base) + ".semantic-clean.sv")
    if args.forwarded_clocks:
        # Bind the test to actual emitted clock connections and the unchanged
        # complete fixture state, not just a passing self-checking driver.
        from tools.checkpoint_formats.replay import modules, inventory_rtl
        rtl = modules(clean.read_text())
        require(len(manifest['state']) == 15 and sum(e['depth'] for e in manifest['state']) == 22,
                'changed complete forwarded-clock fixture state')
        require(inventory_rtl(rtl, boundary['dut_module']) ==
                {e['hierarchy'][len(manifest['dut_root']) + 1:]: (e['width'], e['depth'], e['kind'])
                 for e in manifest['state']}, 'incomplete independent forwarded-clock RTL inventory')
        dut = rtl[boundary['dut_module']][1]
        require(re.search(r'\.clock\s*\(a_clock\)', dut) and
                re.search(r'\.clock\s*\(b_clock\)', dut) and
                'assign a_clock = b_io_forwarded;' in dut and
                'assign b_clock = relay_forwarded;' in dut and
                'assign forwarded = pin_value;' in rtl['InventoryClockRelay'][1] and
                'assign pin_pad = leaf_forwarded;' in rtl['InventoryClockRelay'][1] and
                'assign value = pad;' in rtl['InventoryClockIOCell'][1] and
                'assign forwarded = clock;' in rtl['InventoryClockForwarder'][1],
                'forwarded-clock test lacks actual nested/sibling clock connections')
    fields = prepare_capture(manifest, boundary, clean.read_text(), Path(str(base) + ".sv").read_text(), out)
    invalidate_stale_driver_objects(generated, out / "rebuilt-driver-objects.json")
    run(make + ["vcs", f"VCS={vcs} -full64", "VCS_FLAGS=-Mupdate", f"VCS_EXTRA_V={out / 'capture.sv'}"],
        out / "fixture-vcs-build.log", sim_dir)
    text = run([generated / design, "+vcs+initreg+0", "+vcs+initmem+0",
                f"+semantic_capture={out / 'capture.jsonl'}"], out / "metasim-run.log")
    require("*** PASSED ***" in text, "metasim fixture did not report PASS")
    rows = [json.loads(line) for line in (out / "capture.jsonl").read_text().splitlines()]
    require(len(rows) == 37, f"unexpected actual DUT edge count {len(rows)}")
    values = [{f["path"]: int(v, 16) for f, v in zip(fields, row["values"])} for row in rows]
    # Independent oracle checks tie row indices to the target test sequence,
    # rather than the clock bridge's count (which reports 38 for this test).
    require(all(v["reset"] == 1 and v["counter"] == 0 for v in values[:5]), "reset edge indexing")
    require(all(v["reset"] == 0 and v["counter"] == c - 5 for c, v in enumerate(values[5:], 5)),
            "target edge indexing disagrees with DUT counter")
    require(values[5]["io_wen"] == 1 and values[5]["io_data"] == 0x100, "first post-reset edge")
    require(values[22]["qValid"] == 1, "queue checkpoint is empty")
    require(values[24]["busy"] == values[24]["qValid"] == 1 and values[24]["delay"] == 1,
            "outstanding operation/queue checkpoint missing")
    require(values[26]["responseValid"] == values[26]["qValid"] == 1 and values[26]["io_respReady"] == 0,
            "stalled response/queue checkpoint missing")
    cases = [("reset", 0), ("active", 5), ("queued", 22), ("outstanding", 24), ("stalled", 26)]
    summary = dict(design=design, forwarded_clocks=args.forwarded_clocks,
                   actual_dut_edges=len(rows), clock_bridge_reported_cycles=38, cases=[],
                   semantic_entries=len(manifest["state"]), words=sum(e["depth"] for e in manifest["state"]))
    traces = {}
    for name, cycle in cases:
        case = out / name
        ckpt, trace = package_capture(manifest, boundary, configuration,
                                      out / "capture.jsonl", cycle, len(rows) - cycle, case)
        traces[name] = (ckpt, trace)
        verify_case(vcs, clean, manifest, boundary, case, configuration=configuration)
        summary["cases"].append(dict(name=name, cycle=cycle, samples=len(rows) - cycle,
                                     checkpoint_state={k: values[cycle][k] for k in
                                                       ("counter", "qValid", "busy", "delay", "responseValid", "io_respReady")}))
    # Corrupt a logically valid, checksummed trace, so comparison must identify
    # the first differing output at its original target cycle.
    mismatch = out / "mismatch"
    mismatch.mkdir(exist_ok=True)
    ckpt, trace = traces["stalled"]
    altered = copy.deepcopy(trace)
    value = altered["records"][3]["outputs"]["io_respData"]
    value["value"] = f"{int(value['value'], 16) ^ 1:03x}"
    (mismatch / "capture.rtlckpt").write_bytes((out / "stalled/capture.rtlckpt").read_bytes())
    (mismatch / "capture.trace").write_bytes(encode("trace", altered))
    result = verify_case(vcs, clean, manifest, boundary, mismatch, expected=None, configuration=configuration)
    require("FIRST_MISMATCH cycle=29 signal=io_respData" in result and result.count("FIRST_MISMATCH") == 1,
            "first mismatch did not name exact signal/cycle")
    summary["first_mismatch"] = dict(cycle=29, signal="io_respData", exit="nonzero")
    if args.forwarded_clocks:
        checkpoint_bytes = (out / 'stalled/capture.rtlckpt').read_bytes()
        trace_bytes = (out / 'stalled/capture.trace').read_bytes()
        incompatible = copy.deepcopy(ckpt)
        incompatible['build']['rtl_build_hash'] = '0' * 64
        incomplete = copy.deepcopy(ckpt)
        incomplete['records'].pop()
        unknown = copy.deepcopy(ckpt)
        unknown['records'][0]['state_id'] = '0' * 64
        unknown['records'].sort(key=lambda e: e['state_id'])
        invalid = dict(truncated=checkpoint_bytes[:-5],
                       corrupt_checksum=checkpoint_bytes[:-1] + bytes([checkpoint_bytes[-1] ^ 1]),
                       incompatible_build=encode('rtlckpt', incompatible),
                       incomplete_state_owner=encode('rtlckpt', incomplete),
                       unknown_state_owner=encode('rtlckpt', unknown))
        rejections = []
        for name, data in invalid.items():
            case = out / ('image-' + name)
            case.mkdir(exist_ok=True)
            (case / 'invalid.rtlckpt').write_bytes(data)
            try:
                prepare_replay(manifest, boundary, configuration, data, trace_bytes, case)
            except FormatError as error:
                rejections.append(dict(case=name, rejection=str(error)))
            else:
                raise AssertionError('invalid image accepted: ' + name)
            require(not (case / 'restore.txt').exists() and not (case / 'replay.sv').exists(),
                    'invalid image published partial restore artifacts: ' + name)
        summary['image_rejections'] = rejections
        fault = out / 'semantic-corruption'
        fault.mkdir(exist_ok=True)
        for suffix in ('rtlckpt', 'trace'):
            (fault / ('capture.' + suffix)).write_bytes((out / 'stalled' / ('capture.' + suffix)).read_bytes())
        # Read back every saved word first, then corrupt actual stored state in
        # the clock-forwarded consumer. The original checkpoint/trace stay intact.
        result = verify_case(vcs, clean, manifest, boundary, fault, expected=None,
                             configuration=configuration,
                             post_restore_checks='  dut.a.saved = dut.a.saved ^ 9\'h001;\n'
                                                 '  $display("INJECTED_SEMANTIC_FAULT a.saved after complete zero-edge readback");',
                             monitor_edges=True)
        require('RESTORE: deposited 22 semantic words before first DUT edge' in result and
                'INJECTED_SEMANTIC_FAULT a.saved after complete zero-edge readback' in result and
                'FIRST_MISMATCH cycle=26 signal=io_left' in result and
                result.count('FIRST_MISMATCH') == 1 and 'ACKNOWLEDGED_TARGET_EDGE' not in result,
                'actual semantic corruption did not stop at its first boundary before any edge')
        summary['semantic_corruption'] = dict(state='a.saved', cycle=26, signal='io_left',
                                               zero_edge_readback_words=22, acknowledged_edges=0, exit='nonzero')
    # Runtime handle/shape failures must terminate before any semantic deposit.
    stalled = out / "stalled"
    restore = (stalled / "restore.txt").read_text()
    bad_files = dict(missing_handle=restore.replace(".counter ", ".absent "),
                     wrong_width=restore.replace(".counter 9 ", ".counter 8 "),
                     malformed=restore + "truncated-row\n",
                     incomplete="\n".join(restore.splitlines()[:-1]) + "\n")
    for name, content in bad_files.items():
        file = out / f"{name}.restore.txt"
        file.write_text(content)
        result = run([stalled / "simv", f"+restore={file}", f"+waveform={out / (name + '.vcd')}"],
                     out / f"{name}.log", expected=None)
        require("RESTORE_ERROR" in result and "RESTORE: deposited" not in result, "bad restore partially deposited state")
    summary["restore_rejections"] = list(bad_files)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def verify_case(vcs, clean, manifest, boundary, case, expected=0,
                configuration="InventoryFixture-NoConfig-DefaultF2Config", post_replay_checks="",
                post_restore_checks="", monitor_edges=False):
    prepare_replay(manifest, boundary, configuration,
                   (case / "capture.rtlckpt").read_bytes(), (case / "capture.trace").read_bytes(), case)
    if post_restore_checks or monitor_edges:
        bench = case / 'replay.sv'
        source = bench.read_text()
        if post_restore_checks:
            first_input = sorted(p['name'] for p in boundary['ports']
                                 if p['direction'] == 'input' and p['name'] != 'clock')[0]
            marker = '  ' + first_input + ' = '
            require(marker in source, 'missing first replay input after complete readback')
            source = source.replace(marker, post_restore_checks + '\n' + marker, 1)
        if monitor_edges:
            require(source.count('initial begin') == 1, 'ambiguous semantic replay process')
            source = source.replace('initial begin',
                'always @(posedge clock) $display("ACKNOWLEDGED_TARGET_EDGE");\ninitial begin')
        bench.write_text(source)
    if post_replay_checks:
        bench = case / "replay.sv"
        source = bench.read_text()
        marker = '  $display("PASS: fresh clean RTL replay'
        require(source.count(marker) == 1, "missing replay completion marker")
        bench.write_text(source.replace(marker, post_replay_checks + "\n" + marker))
    run([vcs, "-full64", "-sverilog", "-debug_access+all", "+vpi", "-cc", os.environ["CC"],
         "-cpp", os.environ["CXX"], "-CFLAGS", f"-std=c++17 -I{os.environ['VCS_HOME']}/include",
         "-timescale=1ns/1ps", "-top", "semantic_replay_tb", f"-Mdir={case / 'csrc'}", "-o", case / "simv",
         clean, case / "replay.sv", ROOT / "tools/checkpoint_formats/semantic_restore.cc"], case / "build.log")
    result = run([case / "simv", f"+restore={case / 'restore.txt'}", f"+waveform={case / 'replay.vcd'}"],
                 case / "run.log", expected=expected)
    if expected == 0:
        require("PASS: fresh clean RTL replay" in result, "clean replay did not report PASS")
        require((case / "replay.vcd").stat().st_size > 0, "missing clean RTL waveform")
    return result


if __name__ == "__main__":
    main()
