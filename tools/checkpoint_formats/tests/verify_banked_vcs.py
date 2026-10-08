"""M3 explicit bank binding: VCS metasim public stream vs backdoor oracle.

Source both repository environments and vcs-env.sh LAST before running.
Diagnostics and generated bindings are written only under --out.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from tools.checkpoint_formats.banked import encode_banked, validate_binding
from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.replay import package_capture, prepare_capture, read_json, state_words
from tools.checkpoint_formats.semantic import decode_semantic, encode_semantic
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, verify_case


PORTS = ["start", "command", "startReady", "freeze", "done", "error", "cycle",
         "stream_valid", "stream_ready", "stream_bits_entry", "stream_bits_address",
         "stream_bits_bitWidth", "stream_bits_data", "stream_bits_error", "stream_bits_last"]
BEAT_PORTS = dict(entry="stream_bits_entry", address="stream_bits_address", width="stream_bits_bitWidth",
                  data="stream_bits_data", error="stream_bits_error", last="stream_bits_last")


def prepare_monitor(out):
    # The hardware collector sees only controller public ports. Direct semantic
    # references exist exclusively in the independent capture.sv oracle.
    widths = [1, 2, 1, 1, 1, 3, 64, 1, 1, 16, 32, 16, 64, 1, 1]
    fmt = '{"edge":%0d,"ports":[' + ','.join('"%h"' for _ in PORTS) + ']}'
    source = ["`timescale 1ps/1ps", "module banked_port_monitor(input wire clock,",
              ",\n".join(f"input wire [{w-1}:0] p{i}" for i, w in enumerate(widths)) + ");",
              "integer fd = 0; longint unsigned edge_index = 0; string path;",
              "initial begin",
              '  if ($value$plusargs("banked_ports=%s", path)) begin',
              '    fd = $fopen(path, "w"); if (!fd) $fatal(1, "Cannot open public port log");',
              "  end", "end", "always @(posedge clock) begin",
              f"  if (fd) begin $fdisplay(fd, {json.dumps(fmt)}, edge_index, " +
              ", ".join(f"p{i}" for i in range(len(PORTS))) + "); $fflush(fd); end",
              "  edge_index = edge_index + 1;", "end", "final if (fd) $fclose(fd);", "endmodule",
              "bind BankedStateAccess banked_port_monitor public_monitor(.clock(clock), " +
              ", ".join(f".p{i}(io_{name})" for i, name in enumerate(PORTS)) + ");"]
    (out / "ports.sv").write_text("\n".join(source) + "\n")


def verify_capture(manifest, boundary, fields, out, run_text):
    oracle = [json.loads(line) for line in (out / "capture.jsonl").read_text().splitlines()]
    # Retain all transfer edges for the detailed freeze/replay checks, and a
    # separate trace of actual semantic advances for clean target-cycle replay.
    edge_rows = [dict(cycle=row["cycle"], values=row["values"]) for row in oracle]
    (out / "edge-capture.jsonl").write_text("".join(json.dumps(row) + "\n" for row in edge_rows))
    events = [json.loads(line) for line in (out / "ports.jsonl").read_text().splitlines()]
    require(len(oracle) == len(events), "DUT/controller clocks do not share capture boundaries")
    values = []
    ports = []
    for edge, (row, event) in enumerate(zip(oracle, events)):
        require(row["cycle"] == event["edge"] == edge, "skipped/duplicated boundary")
        require(len(row["values"]) == len(fields) and len(event["ports"]) == len(PORTS), "log shape")
        require(all(re.fullmatch("[0-9a-f]+", value) for value in row["values"] + event["ports"]),
                "unknown/X/Z captured state or port")
        values.append({f["path"]: int(v, 16) for f, v in zip(fields, row["values"])})
        ports.append(dict(zip(PORTS, (int(v, 16) for v in event["ports"]))))
    words = list(state_words(manifest))
    semantic_paths = [w["path"] for w in words]
    require(len(words) == 22 and len(manifest["state"]) == 15, "unsupported fixture inventory")
    expected_paths = {"a.saved", "b.saved", "counter", "fsm", "bank_0", "bank_1", "bank_2",
                      "qValid", "qAddr", "busy", "delay", "pendingData", "responseValid", "responseData"}
    require(set(semantic_paths) == expected_paths | {f"sram[{i}]" for i in range(8)}, "unsupported fixture state")
    require([e["width"] for e in manifest["state"]] == [
        {"fsm": 2, "qValid": 1, "qAddr": 3, "busy": 1, "delay": 2, "responseValid": 1}.get(
            e["hierarchy"].split(".")[-1], 9) for e in manifest["state"]], "unsupported fixture widths")
    configuration = "InventoryBankedFixture-NoConfig-DefaultF2Config"
    snapshots = []
    current = None
    stalled_cycles = 0
    semantic_advances = 0
    captures = []
    for edge, (p, v) in enumerate(zip(ports, values)):
        require(oracle[edge]["semantic_cycle"] == semantic_advances, "oracle semantic cycle drifted")
        if p["start"] and p["startReady"] and p["command"] == 0:
            require(current is None and p["freeze"], "non-atomic capture acceptance")
            current = dict(edge=edge, values={k: v[k] for k in semantic_paths}, beats=[],
                           cycle=semantic_advances, stalls=0)
            require(v["counter"] == (semantic_advances - 5) % 512, "semantic cycle/counter disagreement")
            snapshots.append(current)
        if current:
            require(p["freeze"], "target resumed before final beat consumed")
            require({k: v[k] for k in semantic_paths} == current["values"], "semantic state changed during freeze")
            if edge > current["edge"]:
                require(p["cycle"] == current["cycle"], "captured semantic cycle drifted")
            if p["stream_valid"] and not p["stream_ready"]:
                current["stalls"] += 1
                stalled_cycles += 1
                next_p = ports[edge + 1]
                require(next_p["stream_valid"] and all(p[k] == next_p[k] for k in BEAT_PORTS.values()),
                        "stream changed under backpressure")
            if p["stream_valid"] and p["stream_ready"]:
                beat = {k: p[name] for k, name in BEAT_PORTS.items()}
                current["beats"].append(beat)
                if beat["last"]:
                    require(p["done"], "final beat missing completion")
                    captures.append(current)
                    current = None
        if not p["freeze"]:
            semantic_advances += 1
    require(current is None and len(captures) == 7, "missing captures or unfinished stream")
    require(captures[0]["values"] == captures[1]["values"] and captures[0]["cycle"] == captures[1]["cycle"],
            "immediate repeat capture advanced target state")
    require(captures[2]["values"]["qValid"] == 1, "queued capture empty")
    require(captures[3]["values"]["busy"] == 1 and captures[3]["values"]["delay"] == 2,
            "outstanding capture missing")
    require(captures[4]["values"]["responseValid"] == 1, "held response capture missing")
    require(any(p["error"] & 1 for p in ports) and any(p["error"] & 2 for p in ports)
            and any(p["error"] & 4 for p in ports), "missing error coverage")
    summary = dict(captures=[], target_semantic_advances=semantic_advances, transport_edges=len(events),
                   stalled_cycles=stalled_cycles, banks=4, semantic_entries=15, words=22,
                   physical_fpga_validated=False, automatic_compiler_binding=False)
    for index, capture in enumerate(captures):
        case = out / f"capture-{index}"
        case.mkdir(exist_ok=True)
        (case / "beats.json").write_text(json.dumps(capture, indent=2) + "\n")
        host = [dict(entry=int(e), address=int(a), width=int(w), data=int(d, 16), error=int(err), last=int(last))
                for e, a, w, d, err, last in re.findall(
                    rf"BANKED_WORD capture={index} entry=(\d+) address=(\d+) width=(\d+) data=([0-9a-f]+) error=(\d+) last=(\d+)",
                    run_text)]
        require(host == capture["beats"], "host port reads differ from actual handshakes")
        if index == 5:
            require(len(host) == 1 and host[0]["error"] == host[0]["last"] == 1, "bank failure did not terminate")
            try:
                encode_banked(manifest, configuration, capture["cycle"], host)
            except FormatError:
                pass
            else:
                raise AssertionError("incomplete error capture was accepted")
            summary["rejected_bank_error"] = index
            continue
        hardware = encode_banked(manifest, configuration, capture["cycle"], host)
        # Independently counted oracle semantic cycles include functional
        # reset and exclude every frozen edge, including request acceptance.
        ckpt, _ = package_capture(manifest, boundary, configuration, out / "edge-capture.jsonl",
                                  capture["edge"], 1, case / "oracle")
        ckpt["target_cycle"] = oracle[capture["edge"]]["semantic_cycle"]
        oracle_bytes = encode_semantic(ckpt, manifest)
        require(hardware == oracle_bytes, f"bit mismatch capture {index}")
        (case / "hardware.rtlckpt").write_bytes(hardware)
        (case / "oracle.rtlckpt").write_bytes(oracle_bytes)
        summary["captures"].append(dict(index=index, semantic_cycle=capture["cycle"], edge=capture["edge"],
                                        words=len(host), stalls=capture["stalls"],
                                        sha256=hashlib.sha256(hardware).hexdigest()))
    logical = [dict(cycle=row["semantic_cycle"], values=row["values"]) for row, p in zip(oracle, ports)
               if not p["freeze"]]
    require([row["cycle"] for row in logical] == list(range(semantic_advances)), "semantic trace has holes")
    (out / "semantic-capture.jsonl").write_text("".join(json.dumps(row) + "\n" for row in logical))
    return summary, captures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    require(str(vcs) == "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs", "source vcs-env.sh LAST")
    make = ["make", "DESIGN=InventoryBankedFixture", "TARGET_CONFIG=NoConfig", "PLATFORM_CONFIG=DefaultF2Config",
            "SEMANTIC_CHECKPOINT_ROOT=InventoryBankedFixture.dut", f"BUILD_DIR={build}"]
    sim_dir = ROOT / "sims/firesim/sim"
    run(make + ["verilog"], out / "verilog.log", sim_dir)
    generated = build / "f2/f2-midasexamples-InventoryBankedFixture-NoConfig-DefaultF2Config"
    base = generated / "FireSim-generated"
    manifest = read_json(str(base) + ".semantic-state.json")
    boundary = read_json(str(base) + ".semantic-boundary.json")
    validate_binding(manifest, read_json(str(base) + ".semantic-access.json"))
    clean = Path(str(base) + ".semantic-clean.sv")
    fields = prepare_capture(manifest, boundary, clean.read_text(), Path(str(base) + ".sv").read_text(), out,
                             freeze_port="io_checkpoint_freeze")
    prepare_monitor(out)
    # VCS's cached external-C Makefile does not include entry.d. entry.cc
    # embeds the generated bridge registry; keep it synchronized with changed
    # ports when reusing a build. Invalidate only the stale generated object.
    registry_object = generated / "InventoryBankedFixture-debug.csrc/entry.o"
    if registry_object.exists() and registry_object.stat().st_mtime_ns < Path(str(base) + ".const.h").stat().st_mtime_ns:
        registry_object.unlink()
        (out / "registry-rebuild.log").write_text("Invalidated stale generated entry.o after bridge header changed\n")
    run(make + ["vcs", f"VCS={vcs} -full64", "VCS_FLAGS=-Mupdate",
                f"VCS_EXTRA_V={out / 'capture.sv'} {out / 'ports.sv'}"], out / "vcs-build.log", sim_dir)
    result = run([generated / "InventoryBankedFixture", "+vcs+initreg+0", "+vcs+initmem+0",
                  f"+semantic_capture={out / 'capture.jsonl'}", f"+banked_ports={out / 'ports.jsonl'}"],
                 out / "metasim-run.log")
    require("*** PASSED ***" in result, "banked fixture failed")
    summary, captures = verify_capture(manifest, boundary, fields, out, result)
    # A fresh clean-DUT process checks every transfer-clock boundary too.
    # This auxiliary replay labels rows by transport edge, independently of
    # the unchanged .rtlckpt semantic-cycle metadata checked above.
    case = out / "clean-replay"
    ckpt, trace = package_capture(manifest, boundary, "InventoryBankedFixture-NoConfig-DefaultF2Config",
                                  out / "edge-capture.jsonl", captures[4]["edge"],
                                  summary["transport_edges"] - captures[4]["edge"], case)
    # Replay with original edge-index metadata; values came from public hardware
    # ports and are already proven equal to the complete independent oracle.
    hardware = (out / "capture-4/hardware.rtlckpt").read_bytes()
    doc = decode_semantic(hardware, ckpt["build"], manifest)
    doc["target_cycle"] = ckpt["target_cycle"]
    (case / "capture.rtlckpt").write_bytes(encode_semantic(doc, manifest))
    invalid = [(4, 0, 0), (0, 12, 0), (0, 0, 1), (1, 1, 0),
               (2, 0, 1), (3, 1, 0), (3, 0, 8), (3, 0, 0xffffffff)]
    checks = ["  io_checkpoint_freeze = 1; reset = 0;"]
    for bank, slot, address in invalid:
        checks += [f"  io_checkpoint_bank_bank = 8'd{bank}; io_checkpoint_bank_slot = 16'd{slot};",
                   f"  io_checkpoint_bank_address = 32'd{address}; #1;",
                   '  if (io_checkpoint_bank_error !== 1 || io_checkpoint_bank_data !== 0) ' +
                   f'semantic_fail("INVALID_BANK_READ bank={bank} slot={slot} address={address}");']
    verify_case(vcs, clean, manifest, boundary, case,
                configuration="InventoryBankedFixture-NoConfig-DefaultF2Config",
                post_replay_checks="\n".join(checks))
    summary["clean_replay_samples"] = len(trace["records"])
    summary["invalid_client_reads_rejected"] = len(invalid)
    # Normal semantic replay uses the actual hardware file without changing
    # its cycle metadata and skips transfer edges which cannot advance the DUT.
    semantic = out / "semantic-replay"
    cycle = captures[4]["cycle"]
    ckpt, trace = package_capture(manifest, boundary, "InventoryBankedFixture-NoConfig-DefaultF2Config",
                                  out / "semantic-capture.jsonl", cycle,
                                  summary["target_semantic_advances"] - cycle, semantic)
    require((semantic / "capture.rtlckpt").read_bytes() == hardware, "resumed semantic boundary changed state")
    verify_case(vcs, clean, manifest, boundary, semantic,
                configuration="InventoryBankedFixture-NoConfig-DefaultF2Config")
    summary["semantic_replay_samples"] = len(trace["records"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("PASS: banked public-port extraction equals complete backdoor oracle")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
