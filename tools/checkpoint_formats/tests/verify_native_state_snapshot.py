"""Native F2-part synthesis and EDA execution of atomic native-state staging.

Consumes an immutable, current-source queue synthesis receipt. No full-image,
physical checkpoint, global freeze, host transport or restore acceptance.
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

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_shared_queue_access as queue

ROOT, RUNS = queue.ROOT, queue.RUNS
RTL = "sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv"
TB = "tools/checkpoint_formats/tests/native_state_snapshot_tb.sv"
SELF = "tools/checkpoint_formats/tests/verify_native_state_snapshot.py"
SOURCES = sorted(set(queue.SOURCES) | {RTL, TB, SELF})
NEGATIVES = ("missing-owner", "no-freeze", "busy-capture", "borrow-before", "sameedge-borrow",
             "drift", "lost-freeze", "missing-after", "duplicate", "busy-release", "early-release", "overlap")
sha = queue.sha


def queue_wrapper(original):
    """Gate actual bank requests until the entire two-queue vector is staged.

    This is a component integration wrapper, not an admitted production graft.
    Original output probes, memory port count and bank ABI remain unchanged.
    """
    ports = """
  input wire snapshot_reset, snapshot_request, snapshot_release, owners_present,
  input wire [63:0] target_cycle,
  input wire [31:0] snapshot_word_address,
  output wire snapshot_ready, snapshot_valid, borrow_enable, snapshot_failed,
  output wire [63:0] snapshot_word_data, cut_cycle,
  output wire snapshot_word_error,
  output wire [1035:0] snapshot_state,
  output wire [5:0] snapshot_error,
  output wire [1106:0] snapshot_control_state,
"""
    require(original.count("module SharedQueueSynthesisTop(\n") == 1, "ambiguous queue wrapper")
    text = original.replace("module SharedQueueSynthesisTop(\n", "module NativeSnapshotQueueTop(\n" + ports)
    for q in range(2):
        valid = f"checkpoint_shell_region{q}_ckpt_req_valid"
        ready = f"checkpoint_shell_region{q}_ckpt_req_ready"
        require(text.count(f".{valid}({valid})") == 1 and text.count(f".{ready}({ready})") == 1,
                "ambiguous native request/ready gate")
        text = text.replace(f".{valid}({valid})", f".{valid}({valid} && borrow_enable)")
        text = text.replace(f".{ready}({ready})", f".{ready}(raw_ready{q})")
    body = """
  wire raw_ready0, raw_ready1;
  assign checkpoint_shell_region0_ckpt_req_ready = raw_ready0 && borrow_enable;
  assign checkpoint_shell_region1_ckpt_req_ready = raw_ready1 && borrow_enable;
  CheckpointNativeStateSnapshot #(.BITS(1036)) snapshot(
    .clock(clock), .reset(snapshot_reset), .request(snapshot_request), .release_snapshot(snapshot_release),
    .owners_present(owners_present),
    .functional_frozen(checkpoint_shell_region0_ckpt_freeze && checkpoint_shell_region1_ckpt_freeze),
    .reader_idle(raw_ready0 && raw_ready1),
    .borrow_attempt(borrow_enable && ((checkpoint_shell_region0_ckpt_req_valid && raw_ready0) ||
                                   (checkpoint_shell_region1_ckpt_req_valid && raw_ready1))),
    .target_cycle(target_cycle),
    .live_state({checkpoint_shell_region1_ckpt_native_state, checkpoint_shell_region0_ckpt_native_state}),
    .word_address(snapshot_word_address), .request_ready(snapshot_ready), .valid(snapshot_valid),
    .borrow_enable(borrow_enable), .failed(snapshot_failed), .word_data(snapshot_word_data),
    .word_error(snapshot_word_error), .snapshot_state(snapshot_state), .cut_cycle(cut_cycle),
    .error(snapshot_error), .control_state(snapshot_control_state));
