#!/usr/bin/env python3
"""AWS F2 manager execution and isolated FireSim configuration generation.

This is orchestration, not an implementation of FPGA checkpoint capture.
The implementation milestones must add the actual synthesizable state access.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Callable

import yaml

ROOT = Path(__file__).resolve().parents[2]
FIRE = ROOT / "sims/firesim"
RUNS = ROOT / "automations/checkpoint_loop/runs"
RECIPES = {
    "Rocket": "firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3",
    "BOOM": "firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3",
    "Shuttle+Saturn": "firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3",
}


def manager_config(name: str) -> tuple[dict, Path]:
    """Use the user's initialized manager files without overwriting them."""
    deploy = FIRE / "deploy"
    source = deploy / f"config_{name}.yaml"
    if not source.is_file():
        source = deploy / f"sample-backup-configs/sample_config_{name}.yaml"
    value = yaml.safe_load(source.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"manager config must contain a YAML mapping: {source}")
    return deepcopy(value), source


def local_build_farm(build_dir: Path) -> dict:
    return {
        "base_recipe": str(FIRE / "deploy/build-farm-recipes/externally_provisioned.yaml"),
        "recipe_arg_overrides": {
            "default_build_dir": str(build_dir.resolve()), "build_farm_hosts": ["localhost"],
        },
    }


class F2Manager:
    def __init__(self, root: Path = ROOT,
                 emit: Callable[[str], None] = lambda s: print(s, end="", flush=True)):
        self.root = root.resolve()
        self.fire = self.root / "sims/firesim"
        self.emit = emit

    def validate_local_build(self, argv: list[str], directory: Path) -> None:
        if Path(argv[0]).name != "firesim" or len(argv) < 2 or argv[1] != "buildbitstream":
            return
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("-b", "--buildconfigfile", default="config_build.yaml")
        flags, _ = parser.parse_known_args(argv[2:])
        config = yaml.safe_load((directory / flags.buildconfigfile).read_text())
        farm = config["build_farm"]
        base = yaml.safe_load((directory / farm["base_recipe"]).read_text())
        args = {**base.get("args", {}), **(farm.get("recipe_arg_overrides") or {})}
        hosts = args.get("build_farm_hosts")
        if (base.get("build_farm_type") != "ExternallyProvisioned" or
                not isinstance(hosts, list) or len(hosts) != 1 or
                not (hosts[0] == "localhost" or isinstance(hosts[0], dict) and list(hosts[0]) == ["localhost"])):
            raise ValueError("bitstream builds must use ExternallyProvisioned with only localhost; regenerate the invocation config")
        build_dir = (hosts[0].get("localhost", {}).get("override_build_dir", args.get("default_build_dir"))
                     if isinstance(hosts[0], dict) else args.get("default_build_dir"))
        if not build_dir or not Path(build_dir).is_absolute():
            raise ValueError("localhost bitstream build directory must be an explicit absolute path")

    def command(self, argv: list[str], cwd: str = ".") -> list[str]:
        if not argv or not all(isinstance(arg, str) for arg in argv):
            raise ValueError("F2 argv must be a nonempty string list")
        if any("vcs-env.sh" in arg or re.search(r"(^|[/\s;&|])(?:vcs|simv)(?:\b|-)", arg)
               or re.search(r"verify_\w+_vcs\b", arg) for arg in argv):
            raise ValueError("VCS checks must use backend eda, not the F2 manager")
        directory = (self.root / cwd).resolve()
        if Path(cwd).is_absolute() or not directory.is_relative_to(self.root):
            raise ValueError("F2 cwd must be relative to the workspace")
        self.validate_local_build(argv, directory)
        # Preserve the caller's Conda/FireSim environment. bash -c (not -lc)
        # avoids a login shell replacing it with unrelated startup defaults.
        script = "set -eo pipefail; "
        setup = os.environ.get("CHECKPOINT_F2_SETUP", "")
        if setup:
            script += "source " + shlex.quote(setup) + "; "
        script += f"cd {shlex.quote(str(self.fire))}; "
        # Fabric uses ~/firesim.pem directly. Skip the interactive ssh-agent
        # helper; the user can source sourceme-manager.sh manually for key setup.
        script += "source ./sourceme-manager.sh --skip-ssh-setup; "
        script += f"cd {shlex.quote(str(directory))}; exec " + shlex.join(argv)
        return ["bash", "-c", script]

    def run(self, argv: list[str], cwd: str = ".") -> int:
        command = self.command(argv, cwd)
        self.emit(f"[F2 manager command] cwd={cwd} argv={json.dumps(argv)}\n")
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace") as process:
            assert process.stdout is not None
            for chunk in iter(lambda: process.stdout.readline(64 * 1024), ""):
                self.emit(chunk)
            return process.wait()

    def preflight(self) -> int:
        # Read-only: no managerinit, instance launches, image builds or IAM edits.
        return self.run(["bash", "-c",
            'set -e; command -v firesim; command -v aws; '
            'test -r "$HOME/firesim.pem" || { echo "Missing ~/firesim.pem" >&2; exit 1; }; '
            'region="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region || true)}}"; '
            'test -n "$region" || { echo "Configure an AWS region" >&2; exit 1; }; '
            'aws --region "$region" sts get-caller-identity --output json; '
            'aws --region "$region" ec2 describe-instance-types --instance-types f2.6xlarge '
            '--query "InstanceTypes[].InstanceType" --output json'], "sims/firesim/deploy")


