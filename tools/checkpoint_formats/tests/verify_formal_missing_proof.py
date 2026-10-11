"""Fresh equivalence-only builds must reject constants without state predicates.

Source Chipyard env.sh, FireSim env.sh, then vcs-env.sh LAST. Each invocation
owns new CAD directories and evidence, including when --out already has runs.
No result is inferred from a previous invocation's files.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import export_state_map, sha
from .verify_formal_state_map import FIXTURE, FORMALITY, GENUS, ROOT, fixture_manifest


def verify(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out))
    rtl = FIXTURE / "constants/dut.v"
    commands, results = [], {}
    for profile in ("direct", "inverted"):
        cells = FIXTURE if profile == "direct" else FIXTURE / "inverted"
        directory = run / profile
        synth, formal = directory / "synthesis", directory / "formal"
        synth.mkdir(parents=True)
        formal.mkdir()
        env = dict(os.environ, CHECKPOINT_FIXTURE=str(FIXTURE),
                   CHECKPOINT_LIBRARY=str(cells / "cells.lib"), CHECKPOINT_RTL=str(rtl),
                   CHECKPOINT_DUPLICATE_REGISTERS="0", CHECKPOINT_REORDER_REGISTERS="0",
                   CHECKPOINT_CELLS=str(cells / "cells.v"),
                   CHECKPOINT_FORMAL_CONFIG=str(cells / "config.tcl"),
                   CHECKPOINT_NETLIST=str(synth / "netlist.v"))
        env.pop("LD_LIBRARY_PATH", None)

        def invoke(argv, cwd, log):
            with log.open("w") as output:
                process = subprocess.run(argv, cwd=cwd, env=env, stdout=output,
                                         stderr=subprocess.STDOUT, timeout=240)
            commands.append(dict(cwd=os.path.relpath(cwd, ROOT), argv=argv,
                                 log=str(log), exit_code=process.returncode))
            (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            assert process.returncode == 0, str(log)

        invoke([GENUS, "-no_gui", "-batch", "-files", str(FIXTURE / "synth.tcl")],
               synth, synth / "synth.log")
        invoke([FORMALITY, "-f", str(FIXTURE / "prove.tcl")], formal, formal / "formal.log")
        manifest, _ = fixture_manifest(rtl, optimize_registers=True, constant_registers=True)
        paths = dict(rtl=rtl, netlist=synth / "netlist.v", models=cells / "cells.v",
                     library=cells / "cells.lib", synthesis_script=FIXTURE / "synth.tcl",
                     synthesis_log=synth / "synth.log", formal_script=FIXTURE / "prove.tcl",
                     formal_configuration=cells / "config.tcl", formal_log=formal / "formal.log",
                     evidence=formal / "evidence.tsv", blackboxes=formal / "blackboxes.rpt",
                     optimization_report=formal / "optimized-unread.rpt")
        artifacts = {role: path.read_bytes() for role, path in paths.items()}
        assert b"Verification SUCCEEDED\n" in artifacts["formal_log"]
        assert artifacts["evidence"].startswith(b"FORMAT\tformality-state-v3\nVERIFY\t1\n")
        rows = artifacts["evidence"].splitlines()
        assert sum(row.startswith(b"OPTIMIZED\tunread\t") for row in rows) == 4
        assert sum(row.startswith(b"PROVEN\t") for row in rows) == 24
        try:
            export_state_map(manifest, "StateMapDUT",
                             json.loads((cells / "cell-adapter.json").read_text()), artifacts)
        except FormatError as error:
            # This exact error is reached only after checking synthesis/proof
            # identities and the complete physical/semantic inventories.
            assert str(error) == "unproven or unmappable semantic state", str(error)
            results[profile] = dict(formal_global_equivalence="passed", original_semantic_bits=32,
                                    gate_bits=24, explicitly_unread_bits=4, unclassified_constant_bits=4,
                                    export_rejected=str(error),
                                    inputs={role: str(path) for role, path in paths.items()},
                                    input_sha256={role: sha(data) for role, data in artifacts.items()})
        else:
            raise AssertionError("Global PASS excused unproven constant state")
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    summary = dict(status="passed", run=str(run), profiles=results)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "automations/checkpoint_loop/runs/formal-missing-proof")
    args = parser.parse_args()
    print(json.dumps(verify(args.out), indent=2))


if __name__ == "__main__":
    main()