"""
    require(text.count("endmodule") == 1, "ambiguous wrapper body")
    return text.replace("endmodule", body + "endmodule")


def integrated_bench(generated):
    """Retain the entire queue regression; add a snapshot before each main cut.

    Its oracle samples every independently identified actual emitted register,
    not the vector being captured. Original queue/latency/cancel tests still run.
    Later intentional broken-cut tests bypass this component through the original
    queue wrapper, as they test the underlying readout rather than staging.
    """
    text = (ROOT / "tools/checkpoint_formats/tests/shared_queue_access_tb.sv").read_text()
    declarations = """
  reg snapshot_reset=1, snapshot_request=0, snapshot_release=0, snapshot_active=0;
  reg [31:0] snapshot_address=0;
  reg [63:0] snapshot_cycle=0;
  wire snapshot_ready,snapshot_valid,snapshot_borrow,snapshot_failed,snapshot_word_error;
  wire [63:0] snapshot_word,snapshot_cut;
  wire [1035:0] snapshot_payload;
  wire [5:0] snapshot_error;
  wire [1106:0] snapshot_control;
  reg [1035:0] expected_snapshot;
  reg [1087:0] expected_padded;
  integer snapshot_checks=0,snapshot_cuts=0,snapshot_words=0,live_changes=0,snapshot_cuts_verified=0;
  integer exported_cuts=0,exported_words=0;
  reg [1035:0] export_expected;
  reg [1087:0] export_padded;
  reg [16:0] snapshot_seen=0;
  CheckpointNativeStateSnapshot #(.BITS(1036)) snapshot(
    .clock(clock),.reset(snapshot_reset),.request(snapshot_request),.release_snapshot(snapshot_release),
    .owners_present(1'b1),.functional_frozen(&freeze),.reader_idle(&request_ready),
    .borrow_attempt(|request_valid),.target_cycle(snapshot_cycle),.live_state({native_state[1],native_state[0]}),
    .word_address(snapshot_address),.request_ready(snapshot_ready),.valid(snapshot_valid),
    .borrow_enable(snapshot_borrow),.failed(snapshot_failed),.word_data(snapshot_word),
    .word_error(snapshot_word_error),.snapshot_state(snapshot_payload),.cut_cycle(snapshot_cut),
    .error(snapshot_error),.control_state(snapshot_control));
  always @(posedge clock) if(!(&freeze)) snapshot_cycle <= snapshot_cycle+1;
  always @(negedge clock) begin
    #3;
    if(snapshot_active)begin
      check(snapshot_valid && snapshot_borrow && !snapshot_failed,"staged cut remains valid");
      check(snapshot_payload===expected_snapshot,"entire staged native vector remains immutable");
      check(!snapshot_word_error && snapshot_word===expected_padded[snapshot_address*64+:64],"serial staged word and padding");
      snapshot_checks+=3;snapshot_words++;snapshot_seen[snapshot_address]=1;
      if({native_state[1],native_state[0]} !== expected_snapshot)live_changes++;
      snapshot_address=(snapshot_address+1)%17;
    end
  end
  task begin_native_snapshot;
    integer capture_file;
    snapshot_reset=0;snapshot_request=1;
    #1;check(snapshot_ready && !snapshot_borrow,"reader not borrowed on capture edge");
    @(posedge clock);
"""
    for q in range(2):
        bank = queue.canonical_json(generated / f"shell-{q}-banks-binding.json")
        for row in queue.emitted_observation(generated, q, bank)["state"]:
            declarations += (f"    expected_snapshot[{q*518+row['offset']} +: {row['width']}] = "
                             f"dut.host.q{q}.{row['emitted_register']};\n")
    declarations += """
    #2;snapshot_request=0;
    #1;check(snapshot_valid && snapshot_payload===expected_snapshot && snapshot_cut==snapshot_cycle,"all 28 emitted owners at one preedge cut");
    capture_file=$fopen($sformatf("native-queue-initial-cut%0d.hex",snapshot_cuts),"w");
    check(capture_file!=0,"native queue staging donor file");
    $fdisplay(capture_file,"%h",snapshot_control);$fclose(capture_file);
    expected_padded=0;expected_padded[1035:0]=expected_snapshot;
    snapshot_seen=0;snapshot_active=1;snapshot_cuts++;
  endtask
  task end_native_snapshot;
    integer capture_file;
    @(negedge clock);#2;snapshot_active=0;snapshot_release=1;
    check(&snapshot_seen,"every staged word read at this cut");snapshot_cuts_verified++;
    #1;check(!snapshot_borrow && !snapshot_valid,"revoke borrowing before release edge");
    @(posedge clock);#2;snapshot_release=0;
    #1;check(!snapshot_failed && !snapshot_valid,"healthy atomic snapshot release");
    // Initially untouched native selectors are genuinely unknown in VCS. Keep
    // that first donor verbatim above. After legal bank transactions finish,
    // atomically restage the now-defined original vector at the SAME frozen
    // target label. Never mask unknown state or initialize it hierarchically.
    @(negedge clock);#2;snapshot_request=1;
    #1;check(snapshot_ready && !snapshot_borrow,"post-read export capture qualified");
    @(posedge clock);
