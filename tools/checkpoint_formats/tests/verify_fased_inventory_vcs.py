"""Full generated-state diagnostic on the production FCFS FASED AXI4 fuzzer.

Source both repository environments, then vcs-env.sh LAST. This deliberately
does not publish .fsckpt: functional memory, drivers and runtime cut/restore are
still separate requirements. All 10,000 fuzzer transactions and every generated
RAM word are included, including the target's large independent RAM scoreboard.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.replay import modules
from tools.checkpoint_formats.simulator import (check_generated_rtl, prepare_generated_stream_probe,
                                                validate_generated_stream)
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects


def check_counter_roles(manifest, rtl):
    """Reject changed counter/channel bindings instead of relying on names alone."""
    instances = {i["hierarchy"]: i["module"] for i in manifest["instances"]}
    mods = modules(re.sub(r"//[^\n]*|/\*.*?\*/", "", rtl, flags=re.S))
    prefix = "FPGATop.FASEDMemoryTimingModel_0"
    for owner, counter, channel in (
        (prefix + ".model", "SatUpDownCounter", "tNasti_io_tNasti_ar"),
        (prefix + ".model", "SatUpDownCounter_1", "tNasti_io_tNasti_aw"),
        (prefix, "SatUpDownCounter", "auto_to_host_dram_out_ar"),
        (prefix, "SatUpDownCounter_1", "auto_to_host_dram_out_aw"),
    ):
        body = mods[instances[owner]][1]
        valid = channel + "_valid" if owner.endswith(".model") else "nastiToHostDRAM_" + channel.rsplit("_", 1)[-1] + "_valid"
        terms = (channel + "_ready", valid)
        expression = r"\s*&\s*".join(re.escape(t) for t in terms)
        require(re.search(rf"assign\s+{counter}_io_inc\s*=\s*{expression}\s*;", body),
                f"unsupported FASED diagnostic counter role {owner}.{counter}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    require(str(vcs) == _toolchain.VCS, "source vcs-env.sh LAST")
    sim_dir = ROOT / "sims/firesim/sim"
    platform = "FCFS16GBQuadRank_DefaultF1Config"
    make = ["make", "TARGET_PROJECT=fasedtests", "DESIGN=AXI4Fuzzer", "TARGET_CONFIG=FCFSConfig",
            f"PLATFORM_CONFIG={platform}", "SIMULATOR_CHECKPOINT_INVENTORY=FPGATop", f"BUILD_DIR={build}"]
    run(make + ["verilog"], out / "fased-verilog.log", sim_dir)
    generated = build / f"f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-{platform}"
    base = generated / "FireSim-generated"
    for suffix in (".simulator-state.json", ".simulator-reference.fir", ".sv", ".const.h"):
        shutil.copyfile(str(base) + suffix, out / ("FireSim-generated" + suffix))
    manifest = json.loads((out / "FireSim-generated.simulator-state.json").read_text())
    rtl = (out / "FireSim-generated.sv").read_text()
    bufgce = (sim_dir / "midas/src/main/verilog/BUFGCE.v").read_text()
    check_generated_rtl(manifest, (out / "FireSim-generated.simulator-reference.fir").read_text(),
                        rtl + bufgce, bufgce)
    check_counter_roles(manifest, rtl)
    instances = {i["hierarchy"]: i["module"] for i in manifest["instances"]}
    prefix = "FPGATop.FASEDMemoryTimingModel_0"
    require(instances.get(prefix + ".model") == "FIFOMASModel", "not the actual FCFS DRAM timing model")
    require(sum(i["module"] == "BankStateTracker" for i in manifest["instances"]) == 32,
            "missing rank/bank state inventory")
    harness = (sim_dir / "midas/src/main/verilog/top.sv").read_text()
    require(harness.count("module emul(") == 1 and harness.count("FPGATop FPGATop(") == 1,
            "unsupported diagnostic harness hierarchy")
    # The source's actual AXI handshakes bind these construction-order names;
    # the captured values independently establish outstanding transactions.
    reads = prefix + ".model.SatUpDownCounter.value"
    writes = prefix + ".model.SatUpDownCounter_1.value"
    host_reads = prefix + ".SatUpDownCounter.value"
    host_writes = prefix + ".SatUpDownCounter_1.value"
    stages = [{reads: 1, host_reads: 1}, {writes: 1, host_writes: 1}, {reads: 1, writes: 1}]
    prepare_generated_stream_probe(manifest, out, stages)
    invalidate_stale_driver_objects(generated, out / "rebuilt-driver-objects.json")
    run(make + ["vcs", f"VCS={vcs} -full64", "VCS_FLAGS=-Mupdate", f"VCS_EXTRA_V={out / 'generated-probe.sv'}"],
        out / "fased-vcs-build.log", sim_dir)
    binary = generated / "AXI4Fuzzer"
    capture = out / "fased.generated-state.jsonl"
    text = run([binary, "+vcs+initreg+0", "+vcs+initmem+0", "+memsize=4194304", "+max-cycles=1000000",
                f"+generated_capture={capture}"], out / "fased-run.log", out)
    require("*** PASSED ***" in text, "full FASED fuzzer did not pass")
    samples = validate_generated_stream(manifest, capture, len(stages))
    observations = []
    for sample, predicate in zip(samples, stages):
        require(all(sample["scalars"][path] >= value for path, value in predicate.items()),
                "missing captured outstanding target/host traffic")
        observations.append(dict(stage=sample["stage"], host_sample=sample["host_sample"], words=sample["words"],
                                 timing_model_cycle=sample["scalars"][prefix + ".model.tCycle"],
                                 target_pending_reads=sample["scalars"][reads], target_pending_writes=sample["scalars"][writes],
                                 host_pending_reads=sample["scalars"][host_reads], host_pending_writes=sample["scalars"][host_writes]))
    rejected = []
    for label, option in (("preflight", "+fs-checkpoint-preflight"),
                          ("save", f"+fs-checkpoint={out / 'must-not-exist.fsckpt'}"),
                          ("restore", f"+fs-restore={out / 'absent.fsckpt'}")):
        result = run([binary, "+memsize=4194304", option], out / f"unsupported-{label}.log", out, expected=1)
        require("FS_CHECKPOINT_UNSUPPORTED: unsupported metasim runtime checkpoint cut/restore" in result
                and "FireSim fingerprint:" not in result, "unsupported driver initialized/executed")
        rejected.append(label)
    require(not (out / "must-not-exist.fsckpt").exists(), "incomplete checkpoint published")
    summary = dict(scope="complete generated RTL diagnostic; not full runtime save/restore",
                   entries=len(manifest["state"]), instances=len(manifest["instances"]),
                   words=sum(e["depth"] for e in manifest["state"]),
                   bits=sum(e["width"] * e["depth"] for e in manifest["state"]),
                   fased_entries=sum(e["hierarchy"].startswith(prefix + ".") for e in manifest["state"]),
                   memory_pipeline_entries=sum(e["adapter"] == "firrtl-emitter-memory-pipeline-v1" for e in manifest["state"]),
                   samples=observations, unsupported_requests_rejected=rejected, fuzzer_transactions=10000,
                   functional_memory_captured=False, external_runtime_required=True, physical_fpga_validated=False)
    with capture.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    summary["capture_sha256"] = digest.hexdigest()
    (out / "summary.json").write_bytes(canonical(summary))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
