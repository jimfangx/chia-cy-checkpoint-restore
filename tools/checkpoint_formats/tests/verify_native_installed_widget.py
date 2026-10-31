"""Verify the selected FireSim native widget, retaining its image-admission guard.

This is a transport component check, never an FPGA checkpoint or CPU migration.
Native synthesis runs on the manager; all VCS execution runs on EDA. The bench
reuses the independent original-register, complete-shadow and first-fault
oracles of the endpoint regression through explicitly recorded port adapters.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_native_widget_endpoint as base
from tools.checkpoint_formats.tests import verify_native_bound_endpoint as bound

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
TOP = "CheckpointCaptureWidget"
ENDPOINT = "dut.nativeEndpoint.endpoint"
WIDGET = "widget/native-widget/"
PROBE = "widget/native-endpoint/CheckpointNativeEndpointLayoutProbe/CheckpointNativeEndpointLayoutProbe.v"
FILES = (WIDGET + TOP + ".v", *(WIDGET + n for n in base.RESOURCES),
         *(WIDGET + n for n in ("manifest.json", "binding.json", "manifest.inc", "constants.h",
                               "endpoint-observation.json")),
         "widget/native-binding/constants.h", PROBE)
SOURCES = tuple(dict.fromkeys((*bound.SOURCES, "tools/checkpoint_formats/tests/verify_native_installed_widget.py",
    "tools/checkpoint_formats/tests/test_native_installed_widget.py",
    "sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureNativeWidgetSpec.scala")))
sha = base.sha


def bench(text, manifest_hash):
    # The original bench observes a concrete native endpoint, while its public
    # transactions now address the actual selected Widget. Preserve all checks.
    require(text.count(".io_endpointState(") == 1, "ambiguous endpoint observation port")
    text, adaptation = bound.bench(text, manifest_hash)
    changes = [
        (bound.TOP + " dut(", TOP + " dut(", "selected_widget"),
        ("dut.endpoint.", ENDPOINT + ".", "native_endpoint_hierarchy"),
        ("dut.originalROM.", "dut.nativeEndpoint.originalROM.", "internal_original_rom"),
        (".io_endpointState(endpoint_state)", ".capture_native_endpointState(endpoint_state)", "endpoint_observation"),
    ]
    ports = {
        "io_stream_valid": "streamToHostCPU_valid", "io_stream_ready": "streamToHostCPU_ready",
        "io_stream_bits": "streamToHostCPU_bits", "io_streamLast": "capture_streamLast",
        "io_streamAbort": "capture_streamAbort", "io_native_ce": "capture_physical_logicalCE",
        "io_native_targetCycle": "capture_targetCycle", "io_native_ownerPresent": "capture_ownerPresent",
        "io_native_ownerFrozen": "capture_ownerFrozen", "io_native_ownerError": "capture_ownerError",
        "io_native_readerIdle": "capture_native_readerIdle", "io_native_liveState": "capture_native_liveState",
        "io_native_clockMask": "capture_physical_clockMask", "io_native_freeze": "capture_freeze",
        "io_native_functionalHold": "capture_native_functionalHold", "io_native_valid": "capture_physical_stopped",
        "io_native_failed": "capture_physical_failed", "io_native_cutCycle": "capture_physical_cutCycle",
        "io_native_capturedCE": "capture_physical_capturedCE", "io_native_snapshotState": "capture_native_snapshotState",
        "io_native_rawControlState": "capture_native_rawControlState",
        "io_native_nativeControlBankState": "capture_native_nativeControlBankState",
        "io_native_endpointControlState": "capture_native_endpointControlState",
        **{"io_" + n: "capture_" + n for n in ("descriptorEntry", "bankRequestValid", "bankRequestReady",
             "bank", "slot", "address", "bankResponseValid", "bankResponseReady", "bankResponseData", "bankResponseError")},
    }
    changes += [("." + a + "(bank)" if a == "io_bank" else "." + a + "(",
                 "." + b + "(bank)" if a == "io_bank" else "." + b + "(", "port_" + a)
                for a, b in ports.items()]
    changes += [
        (".io_native_rootClock(unused_root),.io_native_gateClock(unused_gates),", "", "inactive_clock_outputs"),
        (".capture_descriptorEntry(descriptor_entry),", ".capture_descriptorEntry(descriptor_entry),\n"
         "    .capture_descriptorValid(1'b0),.capture_descriptorBank(8'd99),.capture_descriptorSlot(16'd99),\n"
         "    .capture_descriptorWidth(16'd99),.capture_descriptorDepth(32'd99),", "poison_ignored_descriptor_inputs"),
        ("wire [3:0] bid,rid;", "wire [11:0] bid,rid;", "real_f2_response_id_width"),
        (".io_ctrl_aw_bits_id(4'd3)", ".io_ctrl_aw_bits_id(12'hfa3)", "real_f2_high_write_id"),
        (".io_ctrl_w_bits_id(4'd0)", ".io_ctrl_w_bits_id(12'd0)", "real_f2_write_data_id_width"),
        (".io_ctrl_ar_bits_id(4'd7)", ".io_ctrl_ar_bits_id(12'hb07)", "real_f2_high_read_id"),
    ]
    steps = adaptation["transformations"]
    for before, after, label in changes:
        count = text.count(before)
        require(count > 0 and (label in ("native_endpoint_hierarchy", "internal_original_rom") or count == 1),
                "ambiguous installed widget bench adaptation " + label)
        text = text.replace(before, after)
        steps.append(dict(label=label, before=before, after=after, occurrences=count))
    for before, after, expected, label in (("bid==3", "bid==12'hfa3", 2, "complete_write_id_oracle"),
            ("rid==7", "rid==12'hb07", 2, "complete_read_id_oracle"),
            ("60'b0", "52'b0", 4, "independent_64bit_canonical_id_slots")):
        require(text.count(before) == expected, "changed original ID oracle " + label)
        text = text.replace(before, after)
        steps.append(dict(label=label, before=before, after=after, occurrences=expected))
    return text, dict(adaptation, transformations=steps)


def generated_metadata(directory, sources):
    for name in FILES:
        p = directory / name
        require(p.is_file() and not p.is_symlink() and p.stat().st_size > 0,
                "missing emitted widget input " + name)
    for name in base.RESOURCES:
        require(sha(directory / WIDGET / name) == sources[base.PREFIX + name],
                "native widget resource differs from source " + name)
    # Reuse the independent canonical StateID/selector/provenance reconstruction
    # with the separately emitted native-only header, preserving the full header.
    with tempfile.TemporaryDirectory() as temporary:
        view = Path(temporary) / bound.BOUND
        view.mkdir()
        for name in ("manifest.json", "binding.json", "manifest.inc"):
            shutil.copyfile(directory / WIDGET / name, view / name)
        shutil.copyfile(directory / "widget/native-binding/constants.h", view / "constants.h")
        metadata = bound.validate_descriptors(Path(temporary), sources)
    header = (directory / WIDGET / "constants.h").read_text()
    require("#error Incomplete_checkpoint_hardware_coverage" in header and
            "checkpoint_native_capture_binding_t{1U, 130U, 3U, 2U, 1U, 252U, 251U, 2U, 1585U}" in header and
            "registry.get_stream_engine()," in header and
            (directory / WIDGET / "manifest.inc").read_text() in header,
            "installed header loses native identity, safe installation or image guard")
    return metadata


def validate_scala(receipt, generated):
    doc = json.loads(receipt.read_text())
    require(doc.get("status") == "pass" and doc.get("returncode") == 0 and doc.get("backend") == "f2",
            "complete successful native Scala receipt required")
    phases = doc.get("phases", [])
    require(len(phases) == 3 and all(p.get("passed") is True and p.get("tests", 0) > 0 and
        p.get("tests") == p.get("succeeded") and all(p.get(n) == 0 for n in
            ("aborted", "failed", "canceled", "ignored", "pending")) for p in phases),
            "complete three-phase Scala suite required")
    origin = local(ROOT, doc["generated"])
    require(origin.resolve() == generated.resolve() == (receipt.parent / "generated").resolve() and
            generated.resolve().is_relative_to(receipt.parent.resolve()), "wrong Scala generated directory")
    require(sha(local(ROOT, doc["log"])) == doc["log_sha256"] and
            sha(receipt.parent / "run.sh") == doc["script_sha256"], "Scala log/script identity changed")
    sources = doc.get("sources", {})
    require(sources and all(sha(ROOT / n) == h for n, h in sources.items()), "Scala sources changed")
    for n in SOURCES:
        if n.endswith(".scala"):
            require(sources.get(n) == sha(ROOT / n), "Scala receipt omits current widget source " + n)
    emitted = doc.get("generated_files", {})
    require(isinstance(emitted, dict) and set(FILES).issubset(emitted),
            "Scala receipt omits emitted widget hashes")
    for n in FILES:
        p = generated / n
        require(p.is_file() and not p.is_symlink() and p.stat().st_size > 0 and
                p.resolve().is_relative_to(generated.resolve()) and sha(p) == emitted[n],
                "emitted Scala widget bytes changed " + n)
    require("NATIVE_CAPTURE_WIDGET_ELABORATED" in local(ROOT, doc["log"]).read_text(),
            "actual selected widget not elaborated")
    return doc


def validate_native(path, sources, inputs, scala_sha256):
    """Authenticate synthesis execution and its exact DCP, logs and inputs."""
    doc = json.loads(path.read_text())
    require(doc.get("status") == "pass" and doc.get("backend") == "f2" and
            doc.get("sources") == sources and doc.get("inputs") == inputs and
            doc.get("scala", {}).get("sha256") == scala_sha256 and
            doc.get("physical_fpga_capture") is False and doc.get("full_image") is False and
            doc.get("complete_state_ownership") is False, "native synthesis receipt is stale or incomplete")
    artifacts = doc.get("artifacts", {})
    required = {"native.log", "version.log", "native.tcl", "commands.json", "installed-native-widget.dcp",
                "utilization.rpt", "timing.rpt", "BUFGCE.v", "glbl.v", "installed-bench.sv", "bench-adaptation.json"}
    required.update("generated/" + n for n in FILES)
    require(isinstance(artifacts, dict) and required.issubset(artifacts), "native receipt omits required artifacts")
    for name, digest in artifacts.items():
        p = path.parent / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and
                p.resolve().is_relative_to(path.parent.resolve()) and not p.is_symlink() and
                p.is_file() and p.stat().st_size > 0 and sha(p) == digest, "native artifact hash mismatch " + name)
    require((path.parent / "native.tcl").read_text() == tcl(), "native synthesis recipe differs")
    commands = doc.get("commands", [])
    require(isinstance(commands, list) and len(commands) == 2 and
            json.loads((path.parent / "commands.json").read_text()) == commands,
            "native synthesis execution ledger differs")
    for row, argv, log in zip(commands, (["vivado", "-mode", "batch", "-source", "native.tcl"],
                                       ["vivado", "-version"]), ("native.log", "version.log")):
        require(row.get("argv") == argv and row.get("returncode") == 0 and
                local(ROOT, row.get("cwd", "")).resolve() == path.parent.resolve() and
                local(ROOT, row.get("log", "")).resolve() == (path.parent / log).resolve() and
                row.get("log_sha256") == artifacts[log], "native tool command/log proof differs")
    text = (path.parent / "native.log").read_text()
    require(re.search(r"(?im)^vivado v2025\.2 \(64-bit\)", (path.parent / "version.log").read_text()),
            "native synthesis version differs from required F2 Vivado 2025.2")
    registers = re.search(r"INSTALLED_NATIVE_SYNTH_PASS bank_bits=67 registers=(\d+)", text)
    timing = re.search(r"INSTALLED_NATIVE_TIMING setup_ns=([-+\d.]+) hold_ns=([-+\d.]+) period_ns=7.142857", text)
    require(registers and int(registers[1]) >= 2400 and timing and
            all(float(v) >= 0 for v in timing.groups()) and not re.search(r"ERROR:|CRITICAL WARNING:", text),
            "native synthesis/timing execution did not pass")
    require(doc.get("timing", {}).get("frequency_mhz") == 140 and
            doc["timing"].get("setup_ns") == float(timing[1]) and
            doc["timing"].get("hold_ns") == float(timing[2]), "native timing receipt differs from tool log")
    require(set(doc.get("vendor_models", {})) == {"BUFGCE.v", "glbl.v"} and
            all(doc["vendor_models"][n] == artifacts[n] for n in doc["vendor_models"]), "missing vendor identities")
    require(all(artifacts["generated/" + n] == h for n, h in inputs.items()), "native generated inputs differ")
    return doc


def tcl():
    return """set_param general.maxThreads 4