"""
    for q in range(2):
        bank = queue.canonical_json(generated / f"shell-{q}-banks-binding.json")
        for row in queue.emitted_observation(generated, q, bank)["state"]:
            declarations += (f"    export_expected[{q*518+row['offset']} +: {row['width']}] = "
                             f"dut.host.q{q}.{row['emitted_register']};\n")
    declarations += """
    #2;snapshot_request=0;
    #1;check(snapshot_valid && snapshot_payload===export_expected && snapshot_cut==snapshot_cycle &&
             (^snapshot_control)!==1'bx,"complete binary post-read staging donor");
    capture_file=$fopen($sformatf("native-queue-cut%0d.hex",exported_cuts),"w");
    check(capture_file!=0,"post-read donor file");
    $fdisplay(capture_file,"%h",snapshot_control);$fclose(capture_file);
    export_padded=0;export_padded[1035:0]=export_expected;
    for(integer w=0;w<17;w++)begin
      @(negedge clock);#2;snapshot_address=w;
      #1;check(!snapshot_word_error && snapshot_word===export_padded[w*64+:64],"every binary post-read donor word");
      @(posedge clock);#2;exported_words++;
    end
    exported_cuts++;
    @(negedge clock);#2;snapshot_release=1;
    #1;check(!snapshot_borrow && !snapshot_valid,"post-read export release before ack");
    @(posedge clock);#2;snapshot_release=0;
    #1;check(!snapshot_failed && !snapshot_valid,"post-read export healthy release");
  endtask
