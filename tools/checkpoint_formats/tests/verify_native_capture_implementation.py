"""Native F2-part OOC implementation of an exact synthesized capture component.

This measures internal implemented timing only, without a shell or I/O budgets.
It does not build a FireSim image, create an AFI or establish FPGA capture.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_native_capture_transport as transport

ROOT, RUNS = transport.ROOT, transport.RUNS
sha = transport.sha
SELF = "tools/checkpoint_formats/tests/verify_native_capture_implementation.py"


def script(registers):
    require(len(registers) == 1666 and len(set(registers)) == 1666, "incomplete input register map")
    # Only source-generated register pin names from the validated synthesis log
    # enter Tcl. Braces are not allowed in an emitted identifier here.
    require(all(re.fullmatch(r"[A-Za-z0-9_./\[\]$]+", pin) for pin in registers), "unsafe register pin")
    expected = " ".join("{" + p + "}" for p in registers)
    return """set_param general.maxThreads 4
open_checkpoint input.dcp
set expected [list """ + expected + """]
place_design
route_design
set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] != 1666} {error "implementation changed the complete register inventory"}
for {set index 0} {$index < 1666} {incr index} {
  set port [get_ports [format {control_state[%d]} $index]]
  set net [get_nets -of_objects $port]
  set driver [get_pins -leaf -of_objects $net -filter {DIRECTION == OUT}]
  if {[llength $driver] != 1 || [get_property NAME $driver] ne [lindex $expected $index]} {
    error "implementation changed original state-bit identity $index"
  }
  puts "IMPLEMENTED_REGISTER $index [get_property NAME $driver]"
}
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "changed physical clock topology"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed physical CE semantics"}}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "changed common falling-edge mask"}
set bad [get_nets -hier -filter {ROUTE_STATUS == UNROUTED || ROUTE_STATUS == PARTIAL || ROUTE_STATUS == CONFLICTS}]
if {[llength $bad] != 0} {error "incomplete implementation routing: [llength $bad]"}
report_route_status -file route-status.rpt
report_drc -file routed-drc.rpt
report_utilization -file routed-utilization.rpt
report_timing_summary -delay_type min_max -max_paths 10 -file routed-timing.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
write_checkpoint -force implemented.dcp
puts "NATIVE_IMPLEMENTATION_TIMING setup=$setup hold=$hold registers=1666 gates=4"
if {$setup < 0 || $hold < 0} {error "implemented component timing does not meet the unchanged 140 MHz clock"}
puts "NATIVE_IMPLEMENTATION_PASS"
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),
            "implementation must use native localhost Vivado")
    require(args.out.resolve().is_relative_to(RUNS), "implementation evidence belongs beneath runs")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="implementation-", dir=args.out.resolve()))
    receipt = local(ROOT, str(args.native))
    sources = {name: sha(ROOT / name) for name in (*transport.SOURCES, SELF)}
    native = transport.validate_native(receipt, {n: sources[n] for n in transport.SOURCES})
    pins = re.findall(r"^NATIVE_TRANSPORT_REGISTER (\d+) (\S+)$",
                      (receipt.parent / "native.log").read_text(), re.M)
    require([int(i) for i, _ in pins] == list(range(1666)), "incomplete synthesized state order")
    shutil.copyfile(receipt.parent / "native-transport.dcp", out / "input.dcp")
    (out / "implementation.tcl").write_text(script([pin for _, pin in pins]))
    shutil.copyfile(ROOT / SELF, out / "verifier.py")
    doc = dict(status="running", backend="f2", scope="native F2-part OOC component implementation only",
               host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat(),
               physical_fpga_capture=False, full_image=False, cpu_restore_verified=False,
               cpu_live_acceptance=False, shell_integration=False, io_budgets_applied=False,
               native_receipt=dict(path=str(receipt), sha256=sha(receipt)), sources=sources,
               inputs={name: sha(out / name) for name in ("input.dcp", "implementation.tcl", "verifier.py")},
               native_vivado=os.environ.get("XILINX_VIVADO"))
    summary = out / "summary.json"
    summary.write_text(json.dumps(doc, indent=2) + "\n")
    print(out, flush=True)
    argv = ["vivado", "-mode", "batch", "-source", "implementation.tcl"]
    with (out / "implementation.log").open("w") as stream:
        result = subprocess.run(argv, cwd=out, stdout=stream, stderr=subprocess.STDOUT)
    text = (out / "implementation.log").read_text()
    timing = re.findall(r"NATIVE_IMPLEMENTATION_TIMING setup=([-\d.]+) hold=([-\d.]+) registers=1666 gates=4", text)
    if timing:
        doc.update(setup_slack_ns=float(timing[-1][0]), hold_slack_ns=float(timing[-1][1]))
    doc.update(returncode=result.returncode, argv=argv,
               artifacts={p.name: sha(p) for p in out.iterdir() if p.suffix in (".log", ".rpt", ".dcp")})
    passed = result.returncode == 0 and "NATIVE_IMPLEMENTATION_PASS" in text and len(timing) == 1
    passed = passed and sources == {n: sha(ROOT / n) for n in sources}
    if passed:
        report = (out / "routed-timing.rpt").read_text()
        passed = "There are 0 combinational loops in the design." in report and "There are 0 combinational latch loops" in report
    doc["status"] = "pass" if passed else "fail"
    summary.write_text(json.dumps(doc, indent=2) + "\n")
    require(passed, "inspect native implementation log " + str(out / "implementation.log"))
    print(summary, flush=True)


if __name__ == "__main__":
    main()
