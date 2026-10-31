"""Local F2-part synthesis and EDA SP2 snapshot-owner bank/DMA verification.

The actual native capture sequencer supplies the bank's immutable source.
This is component evidence: production Rocket hookup/owners remain required.
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
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_native_state_capture_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
PREFIX = "sims/firesim/sim/midas/src/main/verilog/"
BANK = PREFIX + "CheckpointSnapshotStateBank.sv"
RTL = tuple(PREFIX + n + ".sv" for n in (
    "CheckpointSnapshotStateBank", "CheckpointNativeCaptureTransport", "CheckpointNativeStateCapture",
    "CheckpointNativeStateSnapshot", "CheckpointPhysicalClockCut", "CheckpointCaptureCut", "CheckpointCaptureTransport"))
UNIT = "tools/checkpoint_formats/tests/snapshot_state_bank_tb.sv"
INTEGRATION = "tools/checkpoint_formats/tests/native_control_bank_transport_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
SOURCES = (*RTL, UNIT, INTEGRATION, EXIT, "tools/checkpoint_formats/tests/verify_snapshot_state_bank.py",
           "tools/checkpoint_formats/tests/audit_native_state_capture_wave.py",
           "tools/checkpoint_formats/toolchain.py", "tools/checkpoint_formats/codec.py",
           "tools/checkpoint_formats/fpga_transport.py", "tools/checkpoint_formats/regression_runner.py")
GEOMETRIES = (1, 64, 65, 130, 1036, 6656)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_inputs(directory, inputs, sources):
    """Bind consumed source bytes to the checkout, not a self-rehashed ledger."""
    require(set(sources)==set(SOURCES), "incomplete current source namespace")
    expected={"sources/"+name:digest for name,digest in sources.items()}
    expected["native.tcl"]=hashlib.sha256(tcl().encode()).hexdigest()
    require(inputs==expected, "frozen input table differs from current sources/native contract")
    for name,digest in expected.items():
        path=Path(directory)/name
        require(path.is_file() and not path.is_symlink() and sha(path)==digest,
                "frozen source/native contract bytes differ from current input "+name)


def tcl():
    return """set_param general.maxThreads 4
