"""M4 scheduler/callback component tests, NOT full metasim restart acceptance.

Source both env.sh files then vcs-env.sh LAST. Native ASan/UBSan and fresh VCS
DPI processes check credits, callback order/state and every owner byte against
an independent Python scheduler oracle, including before/after due callbacks.
"""
import argparse
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CUTS = (0, 1, 2, 3, 4, 9, 16, 27, 38, 39, 40, 60, 79, 83, 84, 85, 86, 99)
CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
TESTS = Path(__file__).resolve().parent


def oracle():
    cycle, counts, deadlines = 0, [0, 0], [0, 2]
    traces, snapshots = [], {}
    def words(*values):
        return struct.pack("<" + "Q" * len(values), *values)
    def text(value):
        data = value.encode()
        return words(len(data)) + data
    def owners():
        payload = words(0x3154504B43484353, 1, 1, 101, 0xFFFFFFFF, cycle, 2)
        for i, ident in enumerate(("A", "B")):
            payload += text(ident) + text("test.scheduler.counter.v1") + words((0, 2)[i], deadlines[i])
        return payload, words(counts[0]), words(counts[1])
    for index in range(100):
        if index in CUTS:
            snapshots[index] = owners()
        line = str(index)
        if cycle == 101:
            line += " finished"
        elif index % 2 == 0:
            line += " callbacks"
            for i, ident in enumerate(("A", "B")):
                if deadlines[i] == cycle:
                    counts[i] += 1
                    line += f" {ident}:{counts[i]}"
                    deadlines[i] += ((3 if counts[i] % 2 else 7) if i == 0 else
                                     (5 if counts[i] % 3 else 2))
        else:
            next_cycle = min(101, *deadlines)
            require(next_cycle > cycle, "oracle lacks progress")
            line += f" credit {next_cycle - cycle}"
            cycle = next_cycle
        traces.append(line + f" cycle {cycle} counts {counts[0]} {counts[1]}")
    return traces, snapshots, owners()


def compare(out, backend):
    expected, snapshots, final = oracle()
    require((out / "reference.trace").read_text().splitlines() == expected,
            f"{backend}: callback order/credits/state differ from independent oracle")
    for i, payload in enumerate(final):
        require((out / f"reference.final.{i}.owner").read_bytes() == payload, "final oracle owner mismatch")
    cases = []
    for cut in CUTS:
        require((out / f"restore-{cut}.trace").read_text().splitlines() == expected[cut:],
                f"{backend}: fresh continuation differs at cut={cut}")
        for i, payload in enumerate(snapshots[cut]):
            require((out / f"cut-{cut}.{i}.owner").read_bytes() == payload, "captured oracle owner mismatch")
            require((out / f"restore-{cut}.final.{i}.owner").read_bytes() == final[i], "final restore owner mismatch")
        cases.append(dict(cut=cut, matched_operations=100-cut))
    return dict(backend=backend, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    require(str(vcs) == "/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs", "source vcs-env.sh LAST")
    cxx = os.environ["CXX"]
    require(cxx == "/usr/bin/g++-13", "keep CXX from vcs-env.sh")
    sources = [TESTS / "scheduler_checkpoint.cc", CC / "core/systematic_scheduler.cc"]
    native = out / "scheduler-native"
    run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-g", "-no-pie",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer", f"-I{CC}",
         *sources, "-o", native], out / "native-build.log")
    simv = out / "scheduler-simv"
    run([vcs, "-full64", "-sverilog", "-timescale=1ns/1ps", "-top", "scheduler_checkpoint_tb",
         "-cc", os.environ["CC"], "-cpp", cxx, f"-Mdir={out / 'scheduler-csrc'}",
         "-CFLAGS", f"-std=c++17 -DSCHEDULER_CHECKPOINT_DPI -I{CC}",
         "-o", simv, TESTS / "scheduler_checkpoint_tb.sv", *sources], out / "vcs-build.log")
    summary = dict(scope="scheduler and callback component owners; not whole-runtime restore", cases=[])
    for backend in ("native-sanitized", "vcs-dpi"):
        case = out / backend
        case.mkdir(exist_ok=True)
        def command(restore, cut):
            if backend == "native-sanitized":
                return [native, "restore" if restore else "reference", case, cut]
            return [simv, "-no_save", f"+outdir={case}", f"+cut={cut}", f"+restore={int(restore)}"]
        run(command(False, 0), case / "reference.log")
        for cut in CUTS:
            run(command(True, cut), case / f"restore-{cut}.log")
        summary["cases"].append(compare(case, backend))
    result = run([native, "negative", out / "native-sanitized", 27], out / "negative.log")
    require("PASS:" in result, "negative checks did not pass")
    summary.update(fresh_continuations=2*len(CUTS), matched_operations=2*sum(100-c for c in CUTS))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
