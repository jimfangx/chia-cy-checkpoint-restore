"""Local Vivado / EDA SP2 verification of static multi-region bank routing.

This verifies the routing component, not a complete FPGA checkpoint image.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
RTL = "sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv"
TB = "tools/checkpoint_formats/tests/checkpoint_region_router_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
SOURCES = (RTL, TB, EXIT, "tools/checkpoint_formats/tests/verify_checkpoint_region_router.py",
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointRegionRouting.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/checkpoint/CheckpointRegionRoutingSpec.scala")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configuration_bench(parameters):
    # VCS SP2 can return zero for $fatal. The final block sets process status
    # through the existing helper, after the simulator closes its outputs.
    return ('module config_tb;\n'
        'import "DPI-C" function void checkpoint_widget_failed();\n'
        'final checkpoint_widget_failed();\n'
        'CheckpointRegionStateRouter #(' + parameters + ') dut();\n'
        'initial begin #10; $fatal(1,"missing configuration rejection"); end\nendmodule\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--generated", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence under runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {name: sha(ROOT / name) for name in SOURCES}
    generated = args.generated
    if args.mode == "vcs":
        require(args.native is not None and generated is None, "one explicit native synthesis receipt required")
        require(args.native.resolve().is_relative_to(RUNS), "native receipt under runs required")
        native = json.loads((args.native / "summary.json").read_text())
        require(native["status"] == "pass" and native["backend"] == "f2" and native["sources"] == sources
            and native["physical_fpga_capture"] is False, "stale/wrong native routing receipt")
        for group in ("inputs", "artifacts"):
            for name, value in native[group].items():
                require(sha(args.native / name) == value, "changed native routing evidence " + name)
        generated = args.native
    require(generated is not None and generated.resolve().is_relative_to(RUNS), "generated routing under runs required")
    for name in SOURCES:
        dest = out / "sources" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    for name in ("parameters.svh", "routing.json", "CheckpointRegionStateRouter.sv"):
        shutil.copyfile(generated / name, out / name)
    require(sha(out / "CheckpointRegionStateRouter.sv") == sources[RTL], "stale emitted router")
    routing = json.loads((out / "routing.json").read_text())
    # Literal independent allocation oracle for this directed hardware bench.
    require(routing["regions"] == [dict(index=0, bank_base=0, bank_count=1, ce_base=0, ce_count=1),
        dict(index=1, bank_base=1, bank_count=2, ce_base=1, ce_count=2)] and
        routing["router_sha256"] == sources[RTL], "changed static routing configuration")
    require((out / "parameters.svh").read_text() == ".REGIONS(2), .BANK_BASE(16'h0100), .BANK_COUNT(16'h0201), "
        ".CE_BASE(32'h00010000), .CE_COUNT(32'h00020001)", "changed synthesized parameters")
    inputs = {n: sha(out / n) for n in ("parameters.svh", "routing.json", "CheckpointRegionStateRouter.sv")}
    commands = []

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")))
        commands.append(row)
        with Path(row["log"]).open("w") as stream:
            proc = subprocess.run(row["argv"], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row["returncode"] = proc.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(proc.returncode == expected if expected is not None else proc.returncode != 0,
            "inspect underlying log " + row["log"])
        return Path(row["log"]).read_text()

    summary = dict(status="running", backend="eda" if args.mode == "vcs" else "f2",
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
        original_root=str(ROOT), sources=sources, inputs=inputs, scope="static native-region routing component only",
        complete_fpga_capture=False, deployable_capture_image=False, physical_fpga_capture=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),
            "native localhost Vivado required")
        # Keep every interface pin observable; endpoints are not constant stubs.
        text = (out / "CheckpointRegionStateRouter.sv").read_text()
        ports = text[text.index(")(\n") + 3:text.index("\n);", text.index(")(\n"))]
        ports = ports.replace("REGIONS", str(len(routing["regions"])))
        wrapper = "module CheckpointRegionSynthesisFixture (\n" + ports + "\n);\n" + \
            "CheckpointRegionStateRouter #(" + (out / "parameters.svh").read_text() + ") dut(.*);\nendmodule\n"
        (out / "fixture.sv").write_text(wrapper)
        (out / "synth.tcl").write_text("""set_param general.maxThreads 4
