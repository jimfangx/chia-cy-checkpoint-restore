"""Verify the generated original-ROM-bound native endpoint component.

Native Vivado runs only on the manager; SP2 VCS runs only on EDA. The complete
Scala execution, original descriptors, transformed bench and every consumed
source are frozen in a unique attempt. This grants no FPGA/restore admission.
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
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_native_widget_endpoint as base
from tools.checkpoint_formats.tests.audit_native_state_capture_wave import audit as audit_native

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
TOP = "CheckpointNativeBoundWidgetEndpoint"
TB, EXIT, PREFIX, RESOURCES = base.TB, base.EXIT, base.PREFIX, base.RESOURCES
SCALA = "sims/firesim/sim/midas/src/"
SOURCES = (*base.SOURCES,
    SCALA + "main/scala/midas/widgets/CheckpointNativeCaptureDescriptors.scala",
    SCALA + "main/scala/midas/widgets/CheckpointCaptureDescriptors.scala",
    SCALA + "main/scala/midas/checkpoint/GeneratedStateBankAccess.scala",
    SCALA + "main/scala/midas/checkpoint/SemanticStateInventory.scala",
    SCALA + "main/scala/midas/checkpoint/BankedStateAccess.scala",
    SCALA + "test/scala/midas/widgets/CheckpointCaptureNativeBindingSpec.scala",
    "tools/checkpoint_formats/tests/verify_native_bound_endpoint.py",
    "tools/checkpoint_formats/tests/test_native_bound_endpoint.py")
BOUND = "native-binding/"
TOP_FILE = BOUND + "bound-endpoint/" + TOP + ".v"
PROBE = "native-endpoint/CheckpointNativeEndpointLayoutProbe/CheckpointNativeEndpointLayoutProbe.v"
RESOURCE_FILES = tuple(BOUND + "bound-endpoint/" + n for n in RESOURCES)
METADATA = tuple(BOUND + n for n in ("manifest.json", "binding.json", "constants.h", "manifest.inc", "endpoint-observation.json"))
GENERATED = (TOP_FILE, *METADATA, *RESOURCE_FILES, PROBE)
ELABORATION_INPUTS = base.ELABORATION_INPUTS
BENCH = "bound-endpoint-tb.sv"
SCOPE = "actual generated Chisel native bound original-ROM NASTI/shadow endpoint component; no production installation/restore ownership"
FLAGS = dict(complete_fpga_capture=False, deployable_capture_image=False,
    production_freeze_owners_bound=False, metasim_restore_supported=False, semantic_dut_inventory=False,
    native_control_bank_state_owner="unsupported_live_response_registers",
    external_transport_state_owner="unsupported_no_atomic_capture_restore_adapter",
    physical_clock_owner="external_common_cut_and_gate_owners_required")
sha = base.sha
coordinator_fault = base.coordinator_fault


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def replace_once(text, before, after, label):
    require(text.count(before) == 1, "ambiguous bound bench transformation " + label)
    return text.replace(before, after), dict(label=label, before=before, after=after)


def bench(text, manifest_hash):
    """Recorded transformations only; no drive of descriptor indices or ROM."""
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_hash) is not None, "invalid bound manifest hash")
    steps = []
    changes = (
        ("CheckpointNativeWidgetEndpoint dut(", TOP + " dut(", "bound_top"),
        ("HASH=256'h" + "1234567890abcdef" * 4, "HASH=256'h" + manifest_hash, "manifest"),
        (".io_descriptorEntry(descriptor_entry),.io_descriptorValid(descriptor_entry==0),\n"
         "    .io_descriptorBank(8'd1),.io_descriptorSlot(16'd0),.io_descriptorWidth(16'd64),.io_descriptorDepth(32'd1),",
         ".io_descriptorEntry(descriptor_entry),", "remove_external_descriptor_drivers"),
        ("  integer checks=0,", "  reg [3:1] rom_seen=0; integer rom_samples=0;\n  integer checks=0,", "rom_observation_counters"),
        ("if(reset)begin bank_response_valid<=0;", "if(reset)begin rom_seen=0;rom_samples=0;bank_response_valid<=0;", "reset_rom_observation"),
        ("      raw_edges++;", """      raw_edges++;
      if(descriptor_entry==0)begin
        check(dut.originalROM.io_valid&&dut.originalROM.io_bank==1&&dut.endpoint.nativeTransport.descriptor_slot==0&&
          dut.originalROM.io_bitWidth==64&&dut.originalROM.io_depth==1,"bound_original_ROM_entry");
      end else begin
        check(!dut.originalROM.io_valid&&dut.originalROM.io_bank==0&&dut.endpoint.nativeTransport.descriptor_slot==0&&
          dut.originalROM.io_bitWidth==0&&dut.originalROM.io_depth==0,"appended_ordinal_invalid_in_original_ROM");
        rom_samples++;
        if(descriptor_entry>=1&&descriptor_entry<=3)rom_seen[descriptor_entry]=1;
      end""", "observe_original_rom_without_driving"),
        ("    check(words==9&&requests==1&&control_acks==5,\"complete_native_descriptor_words\");",
         """    check(words==9&&requests==1&&control_acks==5,"complete_native_descriptor_words");
    check(rom_seen==3'b111&&rom_samples>=3,"all_appended_ordinals_observed_invalid_in_original_ROM");
    $display("NATIVE_BOUND_ROM_PASS appended_seen=%0h invalid_samples=%0d",rom_seen,rom_samples);""", "require_real_appended_ordinals"),
    )
    # Redirect existing endpoint observations before adding wrapper ROM checks.
    count = text.count("dut.")
    require(count > 30 and "dut.endpoint." not in text, "changed original endpoint hierarchy observations")
    text = text.replace("dut.", "dut.endpoint.")
    steps.append(dict(label="nested_endpoint_hierarchy", before="dut.", after="dut.endpoint.", occurrences=count))
    for before, after, label in changes:
        text, step = replace_once(text, before, after, label)
        steps.append(step)
    require(".io_descriptorValid(" not in text and not re.search(r"\b(force|deposit)\b", text.replace("// Hierarchy is observed for independent readback; no force, deposit or restore.", "")),
        "bound bench must not replace or force descriptor ownership")
    return text, dict(version=1, original_sha256=hashlib.sha256(base_text_bytes()).hexdigest(),
        manifest_sha256=manifest_hash, transformations=steps)


def base_text_bytes():
    return (ROOT / TB).read_bytes()


def tcl():
    text = base.tcl()
    require(text.count(base.TOP) == 2, "changed base native synthesis top sites")
    text = text.replace(base.TOP, TOP)
    text = text.replace("generated/" + TOP + ".v", "generated/" + TOP_FILE)
    for name in RESOURCES:
        text = text.replace("generated/" + name, "generated/" + BOUND + "bound-endpoint/" + name)
    return text


def validate_descriptors(directory, sources):
    """Reconstruct exact fixture identities, appended entries, host constants."""
    path = directory / BOUND
    manifest = json.loads((path / "manifest.json").read_text())
    binding = json.loads((path / "binding.json").read_text())
    require((path / "manifest.json").read_bytes() == canonical(manifest) and
        (path / "binding.json").read_bytes() == canonical(binding), "noncanonical native descriptor JSON")
    mh, bh = digest(manifest), digest(binding)
    require(type(manifest.get("descriptor_version")) is int and manifest["descriptor_version"] == 1 and manifest.get("scope") == "native_transport_ordered_stream_descriptors_only" and
        type(binding.get("binding_version")) is int and binding["binding_version"] == 1 and binding.get("scope") == "validated_original_rom_and_native_appended_stream_binding_only",
        "wrong bound native descriptor scope")
    require(all(canonical(manifest.get(k)) == canonical(v) and canonical(binding.get(k)) == canonical(v) for k, v in FLAGS.items()), "native descriptor ownership claim differs")
    abi = dict(bits=130, gates=3, external_owners=["fixture.functional", "fixture.host"], coordinator_owners=3,
        external_clock_network=1, capture_native_control=True, snapshot_bank=252, native_control_bank=251,
        original_entries=1, stream_entries=4, native_owner_bits=283, raw_control_bits=760, separate_bank_bits=67,
        shadow_control_bits=827, shadow_bits=1585, shadow_layout_version=2, shadow_restore_supported=False)
    require(canonical(manifest.get("abi")) == canonical(abi), "native descriptor ABI/options differ")
    resources = {n: sources[PREFIX + n] for n in RESOURCES}
    require(manifest.get("sources") == resources, "native descriptor source identity differs")
    original, original_binding = binding.get("original_manifest"), binding.get("original_binding")
    require(isinstance(original, dict) and isinstance(original_binding, dict), "missing original descriptor provenance")
    require(manifest.get("original_manifest_sha256") == digest(original) and
        manifest.get("original_binding_sha256") == digest(original_binding) and
        original_binding.get("manifest_sha256") == digest(original) and
        original_binding.get("reference_sha256") == original.get("reference_sha256"), "original descriptor provenance hash differs")
    require(binding.get("manifest") == manifest and binding.get("manifest_sha256") == mh and
        type(binding.get("original_rom_entries")) is int and binding["original_rom_entries"] == 1 and binding.get("original_rom_appended_entries_valid") is False,
        "native binding manifest/ROM identity differs")
    logical, storage = original.get("state", []), original_binding.get("state", [])
    require(len(logical) == len(storage) == 1, "incomplete original fixture storage")
    state_id = digest(dict(hierarchy="NativeBindingFixture.state", kind="register", namespace="pre-fame-state-v1"))
    require(all(r.get("state_id") == state_id and r.get("hierarchy") == "NativeBindingFixture.state" and
        canonical({k:r.get(k) for k in ("width","depth")}) == canonical(dict(width=64,depth=1)) for r in (logical[0], storage[0])) and
        canonical({k:storage[0].get(k) for k in ("bank","slot")}) == canonical(dict(bank=1,slot=0)) and
        original_binding.get("scope") == "all_reachable_firrtl_state_only" and
        type(original_binding.get("access_version")) is int and
        (original_binding.get("access_version"), original_binding.get("protocol")) in
        ((1, "latched-banked64-v1"), (2, "latched-banked64-chunked-v2")), "wrong original fixture identity/selector")
    identity = dict(domain="native_transport_descriptor_v1", original_manifest_sha256=digest(original),
        original_binding_sha256=digest(original_binding), abi=abi, sources=resources)
    def sid(role):
        return hashlib.sha256(canonical(identity) + b"\n" + role.encode()).hexdigest()
    selectors = [(1, 0, 64, 1), (251, 0, 64, 5), (252, 0, 64, 2), (252, 1, 2, 1)]
    roles = ["original", "native_owner", "staged_payload_full", "staged_payload_tail"]
    ids = [state_id, *[sid(role) for role in roles[1:]]]
    rows = [dict(ordinal=i, domain=role, state_id=state_id, bank=sel[0], slot=sel[1], width=sel[2], depth=sel[3])
        for i, (role, state_id, sel) in enumerate(zip(roles, ids, selectors))]
    require(canonical(manifest.get("state")) == canonical(rows), "native descriptor order/shape/StateID differs")
    bytes_ = ", ".join("0x" + mh[i:i+2] for i in range(62, -1, -2))
    cpp = "checkpoint_capture_manifest_t{{{" + bytes_ + "}}, {" + ", ".join(
        "{%dU, %dU, %dU, %dU}" % s for s in selectors) + "}}"
    require((path / "manifest.inc").read_text() == cpp, "full C++ manifest or little-endian digest differs")
    header = (path / "constants.h").read_text()
    definitions = re.findall(r"(?m)^#define NATIVE_([A-Z0-9_]+) (.+)$", header)
    values = dict(NATIVE_DESCRIPTOR_LAYOUT_VERSION=1, ORIGINAL_ROM_ENTRIES=1, STREAM_ENTRIES=4,
        EXTERNAL_OWNERS=2, COORDINATOR_OWNERS=3, NATIVE_BITS=130, PHYSICAL_CLOCK_GATES=3,
        EXTERNAL_CLOCK_NETWORK=1, CAPTURE_NATIVE_CONTROL=1, SNAPSHOT_BANK=252, NATIVE_CONTROL_BANK=251,
        NATIVE_OWNER_BITS=283, RAW_CONTROL_BITS=760, SEPARATE_BANK_BITS=67, SHADOW_CONTROL_BITS=827,
        SHADOW_BITS=1585, SHADOW_LAYOUT_VERSION=2, SHADOW_RESTORE_SUPPORTED=0, FRAME_BYTES=64,
        TRANSPORT_VERSION=1, COMPLETE_FPGA_CAPTURE=0, DEPLOYABLE_CAPTURE_IMAGE=0,
        PRODUCTION_FREEZE_OWNERS_BOUND=0, METASIM_RESTORE_SUPPORTED=0)
    expected = {k: str(v) + "U" for k, v in values.items()}
    expected.update({k: '"' + v + '"' for k, v in dict(MANIFEST_SHA256=mh, DESCRIPTOR_BINDING_SHA256=bh,
        ORIGINAL_MANIFEST_SHA256=digest(original), ORIGINAL_BINDING_SHA256=digest(original_binding)).items()})
    require(len(definitions) == len(expected) and dict(definitions) == expected, "native driver constants differ")
    return dict(manifest_sha256=mh, binding_sha256=bh, original_entries=1, stream_entries=4,
        original_manifest_sha256=digest(original), original_binding_sha256=digest(original_binding))


def validate_generated(directory, sources):
    for name in GENERATED:
        p = directory / name
        require(p.is_file() and not p.is_symlink(), "missing/linked generated bound input " + name)
    for name, relative in zip(RESOURCES, RESOURCE_FILES):
        require(sha(directory / relative) == sources[PREFIX + name], "bound native resource differs " + name)
    descriptor = validate_descriptors(directory, sources)
    metadata = json.loads((directory / BOUND / "endpoint-observation.json").read_text())
    # Share the exact ordinary endpoint metadata contract, with the real digest.
    expected = dict(layout_version=1, scope="native_endpoint_live_observation_only", original_bits=130,
        gates=3, owners=2, external_clock_network=1, clock_ownership="externally_owned_clock_network_required",
        external_clock_contract="caller_supplies_raw_clock_and_routes_clock_mask_and_ce_to_separately_owned_gates",
        root_and_gate_clock_outputs="constant_zero_in_external_clock_network_mode", endpoint_shadow_layout_version=2,
        endpoint_shadow_bits=1585, endpoint_shadow_restore_supported=False, raw_composite_bits=760,
        separate_bank_bits=67, endpoint_bits=827, raw_coordinator_offset=283, native_owner_bits=283,
        capture_native_control=True, original_entries=1, total_entries=4, snapshot_bank=252, native_control_bank=251,
        manifest_sha256=descriptor["manifest_sha256"], endpoint_order_lsb0=["coordinator_411", "native_owner",
        "payload_response_66", "native_control_bank_67"], external_transport_state_owner="unsupported_no_atomic_capture_restore_adapter",
        native_control_bank_state_owner="unsupported_live_response_registers", complete_fpga_capture=False,
        deployable_capture_image=False, production_freeze_owners_bound=False, metasim_restore_supported=False,
        sources={n: sources[PREFIX+n] for n in RESOURCES})
    require(canonical(metadata) == canonical(expected), "bound endpoint observation identity/layout differs")
    text = (directory / TOP_FILE).read_text()
    require(re.search(r"module\s+" + TOP + r"\s*\(", text), "wrong generated bound Chisel top")
    for token in ("CheckpointNastiAdapter", "CheckpointLiveWidgetSnapshot", "CheckpointNativeCaptureTransport",
        "CheckpointCaptureDescriptorROM", "originalROM", "CheckpointNativeWidgetEndpoint"):
        require(token in text, "bound generated endpoint omits " + token)
    top = re.search(r"module\s+" + TOP + r"\s*\((.*?)\);", text, re.S)
    require(top and not re.search(r"\bio_descriptor(?:Valid|Bank|Slot|Width|Depth)\b", top[1]), "bound top exposes descriptor replacement input")
    return dict(descriptors=descriptor, observation=metadata)
def validate_elaboration(directory, sources, generated_origin=None):
    """Bind emitted bytes to the central completed Scala execution receipt."""
    elaboration=json.loads((directory/"elaboration.json").read_text())
    require(elaboration.get("status")=="pass" and elaboration.get("backend")=="f2" and
        elaboration.get("scope")=="completed Scala native bound endpoint elaboration", "wrong elaboration receipt scope/status")
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
    require("NATIVE_BOUND_ENDPOINT_ELABORATED" in text and "original=1 stream=4 bits=130 gates=3 owners=2" in text,
        "Scala execution log omits actual native endpoint elaboration")
    return elaboration



def validate_inputs(directory, inputs, sources, generated_origin=None):
    require(set(sources) == set(SOURCES), "wrong bound current source namespace")
    elaboration = validate_elaboration(directory, sources, generated_origin)
    generated = validate_generated(directory / "generated", sources)
    manifest_hash = generated["descriptors"]["manifest_sha256"]
    transformed, transformation = bench((directory / "sources" / TB).read_text(), manifest_hash)
    expected = {"sources/" + n: h for n, h in sources.items()}
    expected.update({"generated/" + n: h for n, h in elaboration["generated"].items()})
    expected.update({n: sha(directory / n) for n in ELABORATION_INPUTS})
    expected["native.tcl"] = hashlib.sha256(tcl().encode()).hexdigest()
    expected[BENCH] = hashlib.sha256(transformed.encode()).hexdigest()
    expected["bench-transformation.json"] = hashlib.sha256(canonical(transformation)).hexdigest()
    require(inputs == expected, "bound source/generated/Tcl/bench namespace differs")
    for name, value in expected.items():
        p = directory / name
        require(p.is_file() and not p.is_symlink() and sha(p) == value, "changed frozen bound endpoint input " + name)
    require((directory / "native.tcl").read_text() == tcl(), "changed bound native synthesis recipe")
    return generated


def audit_fault_wave(path, diagnostic, endpoint="dut"):
    """Find the real qualified mismatch and establish pre-ack termination."""
    fields=dict(re.findall(r"([a-z_]+)=([A-Za-z0-9_]+)",diagnostic))
    kind={"endpoint_coordinator_layout":"coordinator","native_control_saved_data":"native_data"}.get(fields.get("signal"))
    require(kind is not None,"unknown compiled fault signal")
    expected_signal="endpoint_coordinator_layout" if kind=="coordinator" else "native_control_saved_data"
    require(fields.get("signal")==expected_signal and all(re.fullmatch(r"[0-9]+",fields.get(n,""))
        for n in ("raw_time","raw_phase","target_cycle","cut","frames","words","requests","control_acks","shadow_captures")),
        "incomplete compiled fault diagnostic")
    prefix="native_widget_endpoint_tb."
    native=endpoint+".nativeTransport."
    names=["clock","target_cycle","native_cut_cycle","frames","words","requests","control_acks","shadow_captures",
        "native_valid","endpoint_view","original_view","original_bank",native+"native_capture.phase"]
    data=[native+n for n in ("control_response_valid","response_ready","control_selected","response_data","control_response_data")]
    if kind=="native_data":names+=data
    wanted={prefix+n:n for n in names};scopes=[];codes={};values={};previous={};rises=[]
    timestamp=None;timescale=[];first=None;last=None;falls=[];history=[]
    def sample():
        nonlocal previous,first,last
        if timestamp is None:return
        now={n:values.get(c,"x") for n,c in codes.items()}
        binary=lambda n:re.fullmatch("[01]+",now.get(n,"x")) is not None
        integer=lambda n:int(now[n],2)
        if previous.get("clock")=="0" and now.get("clock")=="1":rises.append(timestamp)
        if previous.get("clock")=="1" and now.get("clock")=="0":falls.append(timestamp)
        if all(binary(n) for n in names):
            mismatch=(integer("native_valid")==1 and integer("endpoint_view")!=integer("original_view")) if kind=="coordinator" else (
                all(integer(n)==1 for n in data[:3]) and
                (integer(data[3])!=(integer("original_bank")&((1<<64)-1)) or integer(data[3])!=integer(data[4])))
            if mismatch and first is None:first=dict(time=timestamp,values={n:integer(n) for n in names})
            last=dict(time=timestamp,values={n:integer(n) for n in names},mismatch=mismatch)
            history.append(last)
        previous=now
    with Path(path).open() as stream:
        for line in stream:
            parts=line.split()
            if not parts:continue
            if timestamp is None:timescale.append(line)
            if parts[0]=="$scope":scopes.append(parts[2])
            elif parts[0]=="$upscope":scopes.pop()
            elif parts[0]=="$var":
                name=".".join(scopes+[parts[4].lstrip("\\")])
                if name in wanted:codes[wanted[name]]=parts[3]
            elif line.startswith("#"):
                sample();timestamp=int(line[1:])
            elif line[0] in "bB" and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
            elif line[0] in "01xXzZ":values[line[1:].strip()]=line[0].lower()
    sample()
    require(set(codes)==set(names) and first is not None and last is not None,"missing complete compiled-fault waveform/mismatch")
    scale=re.search(r"\$timescale\s+(\d+)\s*(ms|us|ns|ps|fs|s)\s+\$end","".join(timescale))
    require(scale is not None,"missing compiled-fault waveform timescale")
    femtoseconds={"s":10**15,"ms":10**12,"us":10**9,"ns":10**6,"ps":1000,"fs":1}
    unit=int(scale[1])*femtoseconds[scale[2]]
    raw_fs=int(fields["raw_time"])*1000  # VCS %t uses the bench's 1 ps precision.
    require(raw_fs%unit==0,"fault diagnostic cannot align with VCD precision")
    diagnosis=raw_fs//unit
    require(timestamp==diagnosis and last["time"]==diagnosis and last["mismatch"] and last["values"]["clock"]==0,
        "compiled fault does not end at its settled low-phase mismatch")
    require(10**6%unit==0,"bench 1 ns observation delay cannot align with waveform")
    delay=10**6//unit
    eligible=[];index=0
    for fall in falls:
        sample_time=fall+delay
        if sample_time>diagnosis:continue
        while index+1<len(history) and history[index+1]["time"]<=sample_time:index+=1
        if history[index]["time"]<=sample_time and history[index]["mismatch"]:eligible.append(sample_time)
    require(eligible and eligible[0]==diagnosis,"diagnosis missed first eligible low-phase compiled mismatch")
    require(not any(t>diagnosis for t in rises),"raw positive edge advanced after compiled diagnosis")
    mappings=dict(target_cycle="target_cycle",cut="native_cut_cycle",raw_phase=native+"native_capture.phase",
        frames="frames",words="words",requests="requests",control_acks="control_acks",shadow_captures="shadow_captures")
    require(all(last["values"][name]==int(fields[field]) for field,name in mappings.items()),"fault diagnostic differs from original waveform counters/cut")
    required_zero=("frames","words","requests","control_acks","shadow_captures") if kind=="coordinator" else ("control_acks","shadow_captures")
    require(all(first["values"][n]==last["values"][n]==0 for n in required_zero),"compiled mismatch acknowledged before termination")
    return dict(kind=kind,first_mismatch_timestamp=first["time"],diagnostic_timestamp=diagnosis,last_timestamp=timestamp,
        timescale=scale[1]+scale[2],first_eligible_mismatch_timestamp=eligible[0],
        raw_clock_at_diagnosis=0,raw_posedges_after_diagnosis=0,
        counters={n:last["values"][n] for n in ("frames","words","requests","control_acks","shadow_captures")},
        target_cycle=last["values"]["target_cycle"],cut=last["values"]["native_cut_cycle"],sha256=sha(path))


native_data_fault = base.native_data_fault


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
        scope=SCOPE,
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
            descriptor=validate_generated(out/"generated",sources)["descriptors"]
            transformed,transform=bench((out/"sources"/TB).read_text(),descriptor["manifest_sha256"])
            (out/BENCH).write_text(transformed)
            (out/"bench-transformation.json").write_bytes(canonical(transform))
            # Refuse missing/ambiguous fault sites before committing native time.
            coordinator_fault((out/"generated"/TOP_FILE).read_text())
            native_data_fault((out/"generated"/(BOUND+"bound-endpoint/CheckpointNativeCaptureTransport.sv")).read_text())
            doc["generated_origin"]=str(args.generated.resolve())
            doc["elaboration"]=dict(path=str(args.elaboration.resolve()),sha256=sha(args.elaboration))
            doc["inputs"]={**{"sources/"+n:h for n,h in sources.items()},
                **{"generated/"+n:h for n,h in elaboration["generated"].items()},
                **{n:sha(out/n) for n in ELABORATION_INPUTS},"native.tcl":sha(out/"native.tcl"), BENCH:sha(out/BENCH),
                "bench-transformation.json":sha(out/"bench-transformation.json")}
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
            require(native["status"]=="pass" and native["backend"]=="f2" and native["sources"]==sources and native.get("scope")==SCOPE and
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
            files=[*[out/"generated"/n for n in RESOURCE_FILES],out/"generated"/PROBE,
                out/BENCH,frozen/EXIT,out/"BUFGCE.v",out/"glbl.v"]
            run([*common,"-Mdir=csrc","-o","simv",out/"generated"/TOP_FILE,*files],"compile")
            doc["executions"]=[]
            for case,marker in (("healthy","NATIVE_ENDPOINT_PASS cuts=4 frames_per_cut=11 shadow_bits=1585 shadow_words=25 separate_bank_bits=67"),
                ("lost-owner","NATIVE_ENDPOINT_OWNER_LOSS_PASS control_acks_before_reset=0 recovery_frames=11"),
                ("shadow-owner-loss","NATIVE_ENDPOINT_SHADOW_FAULT_PASS accepted_captures=1 rejected_captures=1 preserved_bits=1585 recovery_frames=11"),
                ("abort","NATIVE_ENDPOINT_ABORT_PASS published_frames=0 blocked_restart=1 recovery_frames=11")):
                work=out/case;work.mkdir()
                text=run([out/"simv","-no_save","+CASE="+case],"run",work)
                require(marker in text and "DIVERGENCE" not in text,"native endpoint case incomplete "+case)
                require("NATIVE_ENDPOINT_LAYOUT_PASS planes=827 raw_bits=760 separate_bank_bits=67 correct_high=1 misleading_low=0" in text,
                    "incomplete independent literal layout planes")
                rom_rows=re.findall(r"NATIVE_BOUND_ROM_PASS appended_seen=7 invalid_samples=(\d+)",text)
                require(len(rom_rows)==(4 if case=="healthy" else 1) and all(int(n)>=3 for n in rom_rows),
                    "incomplete real appended ordinal observations "+case)
                row=dict(case=case,marker=marker,layout_planes=827,correct_high_certificate=True,misleading_low_certificate=False,
                    appended_rom_observations=list(map(int,rom_rows)))
                if case=="healthy":
                    row["native_wave"]=audit_native(work/"native-widget-endpoint.vcd",130,top="native_widget_endpoint_tb.dut.endpoint.nativeTransport.native_capture")
                    require(row["native_wave"]["captures"]==4,"missing original native cuts")
                    row["endpoint_wave"]=base.audit_observation_wave(work/"native-widget-endpoint.vcd",endpoint="dut.endpoint")
                    row["cuts"]=[base.audit_frames(work/f"cut{i}.frames",int(doc["observation_binding"]["descriptors"]["manifest_sha256"],16)) for i in range(4)]
                    require(len({r["cut"] for r in row["cuts"]})==4,"nonprogressing native target cuts")
                    for i in range(4):
                        lines=(work/f"cut{i}.shadow").read_text().splitlines()
                        require(len(lines)==25 and all(re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8}",n) for n in lines),"incomplete frontdoor shadow words")
                else:
                    row["recovery"]=base.audit_frames(work/"recovery.frames",int(doc["observation_binding"]["descriptors"]["manifest_sha256"],16))
                    if case=="shadow-owner-loss":
                        row["endpoint_wave"]=base.audit_observation_wave(work/"native-widget-endpoint.vcd",expected_captures=1,endpoint="dut.endpoint")
                        require(row["endpoint_wave"]["rejections"]==1,"missing first-edge owner-loss rejection")
                doc["executions"].append(row)
            mutated,site=coordinator_fault((out/"generated"/TOP_FILE).read_text())
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
            doc["compiled_fault"]=dict(site=site,first_fault=lines[0],source_sha256=sha(out/"broken-coordinator.v"),
                waveform=audit_fault_wave(work/"native-widget-endpoint.vcd",lines[0],endpoint="dut.endpoint"))
            mutated,site=native_data_fault((out/"generated"/(BOUND+"bound-endpoint/CheckpointNativeCaptureTransport.sv")).read_text())
            (out/"broken-native-data.sv").write_text(mutated)
            fault_files=[out/"broken-native-data.sv" if p.name=="CheckpointNativeCaptureTransport.sv" else p for p in files]
            run([*common,"-Mdir=data-csrc","-o","data-simv",out/"generated"/TOP_FILE,*fault_files],"data-compile")
            work=out/"broken-native-data";work.mkdir()
            text=run([out/"data-simv","-no_save"],"run",work,expected=1)
            lines=[n for n in text.splitlines() if n.startswith("NATIVE_ENDPOINT_DIVERGENCE")]
            require(len(lines)==1 and "signal=native_control_saved_data" in lines[0] and
                all(re.search(r"\b"+name+r"=0\b",lines[0]) for name in ("control_acks","shadow_captures")),
                "compiled saved-data fault escaped pre-ack original-register oracle")
            doc["compiled_data_fault"]=dict(site=site,first_fault=lines[0],source_sha256=sha(out/"broken-native-data.sv"),
                waveform=audit_fault_wave(work/"native-widget-endpoint.vcd",lines[0],endpoint="dut.endpoint"))
        require(sources=={n:sha(ROOT/n) for n in SOURCES},"sources changed during endpoint verification")
        validate_inputs(out,doc["inputs"],sources,doc["generated_origin"])
        doc["status"]="pass"
    except Exception as error:
        doc.update(status="fail",error_type=type(error).__name__,error=str(error))
        raise
    finally:
        doc["artifacts"]={str(p.relative_to(out)):sha(p) for p in out.rglob("*") if p.is_file() and p.name!="summary.json"
            and not any(part in ("csrc","broken-csrc","data-csrc",".Xil") or part.endswith(".daidir") for part in p.relative_to(out).parts)
            and p.name not in ("simv","broken-simv","data-simv")}
        with (out/"summary.json").open("x") as stream:json.dump(doc,stream,indent=2);stream.write("\n")
        print(out/"summary.json",flush=True)


if __name__=="__main__":
    main()