def prepare(family: str, workload: str, out: Path, *, phase: str = "checkpoint",
            hwdb: Path | None = None, hwconfig: str | None = None,
            tag: str | None = None) -> dict:
    """Generate configs without contacting AWS or claiming capture support."""
    out = out.resolve()
    if not out.is_relative_to(RUNS.resolve()):
        raise ValueError("F2 configuration output must be under checkpoint_loop/runs/")
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a fresh output directory; do not overwrite a retained invocation")
    recipe_name = RECIPES[family]
    source_configs = {name: manager_config(name) for name in ("runtime", "build", "build_recipes", "hwdb")}
    recipes, recipes_file = source_configs["build_recipes"]
    recipe_source = recipes_file
    if recipe_name not in recipes:
        recipe_source = ROOT / "sims/firesim-staging/sample_config_build_recipes.yaml"
        recipe = deepcopy(yaml.safe_load(recipe_source.read_text())[recipe_name])
    else:
        recipe = deepcopy(recipes[recipe_name])
    if recipe["PLATFORM"] != "f2" or recipe["bit_builder_recipe"] != "bit-builder-recipes/f2.yaml":
        raise ValueError("selected recipe is not an AWS F2 build")
    recipe["TARGET_PROJECT_MAKEFRAG"] = str(
        (FIRE / recipe["TARGET_PROJECT_MAKEFRAG"]).resolve())
    recipe["bit_builder_recipe"] = str(FIRE / "deploy/bit-builder-recipes/f2.yaml")
    tag = tag or "checkpoint-f2-" + hashlib.sha256(str(out).encode()).hexdigest()[:12]
    if not re.fullmatch(r"checkpoint-f2-[A-Za-z0-9_-]+", tag):
        raise ValueError("use a dedicated checkpoint-f2-* run-farm tag")
    if not workload or Path(workload).name != workload or not workload.endswith(".json"):
        raise ValueError("workload must name an installed FireSim workload JSON")
    selected = hwconfig or recipe_name
    public_database = yaml.safe_load((ROOT / "sims/firesim-staging/sample_config_hwdb.yaml").read_text())
    database = source_configs["hwdb"][0]
    if hwdb is not None:
        database = yaml.safe_load(hwdb.read_text()) or {}
    elif selected not in database or (phase == "checkpoint" and
            isinstance(database.get(selected), dict) and database[selected].get("agfi") in {
                value.get("agfi") for value in public_database.values() if isinstance(value, dict)}):
        # Existing private entries are preferred; public images are baseline
        # seeds only. A checkpoint image not yet built has no invented AGFI.
        database = public_database if phase == "baseline" else {}
    if phase == "baseline" and not database:
        raise ValueError("baseline requires an available F2 HWDB entry")
    if database:
        entry = database.get(selected)
        if not isinstance(entry, dict) or not re.fullmatch(r"agfi-[0-9a-f]+", entry.get("agfi", "")):
            raise ValueError("select an F2 HWDB entry with a real AGFI")
        if phase == "checkpoint" and entry["agfi"] in {
                value.get("agfi") for value in public_database.values() if isinstance(value, dict)}:
            raise ValueError("stock public AGFIs are baseline-only; build a checkpoint-enabled image")
        entry = deepcopy(entry)
        if entry.get("deploy_makefrag_override"):
            entry["deploy_makefrag_override"] = str((FIRE / entry["deploy_makefrag_override"]).resolve())
        database = {selected: entry}
    runtime = source_configs["runtime"][0]
    farm = runtime.setdefault("run_farm", {})
    farm["base_recipe"] = str((FIRE / "deploy" / farm.get("base_recipe", "run-farm-recipes/aws_ec2.yaml")).resolve())
    farm.setdefault("recipe_arg_overrides", {}).update(
        run_farm_tag=tag, always_expand_run_farm=False, run_farm_hosts_to_use=[{"f2.6xlarge": 1}])
    runtime["metasimulation"]["metasimulation_enabled"] = False
    runtime["target_config"].update(topology="no_net_config", no_net_num_nodes=1, default_hw_config=selected)
    runtime["workload"].update(workload_name=workload, terminate_on_completion=False, suffix_tag=tag)
    build = source_configs["build"][0]
    build.update(build_farm=local_build_farm(out / "build-host"), builds_to_run=[recipe_name],
                 agfis_to_share=[], share_with_accounts={})
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (("runtime", runtime), ("build", build), ("hwdb", database),
                        ("build_recipes", {recipe_name: recipe})):
        (out / f"config_{name}.yaml").write_text(yaml.safe_dump(value, sort_keys=False))
    flags = ["-c", str(out / "config_runtime.yaml"), "-b", str(out / "config_build.yaml"),
             "-r", str(out / "config_build_recipes.yaml"), "-a", str(out / "config_hwdb.yaml")]
    tasks = ["buildbitstream", "launchrunfarm", "infrasetup", "runworkload", "terminaterunfarm"]
    commands = {task: {"backend": "f2", "cwd": "sims/firesim/deploy",
                       "argv": ["firesim", task, *flags,
                                *(["--forceterminate"] if task in ("buildbitstream", "terminaterunfarm") else [])]}
                for task in tasks}
    manifest = dict(phase=phase, family=family, recipe=recipe_name, run_farm_tag=tag,
                    intended_capture_source="aws-f2", metasimulation_enabled=False,
                    hwdb_ready=bool(database), checkpoint_hardware_verified=False,
                    build_execution="localhost", build_dir=str(out / "build-host"),
                    recipe_file_sha256=hashlib.sha256(recipe_source.read_bytes()).hexdigest(),
                    recipe_source=str(recipe_source),
                    manager_config_sources={name: {"path": str(source),
                                                  "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
                                            for name, (_, source) in source_configs.items()},
                    commands=commands)
    (out / "manager-commands.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check", help="read-only manager/AWS checks; no instances launched")
    generate = sub.add_parser("prepare", help="generate isolated configs and command argv; offline")
    generate.add_argument("--family", choices=list(RECIPES), default="Rocket")
    generate.add_argument("--phase", choices=["baseline", "checkpoint"], default="checkpoint")
    generate.add_argument("--workload", required=True)
    generate.add_argument("--out", type=Path, required=True)
    generate.add_argument("--hwdb", type=Path)
    generate.add_argument("--hwconfig")
    generate.add_argument("--tag")
    execute = sub.add_parser("run", help="execute one manager-side command; may launch AWS resources")
    execute.add_argument("--cwd", default="sims/firesim/deploy")
    execute.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "check":
            return F2Manager().preflight()
        if args.action == "prepare":
            result = prepare(args.family, args.workload, args.out, phase=args.phase,
                             hwdb=args.hwdb, hwconfig=args.hwconfig, tag=args.tag)
            print(json.dumps(result, indent=2))
            return 0
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        return F2Manager().run(argv, args.cwd)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"[F2 error] {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
