"""M4 incremental generated-state coverage/capture and fail-closed host check.

Source both repository env.sh files, then vcs-env.sh LAST before invoking.
This is not full checkpoint/restart acceptance: diagnostics cannot be restored.
"""

import argparse
import json
import os
from pathlib import Path
import shutil

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.simulator import (check_generated_rtl, generated_capture,
                                                prepare_generated_probe)
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    require(str(vcs) == "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs", "source vcs-env.sh LAST")
    sim_dir = ROOT / "sims/firesim/sim"
    make = ["make", "DESIGN=InventoryFixture", "TARGET_CONFIG=NoConfig", "PLATFORM_CONFIG=DefaultF2Config",
            "SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut", "SIMULATOR_CHECKPOINT_INVENTORY=FPGATop",
            f"BUILD_DIR={build}"]
    run(make + ["verilog"], out / "fixture-verilog.log", sim_dir)
    generated = build / "f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config"
    base = generated / "FireSim-generated"
    for suffix in (".simulator-state.json", ".simulator-reference.fir", ".sv", ".const.h"):
        shutil.copyfile(str(base) + suffix, out / ("FireSim-generated" + suffix))
    manifest = json.loads((out / "FireSim-generated.simulator-state.json").read_text())
    bufgce_model = sim_dir / "midas/src/main/verilog/BUFGCE.v"
    check_generated_rtl(manifest, (out / "FireSim-generated.simulator-reference.fir").read_text(),
                        (out / "FireSim-generated.sv").read_text() + bufgce_model.read_text(), bufgce_model.read_text())
    words = prepare_generated_probe(manifest, out)
    invalidate_stale_driver_objects(generated, out / "rebuilt-driver-objects.json")
    run(make + ["vcs", f"VCS={vcs} -full64", "VCS_FLAGS=-Mupdate", f"VCS_EXTRA_V={out / 'generated-probe.sv'}"],
        out / "fixture-vcs-build.log", sim_dir)
    binary = generated / "InventoryFixture"
    text = run([binary, "+vcs+initreg+0", "+vcs+initmem+0", f"+generated_capture={out / 'generated-capture.jsonl'}"],
               out / "metasim-run.log")
    require("*** PASSED ***" in text, "fixture did not pass")
    rows = [json.loads(line) for line in (out / "generated-capture.jsonl").read_text().splitlines()]
    require(len(rows) == 3 and [r["stage"] for r in rows] == [0, 1, 2], "incomplete diagnostic probe stages")
    require([r["host_sample"] for r in rows] == sorted(set(r["host_sample"] for r in rows)), "host sample order")
    samples = []
    for row, label in zip(rows, ("active", "outstanding", "held-response")):
        snapshot = generated_capture(manifest, row["values"], row["host_sample"])
        (out / f"{label}.generated-state.json").write_bytes(canonical(snapshot))
        observed = {r["owner"].rsplit(".dut.", 1)[-1]: int(r["value"], 16) for r in snapshot["records"]
                    if ".dut." in r["owner"]}
        if label == "outstanding":
            require(observed["busy"] == observed["qValid"] == 1, "missing outstanding/queued transaction")
        if label == "held-response":
            require(observed["responseValid"] == 1, "missing held response")
        samples.append(dict(label=label, host_sample=row["host_sample"], words=len(snapshot["records"]),
                            dut_counter=observed["counter"]))
    rejected = []
    for label, option in (("preflight", "+fs-checkpoint-preflight"),
                          ("save", f"+fs-checkpoint={out / 'must-not-exist.fsckpt'}"),
                          ("restore", f"+fs-restore={out / 'absent.fsckpt'}")):
        result = run([binary, "+vcs+initreg+0", "+vcs+initmem+0", option], out / f"unsupported-{label}.log", expected=1)
        require("FS_CHECKPOINT_UNSUPPORTED: unsupported metasim runtime checkpoint cut/restore" in result,
                "unsupported driver was not explicitly rejected")
        require("FireSim fingerprint:" not in result and "*** PASSED ***" not in result,
                "driver initialization or execution occurred after checkpoint rejection")
        rejected.append(label)
    require(not (out / "must-not-exist.fsckpt").exists(), "incomplete checkpoint was published")
    summary = dict(scope="generated RTL diagnostic only; no full restore acceptance", root=manifest["root_module"],
                   instances=len(manifest["instances"]), entries=len(manifest["state"]), words=len(words),
                   bits=sum(w["width"] for w in words), samples=samples, unsupported_requests_rejected=rejected,
                   external_runtime_required=True, fased_present=False, physical_fpga_validated=False)
    (out / "summary.json").write_bytes(canonical(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
