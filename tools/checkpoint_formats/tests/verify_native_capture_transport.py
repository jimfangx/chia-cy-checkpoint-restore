"""Source-bound native MMIO/DMA component synthesis and EDA-only SP2 checks.

This does not build/admit a Rocket image or create FPGA-origin checkpoints.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import zipfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_native_state_capture_wave import audit as audit_native
from tools.checkpoint_formats.tests.verify_transport_control_state import reconstruct

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
VERILOG = "sims/firesim/sim/midas/src/main/verilog/"
RTL = tuple(VERILOG + n + ".sv" for n in (
    "CheckpointSnapshotStateBank",
    "CheckpointNativeCaptureTransport", "CheckpointNativeStateCapture", "CheckpointNativeStateSnapshot",
    "CheckpointPhysicalClockCut", "CheckpointCaptureCut", "CheckpointCaptureTransport"))
TB = "tools/checkpoint_formats/tests/native_capture_transport_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
SOURCES = (*RTL, TB, EXIT,
    "tools/checkpoint_formats/tests/verify_native_capture_transport.py",
    "tools/checkpoint_formats/tests/audit_native_state_capture_wave.py",
    "tools/checkpoint_formats/tests/verify_transport_control_state.py",
    VERILOG + "CheckpointPhysicalCaptureTransport.sv",
    "tools/checkpoint_formats/codec.py", "tools/checkpoint_formats/fpga_transport.py",
    "tools/checkpoint_formats/toolchain.py", "tools/checkpoint_formats/regression_runner.py")
GEOMETRIES = (1, 64, 65, 130, 1036, 1664, 6656)
CASES = ("healthy", "abort-wait", "abort-response", "abort-native", "alias",
         "owner", "owner-error", "freeze", "ce", "cycle")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tcl():
    return """set_param general.maxThreads 4