read_verilog -sv sources/sims/firesim/sim/midas/src/main/verilog/CheckpointSnapshotStateBank.sv
synth_design -top CheckpointSnapshotStateBank -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] != 67} {error "snapshot bank state count: [llength $registers]"}
set drivers {}
for {set index 0} {$index < 67} {incr index} {
    set port [get_ports [format {control_state[%d]} $index]]
    set net [get_nets -of_objects $port]
    set driver [get_pins -leaf -of_objects $net -filter {DIRECTION == OUT}]
    if {[llength $driver] != 1 || [get_property REF_PIN_NAME $driver] ne "Q"} {error "unmapped bank state bit $index"}
    set cell [get_cells -of_objects $driver]
    if {![string match FD* [get_property REF_NAME $cell]]} {error "non-register bank state bit $index"}
    lappend drivers [get_property NAME $driver]
    puts "SNAPSHOT_BANK_REGISTER $index [get_property NAME $driver]"
}
if {[llength [lsort -unique $drivers]] != 67} {error "aliased bank state"}
# Independently require every staged input bit in the real synthesized data
# cone. Registers/control observations alone cannot establish payload readout.
set data_inputs [all_fanin -flat -startpoints_only -to [get_pins -hier -filter {NAME =~ saved_data_reg*/D}]]
set payload_inputs [filter $data_inputs {NAME =~ snapshot_state*}]
if {[llength $payload_inputs] != 6727} {error "incomplete staged input cone: [llength $payload_inputs]"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force snapshot-bank.dcp
puts "SNAPSHOT_BANK_SYNTH_PASS state_bits=67 input_bits=6727"
close_design
read_verilog -sv """ + " ".join("sources/"+n for n in RTL) + """
synth_design -top CheckpointNativeCaptureTransport -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -generic {BITS=1036 GATES=3 OWNERS=2 ENTRIES=1 CAPTURE_NATIVE_CONTROL=1 MANIFEST_SHA256=256'h0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef}
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] != 1733} {error "incomplete integrated native/control/bank state: [llength $registers]"}
set drivers {}
foreach {port_name bits} {control_state 1666 native_control_bank_state 67} {
    for {set index 0} {$index < $bits} {incr index} {
        set port [get_ports [format {%s[%d]} $port_name $index]]
        set driver [get_pins -leaf -of_objects [get_nets -of_objects $port] -filter {DIRECTION == OUT}]
        if {[llength $driver] != 1 || [get_property REF_PIN_NAME $driver] ne "Q"} {error "unmapped integrated bit $port_name $index"}
        set cell [get_cells -of_objects $driver]
        if {![string match FD* [get_property REF_NAME $cell]]} {error "non-register integrated state bit"}
        lappend drivers [get_property NAME $driver]
        puts "INTEGRATED_BANK_REGISTER $port_name $index [get_property NAME $driver]"
    }
}
if {[llength [lsort -unique $drivers]] != 1733} {error "aliased integrated storage"}
report_utilization -file integrated-utilization.rpt
report_timing_summary -file integrated-timing.rpt
write_checkpoint -force integrated-bank.dcp
puts "INTEGRATED_BANK_SYNTH_PASS bits=1733"
"""


def audit_frames(path, bits, expected_owner=None):
    frames = [int(line, 16) for line in path.read_text().splitlines()]
    control_words = (bits+153+63)//64
    payload_words = (bits+63)//64
    require(len(frames) == control_words+payload_words+3, "incomplete bank/DMA stream")
    cut = field(frames[0], 96, 64)
    words = []
    for index, frame in enumerate(frames):
        require(field(frame, 0, 64) == 0x3154504b434d5346 and field(frame, 64, 16) == 1 and
                field(frame, 96, 64) == cut, "wrong DMA identity/cut")
        require(field(frame, 80, 16) == (1 if index == 0 else 3 if index == len(frames)-1 else 2),
                "wrong DMA frame order")
        require(field(frame, 160, 64) == (0 if index == 0 else len(frames)-2 if index == len(frames)-1 else index-1),
                "missing/duplicate DMA word")
        if index == 0:
            require(field(frame,224,32) == 2+bool(bits//64)+bool(bits%64) and
                    field(frame,256,256) == int("0123456789abcdef"*4,16), "wrong bound manifest/count")
        if 0 < index < len(frames)-1:
            words.append(field(frame, 336, 64))
            ordinal = 0 if index == 1 else 1 if index <= control_words+1 else 2 if index <= control_words+1+bits//64 else 2+bool(bits//64)
            address = 0 if index == 1 else index-2 if index <= control_words+1 else index-control_words-2 if index <= control_words+1+bits//64 else 0
            width = 64 if index <= control_words+1+bits//64 else bits%64
            bank = 1 if index == 1 else 251 if index <= control_words+1 else 252
            slot = int(index > control_words+1+bits//64)
            require(tuple(field(frame, o, w) for o, w in ((224,32),(256,32),(288,16),(304,8),(312,16))) ==
                    (ordinal,address,width,bank,slot), "wrong native-owner bank selector")
            require(field(frame,328,8) == 0 and frame >> 400 == 0, "noncanonical DMA reserved bits")
    raw = b"".join(f.to_bytes(64,"little") for f in frames[:-1])
    require(field(frames[-1],224,32) == crc32c(raw)^0xffffffff, "bad DMA CRC")
    require(frames[-1] >> 256 == 0, "noncanonical DMA trailer reserved bits")
    require(words[0] == 0x123456789abcdef0,"wrong original functional bank word")
    owner = sum(w << (64*i) for i,w in enumerate(words[1:control_words+1]))
    payload = sum(w << (64*i) for i,w in enumerate(words[control_words+1:]))
    require(owner >> (bits+153) == payload >> bits == 0, "noncanonical tail padding")
    require(owner & ((1 << bits)-1) == payload, "native owner/payload checkpoint disagreement")
    require(field(owner,bits,1) == 1 and field(owner,bits+1,64) == cut and field(owner,bits+65,6) == 0,
            "missing staged occupied/cycle/error state")
    physical = owner >> (bits+71)
    require(field(physical,0,3) == 3 and field(physical,6,64) == cut and field(physical,70,3) == 0,
            "missing physical mask/sample/release/cycle/error state")
    require(field(owner,bits+144,3) == 3 and field(owner,bits+147,6) == 0, "missing native sequencer phase/error")
    if expected_owner is not None:
        require(owner == expected_owner, "DMA native owner differs from independent original-register waveform")
    return dict(cut=cut, owner_bits=bits+153, control_words=control_words, payload_words=payload_words,
                frames=len(frames), sha256=sha(path))


def original_owners(path, bits):
    """Observe the underlying register groups, independently of packed ports."""
    prefix="native_control_bank_transport_tb.dut.native_capture."
    fields=(("snapshot.payload",bits),("snapshot.occupied",1),("snapshot.cut_cycle",64),("snapshot.error",6),
            ("physical.freeze_low",1),("physical.sampled",1),("physical.release_pending",1),
            ("physical.captured_ce",3),("physical.cut_cycle",64),("physical.error",3),("phase",3),("error",6))
    names={prefix+n:n for n,_ in fields};names[prefix+"valid"]="valid"
    scopes=[];codes={};values={};previous=False;owners=[]
    def sample():
        nonlocal previous
        now={n:values.get(c,"x") for n,c in codes.items()}
        valid=now.get("valid")=="1"
        if valid:
            require(len(codes)==len(names) and all(re.fullmatch("[01]+",now[n]) for n,_ in fields),"missing/unknown original owner")
            owner=offset=0
            for n,width in fields:
                owner |= int(now[n],2) << offset;offset += width
            if not previous:owners.append(owner)
            require(owner==owners[-1],"original native owner changed during DMA cut")
        previous=valid
    with Path(path).open() as stream:
        for line in stream:
            parts=line.split()
            if not parts:continue
            if parts[0]=="$scope":scopes.append(parts[2])
            elif parts[0]=="$upscope":scopes.pop()
            elif parts[0]=="$var":
                name=".".join(scopes+[parts[4].lstrip("\\")])
                if name in names:codes[names[name]]=parts[3]
            elif line.startswith("#"):sample()
            elif line[0] in "bB" and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
            elif line[0] in "01xXzZ":values[line[1:].strip()]=line[0].lower()
    sample();require(len(owners)==4,"missing complete original-owner cuts")
    return owners


def audit_bank_wave(path, bits, case):
    names=("clock","reset","read_enable","snapshot_state","request_valid","request_ready",
           "bank","slot","address","response_valid","response_ready","response_data","response_error",
           "dut.pending","dut.saved_data","dut.saved_error","dut.failed","control_state")
    wanted={"snapshot_state_bank_tb."+n:n for n in names}
    codes={};values={};scopes=[];previous={};samples=requests=acks=0
    def sample():
        nonlocal previous,samples,requests,acks
        now={n:values.get(c,"x") for n,c in codes.items()}
        binary=lambda d,n:n in d and re.fullmatch("[01]+",d[n]) is not None
        integer=lambda d,n:int(d[n],2)
        if all(binary(now,n) for n in names):
            require(integer(now,"control_state") == integer(now,"dut.saved_data") |
                    integer(now,"dut.saved_error") << 64 | integer(now,"dut.pending") << 65 |
                    integer(now,"dut.failed") << 66,"bank control readout omits original storage")
            permission=now['read_enable']=='1' and now['dut.failed']=='0' and now['reset']=='0'
            require(integer(now,'response_valid')==int(permission and now['dut.pending']=='1'),
                    'bank acknowledged without common-cut permission')
            samples+=1
        if now.get('clock')=='1' and previous.get('clock')=='0' and previous.get('reset')=='0':
            if previous.get('request_valid')==previous.get('request_ready')=='1':
                require(all(binary(previous,n) for n in ('bank','slot','address','snapshot_state')),'unknown accepted bank selector')
                invalid=integer(previous,'bank')!=254 or integer(previous,'slot')!=17 or integer(previous,'address') >= (bits+63)//64
                data=0 if invalid else (integer(previous,'snapshot_state') >> (64*integer(previous,'address'))) & ((1<<64)-1)
                require(integer(now,'dut.saved_data')==data and integer(now,'dut.saved_error')==int(invalid),
                        'bank word differs from independently sampled source/selector')
                requests+=1
            if previous.get('response_valid')==previous.get('response_ready')=='1':acks+=1
        previous=now
    with Path(path).open() as stream:
        for line in stream:
            parts=line.split()
            if not parts:continue
            if parts[0]=='$scope':scopes.append(parts[2])
            elif parts[0]=='$upscope':scopes.pop()
            elif parts[0]=='$var':
                name='.'.join(scopes+[parts[4].lstrip('\\')])
                if name in wanted:codes[wanted[name]]=parts[3]
            elif line.startswith('#'):sample()
            elif line[0] in 'bB' and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
            elif line[0] in '01xXzZ':values[line[1:].strip()]=line[0].lower()
    sample()
    require(set(codes)==set(names) and samples>0,'incomplete bank debug readback')
    expected_requests=(bits+63)//64*((bits-1).bit_length()+1)+5
    require((requests,acks)==((expected_requests,)*2 if case=='healthy' else (1,0)),
            'bank waveform request/acknowledgement scope differs')
    return dict(storage_bits=67,samples=samples,requests=requests,acknowledgements=acks)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("vivado","vcs"),required=True)
    parser.add_argument("--native",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence must be under runs")
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+"-",dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    doc=dict(status="running",backend="f2" if args.mode=="vivado" else "eda",sources=sources,
             observed_utc=datetime.now(timezone.utc).isoformat(),source_root=str(ROOT),host=socket.gethostname(),
             scope="staged native-owner bank plus actual component MMIO/DMA; production hookup pending",
             physical_fpga_capture=False,full_image=False,complete_capture_owner=False,commands=[])

    def save():
        (out/"summary.json").write_text(json.dumps(doc,indent=2)+"\n")

    def run(argv,label,expected=0):
        log=out/(label+".log")
        with log.open("w") as stream:
            result=subprocess.run(list(map(str,argv)),cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        doc["commands"].append(dict(argv=list(map(str,argv)),cwd=str(out),log=str(log),log_sha256=sha(log),returncode=result.returncode))
        doc["status"]="running" if result.returncode==expected else "fail";save()
        require(result.returncode==expected, "inspect compiler/runtime log "+str(log))
        return log.read_text()

    save();print(out,flush=True)
    if args.mode=="vivado":
        require(ROOT==Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native localhost Vivado required")
        for name in SOURCES:
            dest=out/"sources"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        (out/"native.tcl").write_text(tcl())
        doc["inputs"]={str(p.relative_to(out)):sha(p) for p in out.rglob("*") if p.is_file() and p.name!="summary.json"}
        validate_inputs(out,doc['inputs'],sources)
        text=run(["vivado","-mode","batch","-source","native.tcl"],"native")
        require("SNAPSHOT_BANK_SYNTH_PASS state_bits=67 input_bits=6727" in text and
                "INTEGRATED_BANK_SYNTH_PASS bits=1733" in text and not re.search(r"ERROR:|CRITICAL WARNING:",text),
                "native bank synthesis/coverage did not pass")
    else:
        require(ROOT==Path("/scratch/jfx/chia-cy-checkpoint-restore") and shutil.which("vcs")==toolchain.VCS and
                toolchain.VCS=="/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "dedicated EDA mirror/native SP2 required")
        require(args.native is not None,"source-bound native receipt required")
        receipt=local(ROOT,str(args.native))
        require(receipt.resolve().is_relative_to(RUNS), "native evidence must be beneath runs")
        native=json.loads(receipt.read_text())
        require(native["status"]=="pass" and native["backend"]=="f2" and native["sources"]==sources,"stale native bank receipt")
        validate_inputs(receipt.parent,native['inputs'],sources)
        for group in ("inputs","artifacts"):
            for name,digest in native[group].items():require(sha(receipt.parent/name)==digest,"changed native evidence "+name)
        require((receipt.parent/"native.tcl").read_text()==tcl(),"changed native synthesis contract")
        for name in native["inputs"]:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(receipt.parent/name,dest)
        validate_inputs(out,native['inputs'],sources)
        doc["native"]=dict(path=str(receipt),sha256=sha(receipt));doc["inputs"]=native["inputs"]
        # Vendor models travel with their exact native installation bytes.
        for name in ("BUFGCE.v","glbl.v"):
            source=receipt.parent/name
            require(source.is_file(),"native vendor model missing "+name)
            require(sha(source)==native["vendor_models"][name],"changed native vendor model "+name)
            shutil.copyfile(source,out/name)
        common=[toolchain.VCS,"-full64","-sverilog","-timescale=1ns/1ps","-Mupdate","-debug_access+all"]
        doc["executions"]=[]
        doc["bank_wave_audits"]=[]
        for bits in GEOMETRIES:
            unit=out/f"unit-{bits}";unit.mkdir();simv=unit/"simv"
            run(common+[f"+define+SNAPSHOT_BITS={bits}","-top","snapshot_state_bank_tb","-Mdir="+str(unit/"csrc"),"-o",simv,
                        out/"sources"/BANK,out/"sources"/UNIT,out/"sources"/EXIT],f"unit-{bits}-compile")
            for case in ("healthy","lost-cut","reset"):
                text=run([simv,"-no_save","+CASE="+case],f"unit-{bits}-{case}")
                require(("SNAPSHOT_BANK_PASS" if case=="healthy" else "SNAPSHOT_BANK_NEGATIVE_PASS") in text and "DIVERGENCE" not in text,"bank case incomplete")
                shutil.move(out/"snapshot-bank.vcd",unit/(case+".vcd"))
                doc['bank_wave_audits'].append(dict(bits=bits,case=case,**audit_bank_wave(unit/(case+'.vcd'),bits,case)))
            integration=out/f"integration-{bits}";integration.mkdir();simv=integration/"simv"
            run(common+[f"+define+SNAPSHOT_BITS={bits}","-top","native_control_bank_transport_tb","-top","glbl","-Mdir="+str(integration/"csrc"),"-o",simv,
                        *[out/"sources"/n for n in RTL],out/"sources"/INTEGRATION,out/"sources"/EXIT,out/"BUFGCE.v",out/"glbl.v"],f"integration-{bits}-compile")
            text=run([simv,"-no_save"],f"integration-{bits}-run")
            require(f"CONTROL_BANK_TRANSPORT_PASS bits={bits} owner_bits={bits+153} cuts=4" in text and "DIVERGENCE" not in text,"incomplete native-owner DMA execution")
            wave=integration/"debug.vcd";shutil.move(out/"control-bank-transport.vcd",wave)
            wave_audit=audit(wave,bits,top="native_control_bank_transport_tb.dut.native_capture")
            require(wave_audit["captures"]==4,"missing independent complete native-owner waveform cuts")
            owner_values=original_owners(wave,bits)
            frames=[]
            for cut in range(4):
                dest=integration/f"cut{cut}.frames";shutil.move(out/dest.name,dest);frames.append(audit_frames(dest,bits,owner_values[cut]))
            require(len({r["cut"] for r in frames})==4,"non-progressing cuts")
            text=run([simv,"-no_save","+CASE=alias"],f"integration-{bits}-alias")
            require("CONTROL_BANK_ALIAS_PASS words=0 requests=0" in text and "DIVERGENCE" not in text,
                    "reserved control descriptor alias did not reject before request")
            shutil.move(out/"control-bank-transport.vcd",integration/"alias.vcd")
            shutil.move(out/"cut0.frames",integration/"alias.frames")
            text=run([simv,"-no_save","+CASE=abort-control"],f"integration-{bits}-abort-control")
            require("CONTROL_BANK_ABORT_PASS control_acknowledgements=1 safe_drain=1 published_control_words=0" in text and
                    "DIVERGENCE" not in text,"abort did not safely drain without publication")
            shutil.move(out/"control-bank-transport.vcd",integration/"abort-control.vcd")
            shutil.move(out/"cut0.frames",integration/"abort-control.frames")
            text=run([simv,"-no_save","+CASE=lost-control-cut"],f"integration-{bits}-lost-control-cut")
            require("CONTROL_BANK_LOST_CUT_PASS control_acknowledgements=0 common_reset_recovered=1" in text and
                    "DIVERGENCE" not in text,"lost cut acknowledged an incomplete native control owner")
            shutil.move(out/"control-bank-transport.vcd",integration/"lost-control-cut.vcd")
            shutil.move(out/"cut0.frames",integration/"lost-control-cut.frames")
            doc["executions"].append(dict(bits=bits,wave_audit=wave_audit,cuts=frames));save()
    # Freeze native vendor-model input identity before EDA execution.
    if args.mode=="vivado":
        vendor=Path(shutil.which("vivado")).resolve().parents[1]/"data/verilog/src"
        for name,source in (("BUFGCE.v",vendor/"unisims/BUFGCE.v"),("glbl.v",vendor/"glbl.v")):
            require(source.is_file(),"native Vivado model missing "+str(source));shutil.copyfile(source,out/name)
        doc["vendor_models"]={n:sha(out/n) for n in ("BUFGCE.v","glbl.v")}
    require(sources=={n:sha(ROOT/n) for n in SOURCES},"sources changed during verification")
    validate_inputs(out,doc['inputs'],sources)
    doc["artifacts"]={str(p.relative_to(out)):sha(p) for p in out.rglob("*") if p.is_file() and p.name!="summary.json"
                      and not any(part in ("csrc",".Xil") for part in p.relative_to(out).parts) and p.name!="simv" and not p.name.endswith(".daidir")}
    doc["status"]="pass";save();print(out/"summary.json",flush=True)


if __name__=="__main__":
    main()
