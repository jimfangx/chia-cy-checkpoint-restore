#!/usr/bin/env python3
"""Read-only manager preflight with a fresh evidence directory on every attempt.

Run through f2.py run to obtain the initialized FireSim manager environment.
Only the optional selection file changes; receipts and their logs never reuse paths.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import f2_inventory

ROOT = f2_inventory.ROOT
RUNS = f2_inventory.RUNS


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, doc: dict) -> None:
    # A unique attempt owns these files. Exclusive creation detects accidental reuse.
    with path.open("x") as stream:
        stream.write(json.dumps(doc, indent=2, default=str) + "\n")


def audit_receipt(receipt: Path, expected_sha256: str) -> dict:
    """Verify a selected observation, its local evidence and protected inputs."""
    receipt = receipt.resolve()
    if sha(receipt) != expected_sha256:
        raise ValueError(f"preflight receipt hash mismatch: {receipt}")
    doc = json.loads(receipt.read_text())
    if (doc.get("status") != "pass" or doc.get("backend") != "f2"
            or doc.get("new_afi_requested") is not False or doc.get("new_instance_launched") is not False
            or doc.get("protected_inputs_unchanged") is not True):
        raise ValueError(f"preflight receipt is not a successful read-only check: {receipt}")
    artifacts = doc.get("artifacts")
    required = {"native-setup.log", "resource-inventory.json", "protected-inputs.json"}
    if not isinstance(artifacts, dict) or not required.issubset(artifacts):
        raise ValueError("preflight receipt omits required evidence")
    for name, digest in artifacts.items():
        path = receipt.parent / name
        if Path(name).name != name or path.is_symlink() or path.resolve().parent != receipt.parent:
            raise ValueError(f"preflight artifact must be a direct local file: {name}")
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f"preflight artifact hash mismatch: {name}")
    actual = {p.name for p in receipt.parent.iterdir() if p != receipt}
    if actual != set(artifacts):
        raise ValueError("preflight attempt contains unbound evidence")
    protected = json.loads((receipt.parent / "protected-inputs.json").read_text())
    if not isinstance(protected, dict) or not protected:
        raise ValueError("preflight protected inputs must be a nonempty mapping")
    if any(sha(Path(name)) != digest for name, digest in protected.items()):
        raise ValueError("preflight protected inputs changed")
    sources = doc.get("sources", {})
    required_sources = {"automations/checkpoint_loop/f2_preflight.py", "automations/checkpoint_loop/f2_inventory.py"}
    if set(sources) != required_sources or any(sha(ROOT / name) != digest for name, digest in sources.items()):
        raise ValueError("preflight producer sources changed or missing")
    return doc


def localhost_check() -> dict:
    from fabric.api import env, execute, run
    env.timeout = 15
    env.connection_attempts = 1
    env.disable_known_hosts = True
    env.key_filename = os.path.expanduser("~/firesim.pem")
    env.abort_on_prompts = True
    result = execute(run, "true", hosts=["localhost"])["localhost"]
    return dict(command="true", returncode=result.return_code, key_filename=env.key_filename)


def collect(attempt: Path, invocation: Path, protected: dict, session) -> dict:
    hdk = ROOT / "sims/firesim/platforms/f2/aws-fpga-firesim-f2"
    argv = ["bash", "-c", 'set -eo pipefail; cd "$1"; source ./hdk_setup.sh -skip_downloads; '
            "command -v vivado; vivado -version; cat supported_vivado_versions.txt; "
            "cat hdk/common/ip/VIVADO_VERSION; cat hdk/common/shell_stable/shell_version.txt; git rev-parse HEAD",
            "native-setup", str(hdk)]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    with (attempt / "native-setup.log").open("x") as stream:
        stream.write(result.stdout + result.stderr)
    fabric = localhost_check()
    # collect() uses the invocation for resource scope, but its SSH known-host file
    # belongs to this fresh observation rather than the retained build invocation.
    inventory = f2_inventory.collect(invocation, session, process_directory=attempt)
    ec2 = session.client("ec2")
    filters = [{"Name": "tag:fsimcluster", "Values": ["checkpoint-f2-*"]}]
    inventory["all_loop_instance_filters"] = filters
    inventory["all_loop_instances"] = [i for page in ec2.get_paginator("describe_instances").paginate(Filters=filters)
                                       for reservation in page["Reservations"] for i in reservation["Instances"]]
    inventory["owned_fpga_images"] = ec2.describe_fpga_images(Owners=["self"])
    write_json(attempt / "resource-inventory.json", inventory)
    manifest = json.loads((invocation / "manager-commands.json").read_text())
    active = [i["InstanceId"] for i in inventory["all_loop_instances"]
              if i["State"]["Name"] not in ("terminated", "shutting-down")]
    afis = inventory["owned_fpga_images"].get("FpgaImages", [])
    unchanged = all(sha(Path(p)) == expected for p, expected in protected.items())
    passed = result.returncode == 0 and "vivado v2025.2" in result.stdout.lower() and fabric["returncode"] == 0 and unchanged
    return dict(status="pass" if passed else "fail", native_argv=argv, native_returncode=result.returncode,
                fabric_localhost=fabric, protected_inputs_unchanged=unchanged,
                aws_identity=inventory["aws_identity"], region=inventory["region"],
                active_loop_instance_ids=active, owned_afi_ids=[i["FpgaImageId"] for i in afis],
                pending_afi_ids=[i["FpgaImageId"] for i in afis if i["State"]["Code"] == "pending"],
                local_processes=inventory["local_build_processes"]["processes"], retained_invocation=str(invocation),
                retained_build_dir=manifest["build_dir"], hwdb_ready=manifest["hwdb_ready"],
                checkpoint_hardware_verified=manifest["checkpoint_hardware_verified"],
                resume_build=manifest["commands"]["buildbitstream"])


def run_preflight(out: Path, invocation: Path, protected_inputs: Path, *, selected: Path | None = None,
                  session=None) -> Path:
    out, invocation, protected_inputs = out.resolve(), invocation.resolve(), protected_inputs.resolve()
    if not out.is_relative_to(RUNS.resolve()) or (selected is not None and not selected.resolve().is_relative_to(RUNS.resolve())):
        raise ValueError("preflight evidence and selection must be beneath checkpoint_loop/runs")
    # Reject invalid inputs before publishing any receipt, and keep their exact bytes.
    f2_inventory.scoped_runtime(invocation)
    protected_bytes = protected_inputs.read_bytes()
    protected = json.loads(protected_bytes)
    if not isinstance(protected, dict) or not protected:
        raise ValueError("protected inputs must be a nonempty path-to-SHA256 mapping")
    out.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="preflight-", dir=out))
    (attempt / "protected-inputs.json").write_bytes(protected_bytes)
    sources = {name: sha(ROOT / name) for name in (
        "automations/checkpoint_loop/f2_preflight.py", "automations/checkpoint_loop/f2_inventory.py")}
    summary = dict(status="fail", backend="f2", observed_utc=datetime.now(timezone.utc).isoformat(),
                   scope="read-only manager/native HDK/Vivado/localhost SSH/AWS resources; no FPGA acceptance",
                   new_afi_requested=False, new_instance_launched=False, sources=sources)
    try:
        if session is None:
            import boto3
            session = boto3.Session()
        summary.update(collect(attempt, invocation, protected, session))
        if any(sha(ROOT / name) != digest for name, digest in sources.items()):
            summary.update(status="fail", error="preflight producer sources changed during collection")
    except Exception as error:
        # Preserve a failed observation without replacing the last successful selection.
        summary.update(status="fail", error_type=type(error).__name__, error=str(error))
    summary["artifacts"] = {p.name: sha(p) for p in sorted(attempt.iterdir()) if p.is_file()}
    receipt = attempt / "preflight-receipt.json"
    write_json(receipt, summary)
    if summary["status"] == "pass" and selected is not None:
        selected = selected.resolve()
        selected.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=selected.name + ".", dir=selected.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(json.dumps(dict(path=str(receipt), sha256=sha(receipt)), indent=2) + "\n")
            os.replace(temporary, selected)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--invocation", required=True, type=Path)
    parser.add_argument("--protected-inputs", required=True, type=Path)
    parser.add_argument("--selected", type=Path)
    args = parser.parse_args()
    receipt = run_preflight(args.out, args.invocation, args.protected_inputs, selected=args.selected)
    print(receipt)
    return 0 if json.loads(receipt.read_text())["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