read_verilog -sv """ + " ".join(Path(n).name for n in RTL) + """
synth_design -top CheckpointNativeCaptureTransport -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -generic {BITS=1036 GATES=3 OWNERS=2 ENTRIES=1 MANIFEST_SHA256=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef}
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected four native SYNC gates"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed gate semantics"}}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "expected one common falling-edge mask"}
set regs [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $regs] != 1666} {error "incomplete native/transport/response state: [llength $regs]"}
set drivers {}
for {set index 0} {$index < 1666} {incr index} {
  set port [get_ports [format {control_state[%d]} $index]]
  set net [get_nets -of_objects $port]
  set driver [get_pins -leaf -of_objects $net -filter {DIRECTION == OUT}]
  if {[llength $driver] != 1 || [get_property REF_PIN_NAME $driver] ne "Q"} {error "unmapped state bit $index"}
  set cell [get_cells -of_objects $driver]
  if {![string match FD* [get_property REF_NAME $cell]]} {error "non-register state bit $index"}
  lappend drivers [get_property NAME $driver]
  puts "NATIVE_TRANSPORT_REGISTER $index [get_property NAME $driver]"
}
if {[llength [lsort -unique $drivers]] != 1666} {error "aliased composite register readout"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-transport.dcp
puts "NATIVE_TRANSPORT_SYNTH_PASS bits=1666 gates=4 falling_edge_registers=1"
"""


def validate_native(receipt, sources):
    doc = json.loads(receipt.read_text())
    require(doc["status"] == "pass" and doc["backend"] == "f2" and doc["sources"] == sources,
            "stale or incompatible native transport receipt")
    require(doc["physical_fpga_capture"] is False and doc["full_image"] is False, "incorrect evidence scope")
    for group in ("inputs", "artifacts"):
        for name, digest in doc[group].items():
            require(sha(receipt.parent / name) == digest, "changed native transport " + name)
    for n in SOURCES:
        require(sha(receipt.parent / "sources" / n) == sources[n], "different source snapshot " + n)
        if n in (*RTL, TB, EXIT):
            require(sha(receipt.parent / Path(n).name) == sources[n], "different execution source " + n)
    require((receipt.parent / "native.tcl").read_text() == tcl(), "changed native synthesis contract")
    for name in ("BUFGCE.v", "glbl.v"):
        require(sha(receipt.parent / name) == doc["vendor_models"][name]["sha256"], "changed native vendor model")
    with zipfile.ZipFile(receipt.parent / "native-transport.dcp") as dcp:
        require(dcp.testzip() is None and "xcvu47p-fsvh2892-2-e" in dcp.read("dcp.xml").decode(), "invalid F2-part DCP")
    text = (receipt.parent / "native.log").read_text()
    rows = re.findall(r"^NATIVE_TRANSPORT_REGISTER (\d+) (\S+)$", text, re.M)
    require([int(i) for i, _ in rows] == list(range(1666)) and len({p for _, p in rows}) == 1666,
            "incomplete original synthesized register map")
    return doc


def audit_frames(path, bits, samples):
    raw = path.read_bytes()
    count = (bits + 63) // 64
    require(len(raw) == (6 + count) * 64, "truncated native capture stream")
    frames = [int.from_bytes(raw[i:i+64], "little") for i in range(0, len(raw), 64)]
    cut = field(frames[0], 96, 64)
    captures = [s for s in samples if s["target_cycle"] == cut]
    require(len(captures) == 1, "missing/ambiguous independently observed native cut")
    expected_native = int(captures[0]["preedge_live_hex"], 16)
    memory = [1, 2, 3, 4]
    for cycle in range(cut):
        memory = [((v * 33) ^ (cycle + k)) & 0xffffffff for k, v in enumerate(memory)]
    full, tail = divmod(bits, 64)
    for i, frame in enumerate(frames):
        require(field(frame, 0, 64) == 0x3154504b434d5346 and field(frame, 64, 16) == 1 and
                field(frame, 96, 64) == cut, "wrong frame identity/cycle")
        require(field(frame, 80, 16) == (1 if i == 0 else 3 if i == len(frames)-1 else 2), "wrong frame order")
        require(field(frame, 160, 64) == (0 if i == 0 else 4+count if i == len(frames)-1 else i-1), "wrong sequence")
        if i == 0:
            require(field(frame, 224, 32) == 1 + bool(full) + bool(tail) and
                    field(frame, 256, 256) == int("0123456789abcdef" * 4, 16), "wrong manifest header")
        elif i == len(frames)-1:
            require(field(frame, 224, 32) == crc32c(raw[:-64]) ^ 0xffffffff and frame >> 256 == 0, "wrong CRC trailer")
        else:
            word = i-1
            native_word = word-4
            ordinal = 0 if word < 4 else 1 if native_word < full else 1+bool(full)
            address = word if word < 4 else native_word if native_word < full else 0
            width = 32 if word < 4 else 64 if native_word < full else tail
            bank = 1 if word < 4 else 0xfc
            slot = int(word >= 4 and native_word >= full)
            require(field(frame, 224, 32) == ordinal and field(frame, 256, 32) == address and
                    field(frame, 288, 16) == width and field(frame, 304, 8) == bank and
                    field(frame, 312, 16) == slot and field(frame, 328, 8) == 0 and frame >> 400 == 0,
                    "noncanonical descriptor or reserved frame bits")
            value = field(frame, 336, 64)
            require(value >> width == 0, "noncanonical high data bits")
            if word < 4:
                require(value == memory[word], "independent host functional-memory oracle")
            else:
                require(value == ((expected_native >> (64 * native_word)) & ((1 << width)-1)),
                        "independent original-vector/native DMA word mismatch")
    return dict(path=str(path), sha256=sha(path), target_cycle=cut, words=4+count)


def audit_wave(path, bits):
    """Reconstruct complete outer readout from original registers, not sub-buses."""
    native = audit_native(path, bits, top="native_capture_transport_tb.dut.native_capture")
    sources = {Path(n).name: (ROOT / n).read_text() for n in SOURCES if n.startswith(VERILOG)}
    original = reconstruct(sources, 3)
    transport = [r for r in original if not r["relative_path"].startswith("physical.")]
    rows = [("native_capture.snapshot.payload", bits), ("native_capture.snapshot.occupied", 1),
            ("native_capture.snapshot.cut_cycle", 64), ("native_capture.snapshot.error", 6),
            ("native_capture.physical.freeze_low", 1), ("native_capture.physical.sampled", 1),
            ("native_capture.physical.release_pending", 1), ("native_capture.physical.captured_ce", 3),
            ("native_capture.physical.cut_cycle", 64), ("native_capture.physical.error", 3),
            ("native_capture.phase", 3), ("native_capture.error", 6)]
    rows += [(r["relative_path"], r["width"]) for r in transport]
    rows += [("snapshot_response_valid", 1), ("snapshot_response_data", 64), ("snapshot_response_error", 1)]
    # Check every newly added sequential declaration against the independent
    # owner list, so an added/missing response register cannot escape the audit.
    outer = sources["CheckpointNativeCaptureTransport.sv"]
    require(set(re.findall(r"\breg\s+(?:\[[^]]+\]\s*)?(\w+)\s*;", outer)) ==
            {"snapshot_response_valid", "snapshot_response_data", "snapshot_response_error"}, "unowned adapter storage")
    require(sum(w for _, w in rows) == bits+630, "wrong complete composite owner width")
    wanted = {"native_capture_transport_tb.dut." + n: n for n, _ in rows + [("control_state", bits+630)]}
    for n in ("native_capture.clock", "native_capture.live_state", "native_capture.snapshot.request",
              "native_capture.snapshot.request_ready"):
        wanted["native_capture_transport_tb.dut." + n] = n
    codes, values, scopes = {}, {}, []
    samples = 0
    previous, captures = {}, []

    def sample():
        nonlocal samples, previous
        now = {n: values[c] for n, c in codes.items() if c in values}
        if (now.get("native_capture.clock") == "1" and previous.get("native_capture.clock") == "0" and
                previous.get("native_capture.snapshot.request") == previous.get("native_capture.snapshot.request_ready") == "1"):
            vector = previous["native_capture.live_state"]
            require(re.fullmatch("[01]+", vector) is not None, "unknown original sampled native state")
            captures.append(dict(target_cycle=int(now["native_capture.snapshot.cut_cycle"], 2),
                                 preedge_live_hex=hex(int(vector, 2))))
        previous = now
        if len(now) != len(wanted) or not all(re.fullmatch("[01]+", v) for v in now.values()):
            return
        packed = offset = 0
        for n, width in rows:
            packed |= int(now[n], 2) << offset
            offset += width
        require(packed == int(now["control_state"], 2), "complete original transport/native readout mismatch")
        samples += 1

    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "$scope": scopes.append(parts[2])
        elif parts[0] == "$upscope": scopes.pop()
        elif parts[0] == "$var":
            name = ".".join(scopes + [parts[4].lstrip("\\")])
            if name in wanted: codes[wanted[name]] = parts[3]
        elif line.startswith("#"): sample()
        elif line[0] in "bB" and len(parts) == 2: values[parts[1]] = parts[0][1:].lower()
        elif line[0] in "01xXzZ": values[line[1:].strip()] = line[0].lower()
    sample()
    require(len(codes) == len(wanted) and samples > 0, "missing complete original register visibility")
    require(len(captures) == native["captures"], "inconsistent independent native sampling audit")
    if len(captures) == 13:
        planes=[]
        for row in captures:
            vector=int(row["preedge_live_hex"],16)
            planes.append(vector ^ (((1 << bits)-1) if vector & 1 else 0))
        for bit in range(bits):
            identity=sum(((p >> bit) & 1) << i for i,p in enumerate(planes))
            require(identity == (0 if bit==0 else 8191 if bit==1 else bit-1),
                    "native identity planes do not independently distinguish every original bit")
    return dict(path=str(path), sha256=sha(path), register_vectors=len(rows), samples=samples,
                native=native, capture_vectors=captures)


def receipt_negatives(receipt, sources, out):
    results = []
    for case in ("source-copy", "model", "tcl", "incompatible", "truncated", "dcp"):
        folder=out/case;shutil.copytree(receipt.parent,folder)
        path=folder/"summary.json";doc=json.loads(path.read_text())
        if case in ("source-copy", "model", "tcl"):
            name={"source-copy":"CheckpointNativeCaptureTransport.sv", "model":"BUFGCE.v", "tcl":"native.tcl"}[case]
            dest=folder/name;dest.write_text(dest.read_text()+"\n// coherently rehashed foreign input\n")
            doc["inputs"][name]=sha(dest)
        elif case=="incompatible":doc["sources"][RTL[0]]="0"*64
        elif case=="dcp":
            dest=folder/"native-transport.dcp";dest.write_bytes(b"truncated native checkpoint")
            doc["artifacts"][dest.name]=sha(dest)
        path.write_text(json.dumps(doc,indent=2)+"\n")
        if case=="truncated":path.write_bytes(path.read_bytes()[:100])
        try:validate_native(path,sources)
        except (ValueError,zipfile.BadZipFile) as error:
            results.append(dict(case=case,rejected_before_vcs=True,error=str(error),path=str(path),sha256=sha(path)))
        else:require(False,"incompatible native receipt admitted: "+case)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "all evidence belongs under runs")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+"-", dir=args.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda",
               scope="coordinated physical/native MMIO/DMA component only", sources=sources,
               physical_fpga_capture=False, full_image=False, cpu_restore_verified=False,
               cpu_live_acceptance=False, production_owner_integration=False,
               source_root=str(ROOT), host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat())
    commands = []

    def save():
        (out/"summary.json").write_text(json.dumps(doc, indent=2)+"\n")

    def run(argv, name, *, cwd=out, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(out/(name+".log")))
        commands.append(row)
        with Path(row["log"]).open("w") as f:
            result = subprocess.run(row["argv"], cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(row["log"]))
        doc.update(commands=commands, status="running" if result.returncode == expected else "fail")
        save()
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()

    save(); print(out, flush=True)
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native localhost Vivado required")
        for n in SOURCES:
            dest=out/"sources"/n; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/n, dest)
            if n in (*RTL, TB, EXIT): shutil.copyfile(ROOT/n, out/Path(n).name)
        vendor = Path(os.environ["XILINX_VIVADO"])/"data/verilog/src"
        doc["vendor_models"] = {}
        for name, path in (("BUFGCE.v", vendor/"unisims/BUFGCE.v"), ("glbl.v", vendor/"glbl.v")):
            shutil.copyfile(path, out/name)
            doc["vendor_models"][name] = dict(original_path=str(path), sha256=sha(path))
        (out/"native.tcl").write_text(tcl())
        doc["inputs"]={str(p.relative_to(out)):sha(p) for p in out.rglob("*") if p.is_file() and p.name!="summary.json"}
        text=run(["vivado", "-mode", "batch", "-source", "native.tcl"], "native")
        require("NATIVE_TRANSPORT_SYNTH_PASS" in text and not re.search(r"ERROR:|CRITICAL WARNING:", text), "native synthesis failed")
        timing=(out/"timing.rpt").read_text()
        require("There are 0 combinational loops in the design." in timing and
                "There are 0 combinational latch loops" in timing, "combinational permission/clock loop")
        doc["register_bits"]=1666
    else:
        require(str(ROOT).startswith("/scratch/") and shutil.which("vcs")==toolchain.VCS and
                toolchain.VCS.endswith("Y-2026.03-SP2/bin/vcs"), "EDA SP2 required")
        require(args.native is not None, "exact source-bound native receipt required")
        receipt=local(ROOT, str(args.native)); native=validate_native(receipt, sources)
        doc["receipt_negatives"]=receipt_negatives(receipt,sources,out/"receipt-negatives")
        doc["native_receipt"]=dict(path=str(receipt), sha256=sha(receipt))
        for name in native["inputs"]:
            dest=out/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(receipt.parent/name,dest)
        doc["inputs"]=native["inputs"]
        rtl=[out/Path(n).name for n in RTL]
        other=[out/"BUFGCE.v",out/"glbl.v",out/Path(EXIT).name,out/Path(TB).name]
        common=[toolchain.VCS,"-full64","-sverilog","-timescale=1ns/1ps","-Mupdate","-debug_access+all",
                "-top","native_capture_transport_tb","-top","glbl"]
        doc["waves"],doc["captures"]=[],[]
        for bits in GEOMETRIES:
            folder=out/f"unit-{bits}"; folder.mkdir()
            run(common+[f"+define+CAPTURE_BITS={bits}","-Mdir="+str(folder/"csrc"),"-o",folder/"simv",*rtl,*other], f"compile-{bits}")
            for case in CASES:
                text=run([folder/"simv","-no_save","+CASE="+case],f"run-{bits}-{case}",cwd=folder)
                token="NATIVE_TRANSPORT_PASS" if case=="healthy" else "NATIVE_TRANSPORT_RECOVERY_PASS" if case.startswith("abort-") else "NATIVE_TRANSPORT_NEGATIVE_PASS"
                require(token in text and "DIVERGENCE" not in text, "incomplete native transport scope")
                if case=="healthy":
                    require(f"NATIVE_TRANSPORT_PASS bits={bits} cuts=13 requests=52" in text,
                            "missing complete native bit-identity capture sequence")
                wave=folder/(case+".vcd"); (folder/"native-capture-transport.vcd").rename(wave)
                wave_result=audit_wave(wave,bits)
                doc["waves"].append(wave_result)
                if case=="healthy" or case.startswith("abort-"):
                    for path in sorted(folder.glob("cut-*.frames")):
                        renamed=path.with_name(case+"-"+path.name);path.rename(renamed)
                        doc["captures"].append(dict(bits=bits,case=case,**audit_frames(renamed,bits,wave_result["capture_vectors"])))
        # A real compiled datapath mutation must stop on the first divergent
        # native word, before that frame can be acknowledged by the consumer.
        folder=out/"compiled-corrupt";folder.mkdir()
        original=(out/"CheckpointNativeCaptureTransport.sv").read_text()
        needle="snapshot_response_data <= snapshot_word;"
        require(original.count(needle)==1,"ambiguous semantic mutation")
        broken=folder/"transport.sv";broken.write_text(original.replace(needle,"snapshot_response_data <= snapshot_word ^ 1'b1;"))
        run(common+["+define+CAPTURE_BITS=1036","-Mdir="+str(folder/"csrc"),"-o",folder/"simv",
            *[p for p in rtl if p.name!="CheckpointNativeCaptureTransport.sv"],broken,*other],"corrupt-compile")
        text=run([folder/"simv","-no_save"],"corrupt-run",cwd=folder,expected=1)
        require("signal=native snapshot DMA word frames_ack=5 words_ack=4 requests_ack=4" in text,
                "semantic fault did not stop before first native frame acknowledgement")
        folder=out/"compiled-early-hold";folder.mkdir()
        needle="assign functional_hold = native_hold;"
        require(original.count(needle)==1,"ambiguous native hold mutation")
        broken=folder/"transport.sv";broken.write_text(original.replace(needle,"assign functional_hold = freeze;"))
        run(common+["+define+CAPTURE_BITS=1036","-Mdir="+str(folder/"csrc"),"-o",folder/"simv",
            *[p for p in rtl if p.name!="CheckpointNativeCaptureTransport.sv"],broken,*other],"early-hold-compile")
        text=run([folder/"simv","-no_save"],"early-hold-run",cwd=folder,expected=1)
        require("signal=independent original functional state frames_ack=0 words_ack=0 requests_ack=0" in text,
                "one-edge-early native freeze did not stop at the first inconsistent functional edge")
        folder=out/"compiled-start-guard";folder.mkdir()
        needle="wire command_allowed = !is_start || start_allowed;"
        require(original.count(needle)==1,"ambiguous restart guard mutation")
        broken=folder/"transport.sv";broken.write_text(original.replace(needle,"wire command_allowed = 1'b1;"))
        run(common+["+define+CAPTURE_BITS=1036","-Mdir="+str(folder/"csrc"),"-o",folder/"simv",
            *[p for p in rtl if p.name!="CheckpointNativeCaptureTransport.sv"],broken,*other],"start-guard-compile")
        text=run([folder/"simv","-no_save"],"start-guard-run",cwd=folder,expected=1)
        require("signal=start backpressure during physical release frames_ack=23 words_ack=21 requests_ack=4" in text,
                "removed restart guard did not stop before premature command acceptance")
        folder=out/"compiled-permutation";folder.mkdir()
        snapshot_original=(out/"CheckpointNativeStateSnapshot.sv").read_text()
        needle="payload <= live_state;"
        require(snapshot_original.count(needle)==1,"ambiguous staged-bit permutation")
        broken=folder/"snapshot.sv";broken.write_text(snapshot_original.replace(needle,
            "payload <= {live_state[BITS-1:2], live_state[0], live_state[1]};"))
        run(common+["+define+CAPTURE_BITS=1036","-Mdir="+str(folder/"csrc"),"-o",folder/"simv",
            *[p for p in rtl if p.name!="CheckpointNativeStateSnapshot.sv"],broken,*other],"permutation-compile")
        text=run([folder/"simv","-no_save"],"permutation-run",cwd=folder,expected=1)
        require("signal=all staged native bits before first bank acknowledgement frames_ack=0 words_ack=0 requests_ack=0" in text,
                "staged native permutation did not stop before the first bank or stream acknowledgement")
        permutation_rejected=False
        try:audit_wave(folder/"native-capture-transport.vcd",1036)
        except ValueError:permutation_rejected=True
        require(permutation_rejected,"independent original-register audit accepted the staged native permutation")
        doc.update(geometries=list(GEOMETRIES),negative_processes=7*6,recovery_processes=7*3,
                   compiled_semantic_fault_rejected_before_ack=True,
                   compiled_early_hold_rejected_before_ack=True,
                   compiled_restart_guard_rejected_before_ack=True,
                   compiled_permutation_rejected_before_ack=True,
                   independent_permutation_rejected=True,identity_planes=13)
    require(sources=={n:sha(ROOT/n) for n in SOURCES}, "source changed during verification")
    doc.update(status="pass",commands=commands,artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob("*")
        if p.is_file() and p.suffix in {".log",".rpt",".dcp",".vcd",".frames"}})
    save(); print(out/"summary.json",flush=True)


if __name__=="__main__":
    main()