read_verilog -sv CheckpointRegionStateRouter.sv fixture.sv
synth_design -top CheckpointRegionSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_host_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME == FDRE}]] < 3} {error "lost pending/invalid/owner registers"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force region-router.dcp
puts "REGION_ROUTER_SYNTH_PASS"
""")
        log = run([shutil.which("vivado"), "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("REGION_ROUTER_SYNTH_PASS" in log and not re.search(r"ERROR:|CRITICAL WARNING:", log),
            "native synthesis failed")
        summary["artifacts"] = {n: sha(out / n) for n in
            ("fixture.sv", "synth.tcl", "synth.log", "utilization.rpt", "timing.rpt", "region-router.dcp")}
    else:
        require(shutil.which("vcs") == toolchain.VCS and toolchain.VCS ==
            "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "EDA native SP2 required")
        common = [toolchain.VCS, "-full64", "-sverilog", "-debug_access+all", "-timescale=1ns/1ps", "-Mupdate",
            "+incdir+" + str(out), "-top", "checkpoint_region_router_tb"]
        run([*common, "-Mdir=csrc", "-o", "simv", out / "CheckpointRegionStateRouter.sv",
            out / "sources" / TB, out / "sources" / EXIT], "compile")
        log = run([out / "simv", "-no_save"], "healthy")
        match = re.search(r"REGION_ROUTER_PASS checks=(\d+) requests=(\d+) responses=(\d+) invalids=(\d+) stalls=(\d+) resets=(\d+)", log)
        require(match and tuple(map(int, match.groups()[1:4])) == (201, 199, 4)
            and int(match[5]) > 2000 and int(match[6]) == 2, "incomplete region regression")
        summary["counts"] = dict(zip(("checks", "requests", "responses", "invalids", "stalls", "resets"), map(int, match.groups())))
        shutil.move(out / "region-router.vcd", out / "healthy.vcd")
        # Change the compiled response owner, leaving the oracle and inputs intact.
        rtl = (out / "CheckpointRegionStateRouter.sv").read_text()
        require(rtl.count("owner <= route;") == 1, "mutation target changed")
        (out / "corrupt.sv").write_text(rtl.replace("owner <= route;", "owner <= 0;"))
        run([*common, "-Mdir=corrupt-csrc", "-o", "corrupt-simv", out / "corrupt.sv",
            out / "sources" / TB, out / "sources" / EXIT], "corrupt-compile")
        bad = run([out / "corrupt-simv", "-no_save"], "corrupt", expected=None)
        require("REGION_ROUTER_PASS" not in bad and
            "REGION_ROUTER_DIVERGENCE reason=selected delayed response only requests=2 responses=1" in bad,
            "compiled routing corruption did not stop at first divergent response")
        shutil.move(out / "region-router.vcd", out / "corrupt.vcd")
        # Highest legal selectors and a non-power-of-two owner index exercise
        # unsigned range arithmetic and the parameterized owner register.
        summary["boundary_cases"] = []
        for count in (1, 3):
            name = "boundary-" + str(count)
            bases = [0, 1, 254] if count == 3 else [254]
            ce_bases = [0, 1, 65535] if count == 3 else [65535]
            packed = lambda width, values: str(width * len(values)) + "'h" + "".join(
                format(v, "0" + str(width // 4) + "x") for v in reversed(values))
            parameters = ".REGIONS(" + str(count) + "), .BANK_BASE(" + packed(8, bases) + \
                "), .BANK_COUNT(" + packed(8, [1] * count) + "), .CE_BASE(" + packed(16, ce_bases) + \
                "), .CE_COUNT(" + packed(16, [1] * count) + ")"
            (out / (name + ".sv")).write_text("""`timescale 1ns/1ps
module boundary_tb;
reg clock=0, reset=1, request_valid=0, response_ready=0;
always #5 clock=!clock;
reg [7:0] bank=254; reg [15:0] slot=7; wire request_ready,response_valid,response_error;
wire [63:0] response_data; wire [COUNT-1:0] region_request_valid,region_response_ready;
wire [7:0] region_bank; wire [15:0] region_slot; wire [31:0] region_address;
CheckpointRegionStateRouter #(PARAMETERS) dut(.clock(clock),.reset(reset),.request_valid(request_valid),
.request_ready(request_ready),.bank(bank),.slot(slot),.address(32'd9),.response_valid(response_valid),
.response_ready(response_ready),.response_data(response_data),.response_error(response_error),
.region_request_valid(region_request_valid),.region_request_ready({COUNT{1'b1}}),.region_bank(region_bank),
.region_slot(region_slot),.region_address(region_address),.region_response_valid({COUNT{1'b1}}),
.region_response_ready(region_response_ready),.region_response_data({COUNT{64'h123456789abcdef0}}),
.region_response_error({COUNT{1'b0}}));
initial begin
@(posedge clock); #2; @(negedge clock); #1; reset=0; request_valid=1; #1;
if(!request_ready || region_request_valid!=(1<<(COUNT-1)) || region_bank!=0 || region_slot!=7)
  $fatal(1,"highest functional selector");
@(posedge clock); #2; request_valid=0; bank=255; slot=65535; response_ready=1; #1;
if(!response_valid || response_error || region_response_ready!=(1<<(COUNT-1)) ||
 response_data!==64'h123456789abcdef0) $fatal(1,"highest owner response");
@(posedge clock); #2; response_ready=0;
@(negedge clock); #1; request_valid=1; #1;
if(!request_ready || region_request_valid!=(1<<(COUNT-1)) || region_bank!=255 || region_slot!=0)
  $fatal(1,"highest physical selector");
@(posedge clock); #2; request_valid=0; response_ready=1; #1;
if(!response_valid || region_response_ready!=(1<<(COUNT-1))) $fatal(1,"physical owner response");
@(posedge clock); #2; response_ready=0;
$display("REGION_BOUNDARY_PASS"); $finish;
end
endmodule
""".replace("COUNT", str(count)).replace("PARAMETERS", parameters))
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-top", "boundary_tb",
                "-Mdir=" + name + "-csrc", "-o", name + "-simv", out / "CheckpointRegionStateRouter.sv",
                out / (name + ".sv")], name + "-compile")
            require("REGION_BOUNDARY_PASS" in run([out / (name + "-simv"), "-no_save"], name), "boundary regression failed")
            summary["boundary_cases"].append(count)
        # Elaboration must reject malformed or overlapping static ranges.
        negatives = {
            "functional-overlap": (".REGIONS(2), .BANK_BASE(16'h0000)", "checkpoint functional bank overlap"),
            "physical-overlap": (".REGIONS(2), .CE_BASE(32'h00000000)", "checkpoint physical slot overlap"),
            "bank-overflow": (".REGIONS(2), .BANK_BASE(16'hff00)", "checkpoint region range"),
            "ce-overflow": (".REGIONS(2), .CE_BASE(32'hffff0000), .CE_COUNT(32'h00020001)", "checkpoint region range"),
            "empty-bank": (".REGIONS(2), .BANK_COUNT(16'h0001)", "checkpoint region range"),
        }
        summary["rejections"] = {}
        for name, (parameters, marker) in negatives.items():
            bench = out / (name + ".sv")
            bench.write_text(configuration_bench(parameters))
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-top", "config_tb",
                "-Mdir=" + name + "-csrc", "-o", name + "-simv", out / "CheckpointRegionStateRouter.sv", bench,
                out / "sources" / EXIT], name + "-compile")
            rejected = run([out / (name + "-simv"), "-no_save"], name, expected=None)
            require(marker in rejected and "missing configuration rejection" not in rejected
                and re.search(r"at time 0 (?:ps|ns)", rejected), "wrong rejection " + name)
            summary["rejections"][name] = marker
        summary["artifacts"] = {p.name: sha(p) for p in out.iterdir()
            if p.is_file() and p.suffix in (".log", ".vcd", ".sv")}
        require((out / "healthy.vcd").stat().st_size > 10000 and (out / "corrupt.vcd").stat().st_size > 1000,
            "complete debug waves required")
    require(sources == {name: sha(ROOT / name) for name in SOURCES}, "live source changed")
    require(inputs == {name: sha(out / name) for name in inputs}, "generated routing changed")
    summary.update(status="pass", commands=commands)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(out / "summary.json")


if __name__ == "__main__":
    main()
