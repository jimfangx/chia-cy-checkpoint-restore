"""Offline tamper tests for the F2 baseline auditor; never alter real evidence."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.tests.audit_f2_baseline import audit, require


def verify(root):
    baseline = audit(root)
    rejected = []
    with tempfile.TemporaryDirectory(prefix="offline-f2-audit-", dir=root.parent) as scratch:
        fixture = Path(scratch) / "evidence"
        shutil.copytree(root, fixture)
        # Rebind only the offline clone's source copies, never the originals.
        driver_path = fixture / "driver-provenance.json"
        driver = json.loads(driver_path.read_text())
        for source in driver["sources"]:
            source["snapshot"] = str(fixture / Path(source["snapshot"]).relative_to(root))
        driver_path.write_text(json.dumps(driver))
        audit(fixture)

        def reject(name, relative_path, change):
            path = fixture / relative_path
            original = path.read_bytes()
            try:
                path.write_bytes(change(original))
                try:
                    audit(fixture)
                except (ValueError, KeyError) as error:
                    rejected.append(dict(case=name, reason=str(error)))
                else:
                    raise AssertionError("forged evidence accepted: " + name)
            finally:
                path.write_bytes(original)

        reject("metasim-enabled", "baseline/config_runtime.yaml",
               lambda data: data.replace(b"metasimulation_enabled: false", b"metasimulation_enabled: true"))
        reject("wrong-loaded-image", "loaded-slot.stdout",
               lambda data: data.replace(baseline["agfi"].encode(), b"agfi-00000000000000000"))
        reject("wrong-instance", "imds-document.stdout",
               lambda data: data.replace(baseline["instance_id"].encode(), b"i-00000000000000000"))
        reject("changed-workload-byte", "workload/rocket-quad.riscv",
               lambda data: data[:-1] + bytes([data[-1] ^ 1]))
        reject("changed-deployed-driver", "deployed-hashes.stdout",
               lambda data: b"0" * 64 + data[64:])
        log = next(fixture.glob("results-workload/*/uartlog")).relative_to(fixture)
        reject("target-failed", log, lambda data: data.replace(b"*** PASSED ***", b"*** FAILED ***"))
        reject("driver-exit-nonzero", log,
               lambda data: data.replace(b'COMMAND_EXIT_CODE="0"', b'COMMAND_EXIT_CODE="1"'))

        def still_running(data):
            value = json.loads(data)
            value["instances"][0]["State"]["Name"] = "running"
            return json.dumps(value).encode()

        reject("cleanup-unconfirmed", "resources-after-cleanup.json", still_running)
        source = Path(driver["sources"][0]["snapshot"]).relative_to(fixture)
        reject("driver-source-changed", source, lambda data: data + b"\n// tampered offline copy\n")
        native = baseline["native_manager_logs"]["runworkload"]["path"]
        reject("empty-native-manager-log", native, lambda data: b"")
        reject("native-manager-enables-metasim", native,
               lambda data: data.replace(b"'metasimulation_enabled': False",
                                         b"'metasimulation_enabled': True"))
        reject("native-workload-completion-missing", native,
               lambda data: data.replace(b"FireSim Simulation Exited Successfully", b"workload interrupted"))
        reject("checkpoint-build-uses-remote-host", "checkpoint-build/config_build.yaml",
               lambda data: data.replace(b"- localhost", b"- remote-build-host"))
        reject("checkpoint-build-recipe-drift", "checkpoint-build/config_build_recipes.yaml",
               lambda data: data.replace(b"fpga_frequency: 140", b"fpga_frequency: 150"))
        audit(fixture)
    require(len(rejected) == 14, "missing negative audit cases")
    return dict(status="passed", scope="offline evidence auditor tamper tests only",
                original_hardware_evidence_unchanged=True, rejected=rejected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()), indent=2))