read_verilog generated/""" + WIDGET + TOP + ".v\nread_verilog -sv " + " ".join(
        "generated/" + WIDGET + n for n in base.RESOURCES) + """
synth_design -top CheckpointCaptureWidget -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy rebuilt
create_clock -name raw_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME =~ BUFG*}]] != 0} {error "duplicate physical clock network"}
set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] < 2400} {error "missing selected native widget state"}
set bank_drivers {}
for {set i 0} {$i < 67} {incr i} {
  set port [get_ports [format {capture_native_nativeControlBankState[%d]} $i]]
  set driver [get_pins -leaf -of_objects [get_nets -of_objects $port] -filter {DIRECTION == OUT}]
  if {[llength $driver] != 1 || [get_property REF_PIN_NAME $driver] ne "Q" ||
      ![string match FD* [get_property REF_NAME [get_cells -of_objects $driver]]]} {error "missing native bank driver $i"}
  lappend bank_drivers [get_property NAME $driver]
}
if {[llength [lsort -unique $bank_drivers]] != 67} {error "aliased native response bank"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {error "missing timing paths"}
puts "INSTALLED_NATIVE_TIMING setup_ns=[get_property SLACK $setup] hold_ns=[get_property SLACK $hold] period_ns=7.142857"
if {[get_property SLACK $setup] < 0 || [get_property SLACK $hold] < 0} {error "selected widget misses unchanged 140 MHz timing"}
write_checkpoint -force installed-native-widget.dcp
puts "INSTALLED_NATIVE_SYNTH_PASS bank_bits=67 registers=[llength $registers]"
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--scala", type=Path, required=True)
    parser.add_argument("--native", type=Path, help="successful manager synthesis receipt for VCS")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence must be beneath runs")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    receipt = local(ROOT, str(args.scala)).resolve()
    require(receipt.is_relative_to(RUNS), "Scala receipt must be beneath runs")
    sources = {n: sha(ROOT / n) for n in SOURCES}
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda",
        observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT), sources=sources,
        scope="actual installed native transport component only; no FPGA image, atomic owners or CPU migration",
        physical_fpga_capture=False, full_image=False, complete_state_ownership=False, commands=[])
    print(out, flush=True)

    def run(argv, label, cwd=out, expected=0):
        log = cwd / (label + ".log")
        with log.open("x") as stream:
            result = subprocess.run(list(map(str, argv)), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        doc["commands"].append(dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log),
                                    log_sha256=sha(log), returncode=result.returncode))
        (out / "commands.json").write_text(json.dumps(doc["commands"], indent=2) + "\n")
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + str(log))
        return log.read_text()

    try:
        scala = json.loads(receipt.read_text())
        generated = local(ROOT, scala["generated"])
        validate_scala(receipt, generated)
        doc["scala"] = dict(path=str(receipt), sha256=sha(receipt))
        doc["metadata"] = generated_metadata(generated, sources)
        frozen = out / "generated"
        for name in FILES:
            dest = frozen / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(generated / name, dest)
        doc["inputs"] = {n: sha(frozen / n) for n in FILES}
        text, adaptation = bench((ROOT / base.TB).read_text(), doc["metadata"]["manifest_sha256"])
        (out / "installed-bench.sv").write_text(text)
        (out / "bench-adaptation.json").write_text(json.dumps(adaptation, indent=2) + "\n")
        rtl = frozen / WIDGET / (TOP + ".v")
        if args.mode == "vivado":
            require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),
                    "native Vivado manager required")
            (out / "native.tcl").write_text(tcl())
            log = run(["vivado", "-mode", "batch", "-source", "native.tcl"], "native")
            require("INSTALLED_NATIVE_SYNTH_PASS" in log and not re.search(r"ERROR:|CRITICAL WARNING:", log),
                    "installed widget native synthesis incomplete")
            match = re.search(r"INSTALLED_NATIVE_TIMING setup_ns=([-+\d.]+) hold_ns=([-+\d.]+) period_ns=7.142857", log)
            require(match and all(float(v) >= 0 for v in match.groups()), "unchanged 140 MHz OOC timing failed")
            doc["timing"] = dict(frequency_mhz=140, setup_ns=float(match[1]), hold_ns=float(match[2]),
                                 scope="OOC synthesis estimate; shell placement/routing and image timing pending")
            run(["vivado", "-version"], "version")
            vendor = Path(shutil.which("vivado")).resolve().parents[1] / "data/verilog/src"
            for name, source in (("BUFGCE.v", vendor / "unisims/BUFGCE.v"), ("glbl.v", vendor / "glbl.v")):
                require(source.is_file(), "native vendor model missing " + str(source))
                shutil.copyfile(source, out / name)
            doc["vendor_models"] = {n: sha(out / n) for n in ("BUFGCE.v", "glbl.v")}
        else:
            require(ROOT == Path("/scratch/jfx/chia-cy-checkpoint-restore") and
                    os.environ.get("VCS_HOME") == toolchain.VCS_HOME and shutil.which("vcs") == toolchain.VCS,
                    "dedicated EDA SP2 with vcs-env.sh sourced last required")
            require(args.native is not None, "successful native synthesis receipt required")
            native_path = local(ROOT, str(args.native)).resolve()
            require(native_path.is_relative_to(RUNS), "native receipt must be beneath runs")
            native = validate_native(native_path, sources, doc["inputs"], sha(receipt))
            doc["native"] = dict(path=str(native_path), sha256=sha(native_path))
            # Vendor models are frozen by native synthesis on the manager and
            # transferred as explicit inputs, not copied from EDA tools.
            vendor = native_path.parent
            require(set(native.get("vendor_models", {})) == {"BUFGCE.v", "glbl.v"}, "missing vendor identities")
            for name in ("BUFGCE.v", "glbl.v"):
                require((vendor / name).is_file() and sha(vendor / name) == native["vendor_models"][name],
                        "missing or changed staged native vendor model " + name)
                shutil.copyfile(vendor / name, out / name)
            doc["vendor_models"] = {n: sha(out / n) for n in ("BUFGCE.v", "glbl.v")}
            common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
                      "-debug_access+all", "-top", "native_widget_endpoint_tb", "-top", "glbl"]
            files = [*(frozen / WIDGET / n for n in base.RESOURCES), frozen / PROBE,
                     out / "installed-bench.sv", ROOT / base.EXIT, out / "BUFGCE.v", out / "glbl.v"]
            run([*common, "-Mdir=csrc", "-o", "simv", rtl, *files], "compile")
            doc["executions"] = []
            for case, marker in (("healthy", "NATIVE_ENDPOINT_PASS cuts=4"),
                                 ("lost-owner", "NATIVE_ENDPOINT_OWNER_LOSS_PASS"),
                                 ("shadow-owner-loss", "NATIVE_ENDPOINT_SHADOW_FAULT_PASS"),
                                 ("abort", "NATIVE_ENDPOINT_ABORT_PASS")):
                work = out / case
                work.mkdir()
                log = run([out / "simv", "-no_save", "+CASE=" + case], "run", work)
                require(marker in log and "DIVERGENCE" not in log and "NATIVE_BOUND_ROM_PASS" in log,
                        "installed widget case incomplete " + case)
                row = dict(case=case)
                if case == "healthy":
                    row["cuts"] = [base.audit_frames(work / f"cut{i}.frames", int(doc["metadata"]["manifest_sha256"], 16)) for i in range(4)]
                    require(len({r["cut"] for r in row["cuts"]}) == 4, "nonprogressing cuts")
                    row["native_wave"] = base.audit_native(work / "native-widget-endpoint.vcd", 130,
                        top="native_widget_endpoint_tb." + ENDPOINT + ".nativeTransport.native_capture")
                    row["endpoint_wave"] = base.audit_observation_wave(work / "native-widget-endpoint.vcd", endpoint=ENDPOINT)
                else:
                    row["recovery"] = base.audit_frames(work / "recovery.frames", int(doc["metadata"]["manifest_sha256"], 16))
                    if case == "shadow-owner-loss":
                        row["endpoint_wave"] = base.audit_observation_wave(work / "native-widget-endpoint.vcd", 1, ENDPOINT)
                        require(row["endpoint_wave"]["rejections"] == 1, "missing preedge owner-loss rejection")
                doc["executions"].append(row)
            doc["compiled_faults"] = []
            for label, source, mutate in (("coordinator", rtl, base.coordinator_fault),
                ("native-data", frozen / WIDGET / "CheckpointNativeCaptureTransport.sv", base.native_data_fault)):
                changed, site = mutate(source.read_text())
                broken = out / (label + (".v" if label == "coordinator" else ".sv"))
                broken.write_text(changed)
                fault_files = [broken if p == source else p for p in files]
                run([*common, "-Mdir=" + label + "-csrc", "-o", label + "-simv",
                     broken if source == rtl else rtl, *fault_files], label + "-compile")
                work = out / label
                work.mkdir()
                log = run([out / (label + "-simv"), "-no_save"], "run", work, expected=1)
                lines = [n for n in log.splitlines() if n.startswith("NATIVE_ENDPOINT_DIVERGENCE")]
                require(len(lines) == 1, "compiled fault must stop at one divergence")
                audit = bound.audit_fault_wave(work / "native-widget-endpoint.vcd", lines[0], ENDPOINT)
                doc["compiled_faults"].append(dict(label=label, site=site, diagnostic=lines[0], wave=audit))
        require(sources == {n: sha(ROOT / n) for n in SOURCES}, "verification sources changed")
        require(doc["inputs"] == {n: sha(frozen / n) for n in FILES}, "frozen generated inputs changed")
        validate_scala(receipt, generated)
        doc["status"] = "pass"
    except Exception as error:
        doc.update(status="fail", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        doc["artifacts"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and
            p.name != "summary.json" and not any(n.endswith("csrc") or n.endswith(".daidir") or n == ".Xil"
                for n in p.relative_to(out).parts) and not p.name.endswith("simv")}
        (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")
        print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