"""
    needle = "  wire [517:0] native_state[0:1];"
    require(text.count(needle) == 1, "missing queue vector boundary")
    text = text.replace(needle, needle + declarations)
    needle = "    step_before=selected_edges;sibling_before=pushes[2];sibling_pops_before=pops[2];"
    require(text.count(needle) == 1, "ambiguous main capture start")
    text = text.replace(needle, needle + "\n    begin_native_snapshot();")
    needle = "    @(negedge clock);#2;reset=0;freeze=0;cuts++;"
    require(text.count(needle) == 1, "ambiguous main capture release")
    text = text.replace(needle, "    end_native_snapshot();\n" + needle)
    # Keep the underlying cancellation, reset and premature-release cases; they
    # are independent of snapshot ownership and run after these four cuts.
    needle = "    // Explicitly reject requests outside hold"
    require(text.count(needle) == 1, "missing retained negative scopes")
    text = text.replace(needle, "    snapshot_reset=1;\n" + needle)
    needle = '    $display("NATIVE_OBSERVATION_PASS'
    require(text.count(needle) == 1, "missing retained observation summary")
    text = text.replace(needle, '''    check(snapshot_cuts==4 && snapshot_cuts_verified==4 && snapshot_checks==snapshot_words*3 && live_changes>100,"active borrowed native pipeline snapshot coverage");
    check(exported_cuts==4 && exported_words==68,"complete binary post-read export scope");
    $display("NATIVE_SNAPSHOT_EXPORT_PASS cuts=4 bits=1036 serial_words=68");
    $display("NATIVE_SNAPSHOT_QUEUE_PASS cuts=%0d fields=28 bits=1036 checks=%0d serial_words=%0d live_changes=%0d",snapshot_cuts,snapshot_checks,snapshot_words,live_changes);
''' + needle)
    return text


def gated_bench(generated):
    """Execute the same request gates and snapshot instance as synthesized.

    The complete underlying queue/reset/cancel regression runs independently.
    This additional process exercises the real gated wrapper for four cuts.
    """
    text = integrated_bench(generated)
    start = text.index("  CheckpointNativeStateSnapshot #(.BITS(1036)) snapshot(")
    end = text.index(".error(snapshot_error),.control_state(snapshot_control));", start)
    end += len(".error(snapshot_error),.control_state(snapshot_control));")
    text = text[:start] + text[end:]
    needle = "  SharedQueueSynthesisTop dut(.clock(clock),.reset(reset),"
    require(text.count(needle) == 1, "ambiguous executable queue wrapper")
    text = text.replace(needle, """  NativeSnapshotQueueTop dut(.clock(clock),.reset(reset),
    .snapshot_reset(snapshot_reset),.snapshot_request(snapshot_request),.snapshot_release(snapshot_release),
    .owners_present(1'b1),.target_cycle(snapshot_cycle),.snapshot_word_address(snapshot_address),
    .snapshot_ready(snapshot_ready),.snapshot_valid(snapshot_valid),.borrow_enable(snapshot_borrow),
    .snapshot_failed(snapshot_failed),.snapshot_word_data(snapshot_word),.cut_cycle(snapshot_cut),
    .snapshot_word_error(snapshot_word_error),.snapshot_state(snapshot_payload),
    .snapshot_error(snapshot_error),.snapshot_control_state(snapshot_control),"""
    )
    needle = "    snapshot_reset=1;\n    // Explicitly reject requests outside hold"
    require(text.count(needle) == 1, "ambiguous gated-only scope boundary")
    text = text.replace(needle, """    check(snapshot_cuts==4 && snapshot_cuts_verified==4 && snapshot_checks==snapshot_words*3 && live_changes>100,"gated snapshot workload coverage");
    $display("NATIVE_SNAPSHOT_GATED_PASS cuts=4 fields=28 bits=1036 reads=%0d serial_words=%0d live_changes=%0d",reads,snapshot_words,live_changes);
    check(exported_cuts==4 && exported_words==68,"complete gated binary post-read export scope");
    $display("NATIVE_SNAPSHOT_EXPORT_PASS cuts=4 bits=1036 serial_words=68");
    $finish;
    // Explicitly reject requests outside hold"""
    )
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("vivado", "vcs"))
    parser.add_argument("--queue-receipt", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence beneath runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    commands = []
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda", sources=sources,
               scope="atomic native-state staging component; global capture/restore owners remain incomplete",
               physical_fpga_capture=False, full_image=False, complete_capture_owner=False,
               metasim_restore_supported=False, host=socket.gethostname(), source_root=str(ROOT),
               observed_utc=datetime.now(timezone.utc).isoformat())
    def save():
        (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")
    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")))
        commands.append(row)
        with Path(row["log"]).open("w") as log:
            result = subprocess.run(row["argv"], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(row["log"]))
        doc.update(commands=commands, status="running" if result.returncode == expected else "fail")
        save()
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()
    save();print(out, flush=True)
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native localhost synthesis required")
        require(args.queue_receipt is not None and args.native is None, "explicit queue receipt required")
        receipt = args.queue_receipt.resolve()
        original = json.loads(receipt.read_text())
        require(original["status"] == "pass" and original["backend"] == "f2" and
                original["sources"] == {n: sources[n] for n in queue.SOURCES}, "stale original queue receipt")
        for group in ("inputs", "artifacts"):
            for name, digest in original[group].items():
                require(sha(receipt.parent / name) == digest, "changed original queue evidence " + name)
        shutil.copytree(receipt.parent / "generated", out / "generated")
        queue.audit(out / "generated")
        for name in ("synthesis-wrapper.sv", "shared-queue-selectors.svh", "BUFGCE.v", "glbl.v"):
            shutil.copyfile(receipt.parent / name, out / name)
        (out / "queue-input-receipt.json").write_bytes(receipt.read_bytes())
        (out / "native-snapshot-queue.sv").write_text(queue_wrapper((out / "synthesis-wrapper.sv").read_text()))
        (out / "native-snapshot-queue-tb.sv").write_text(integrated_bench(out / "generated"))
        (out / "native-snapshot-gated-tb.sv").write_text(gated_bench(out / "generated"))
        for name in (RTL, TB, "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"):
            shutil.copyfile(ROOT / name, out / Path(name).name)
        (out / "synth.tcl").write_text('''set_param general.maxThreads 4
read_verilog -sv generated/generated.sv
read_verilog -sv CheckpointNativeStateSnapshot.sv
read_verilog -sv native-snapshot-queue.sv
read_xdc generated/generated.synthesis.xdc
synth_design -top NativeSnapshotQueueTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set block [get_cells -hier -filter {REF_NAME =~ RAMB*}]
foreach path {host/q0 host/q1 host/q2} {
  set count 0
  foreach cell $block {
    if {[string match "$path/*" [get_property NAME $cell]]} {incr count}
  }
  if {$count != 2} {error "changed BLOCK memory policy at $path: $count"}
}
set registers [get_cells -hier -filter {NAME =~ snapshot/* && REF_NAME =~ FD*}]
if {[llength $registers] != 1107} {error "lost staging/control register ownership: [llength $registers]"}
puts "NATIVE_SNAPSHOT_STORAGE registers=[llength $registers] bits=1036 cycle=64 occupied=1 error=6"
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-snapshot-queue.dcp
puts "NATIVE_SNAPSHOT_SYNTH_PASS queues=2 sibling=1 RAMB_per_queue=2"
''')
        doc["queue_receipt"] = dict(path=str(receipt), sha256=sha(receipt), reused_immutable=True)
        doc["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and p.name != "summary.json"}
        log = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("NATIVE_SNAPSHOT_SYNTH_PASS queues=2 sibling=1 RAMB_per_queue=2" in log and
                not re.search(r"ERROR:|CRITICAL WARNING:", log), "native snapshot synthesis failed")
        doc["staging_register_bits"] = 1107
    else:
        require(str(ROOT).startswith("/scratch/") and toolchain.VCS.endswith("Y-2026.03-SP2/bin/vcs"), "EDA SP2 required")
        require(args.native is not None and args.queue_receipt is None, "native snapshot receipt required")
        receipt = local(ROOT, str(args.native))
        native = json.loads(receipt.read_text())
        require(native["status"] == "pass" and native["backend"] == "f2" and native["sources"] == sources,
                "stale native snapshot receipt")
        for group in ("inputs", "artifacts"):
            for name, digest in native[group].items():
                require(sha(receipt.parent / name) == digest, "changed native snapshot evidence " + name)
        for name in native["inputs"]:
            dest = out / name;dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt.parent / name, dest)
        queue.audit(out / "generated")
        require((out / "native-snapshot-queue.sv").read_text() == queue_wrapper((out / "synthesis-wrapper.sv").read_text()),
                "changed synthesized request gates/staging integration")
        require((out / "native-snapshot-queue-tb.sv").read_text() == integrated_bench(out / "generated"), "changed full-register snapshot oracle")
        require((out / "native-snapshot-gated-tb.sv").read_text() == gated_bench(out / "generated"), "changed synthesized-wrapper execution")
        doc["inputs"] = native["inputs"]
        common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all"]
        for bits in (1, 64, 65, 130, 1664):
            folder = out / f"unit-{bits}";folder.mkdir()
            run(common + [f"+define+SNAPSHOT_BITS={bits}", "-top", "native_state_snapshot_tb",
                "-Mdir=" + str(folder / "csrc"), "-o", str(folder / "simv"),
                str(out / "CheckpointNativeStateSnapshot.sv"), str(out / "native_state_snapshot_tb.sv"),
                str(out / "checkpoint_widget_exit.cc")], f"unit-{bits}-compile")
            for case in ("healthy",) + NEGATIVES:
                log = run([folder / "simv", "-no_save", "+CASE=" + case], f"unit-{bits}-{case}")
                token = f"NATIVE_SNAPSHOT_PASS bits={bits} captures=6 reads={5*((bits+63)//64)}" if case == "healthy" else f"NATIVE_SNAPSHOT_NEGATIVE_PASS case={case} "
                require(token in log and "DIVERGENCE" not in log, "missing snapshot unit coverage")
                shutil.move(out / "native-state-snapshot.vcd", folder / f"{case}.vcd")
        doc["unit_geometries"] = [1, 64, 65, 130, 1664]
        doc["negative_processes"] = len(NEGATIVES)*5
        # Actual emitted native queue state is the donor for these four cuts.
        # An output-bit fault must stop on the first sampled cut, before any
        # original bank response is acknowledged.
        for mode in ("healthy", "corrupt", "gated"):
            folder = out / ("queue-" + mode);folder.mkdir()
            text = (out / "CheckpointNativeStateSnapshot.sv").read_text()
            if mode == "corrupt":
                require(text.count("assign snapshot_state = payload;") == 1, "ambiguous compiled semantic fault")
                text = text.replace("assign snapshot_state = payload;", "assign snapshot_state = payload ^ 1'b1;")
            (folder / "snapshot.sv").write_text(text)
            wrapper = "native-snapshot-queue.sv" if mode == "gated" else "synthesis-wrapper.sv"
            bench = "native-snapshot-gated-tb.sv" if mode == "gated" else "native-snapshot-queue-tb.sv"
            run(common + ["+incdir+" + str(out), "-top", "shared_queue_access_tb", "-top", "glbl",
                "-Mdir=" + str(folder / "csrc"), "-o", str(folder / "simv"),
                str(out / "generated/generated.sv"), str(out / wrapper), str(folder / "snapshot.sv"),
                str(out / bench), str(out / "checkpoint_widget_exit.cc"),
                str(out / "BUFGCE.v"), str(out / "glbl.v")], "queue-" + mode + "-compile")
            log = run([folder / "simv", "-no_save"], "queue-" + mode + "-run", 1 if mode == "corrupt" else 0)
            shutil.move(out / "shared-queue-access.vcd", folder / "debug.vcd")
            if mode != "corrupt":
                for cut in range(4):
                    for prefix in ("native-queue-cut", "native-queue-initial-cut"):
                        image = out / f"{prefix}{cut}.hex"
                        require(image.is_file(), "missing native queue staging donor")
                        shutil.move(image, folder / image.name)
                require("NATIVE_SNAPSHOT_EXPORT_PASS cuts=4 bits=1036 serial_words=68" in log,
                        "missing complete post-read staging exports")
            if mode == "healthy":
                match = re.search(r"NATIVE_SNAPSHOT_QUEUE_PASS cuts=4 fields=28 bits=1036 checks=(\d+) serial_words=(\d+) live_changes=(\d+)", log)
                require(match is not None and "SHARED_QUEUE_PASS" in log and "reads=364" in log,
                        "missing complete queue/snapshot continuation scope")
                doc["queue_snapshot_checks"], doc["queue_serial_words"], doc["live_vector_changes"] = map(int, match.groups())
            elif mode == "corrupt":
                require("signal=all 28 emitted owners at one preedge cut cuts=0" in log and
                        "response_ack=00 reads=0" in log and "NATIVE_SNAPSHOT_QUEUE_PASS" not in log,
                        "snapshot semantic corruption escaped first sample/ack")
                doc["compiled_semantic_fault_rejected_before_ack"] = True
            else:
                match = re.search(r"NATIVE_SNAPSHOT_GATED_PASS cuts=4 fields=28 bits=1036 reads=(\d+) serial_words=(\d+) live_changes=(\d+)", log)
                require(match is not None and int(match[1]) == 360, "incomplete synthesized request-gate execution")
                doc["gated_queue_reads"], doc["gated_serial_words"], doc["gated_live_vector_changes"] = map(int, match.groups())
        doc["native_receipt"] = dict(path=str(receipt), sha256=sha(receipt))
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, "sources changed during verification")
    doc.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
        if p.is_file() and p.suffix in {".log", ".rpt", ".dcp", ".vcd", ".hex"}})
    save();print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
