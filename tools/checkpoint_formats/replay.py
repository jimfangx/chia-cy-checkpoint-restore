"""VCS Level-2 oracle for single-instance, hierarchy-preserving DUTs.

Capture is on actual gated DUT rising edges, in the active region before NBA
state updates. Row C contains S[C], I[C], O[C] before edge C. Host/model
stalls produce no rows. This backend explicitly rejects renamed/threaded state;
it does not implement a general mapping through FAME or an FPGA transport.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from .codec import canonical, decode, encode, keys, require, bit_value
from .semantic import decode_semantic, encode_semantic, manifest_hash, validate_manifest, PLUSARG_MODEL_SHA256


IDENT = r"[A-Za-z_][A-Za-z0-9_$]*"
RANGE = r"(?:\[(\d+):0\]\s*)?"


def read_json(path):
    return json.loads(Path(path).read_text())


def boundary_ports(boundary):
    keys(boundary, {"boundary_version", "dut_module", "dut_root", "clock", "sample_phase", "ports"})
    require(type(boundary["boundary_version"]) is int and boundary["boundary_version"] == 1
            and boundary["sample_phase"] == "before_rising_edge",
            "unsupported boundary schema/phase")
    require(boundary["clock"] == "clock", "oracle supports only the clock port")
    require(re.fullmatch(IDENT, boundary["dut_module"]), "invalid DUT module")
    ports = boundary["ports"]
    require(type(ports) is list and ports, "empty boundary")
    for port in ports:
        keys(port, {"name", "direction", "width"})
        require(re.fullmatch(IDENT, port["name"]) and port["direction"] in ("input", "output")
                and type(port["width"]) is int and port["width"] > 0, "unsupported boundary port")
    require(len({p["name"] for p in ports}) == len(ports), "duplicate boundary port")
    require([p for p in ports if p["name"] == "clock"] ==
            [dict(name="clock", direction="input", width=1)], "invalid boundary clock")
    return sorted((p for p in ports if p["name"] != "clock"), key=lambda p: p["name"])


def state_words(manifest):
    for entry in manifest["state"]:
        relative = entry["hierarchy"][len(manifest["dut_root"]) + 1:]
        for address in range(entry["depth"]):
            path = relative + (f"[{address}]" if entry["kind"] == "memory" else "")
            yield dict(path=path, width=entry["width"], state_id=entry["state_id"], address=address)


def modules(text):
    # Deliberately restricted to FIRRTL emitter syntax. Unsupported syntax fails
    # the complete port/state membership checks instead of guessing a mapping.
    text = re.sub(r"//[^\n]*", "", text)
    return {name: (header, body) for name, header, body in re.findall(
        rf"module\s+({IDENT})\s*\((.*?)\);(.*?)endmodule", text, re.S)}


def inventory_rtl(mods, module, prefix="", *, external=None, visited=None):
    require(module in mods, f"missing concrete RTL module {module}")
    header, body = mods[module]
    result = {}
    for high, name, depth_high in re.findall(
            rf"\breg\s+{RANGE}({IDENT})\s*(?:\[0:(\d+)\])?\s*;", body):
        if name.startswith("_RAND_"):
            continue
        result[prefix + name] = (int(high) + 1 if high else 1,
                               int(depth_high) + 1 if depth_high else 1,
                               "memory" if depth_high else "register")
    for child_module, instance in re.findall(rf"^[ \t]*({IDENT})[ \t]+({IDENT})[ \t]*\(", body, re.M):
        result.update(inventory_rtl(mods, child_module, prefix + instance + ".", external=external, visited=visited))
    parameterized = list(re.finditer(rf"\b({IDENT})\s*#\((.*?)\)\s+({IDENT})\s*\(", body, re.S))
    require(len(parameterized) == len(re.findall(rf"\b{IDENT}\s*#\s*\(", body)),
            "unsupported parameterized semantic instance syntax")
    for match in parameterized:
        child, parameters, instance = match.groups()
        owner = prefix + instance
        require(child == "plusarg_reader" and external is not None and owner in external,
                "unadapted parameterized semantic instance")
        pattern = r'\.(DEFAULT|FORMAT|WIDTH)\(\s*("[A-Za-z_][A-Za-z0-9_]*=%[dbh]"|[0-9]+)\s*\)'
        values = re.findall(pattern, parameters)
        require(len(values) == 3 and len(dict(values)) == 3 and
                not re.sub(pattern, '', parameters).replace(',', '').strip(), "unsupported semantic plusarg parameters")
        values = dict(values)
        model = external[owner]
        require((int(values["WIDTH"]), int(values["DEFAULT"]), json.loads(values["FORMAT"])) ==
                (model["width"], model["default"], model["format"]), "emitted semantic plusarg specialization mismatch")
        require(owner not in visited and owner + ".myplus" not in result, "duplicate semantic plusarg instance")
        visited.add(owner)
        result[owner + ".myplus"] = (model["width"], 1, "register")
    return result


def audit_semantic_rtl(manifest, module, text):
    """Audit emitter declarations and exact non-SYNTHESIS external models.

    The source model is bound separately from the FIRRTL reference; matching an
    instance name or DEFAULT cannot establish complete external state ownership.
    """
    external = {m["hierarchy"][len(manifest["dut_root"]) + 1:]: m
                for m in manifest.get("external_models", [])}
    if external:
        model = (Path(__file__).resolve().parents[2] /
                 "generators/rocket-chip/src/main/resources/vsrc/plusarg_reader.v").read_text()
        require(hashlib.sha256(model.encode()).hexdigest() == PLUSARG_MODEL_SHA256 and text.count(model) == 1,
                "missing/duplicate/altered semantic plusarg model")
        require(not re.search(r"^\s*`define\s+SYNTHESIS\b", text, re.M),
                "semantic plusarg adapter requires non-SYNTHESIS RTL")
        text = text.replace(model, "")
    mods = modules(text)
    visited = set()
    actual = inventory_rtl(mods, module, external=external, visited=visited)
    require(visited == set(external), "incomplete emitted semantic plusarg ownership")
    return mods, actual


def prepare_capture(manifest, boundary, clean_text, transformed_text, out, freeze_port=None):
    validate_manifest(manifest)
    ports = boundary_ports(boundary)
    if freeze_port is not None:
        require(dict(name=freeze_port, direction="input", width=1) in ports, "invalid freeze boundary port")
    require(boundary["dut_root"] == manifest["dut_root"], "DUT boundary root mismatch")
    require(manifest["clock_domain"] == manifest["dut_root"] + ".clock", "unsupported oracle clock domain")
    expected = {e["hierarchy"][len(manifest["dut_root"]) + 1:]:
                (e["width"], e["depth"], e["kind"]) for e in manifest["state"]}
    module = boundary["dut_module"]
    for text in (clean_text, transformed_text):
        mods, actual = audit_semantic_rtl(manifest, module, text)
        require(actual == expected,
                "unsupported/lost/extra/reshaped semantic RTL state mapping")
        actual_ports = [dict(direction=d, width=int(h) + 1 if h else 1, name=n)
                        for d, h, n in re.findall(rf"\b(input|output)\s+{RANGE}({IDENT})", mods[module][0])]
        require(sorted(actual_ports, key=lambda p: p["name"]) ==
                sorted(boundary["ports"], key=lambda p: p["name"]), "RTL boundary mapping mismatch")
    # A module-wide bind is safe only for one instance in this oracle prototype.
    require(len(re.findall(rf"\b{module}\s+{IDENT}\s*\(", transformed_text)) == 1,
            "oracle requires exactly one unthreaded DUT instance")
    words = list(state_words(manifest))
    fields = [dict(path=p["name"], width=p["width"]) for p in ports] + words
    declarations = [f"input wire [{f['width'] - 1}:0] f{i}" for i, f in enumerate(fields)]
    arguments = [f".f{i}({f['path']})" for i, f in enumerate(fields)]
    fmt = '{"cycle":%0d,"values":[' + ','.join('"%h"' for _ in fields) + ']}'
    if freeze_port is not None:
        fmt = fmt[:-1] + ',"semantic_cycle":%0d}'
    freeze_index = next((i for i, f in enumerate(fields) if f["path"] == freeze_port), None)
    source = ["`timescale 1ps/1ps", "module semantic_capture_oracle(input wire clock,",
              ",\n".join(declarations) + ");", "integer fd = 0;", "longint unsigned cycle = 0;",
              "longint unsigned semantic_cycle = 0;", "string filename;", "initial begin",
              '  if ($value$plusargs("semantic_capture=%s", filename)) begin',
              '    fd = $fopen(filename, "w");',
              '    if (!fd) $fatal(1, "Cannot open semantic capture");', "  end", "end",
              "always @(posedge clock) begin", "  if (fd) begin",
              f"    $fdisplay(fd, {json.dumps(fmt)}, cycle, " +
              ", ".join(f"f{i}" for i in range(len(fields))) +
              (", semantic_cycle" if freeze_port is not None else "") + ");",
              "    $fflush(fd);", "  end", "  cycle = cycle + 1;",
              (f"  if (!f{freeze_index}) semantic_cycle = semantic_cycle + 1;" if freeze_port is not None else ""), "end",
              "final if (fd) $fclose(fd);", "endmodule",
              f"bind {module} semantic_capture_oracle semantic_oracle(.clock(clock), " +
              ", ".join(arguments) + ");"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "capture.sv").write_text("\n".join(source) + "\n")
    (out / "capture-layout.json").write_bytes(canonical(fields))
    return fields


def builds(manifest, boundary, configuration):
    common = dict(target_configuration=configuration, rtl_build_hash=manifest["reference_sha256"])
    return (dict(common, state_manifest_hash=manifest_hash(manifest)),
            dict(common, boundary_manifest_hash=hashlib.sha256(canonical(boundary)).hexdigest()))


def package_capture(manifest, boundary, configuration, raw, start, length, out):
    validate_manifest(manifest)
    ports = boundary_ports(boundary)
    require(boundary["dut_root"] == manifest["dut_root"], "DUT boundary root mismatch")
    require(manifest["clock_domain"] == manifest["dut_root"] + ".clock", "unsupported oracle clock domain")
    words = list(state_words(manifest))
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    for cycle, row in enumerate(rows):
        keys(row, {"cycle", "values"})
        require(row["cycle"] == cycle, "capture skipped/duplicated target edge")
        require(len(row["values"]) == len(ports) + len(words), "capture shape mismatch")
    require(start >= 0 and length > 0 and start + length <= len(rows), "trace outside captured edges")
    for row in rows[start:start + length]:
        for field, value in zip(ports + words, row["values"]):
            bit_value(dict(width=field["width"], value=value))
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    values = iter(rows[start]["values"][len(ports):])
    ckpt = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=start,
                target_clock_phase="before_rising_edge", build=rtl_build,
                records=[dict(state_id=e["state_id"], width=e["width"], depth=e["depth"],
                              values=[next(values) for _ in range(e["depth"])]) for e in manifest["state"]])
    records = []
    for row in rows[start:start + length]:
        record = dict(cycle=row["cycle"], inputs={}, outputs={})
        for port, value in zip(ports, row["values"]):
            record[port["direction"] + "s"][port["name"]] = dict(width=port["width"], value=value)
        records.append(record)
    trace = dict(format_version=1, checkpoint_type="trace", target_cycle=start,
                 target_clock_phase="before_rising_edge", build=trace_build, records=records)
    out.mkdir(parents=True, exist_ok=True)
    (out / "capture.rtlckpt").write_bytes(encode_semantic(ckpt, manifest))
    (out / "capture.trace").write_bytes(encode("trace", trace))
    return ckpt, trace


def prepare_replay(manifest, boundary, configuration, ckpt_data, trace_data, out):
    ports = boundary_ports(boundary)
    require(boundary["dut_root"] == manifest["dut_root"], "DUT boundary root mismatch")
    require(manifest["clock_domain"] == manifest["dut_root"] + ".clock", "unsupported oracle clock domain")
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    ckpt = decode_semantic(ckpt_data, rtl_build, manifest)
    trace = decode(trace_data, "trace", trace_build)
    require(ckpt["target_cycle"] == trace["target_cycle"] and trace["records"], "checkpoint/trace cycle mismatch")
    for record in trace["records"]:
        for direction in ("input", "output"):
            require({k: v["width"] for k, v in record[direction + "s"].items()} ==
                    {p["name"]: p["width"] for p in ports if p["direction"] == direction},
                    "incomplete, unknown, or wrong-width boundary signals")
    restore = []
    records = {r["state_id"]: r for r in ckpt["records"]}
    for word in state_words(manifest):
        value = records[word["state_id"]]["values"][word["address"]]
        restore.append(f"semantic_replay_tb.dut.{word['path']} {word['width']} {value}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "restore.txt").write_text("\n".join(restore) + "\n")
    source = ["`timescale 1ns/1ps", "module semantic_replay_tb;",
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function void semantic_fail(input string message);', "reg clock = 0;"]
    for port in ports:
        source.append(f"{'reg' if port['direction'] == 'input' else 'wire'} [{port['width'] - 1}:0] {port['name']};")
    source += [boundary["dut_module"] + " dut(.clock(clock), " +
               ", ".join(f".{p['name']}({p['name']})" for p in ports) + ");", "string restore_path, waveform;",
               "initial begin", '  if (!$value$plusargs("restore=%s", restore_path)) semantic_fail("Missing restore path");',
               '  if (!$value$plusargs("waveform=%s", waveform)) semantic_fail("Missing waveform path");',
               "  $dumpfile(waveform); $dumpvars(0, semantic_replay_tb);",
               f'  #1; if (semantic_restore(restore_path, {len(restore)})) semantic_fail("RESTORE_ERROR before first DUT edge");', "  #1;"]
    # Verify every deposited register and memory word before the first DUT edge.
    for word, line in zip(state_words(manifest), restore):
        value = line.split()[2]
        source.append(f"  if (dut.{word['path']} !== {word['width']}'h{value}) " +
                      f'semantic_fail("RESTORE_MISMATCH cycle={ckpt["target_cycle"]} signal={word["path"]}");')
    for record in trace["records"]:
        for signal, value in sorted(record["inputs"].items()):
            source.append(f"  {signal} = {value['width']}'h{value['value']};")
        source.append("  #1;")
        for signal, value in sorted(record["outputs"].items()):
            source.append(f"  if ({signal} !== {value['width']}'h{value['value']}) " +
                          f'semantic_fail($sformatf("FIRST_MISMATCH cycle={record["cycle"]} signal={signal} expected=%h actual=%h", ' +
                          f"{value['width']}'h{value['value']}, {signal}));")
        source.append("  clock = 1; #1; clock = 0; #1;")
    source += [f'  $display("PASS: fresh clean RTL replay cycles={trace["target_cycle"]}..{trace["records"][-1]["cycle"]} samples={len(trace["records"])} outputs_per_cycle={sum(p["direction"] == "output" for p in ports)} restored_words={len(restore)}");',
               "  $finish;", "end", "endmodule"]
    (out / "replay.sv").write_text("\n".join(source) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "package", "replay"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--configuration", default="InventoryFixture-NoConfig-DefaultF2Config")
    parser.add_argument("--clean", type=Path)
    parser.add_argument("--transformed", type=Path)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--cycle", type=int)
    parser.add_argument("--length", type=int)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    manifest, boundary = read_json(args.manifest), read_json(args.boundary)
    if args.action == "capture":
        prepare_capture(manifest, boundary, args.clean.read_text(), args.transformed.read_text(), args.out)
    elif args.action == "package":
        package_capture(manifest, boundary, args.configuration, args.raw, args.cycle, args.length, args.out)
    else:
        prepare_replay(manifest, boundary, args.configuration, args.checkpoint.read_bytes(), args.trace.read_bytes(), args.out)
    print(f"PASS: {args.action} validated; artifacts in {args.out.resolve()}")


if __name__ == "__main__":
    main()
