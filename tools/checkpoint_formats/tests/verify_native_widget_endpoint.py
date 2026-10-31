"""Synthesize the generated native Chisel endpoint here; execute it only on EDA.

This preparatory endpoint connects the actual NASTI/shadow equations to the
actual staged native transport. It establishes no production owner or restore.
Every attempt has a new directory; completed receipts are never rewritten.
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

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_native_state_capture_wave import audit as audit_native

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
TOP = "CheckpointNativeWidgetEndpoint"
TB = "tools/checkpoint_formats/tests/native_widget_endpoint_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
PREFIX = "sims/firesim/sim/midas/src/main/verilog/"
RESOURCES = tuple(n + ".sv" for n in (
    "CheckpointNativeCaptureTransport", "CheckpointNativeStateCapture", "CheckpointNativeStateSnapshot",
    "CheckpointSnapshotStateBank", "CheckpointPhysicalClockCut", "CheckpointCaptureTransport", "CheckpointCaptureCut"))
RTL = tuple(PREFIX + n for n in RESOURCES)
SOURCES = (*RTL, TB, EXIT, "tools/checkpoint_formats/tests/verify_native_widget_endpoint.py",
    "tools/checkpoint_formats/tests/audit_native_state_capture_wave.py",
    "tools/checkpoint_formats/toolchain.py", "tools/checkpoint_formats/codec.py",
    "tools/checkpoint_formats/fpga_transport.py", "tools/checkpoint_formats/regression_runner.py",
    *tuple("sims/firesim/sim/midas/src/main/scala/midas/widgets/" + n + ".scala" for n in (
        "CheckpointNativeWidgetEndpoint", "CheckpointWidgetEndpoint", "CheckpointLiveWidgetSnapshot",
        "CheckpointNastiState", "CheckpointCaptureWidget")),
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureNativeEndpointSpec.scala")
PROBE = "probe/CheckpointNativeEndpointLayoutProbe.v"
GENERATED = (TOP + ".v", "native-endpoint-observation.json", *RESOURCES, PROBE)
ELABORATION_INPUTS = ("elaboration.json", "scala-summary.json", "scala-execution.log", "scala-run.sh")
HASH = int("1234567890abcdef" * 4, 16)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tcl():
    return """set_param general.maxThreads 4
