"""Native localhost synthesis and fresh EDA VCS of concrete shared queue banks.

These fixtures prove readout and sibling isolation only. No FPGA checkpoint,
complete owner freeze, restoration or target-cycle authority is established.
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
from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
SOURCES = tuple(sorted({
    str(p.relative_to(ROOT))
    for p in (ROOT / "sims/firesim/sim/midas/src/main/scala/midas/checkpoint").glob("*.scala")
} | {
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointSharedQueueSpec.scala",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/SharedQueue.firrtl",
    "tools/checkpoint_formats/tests/verify_shared_queue_access.py",
    "tools/checkpoint_formats/tests/shared_queue_access_tb.sv",
    "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc",
    "tools/checkpoint_formats/tests/audit_checkpoint_regions.py",
    "tools/checkpoint_formats/tests/audit_physical_clock_plan.py",
    "tools/checkpoint_formats/codec.py", "tools/checkpoint_formats/toolchain.py",
}))
FLAGS = ("complete_fpga_capture", "deployable_capture_image",
         "production_freeze_owners_bound", "metasim_restore_supported")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(doc):
    return hashlib.sha256(canonical(doc)).hexdigest()


def audit(directory):
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text())
    source = (directory / "source.fir").read_text()
    before = parse_modules(source)
    after = parse_modules((directory / "generated.fir").read_text())
    original = inventory_from_firrtl(source, "SharedQueueHost")
    expected = {row["state_id"]: row for row in original
                if row["hierarchy"].split(".")[1] in ("q0", "q1")}
    require(len(expected) == 10, "different independent shared queue inventory")
    require(before["SharedQueueHost"]["instances"] ==
            dict(gate="Native", q0="SharedQueue", q1="SharedQueue", q2="SharedQueue"), "different original queue topology")
    require(after["SharedQueue"]["body"] == before["SharedQueue"]["body"], "changed unselected original queue")
    require(after["SharedQueueHost"]["instances"] == dict(
        gate="Native", q0="checkpoint_shell_region0_selected_SharedQueue",
        q1="checkpoint_shell_region1_selected_SharedQueue", q2="SharedQueue"), "crossed or lost concrete queue copy")
    require(after["Native"] == before["Native"], "changed uncovered physical clock owner")
    manifest, binding, identities = map(read, ("descriptors.json", "binding.json", "descriptor-binding.json"))
    require(binding["host_sha256"] == sha(directory / "source.fir")
            and binding["instrumented_sha256"] == sha(directory / "generated.fir")
            and binding["descriptor_manifest_sha256"] == digest(manifest)
            and binding["descriptor_binding_sha256"] == digest(identities), "unbound shared queue source/output")
    require(identities["manifest_sha256"] == digest(manifest), "changed descriptor identity")
    for doc in (manifest, binding, identities):
        require(all(doc[k] is False for k in FLAGS), "shared queue readout claims hardware admission")
    rows = manifest["state"]
    require(len(rows) == 10 and {r["state_id"] for r in rows} == set(expected), "omitted/duplicated selected queue owner")
    require(len({(r["bank"], r["slot"]) for r in rows}) == 10, "aliased shared queue selector")
    for row in rows:
        logical = expected[row["state_id"]]
        q = int(logical["hierarchy"].split(".")[1][1:])
        require(row["logical_state"] == logical and row["hierarchy"] == logical["hierarchy"]
                and row["region"] == q, "changed original queue identity or shape")
        require(row["width"] == min(64, logical["width"])
                and row["depth"] == ((logical["width"] + 63) // 64) * logical["depth"], "truncated multiword queue RAM")
    uncovered = [r for r in original if r["hierarchy"].startswith("SharedQueueHost.q2.")]
    require(sorted(manifest["uncovered_functional_state"], key=lambda r: r["state_id"]) == uncovered,
            "lost unselected queue ownership deficit")
    require(len(manifest["uncovered_physical_gates"]) == 1 and sum(r["count"] for r in manifest["physical_ce_order"]) == 0,
            "readout cannot certify physical clock ownership")
    physical = manifest["uncovered_physical_gates"][0]
    physical_path = "SharedQueueHost.gate.CE_latch"
    require(physical["hierarchy"] == "SharedQueueHost.gate"
            and physical["logical_latch_hierarchy"] == physical_path
            and physical["logical_latch_state_id"] == digest(dict(
                namespace="physical-bufgce-ce-latch-v1", hierarchy=physical_path)),
            "changed uncovered physical owner")
    for q in range(2):
        mapping = read(f"shell-{q}-mapping.json")
        shell = read(f"shell-{q}-binding.json")
        require(mapping["selected_execution"] == f"SharedQueueHost.q{q}" and len(mapping["state"]) == 5,
                "wrong shell execution")
        require(shell["mapping_sha256"] == digest(mapping) and shell["host_sha256"] == sha(directory / "source.fir"),
                "unbound shell mapping")
        require(shell["annotation_policy"]["translation_results_applied"] is True
                and shell["annotation_policy"]["preservation"] == "concrete_execution_translation", "missing shared owner translation")
        region = identities["regions"][q]
        require(region["manifest_sha256"] == digest(region["manifest"])
                and region["binding_sha256"] == digest(region["binding"])
                and region["binding"]["manifest_sha256"] == digest(region["manifest"]), "changed region identity envelope")
        region_rows = {r["state_id"]: r for r in region["manifest"]["state"]}
        require(len(region_rows) == 5 and region["manifest"]["selected_scope"] == f"SharedQueueHost.q{q}",
                "different region identity execution")
        require(region["binding"]["shell_binding_sha256"] == digest(shell), "unbound shared shell identity")
        expected_ids = {state_id for state_id, row in expected.items()
                        if row["hierarchy"].startswith(f"SharedQueueHost.q{q}.")}
        require({m["state_id"] for m in mapping["state"]} == expected_ids
                and len({m["state_id"] for m in mapping["state"]}) == 5,
                "omitted or duplicate concrete shell mapping")
        require(sum(m["transfer_depth"] for m in mapping["state"]) == 22, "incomplete shell transfer words")
        for m in mapping["state"]:
            logical = expected.get(m["state_id"])
            require(logical is not None and logical["hierarchy"] == m["hierarchy"], "crossed shell owner")
            descriptor = next(row for row in rows if row["state_id"] == m["state_id"])
            local = region_rows.get(m["state_id"])
            require(local is not None and local["logical_state"] == logical
                    and local["bank"] == m["bank"] and local["slot"] == m["slot"]
                    and local["width"] == m["transfer_width"] and local["depth"] == m["transfer_depth"]
                    and local["storage_hierarchy"] == m["storage_hierarchy"], "changed embedded local mapping")
            require(all(m[k] == logical[k] for k in ("width", "depth", "kind"))
                    and m["transfer_width"] == descriptor["width"]
                    and m["transfer_depth"] == descriptor["depth"]
                    and m["bank"] == descriptor["local_bank"]
                    and m["slot"] == descriptor["local_slot"], "changed shell selector or transfer geometry")
            suffix = m["hierarchy"].rsplit(".", 1)[1]
            storage = "CheckpointPipeline_ram_r_addr" if suffix == "ram_r_addr" else suffix
            require(m["storage_hierarchy"] == f"SharedQueueHost.q{q}." + storage, "crossed queue pipeline storage")
    xdc = (directory / "generated.synthesis.xdc").read_text()
    commands = [line for line in xdc.splitlines() if line and not line.startswith("#")]
    require(commands == [f"set_property RAM_STYLE BLOCK [get_cells -hierarchical -regexp .*q{q}/ram_reg.*]"
                         for q in range(3)], "changed concrete original RAM-style policy")
    return rows


def selectors(directory):
    lines = ["task allwords;", "begin"]
    for q in range(2):
        mapping = json.loads((Path(directory) / f"shell-{q}-mapping.json").read_text())
        for row in mapping["state"]:
            suffix = row["hierarchy"].rsplit(".", 1)[1]
            if suffix == "ram":
                values = [f"64'(memory[{q}][{i // 3}] >> {64 * (i % 3)})" for i in range(18)]
            else:
                key = {"enq_ptr": "wp", "deq_ptr": "rp", "full": "full", "ram_r_addr": "ra"}[suffix]
                values = [f"64'({key}[{q}])"]
            require(len(values) == row["transfer_depth"], "incomplete independent queue oracle")
            lines.extend(f"readword({q},{row['bank']},{row['slot']},{a},{value},0);" for a, value in enumerate(values))
    return "\n".join(lines + ["end", "endtask", ""])


def synthesis_wrapper(generated):
    # The actual region graft consumes only the registered endpoint and ties
    # access clocks to the common raw clock. Raw combinational bank probes are
    # internal wires, not additional externally observed memory read ports.
    text = (Path(generated) / "generated.sv").read_text()
    match = re.search(r"module SharedQueueHost\((.*?)\n\);", text, re.S)
    require(match is not None, "missing queue host interface")
    pins = []
    connections = []
    for line in match[1].splitlines():
        if not line.strip(): continue
        pin = re.fullmatch(r"\s*(input|output)\s*(\[\d+:\d+\])?\s*(\w+),?", line)
        require(pin is not None, "unknown generated queue host port")
        name = pin[3]
        if name.endswith("_ckpt_clock"):
            connections.append(f".{name}(clock)")
        elif name.endswith(("_ckpt_data", "_ckpt_match")):
            require(pin[1] == "output", "raw probe must be output only")
            connections.append(f".{name}()")
        else:
            pins.append(f"  {pin[1]} wire {pin[2] or ''} {name}")
            connections.append(f".{name}({name})")
    require(len(connections) == 51 and len(pins) == 45, "changed queue endpoint boundary")
    return "module SharedQueueSynthesisTop(\n" + ",\n".join(pins) + ");\n" + \
        "  SharedQueueHost host(\n    " + ",\n    ".join(connections) + ");\nendmodule\n"


def negative_audits(generated, out):
    results = []
    for case in ("omitted", "duplicate", "shape", "pipeline", "selector", "duplicate_mapping", "sibling", "false_admission"):
        directory = out / case
        shutil.copytree(generated, directory)
        manifest = json.loads((directory / "descriptors.json").read_text())
        binding = json.loads((directory / "binding.json").read_text())
        identities = json.loads((directory / "descriptor-binding.json").read_text())
        if case == "omitted": manifest["state"].pop()
        elif case == "duplicate": manifest["state"][-1] = manifest["state"][0]
        elif case == "shape": next(r for r in manifest["state"] if r["logical_state"]["kind"] == "memory")["depth"] = 6
        elif case in ("pipeline", "selector", "duplicate_mapping"):
            p = directory / "shell-0-mapping.json"
            mapping = json.loads(p.read_text())
            if case == "pipeline":
                next(r for r in mapping["state"] if r["hierarchy"].endswith(".ram_r_addr"))["storage_hierarchy"] = "SharedQueueHost.q1.enq_ptr"
            elif case == "selector": mapping["state"][0]["slot"] += 1
            else: mapping["state"][-1] = dict(mapping["state"][0])
            p.write_bytes(canonical(mapping))
            p = directory / "shell-0-binding.json"
            shell = json.loads(p.read_text());shell["mapping_sha256"] = digest(mapping);p.write_bytes(canonical(shell))
            identities["regions"][0]["binding"]["shell_binding_sha256"] = digest(shell)
            identities["regions"][0]["binding_sha256"] = digest(identities["regions"][0]["binding"])
        elif case == "sibling":
            p = directory / "generated.fir"
            text = p.read_text();require(text.count("module SharedQueue :") == 1, "ambiguous sibling fault")
            start = text.index("  module SharedQueue :")
            end = text.index("\n  module ", start + 1)
            body = text[start:end]
            needle = "node enq = and(enq_ready, enq_valid)"
            require(body.count(needle) == 1, "ambiguous original sibling enqueue")
            text = text[:start] + body.replace(needle, 'node enq = UInt<1>("h0")') + text[end:]
            p.write_text(text);binding["instrumented_sha256"] = sha(p)
        else: manifest["complete_fpga_capture"] = True
        (directory / "descriptors.json").write_bytes(canonical(manifest))
        identities["manifest_sha256"] = digest(manifest)
        (directory / "descriptor-binding.json").write_bytes(canonical(identities))
        binding["descriptor_manifest_sha256"] = digest(manifest);binding["descriptor_binding_sha256"] = digest(identities)
        (directory / "binding.json").write_bytes(canonical(binding))
        try: audit(directory)
        except FormatError as error: results.append(dict(case=case, rejected=True, reason=str(error)))
        else: raise FormatError("coherently rehashed queue metadata corruption accepted: " + case)
    (out / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--generated", type=Path);parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args();require(args.out.resolve().is_relative_to(RUNS), "evidence beneath runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES};commands = []
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda",
               scope="concrete shared queue readout component; no FPGA capture or restore", physical_fpga_capture=False,
               full_image=False, host=socket.gethostname(), source_root=str(ROOT),
               observed_utc=datetime.now(timezone.utc).isoformat(), sources=sources)
    (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n");print(out, flush=True)
    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")));commands.append(row)
        with Path(row["log"]).open("w") as f: result = subprocess.run(row["argv"], cwd=out, stdout=f, stderr=subprocess.STDOUT)
        row["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode != expected:
            # Preserve a source/input-bound failure; no native receipt becomes
            # successful merely because the unsupported policy is diagnosed.
            doc.update(status="fail", commands=commands, failed_command=row,
                       artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
                                  if p.is_file() and p.suffix in {".log", ".rpt", ".dcp", ".vcd"}})
            (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native localhost Vivado required")
        require(args.generated is not None and args.native is None, "explicit generated input required")
        shutil.copytree(args.generated, out / "generated");rows = audit(out / "generated")
        doc["rehashed_negatives"] = negative_audits(out / "generated", out / "audit-negatives")
        (out / "shared-queue-selectors.svh").write_text(selectors(out / "generated"))
        (out / "synthesis-wrapper.sv").write_text(synthesis_wrapper(out / "generated"))
        (out / "sources").mkdir()
        for n in SOURCES: shutil.copyfile(ROOT / n, out / "sources" / Path(n).name)
        vendor = Path(os.environ["XILINX_VIVADO"]) / "data/verilog/src"
        for n, p in [("BUFGCE.v", vendor / "unisims/BUFGCE.v"), ("glbl.v", vendor / "glbl.v")]: shutil.copyfile(p, out / n)
        (out / "synth.tcl").write_text('''set_param general.maxThreads 4
read_verilog -sv generated/generated.sv
read_verilog -sv synthesis-wrapper.sv
read_xdc generated/generated.synthesis.xdc
synth_design -top SharedQueueSynthesisTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
foreach path {host/q0 host/q1 host/q2} {
  if {[llength [get_cells $path]] != 1} {error "original queue execution disappeared"}
}
set all_block [get_cells -hier -filter {REF_NAME =~ RAMB*}]
set counts {}
foreach path {host/q0 host/q1 host/q2} {
  set count 0
  foreach cell $all_block {
    if {[string match "$path/*" [get_property NAME $cell]]} {incr count}
  }
  if {$count == 0} {error "original BLOCK memory policy has no primitive at $path"}
  lappend counts $count
}
puts "SHARED_QUEUE_MEMORY_PRIMITIVES selected0=[lindex $counts 0] selected1=[lindex $counts 1] sibling=[lindex $counts 2]"
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force shared-queue-access.dcp
puts "SHARED_QUEUE_SYNTH_PASS selected=2 untouched=1"
''')
        doc["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and p.name != "summary.json"}
        text = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("SHARED_QUEUE_SYNTH_PASS selected=2 untouched=1" in text and not re.search(r"ERROR:|CRITICAL WARNING:", text), "native shared queue synthesis failure")
        resources = re.search(r"SHARED_QUEUE_MEMORY_PRIMITIVES selected0=(\d+) selected1=(\d+) sibling=(\d+)", text)
        require(resources is not None and min(map(int, resources.groups())) > 0, "missing physical BLOCK memory policy audit")
        doc["block_memory_primitives"] = dict(zip(("selected0", "selected1", "sibling"), map(int, resources.groups())))
        doc["entries"] = len(rows)
    else:
        require(str(ROOT).startswith("/scratch/") and toolchain.VCS == "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "fresh EDA SP2 required")
        require(args.native is not None and args.generated is None, "explicit native receipt required")
        native = json.loads((args.native / "summary.json").read_text())
        require(native["status"] == "pass" and native["backend"] == "f2" and native["sources"] == sources, "stale native queue source binding")
        for group in ("inputs", "artifacts"):
            for n, h in native[group].items(): require(sha(args.native / n) == h, "changed native evidence " + n)
        for n in native["inputs"]:
            dest = out / n;dest.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(args.native / n, dest)
        doc["inputs"] = native["inputs"];audit(out / "generated")
        require((out / "synthesis-wrapper.sv").read_text() == synthesis_wrapper(out / "generated"), "changed production-shaped endpoint wrapper")
        require((out / "shared-queue-selectors.svh").read_text() == selectors(out / "generated"), "changed queue oracle selectors")
        for mode in ("healthy", "corrupt"):
            folder = out / mode;folder.mkdir()
            text = (out / "generated/generated.sv").read_text()
            if mode == "corrupt":
                needle = "assign checkpoint_shell_region0_ckpt_resp_data = checkpoint_shell_region0_ckpt_saved_data;"
                require(text.count(needle) == 1, "ambiguous first response corruption site")
                text = text.replace(needle, needle[:-1] + " ^ 64'h1;")
            (folder / "compiled.sv").write_text(text)
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                 "+incdir+" + str(out), "-top", "shared_queue_access_tb", "-top", "glbl", "-Mdir=" + str(folder / "csrc"),
                 "-o", str(folder / "simv"), str(folder / "compiled.sv"), str(out / "synthesis-wrapper.sv"),
                 str(out / "sources/shared_queue_access_tb.sv"), str(out / "sources/checkpoint_widget_exit.cc"),
                 str(out / "BUFGCE.v"), str(out / "glbl.v")], mode + "-compile")
            text = run([folder / "simv", "-no_save"], mode + "-run", 0 if mode == "healthy" else 1)
            wave = out / "shared-queue-access.vcd";require(wave.is_file() and wave.stat().st_size > 0, "missing queue debug waveform")
            shutil.move(wave, folder / wave.name)
            if mode == "healthy":
                match = re.search(r"SHARED_QUEUE_PASS checks=(\d+) reads=361 stalls=(\d+) edges=(\d+) cuts=4 sibling_pushes=(\d+)", text)
                require(match and int(match[1]) > 1000 and int(match[4]) > 100, "incomplete active queue coverage")
                doc["checks"], doc["stalls"], doc["edges"], doc["sibling_pushes"] = map(int, match.groups())
                doc["reads"] = 361;doc["cuts"] = 4
            else:
                require("SHARED_QUEUE_DIVERGENCE signal=complete selected word cuts=0" in text
                        and "frozen=11 response_ack=00 reads=0" in text and "SHARED_QUEUE_PASS" not in text,
                        "corruption acknowledged an edge/word or failed to stop on first read")
                doc["compiled_first_word_corruption_rejected_before_ack"] = True
        doc["native_receipt"] = dict(path=str(args.native / "summary.json"), sha256=sha(args.native / "summary.json"))
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, "queue sources changed during verification")
    doc.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
               if p.is_file() and (p.suffix in {".log", ".rpt", ".dcp", ".vcd"} or p.name in {"commands.json", "compiled.sv", "simv"})})
    (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n");print(out / "summary.json", flush=True)


if __name__ == "__main__": main()
