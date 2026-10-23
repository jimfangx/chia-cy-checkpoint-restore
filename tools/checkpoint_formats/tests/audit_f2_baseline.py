"""Independently cross-check retained real F2 bring-up evidence (no cloud writes).

This proves baseline execution only, never hardware checkpoint support.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import yaml


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    def load(name):
        return json.loads((root / name).read_text())

    manifest = load("baseline/manager-commands.json")
    runtime = yaml.safe_load((root / "baseline/config_runtime.yaml").read_text())
    hwdb = yaml.safe_load((root / "baseline/config_hwdb.yaml").read_text())
    recipe = manifest["recipe"]
    require(recipe == "firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3", "not the required Rocket baseline recipe")
    agfi = hwdb[recipe]["agfi"]
    require(manifest["phase"] == "baseline" and manifest["checkpoint_hardware_verified"] is False,
            "baseline must not claim checkpoint support")
    require(runtime["metasimulation"]["metasimulation_enabled"] is False, "actual runtime enables metasim")
    require(runtime["target_config"]["no_net_num_nodes"] == 1 and
            runtime["target_config"]["topology"] == "no_net_config" and
            runtime["target_config"]["default_hw_config"] == recipe, "not the single-node Rocket recipe")
    farm = runtime["run_farm"]["recipe_arg_overrides"]
    require(farm["run_farm_hosts_to_use"] == [{"f2.6xlarge": 1}] and
            farm["always_expand_run_farm"] is False and
            farm["run_farm_tag"] == manifest["run_farm_tag"], "farm scope changed")
    native_logs = {}
    for task in ("launchrunfarm", "infrasetup", "runworkload", "terminaterunfarm"):
        candidates = list((root / "native-manager-logs").glob(f"*-{task}-*.log"))
        require(len(candidates) == 1, "missing or ambiguous native manager log: " + task)
        path = candidates[0]
        native = path.read_text()
        require(f"Running: {task}\n" in native and manifest["run_farm_tag"] in native,
                "native manager task/farm mismatch: " + task)
        require("'metasimulation_enabled': False" in native and
                "'metasimulation_enabled': True" not in native,
                "native manager did not disable metasim: " + task)
        native_logs[task] = dict(path=str(path.relative_to(root)), sha256=sha(path))
    native_run = (root / native_logs["runworkload"]["path"]).read_text()
    require("FireSim Simulation Exited Successfully" in native_run and
            runtime["workload"]["workload_name"] in native_run and
            load("native-paths.json")["result_dir"] in native_run,
            "native workload completion/results provenance missing")
    for step in ("launchrunfarm", "infrasetup", "runworkload"):
        name = {"launchrunfarm": "launch", "infrasetup": "infrasetup", "runworkload": "runworkload"}[step]
        receipt = load(f"baseline/{name}-returncode.json")
        require(receipt["returncode"] == 0 and receipt["command"] == manifest["commands"][step],
                "manager step failed or used different configs: " + step)
    inventory = load("resources-running.json")
    require(inventory["metasimulation_enabled"] is False, "inventory recorded a metasim invocation")
    for name, digest in inventory["config_sha256"].items():
        require(sha(root / "baseline" / name) == digest, "runtime config changed after hardware execution")
    identity = load("aws-identity.json")
    region = (root / "aws-region.txt").read_text().strip()
    imds = load("imds-document.stdout")
    instances = [i for r in load("instance.json")["Reservations"] for i in r["Instances"]]
    require(len(instances) == 1 and len(inventory["instances"]) == 1, "ambiguous instance identity")
    instance = instances[0]
    require(instance["InstanceId"] == inventory["instances"][0]["InstanceId"] == imds["instanceId"] and
            instance["InstanceType"] == imds["instanceType"] == "f2.6xlarge" and
            instance["ImageId"] == imds["imageId"] and
            instance["PrivateIpAddress"] == imds["privateIp"], "API and on-host identity disagree")
    require(identity["Account"] == inventory["aws_identity"]["Account"] == imds["accountId"] and
            region == inventory["region"] == imds["region"], "account/region identity mismatch")
    require({"Key": "fsimcluster", "Value": manifest["run_farm_tag"]} in instance["Tags"], "wrong farm tag")
    probes = load("hardware-probe-commands.json")
    for probe in ("imds-document", "loaded-slot", "deployed-hashes"):
        require(probes[probe]["returncode"] == 0, "required hardware probe failed: " + probe)
    slot = (root / "loaded-slot.stdout").read_text()
    require(re.search(r"^AFI\s+0\s+" + re.escape(agfi) + r"\s+loaded\s+0\s+ok\s+0\s+", slot, re.M),
            "slot 0 not independently recorded as loaded/error-free")
    public = load("public-image.json")["FpgaImages"]
    require(len(public) == 1 and public[0]["FpgaImageGlobalId"] == agfi and
            public[0]["State"]["Code"] == "available" and public[0]["Public"] is True,
            "public image identity/availability mismatch")
    driver = load("driver-provenance.json")
    require(driver["quintuplet"] in public[0]["Description"], "driver recipe and public image differ")
    remote_hashes = dict((line.split()[1], line.split()[0]) for line in
                         (root / "deployed-hashes.stdout").read_text().splitlines())
    workload = load("workload-provenance.json")
    require(sha(root / "workload/rocket-quad.riscv") == workload["sha256"], "workload bytes changed")
    require((root / "workload/rocket-quad.riscv").stat().st_size == workload["size"], "workload size changed")
    results = root / "results-workload"
    logs = list(results.glob("*/uartlog"))
    require(len(logs) == 1, "expected exactly one target job log")
    log = logs[0].read_text()
    script = (logs[0].parent / "sim-run.sh").read_text()
    programs = re.findall(r"\+prog0=([^\s]+)", script)
    require(len(programs) == 1 and remote_hashes[programs[0]] == workload["sha256"],
            "actual program argv does not match deployed workload bytes")
    require("+slotid=0" in script and "./FireSim-f2" in script, "actual hardware driver/slot missing")
    require(remote_hashes["sim-run.sh"] == sha(logs[0].parent / "sim-run.sh"), "run script hash mismatch")
    require(remote_hashes["FireSim-f2"] == driver["driver_sha256"] == sha(root / "FireSim-f2"),
            "deployed driver differs from source-built driver")
    for source in driver["sources"]:
        require(sha(Path(source["snapshot"])) == source["sha256"], "driver source snapshot changed")
    passed = re.findall(r"\*\*\* PASSED \*\*\* after (\d+) cycles", log)
    require(len(passed) == 1 and int(passed[0]) > 0 and
            'COMMAND_EXIT_CODE="0"' in log and "*** FAILED ***" not in log,
            "no successful target termination")
    require(re.search(r"AFI ID for Slot\s+0:\s+" + re.escape(agfi), log) and
            "Attached to BAR0 (OCL)" in log and "Attached to BAR4 (PCIS)" in log,
            "target log does not establish F2 BAR/slot attachment")
    termination = load("baseline/termination-returncode.json")
    require(termination["returncode"] == 0 and
            termination["command"] == manifest["commands"]["terminaterunfarm"],
            "scoped manager teardown failed or changed its config")
    cleaned = load("resources-after-cleanup.json")
    require(cleaned["instance_filters"] == inventory["instance_filters"] and
            len(cleaned["instances"]) == 1 and
            cleaned["instances"][0]["InstanceId"] == instance["InstanceId"] and
            cleaned["instances"][0]["State"]["Name"] == "terminated",
            "final scoped resource inventory does not confirm cleanup")
    build = yaml.safe_load((root / "checkpoint-build/config_build.yaml").read_text())["build_farm"]
    require(Path(build["base_recipe"]).name == "externally_provisioned.yaml" and
            build["recipe_arg_overrides"]["build_farm_hosts"] == ["localhost"],
            "next image build is not constrained to localhost")
    build_manifest = load("checkpoint-build/manager-commands.json")
    require(build_manifest["phase"] == "checkpoint" and
            build_manifest["build_execution"] == "localhost" and
            build_manifest["checkpoint_hardware_verified"] is False and
            build_manifest["recipe"] == recipe,
            "checkpoint build preparation identity/acceptance mismatch")
    require(build["recipe_arg_overrides"]["default_build_dir"] == build_manifest["build_dir"] and
            build_manifest["recipe_file_sha256"] == manifest["recipe_file_sha256"] and
            build_manifest["recipe_source"] == manifest["recipe_source"],
            "checkpoint build workspace/recipe changed")
    baseline_recipe = yaml.safe_load((root / "baseline/config_build_recipes.yaml").read_text())
    build_recipe = yaml.safe_load((root / "checkpoint-build/config_build_recipes.yaml").read_text())
    require(build_recipe == baseline_recipe, "checkpoint build changed the exact CPU recipe")
    return dict(status="passed", scope="real AWS F2 single-node Rocket baseline only",
                checkpoint_hardware_verified=False, account=identity["Account"], region=region,
                instance_id=instance["InstanceId"], instance_type=instance["InstanceType"], slot=0,
                agfi=agfi, afi=public[0]["FpgaImageId"], recipe=recipe,
                workload_sha256=workload["sha256"], workload_bytes=workload["size"],
                driver_sha256=driver["driver_sha256"], target_pass_cycle=int(passed[0]),
                scoped_runtime_cleanup="terminated", checkpoint_image_build="implementation started; no full image yet",
                native_manager_logs=native_logs,
                diagnostic_exception="Optional /dev/xdma* probe failed: F2 driver uses BAR4 PCIS; required identity/slot/hash probes passed. Raw failure retained.",
                evidence_hashes={str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*"))
                                 if p.is_file() and p.name in ("uartlog", "sim-run.sh", "loaded-slot.stdout",
                                                             "imds-document.stdout", "instance.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve()), indent=2))