read_verilog generated/CheckpointNativeWidgetEndpoint.v
read_verilog -sv """ + " ".join("generated/" + n for n in RESOURCES) + """
synth_design -top CheckpointNativeWidgetEndpoint -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME =~ BUFG*}]] != 0} {error "external network mode instantiated duplicate gates"}
set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] < 2400} {error "missing native/endpoint/shadow storage"}
set clocks [get_pins -of_objects $registers -filter {REF_PIN_NAME == C}]
if {[llength $clocks] != [llength $registers]} {error "register clock coverage"}
foreach {name count} {io_native_rawControlState 760 io_native_nativeControlBankState 67 io_native_endpointControlState 827 io_endpointState 758} {
  if {[llength [get_ports [format {%s[*]} $name]]] != $count} {error "changed observation width $name"}
}
# These output bits expose the actual 67 bank registers and must each have a
# distinct original storage driver, rather than a synthesized constant alias.
set bank_drivers {}
for {set i 0} {$i < 67} {incr i} {
  set port [get_ports [format {io_native_nativeControlBankState[%d]} $i]]
  set driver [get_pins -leaf -of_objects [get_nets -of_objects $port] -filter {DIRECTION == OUT}]
  if {[llength $driver] != 1 || [get_property REF_PIN_NAME $driver] ne "Q" ||
      ![string match FD* [get_property REF_NAME [get_cells -of_objects $driver]]]} {error "missing separate bank bit $i"}
  lappend bank_drivers [get_property NAME $driver]
  puts "NATIVE_ENDPOINT_BANK_BIT $i [get_property NAME $driver]"
}
if {[llength [lsort -unique $bank_drivers]] != 67} {error "aliased separate native bank"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-endpoint.dcp
puts "NATIVE_ENDPOINT_SYNTH_PASS view_bits=827 shadow_bits=1585 separate_bank_bits=67 registers=[llength $registers]"
"""


def validate_generated(directory, sources):
    """Require emitted native resources to equal their current tracked bytes."""
    for name in GENERATED:
        p = directory / name
        require(p.is_file() and not p.is_symlink(), "missing/linked generated endpoint input " + name)
    for name in RESOURCES:
        require(sha(directory/name) == sources[PREFIX+name], "generated native resource differs from current source " + name)
    metadata = json.loads((directory / "native-endpoint-observation.json").read_text())
    expected = dict(layout_version=1, original_bits=130, gates=3, owners=2, external_clock_network=1,
        clock_ownership="externally_owned_clock_network_required",
        external_clock_contract="caller_supplies_raw_clock_and_routes_clock_mask_and_ce_to_separately_owned_gates",
        root_and_gate_clock_outputs="constant_zero_in_external_clock_network_mode",
        endpoint_shadow_layout_version=2, endpoint_shadow_bits=1585, endpoint_shadow_restore_supported=False,
        raw_composite_bits=760, separate_bank_bits=67, endpoint_bits=827,
        raw_coordinator_offset=283, native_owner_bits=283, capture_native_control=True,
        original_entries=1, total_entries=4, snapshot_bank=252, native_control_bank=251,
        manifest_sha256="1234567890abcdef"*4,
        endpoint_order_lsb0=["coordinator_411", "native_owner", "payload_response_66", "native_control_bank_67"],
        complete_fpga_capture=False, deployable_capture_image=False, production_freeze_owners_bound=False,
        metasim_restore_supported=False)
    require(all(metadata.get(k) == v for k,v in expected.items()), "wrong generated native observation scope/layout")
    require(metadata.get("sources") == {n:sources[PREFIX+n] for n in RESOURCES}, "incomplete generated native source identity")
    text = (directory / (TOP + ".v")).read_text()
    require(re.search(r"module\s+" + TOP + r"\s*\(", text), "wrong generated Chisel top")
    for token in ("CheckpointNastiAdapter", "CheckpointLiveWidgetSnapshot", "CheckpointNativeCaptureTransport"):
        require(token in text, "generated endpoint omits actual module " + token)
    return metadata


def validate_elaboration(directory, sources, generated_origin=None):
    """Bind emitted bytes to the central completed Scala execution receipt."""
    elaboration=json.loads((directory/"elaboration.json").read_text())
    require(elaboration.get("status")=="pass" and elaboration.get("backend")=="f2" and
        elaboration.get("scope")=="completed Scala native endpoint elaboration", "wrong elaboration receipt scope/status")
    pin=elaboration.get("scala",{})
    require(isinstance(pin.get("path"),str) and sha(directory/"scala-summary.json")==pin.get("sha256"),
        "changed underlying Scala summary")
    scala=json.loads((directory/"scala-summary.json").read_text())
    require(scala.get("status")=="pass" and scala.get("backend")=="f2" and scala.get("returncode")==0,
        "underlying Scala execution failed")
    phases=scala.get("phases",[])
    require(len(phases)==3 and all(p.get("passed") is True and p.get("tests",0)>0 and
        p.get("tests")==p.get("succeeded") and all(p.get(k)==0 for k in
        ("aborted","failed","canceled","ignored","pending")) for p in phases), "incomplete three-phase Scala execution")
    require(sha(directory/"scala-execution.log")==scala.get("log_sha256") and
        sha(directory/"scala-run.sh")==scala.get("script_sha256"), "changed actual Scala script/log")
    current_scala={n:h for n,h in sources.items() if n.endswith(".scala")}
    bound=elaboration.get("sources",{})
    require(isinstance(bound,dict) and current_scala.items() <= bound.items() and
        all(n.endswith(".scala") for n in bound), "elaboration omits current native endpoint Scala sources")
    for table in (bound,scala.get("sources",{})):
        require(isinstance(table,dict) and table,"empty Scala source table")
        for name,digest in table.items():
            p=ROOT/name
            require(not Path(name).is_absolute() and p.resolve().is_relative_to(ROOT) and p.is_file() and
                not p.is_symlink() and sha(p)==digest,"Scala execution source differs from current bytes "+name)
    require(bound.items() <= scala["sources"].items(),"elaboration source map differs from completed Scala execution")
    generated=elaboration.get("generated",{})
    require(isinstance(generated,dict) and set(GENERATED).issubset(generated), "elaboration omits consumed generated files")
    generated_dir=local(ROOT,elaboration.get("generated_directory",""))
    require(generated_dir.resolve().is_relative_to(RUNS) and
        generated_dir.resolve().is_relative_to(local(ROOT,scala.get("generated","")).resolve()),
        "elaboration output escapes completed Scala execution")
    if generated_origin is not None:
        require(generated_dir.resolve()==local(ROOT,str(generated_origin)).resolve(), "elaboration directory differs from --generated")
    for name,digest in generated.items():
        p=directory/"generated"/name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and
            p.resolve().is_relative_to((directory/"generated").resolve()) and p.is_file() and
            not p.is_symlink() and sha(p)==digest,"generated bytes differ from actual elaboration "+name)
    text=(directory/"scala-execution.log").read_text()
    require("NATIVE_ENDPOINT_ELABORATED" in text and "top=CheckpointNativeWidgetEndpoint bits=130 gates=3 owners=2 entries=1 shadow=1585" in text,
        "Scala execution log omits actual native endpoint elaboration")
    return elaboration


def validate_inputs(directory, inputs, sources, generated_origin=None):
    require(set(sources) == set(SOURCES), "wrong current source namespace")
    elaboration=validate_elaboration(directory,sources,generated_origin)
    expected = {"sources/"+n:h for n,h in sources.items()}
    expected.update({"generated/"+n:h for n,h in elaboration["generated"].items()})
    expected.update({n:sha(directory/n) for n in ELABORATION_INPUTS})
    expected["native.tcl"] = hashlib.sha256(tcl().encode()).hexdigest()
    require(inputs == expected, "native source/generated/Tcl namespace differs")
    for name,digest in expected.items():
        p = directory/name
        require(p.is_file() and not p.is_symlink() and sha(p) == digest, "changed frozen endpoint input " + name)
    require((directory/"native.tcl").read_text() == tcl(), "changed native synthesis recipe")
    return validate_generated(directory/"generated", sources)


def audit_frames(path):
    frames = [int(line,16) for line in path.read_text().splitlines()]
    require(len(frames) == 11, "incomplete endpoint native DMA frames")
    cut = field(frames[0],96,64)
    words = []
    selectors = [(0,0,64,1,0)] + [(1,i,64,251,0) for i in range(5)] + [(2,i,64,252,0) for i in range(2)] + [(3,0,2,252,1)]
    for index,frame in enumerate(frames):
        require(field(frame,0,64) == 0x3154504b434d5346 and field(frame,64,16) == 1 and
            field(frame,96,64) == cut, "DMA identity/cut differs")
        require(field(frame,80,16) == (1 if index == 0 else 3 if index == 10 else 2), "DMA frame order differs")
        require(field(frame,160,64) == (0 if index == 0 else 9 if index == 10 else index-1), "DMA sequence differs")
        if index == 0:
            require(field(frame,224,32) == 4 and field(frame,256,256) == HASH, "DMA manifest/count differs")
        elif index != 10:
            require(tuple(field(frame,o,w) for o,w in ((224,32),(256,32),(288,16),(304,8),(312,16))) == selectors[index-1], "DMA selector differs")
            require(field(frame,328,8) == 0 and frame >> 400 == 0, "noncanonical DMA data padding")
            words.append(field(frame,336,64))
    require(field(frames[-1],224,32) == crc32c(b"".join(f.to_bytes(64,"little") for f in frames[:-1]))^0xffffffff,
        "DMA CRC differs")
    require(frames[-1] >> 256 == 0 and words[0] == 0x123456789abcdef0, "DMA trailer/external bank differs")
    owner = sum(w << (64*i) for i,w in enumerate(words[1:6]))
    payload = sum(w << (64*i) for i,w in enumerate(words[6:]))
    require(owner >> 283 == payload >> 130 == 0 and owner & ((1<<130)-1) == payload, "native owner/payload/padding differs")
    require(field(owner,130,1) == 1 and field(owner,131,64) == cut and field(owner,195,6) == 0,
        "staging owner/label/error differs")
    require(field(owner,201,3) == 3 and field(owner,207,64) == cut and field(owner,271,3) == 0 and
        field(owner,274,3) == 3 and field(owner,277,6) == 0, "physical/native owner state differs")
    return dict(cut=cut,frames=11,words=9,owner_bits=283,sha256=sha(path))


def audit_observation_wave(path):
    """Independent bitwise layout and preedge shadow audit from original groups.

    The SV bench reconstructs each group directly from original register names;
    the native-owner auditor separately checks every member and sampling edge.
    This second parser checks the endpoint's reordered view and immutable bank.
    """
    prefix = "native_widget_endpoint_tb."
    names = ("clock", "reset", "original_view", "endpoint_view", "original_endpoint", "endpoint_state",
        "original_bank", "bank_state", "raw_state", "original_payload_response", "original_coordinator", "original_owner",
        "dut.snapshot.io_access", "dut.snapshot.io_write", "dut.snapshot.io_address", "dut.snapshot.io_data",
        "dut.snapshot.io_error", "dut.snapshot.saved")
    wanted = {prefix+n:n for n in names}
    scopes=[];codes={};values={};previous={};samples=captures=0
    def sample():
        nonlocal previous,samples,captures
        now={n:values.get(c,"x") for n,c in codes.items()}
        binary=lambda d,n:re.fullmatch("[01]+",d.get(n,"x")) is not None
        integer=lambda d,n:int(d[n],2)
        if all(binary(now,n) for n in names[:12]):
            owner=integer(now,"original_owner");coordinator=integer(now,"original_coordinator")
            response=integer(now,"original_payload_response");bank=integer(now,"original_bank")
            view=coordinator | owner << 411 | response << 694 | bank << 760
            require(integer(now,"endpoint_view") == view, "wave endpoint coordinator/native/separate67 mapping differs")
            require(integer(now,"raw_state") == owner | coordinator << 283 | response << 694, "wave raw native composite differs")
            require(integer(now,"bank_state") == bank and integer(now,"endpoint_state") == integer(now,"original_endpoint"),
                "wave endpoint/separate bank original state differs")
            samples+=1
        if now.get("clock") == "1" and previous.get("clock") == "0" and previous.get("reset") == "0":
            take=all(previous.get(n)=="1" for n in ("dut.snapshot.io_access","dut.snapshot.io_write")) and previous.get("dut.snapshot.io_error")=="0"
            if take and binary(previous,"dut.snapshot.io_address") and binary(previous,"dut.snapshot.io_data") and integer(previous,"dut.snapshot.io_address")==0x78 and integer(previous,"dut.snapshot.io_data")==1:
                require(integer(now,"dut.snapshot.saved") == integer(previous,"original_view") | integer(previous,"original_endpoint") << 827,
                    "shadow did not stage complete preedge original endpoint/native/separate67")
                captures+=1
        previous=now
    with Path(path).open() as stream:
        for line in stream:
            parts=line.split()
            if not parts:continue
            if parts[0]=="$scope":scopes.append(parts[2])
            elif parts[0]=="$upscope":scopes.pop()
            elif parts[0]=="$var":
                name=".".join(scopes+[parts[4].lstrip("\\")])
                if name in wanted:codes[wanted[name]]=parts[3]
            elif line.startswith("#"):sample()
            elif line[0] in "bB" and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
            elif line[0] in "01xXzZ":values[line[1:].strip()]=line[0].lower()
    sample();require(set(codes)==set(names) and samples>0 and captures==4,"incomplete native endpoint shadow waveform")
    return dict(samples=samples,captures=captures,shadow_bits=1585,separate_bank_bits=67)


def coordinator_fault(text):
    """Change one semantic selection in all three emitted expression copies.

    FIRRTL duplicates this expression for the exported view, cut predicate
    and shadow payload, and wraps the two longer declarations across lines.
    Bind every copy rather than mutating an unused or merely observed alias.
    """
    before="nativeTransport_control_state[693:283]"
    after="nativeTransport_control_state[410:0]"
    widths={"view_lo":"693:0", "view":"826:0", "snapshot_io_live_lo":"1019:0"}
    pattern=r"(?m)^\s*wire\s+\[([^]]+)\]\s+(view_lo|view|snapshot_io_live_lo)\s*=[^;]+;"
    matches=list(re.finditer(pattern,text))
    require(len(matches)==3 and {m[2] for m in matches}==set(widths) and text.count(before)==3,
        "ambiguous generated coordinator expression copies")
    sites=[]
    for match in matches:
        require(match[1]==widths[match[2]] and match[0].count(before)==1,
            "changed generated coordinator declaration "+match[2])
        sites.append(dict(name=match[2],line=text.count("\n",0,match.start())+1,
            before=match[0],after=match[0].replace(before,after)))
    return text.replace(before,after),dict(semantic_edit=dict(before=before,after=after),sites=sites)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("vivado","vcs"),required=True)
    parser.add_argument("--generated",type=Path,help="directory containing the emitted Chisel top and native resources")
    parser.add_argument("--elaboration",type=Path,help="central receipt binding generated bytes to completed Scala execution")
    parser.add_argument("--native",type=Path,help="successful native summary.json or its directory")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS),"evidence must be under runs")
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+"-",dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    doc=dict(status="running",backend="f2" if args.mode=="vivado" else "eda",observed_utc=datetime.now(timezone.utc).isoformat(),
        source_root=str(ROOT),host=socket.gethostname(),sources=sources,commands=[],
        scope="actual generated Chisel native NASTI/shadow endpoint component; no production installation/restore ownership",
        physical_fpga_capture=False,full_image=False,complete_state_ownership=False,production_restore_enabled=False)
    print(out,flush=True)
    def run(argv,label,cwd=out,expected=0):
        log=cwd/(label+".log")
        with log.open("x") as stream:
            result=subprocess.run(list(map(str,argv)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        doc["commands"].append(dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(log),log_sha256=sha(log),returncode=result.returncode))
        with (out/"commands.json").open("w") as stream:json.dump(doc["commands"],stream,indent=2);stream.write("\n")
        require(result.returncode==expected,"inspect exact compiler/runtime log "+str(log))
        return log.read_text()
    try:
        if args.mode=="vivado":
            require(ROOT==Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),"native manager Vivado required")
            require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS),"generated endpoint beneath runs required")
            require(args.elaboration is not None and args.elaboration.resolve().is_relative_to(RUNS),"completed Scala elaboration receipt beneath runs required")
            elaboration=json.loads(args.elaboration.read_text())
            require(isinstance(elaboration.get("generated"),dict),"missing elaboration generated table")
            shutil.copyfile(args.elaboration,out/"elaboration.json")
            scala_path=local(ROOT,elaboration["scala"]["path"])
            require(scala_path.resolve().is_relative_to(RUNS) and sha(scala_path)==elaboration["scala"]["sha256"],"changed original Scala summary")
            shutil.copyfile(scala_path,out/"scala-summary.json")
            scala=json.loads(scala_path.read_text());scala_log=local(ROOT,scala["log"])
            require(scala_log.resolve().is_relative_to(RUNS),"Scala log outside runs")
            shutil.copyfile(scala_log,out/"scala-execution.log");shutil.copyfile(scala_path.parent/"run.sh",out/"scala-run.sh")
            for name in SOURCES:
                dest=out/"sources"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
            (out/"generated").mkdir()
            for name in elaboration["generated"]:
                require(not Path(name).is_absolute() and ".." not in Path(name).parts,"unsafe generated elaboration path")
                dest=out/"generated"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.generated/name,dest)
            (out/"native.tcl").write_text(tcl())
            # Refuse missing/ambiguous fault sites before committing native time.
            coordinator_fault((out/"generated"/(TOP+".v")).read_text())
            doc["generated_origin"]=str(args.generated.resolve())
            doc["elaboration"]=dict(path=str(args.elaboration.resolve()),sha256=sha(args.elaboration))
            doc["inputs"]={**{"sources/"+n:h for n,h in sources.items()},
                **{"generated/"+n:h for n,h in elaboration["generated"].items()},
                **{n:sha(out/n) for n in ELABORATION_INPUTS},"native.tcl":sha(out/"native.tcl")}
            doc["observation_binding"]=validate_inputs(out,doc["inputs"],sources,args.generated)
            text=run(["vivado","-mode","batch","-source","native.tcl"],"native")
            match=re.search(r"NATIVE_ENDPOINT_SYNTH_PASS view_bits=827 shadow_bits=1585 separate_bank_bits=67 registers=(\d+)",text)
            require(match and not re.search(r"ERROR:|CRITICAL WARNING:",text),"native endpoint synthesis did not pass")
            doc["registers"]=int(match[1]);doc["tool_version"]=run(["vivado","-version"],"version")
            vendor=Path(shutil.which("vivado")).resolve().parents[1]/"data/verilog/src"
            for name,source in (("BUFGCE.v",vendor/"unisims/BUFGCE.v"),("glbl.v",vendor/"glbl.v")):
                require(source.is_file(),"native vendor model missing "+str(source));shutil.copyfile(source,out/name)
            doc["vendor_models"]={n:sha(out/n) for n in ("BUFGCE.v","glbl.v")}
        else:
            require(ROOT==Path("/scratch/jfx/chia-cy-checkpoint-restore") and shutil.which("vcs")==toolchain.VCS and
                toolchain.VCS=="/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs" and os.environ.get("VCS_HOME")==toolchain.VCS_HOME,
                "dedicated EDA mirror/native SP2 required; source vcs-env.sh last")
            require(args.native is not None,"successful native receipt required")
            receipt=local(ROOT,str(args.native));receipt=receipt/"summary.json" if receipt.is_dir() else receipt
            require(receipt.resolve().is_relative_to(RUNS),"native receipt beneath runs required")
            native=json.loads(receipt.read_text())
            require(native["status"]=="pass" and native["backend"]=="f2" and native["sources"]==sources and
                native["physical_fpga_capture"] is False and native["production_restore_enabled"] is False,"stale/wrong native endpoint receipt")
            require(sha(receipt.parent/"elaboration.json")==native.get("elaboration",{}).get("sha256"),"changed native elaboration receipt pin")
            validate_inputs(receipt.parent,native["inputs"],sources,native["generated_origin"])
            for group in ("inputs","artifacts"):
                for name,digest in native[group].items():
                    p=receipt.parent/name
                    require(p.resolve().is_relative_to(receipt.parent.resolve()) and not p.is_symlink() and sha(p)==digest,"changed native artifact "+name)
            for name in native["inputs"]:
                dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(receipt.parent/name,dest)
            doc["native"]=dict(path=str(receipt),sha256=sha(receipt));doc["inputs"]=native["inputs"]
            doc["elaboration"]=native["elaboration"];doc["generated_origin"]=native["generated_origin"]
            doc["observation_binding"]=validate_inputs(out,doc["inputs"],sources,native["generated_origin"])
            for name,digest in native["vendor_models"].items():
                require(name in ("BUFGCE.v","glbl.v") and sha(receipt.parent/name)==digest,"changed native vendor model")
                shutil.copyfile(receipt.parent/name,out/name)
            require(set(native["vendor_models"])=={"BUFGCE.v","glbl.v"},"incomplete native vendor models")
            doc["vendor_models"]=native["vendor_models"]
            common=[toolchain.VCS,"-full64","-sverilog","-timescale=1ns/1ps","-Mupdate","-debug_access+all",
                "-top","native_widget_endpoint_tb","-top","glbl"]
            frozen=out/"sources"
            files=[*[out/"generated"/n for n in RESOURCES],out/"generated"/PROBE,
                frozen/TB,frozen/EXIT,out/"BUFGCE.v",out/"glbl.v"]
            run([*common,"-Mdir=csrc","-o","simv",out/"generated"/(TOP+".v"),*files],"compile")
            doc["executions"]=[]
            for case,marker in (("healthy","NATIVE_ENDPOINT_PASS cuts=4 frames_per_cut=11 shadow_bits=1585 shadow_words=25 separate_bank_bits=67"),
                ("lost-owner","NATIVE_ENDPOINT_OWNER_LOSS_PASS control_acks_before_reset=0 recovery_frames=11"),
                ("abort","NATIVE_ENDPOINT_ABORT_PASS published_frames=0 blocked_restart=1 recovery_frames=11")):
                work=out/case;work.mkdir()
                text=run([out/"simv","-no_save","+CASE="+case],"run",work)
                require(marker in text and "DIVERGENCE" not in text,"native endpoint case incomplete "+case)
                require("NATIVE_ENDPOINT_LAYOUT_PASS planes=827 raw_bits=760 separate_bank_bits=67 correct_high=1 misleading_low=0" in text,
                    "incomplete independent literal layout planes")
                row=dict(case=case,marker=marker,layout_planes=827,correct_high_certificate=True,misleading_low_certificate=False)
                if case=="healthy":
                    row["native_wave"]=audit_native(work/"native-widget-endpoint.vcd",130,top="native_widget_endpoint_tb.dut.nativeTransport.native_capture")
                    require(row["native_wave"]["captures"]==4,"missing original native cuts")
                    row["endpoint_wave"]=audit_observation_wave(work/"native-widget-endpoint.vcd")
                    row["cuts"]=[audit_frames(work/f"cut{i}.frames") for i in range(4)]
                    require(len({r["cut"] for r in row["cuts"]})==4,"nonprogressing native target cuts")
                    for i in range(4):
                        lines=(work/f"cut{i}.shadow").read_text().splitlines()
                        require(len(lines)==25 and all(re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8}",n) for n in lines),"incomplete frontdoor shadow words")
                else:row["recovery"]=audit_frames(work/"recovery.frames")
                doc["executions"].append(row)
            mutated,site=coordinator_fault((out/"generated"/(TOP+".v")).read_text())
            (out/"broken-coordinator.v").write_text(mutated)
            run([*common,"-Mdir=broken-csrc","-o","broken-simv",out/"broken-coordinator.v",*files],"broken-compile")
            work=out/"broken-coordinator";work.mkdir()
            text=run([out/"broken-simv","-no_save"],"run",work,expected=1)
            lines=[n for n in text.splitlines() if n.startswith("NATIVE_ENDPOINT_DIVERGENCE")]
            require(len(lines)==1 and "signal=endpoint_coordinator_layout" in lines[0] and "shadow_captures=0" in lines[0],
                "compiled wrong coordinator mapping escaped first-fault oracle")
            require(all(re.search(r"\b"+name+r"=0\b",lines[0]) for name in
                ("frames","words","requests","control_acks","shadow_captures")),
                "compiled coordinator fault advanced an output/request/shadow acknowledgement")
            doc["compiled_fault"]=dict(site=site,first_fault=lines[0],source_sha256=sha(out/"broken-coordinator.v"))
        require(sources=={n:sha(ROOT/n) for n in SOURCES},"sources changed during endpoint verification")
        validate_inputs(out,doc["inputs"],sources,doc["generated_origin"])
        doc["status"]="pass"
    except Exception as error:
        doc.update(status="fail",error_type=type(error).__name__,error=str(error))
        raise
    finally:
        doc["artifacts"]={str(p.relative_to(out)):sha(p) for p in out.rglob("*") if p.is_file() and p.name!="summary.json"
            and not any(part in ("csrc","broken-csrc",".Xil") or part.endswith(".daidir") for part in p.relative_to(out).parts)
            and p.name not in ("simv","broken-simv")}
        with (out/"summary.json").open("x") as stream:json.dump(doc,stream,indent=2);stream.write("\n")
        print(out/"summary.json",flush=True)


if __name__=="__main__":
    main()
