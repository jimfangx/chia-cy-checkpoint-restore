#!/usr/bin/env python3
"""Read-only, invocation-scoped F2 resume inventory. Run through f2.py run.

An inventory is resource evidence, never a workload or checkpoint pass receipt.
AWS exceptions propagate; callers must preserve stderr and the nonzero exit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import shlex
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "automations/checkpoint_loop/runs"


def scoped_runtime(invocation: Path) -> tuple[dict, dict, str]:
    invocation = invocation.resolve()
    if not invocation.is_relative_to(RUNS.resolve()):
        raise ValueError("invocation must be beneath checkpoint_loop/runs")
    manifest = json.loads((invocation / "manager-commands.json").read_text())
    runtime = yaml.safe_load((invocation / "config_runtime.yaml").read_text())
    tag = runtime["run_farm"]["recipe_arg_overrides"]["run_farm_tag"]
    if not tag.startswith("checkpoint-f2-") or tag != manifest["run_farm_tag"]:
        raise ValueError("runtime and manifest must agree on the dedicated farm tag")
    if runtime["metasimulation"]["metasimulation_enabled"] is not False:
        raise ValueError("hardware inventory requires metasimulation_enabled=false")
    return manifest, runtime, tag


def local_processes(root: Path) -> list:
    processes = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            exe = (proc / "exe").resolve(strict=True)
            if exe.name not in ("vivado", "java", "firesim", "python", "python3", "python3.10"):
                continue
            argv = (proc / "cmdline").read_bytes().decode(errors="replace").strip("\0").split("\0")
            cwd = (proc / "cwd").resolve(strict=True)
            if str(root) not in " ".join(argv) and not cwd.is_relative_to(root):
                continue
            processes.append(dict(pid=int(proc.name), executable=str(exe), cwd=str(cwd), argv=argv))
        except (OSError, RuntimeError):  # process exited or belongs to another user
            continue
    return processes


def build_processes(invocation: Path) -> dict:
    # FireSim builds through localhost SSH. Observe that host's process namespace,
    # which may differ from the implementation tool's sandbox /proc namespace.
    script = ("from pathlib import Path\nimport json\n" + inspect.getsource(local_processes) +
              "\nprint(json.dumps(local_processes(Path(" + repr(str(ROOT)) + "))))\n")
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new", "-o",
            "UserKnownHostsFile=" + str(invocation.resolve() / "inventory_known_hosts"),
            "localhost", shlex.join(["python3", "-c", script])]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"localhost process inventory failed: {shlex.join(argv)}\n{result.stderr}")
    return dict(backend="localhost SSH /proc", argv=argv, processes=json.loads(result.stdout))


def collect(invocation: Path, session) -> dict:
    manifest, runtime, tag = scoped_runtime(invocation)
    # FireSim AWSEC2F2 tags runtime instances with fsimcluster, not firesim.
    # Include stopped/terminated instances as well so cleanup remains auditable.
    filters = [{"Name": "tag:fsimcluster", "Values": [tag]}]
    ec2 = session.client("ec2")
    instances = [instance
                 for page in ec2.get_paginator("describe_instances").paginate(Filters=filters)
                 for reservation in page["Reservations"]
                 for instance in reservation["Instances"]]
    return dict(
        observed_utc=datetime.now(timezone.utc).isoformat(),
        scope="resource inventory only; no FPGA workload/checkpoint acceptance",
        manager_root=str(ROOT), invocation=str(invocation.resolve()),
        aws_identity=session.client("sts").get_caller_identity(), region=session.region_name,
        instance_filters=filters, instances=instances, local_build_processes=build_processes(invocation),
        build_execution=manifest["build_execution"], build_dir=manifest["build_dir"],
        config_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(invocation.glob("config_*.yaml"))},
        metasimulation_enabled=runtime["metasimulation"]["metasimulation_enabled"],
        resume_commands=manifest["commands"],
        cleanup_policy="Collect results first; terminate only this fsimcluster tag. Never terminate the manager/localhost.",
    )


def main() -> None:
    import boto3
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(RUNS.resolve()):
        raise ValueError("inventory output must be beneath checkpoint_loop/runs")
    if args.out.exists():
        raise ValueError("preserve previous observations; choose a new output filename")
    result = collect(args.invocation, boto3.Session())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(args.out.resolve())


if __name__ == "__main__":
    main()
