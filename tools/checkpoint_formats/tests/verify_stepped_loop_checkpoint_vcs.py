"""Production FCFS run-loop/scheduler components; not full metasim restore.

The oracle executes the former nested while-loop operation order. Completion
is independent of issued scheduler credit. Every host-operation boundary,
including each bridge index and pending credit, is restored in a fresh native
ASan/UBSan process and a fresh VCS DPI process before its first component edge.
"""
import argparse
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
TESTS = Path(__file__).resolve().parent
CONFIGS = ((3, 0, 17), (3, 6, 17), (0, 0, 17), (0, 6, 17), (3, 0, 0))


def words(*values):
    return struct.pack("<" + "Q" * len(values), *values)


def text(value):
    data = value.encode()
    return words(len(data)) + data


def oracle(bridges, stop, horizon):
    """Original nested-loop calls plus payloads at each call boundary."""
    fields = [0] * (6 + bridges)
    issued_cycle = deadline = 0
    snapshots, traces = {}, []
    done = False

    def owners(phase, index=0):
        loop = words(0x3154504B434C5253, 1, bridges, phase, index, int(done))
        scheduler = words(0x3154504B43484353, 1, 1, horizon, 0xFFFFFFFF, issued_cycle, 1)
        scheduler += text("profile") + text("test.stepped-services.v1") + words(0, deadline)
        services = words(bridges, stop, horizon, *fields)
        return loop, scheduler, services

    def before(phase, index=0):
        snapshots[len(traces)] = owners(phase, index)

    def emit(event):
        traces.append(f"{len(traces)} {event} " + " ".join(map(str, fields)))

    # The legacy loop's observable service order, not the C++ phase dispatcher.
    while not done:
        before(0)
        emit(f"horizon {int(issued_cycle == horizon)}")
        if issued_cycle == horizon:
            break
        before(1)
        if deadline == issued_cycle:
            fields[5] += 1
            deadline += 4
        emit("tasks")
        before(2)
        fields[1] = min(horizon, deadline) - issued_cycle
        require(fields[1] > 0, "oracle cannot issue credit")
        issued_cycle += fields[1]
        fields[2] += 1
        emit(f"issue {fields[1]}")
        while True:
            before(3)
            fields[3] += 1
            if fields[1]:
                fields[1] -= 1
                fields[0] += 1
            emit(f"poll {int(fields[1] == 0)}")
            if fields[1] == 0:
                break
            for bridge in range(bridges):
                before(4, bridge)
                fields[6 + bridge] += 1
                emit(f"tick {bridge}")
            before(5)
            fields[4] += 1
            done = bool(stop and fields[0] >= stop)
            emit(f"sample {int(done)}")
            if done:
                break
    # Capture both terminal states and demonstrate idempotent completion.
    for _ in range(2):
        before(6)
        emit("terminal")
    return traces, snapshots, owners(6)


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
    sources = [TESTS / "stepped_loop_checkpoint.cc", CC / "core/stepped_run_loop.cc",
               CC / "core/systematic_scheduler.cc"]
    native = out / "stepped-loop-native"
    run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-g", "-no-pie",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer", f"-I{CC}",
         *sources, "-o", native], out / "native-build.log")
    simv = out / "stepped-loop-simv"
    run([vcs, "-full64", "-sverilog", "-timescale=1ns/1ps", "-top", "stepped_loop_checkpoint_tb",
         "-cc", os.environ["CC"], "-cpp", cxx, f"-Mdir={out / 'stepped-loop-csrc'}",
         "-CFLAGS", f"-std=c++17 -DSTEPPED_LOOP_CHECKPOINT_DPI -I{CC}",
         "-o", simv, TESTS / "stepped_loop_checkpoint_tb.sv", *sources], out / "vcs-build.log")
    summary = dict(scope="run-loop, scheduler and test services components; not whole-runtime restore",
                   cases=[], fresh_continuations=0, matched_operations=0, fresh_negative_restores=0)
    for backend in ("native-sanitized", "vcs-dpi"):
        for bridges, stop, horizon in CONFIGS:
            case = out / backend / f"b{bridges}-done{stop}-horizon{horizon}"
            case.mkdir(parents=True, exist_ok=True)
            expected, snapshots, final = oracle(bridges, stop, horizon)
            def command(restore, cut, destination=case):
                if backend == "native-sanitized":
                    return [native, "negative" if restore == 2 else ("restore" if restore else "reference"), destination, cut,
                            bridges, stop, horizon, len(expected)]
                return [simv, "-no_save", f"+outdir={destination}", f"+cut={cut}", f"+restore={int(restore)}",
                        f"+bridges={bridges}", f"+stop={stop}", f"+horizon={horizon}",
                        f"+operations={len(expected)}"]
            run(command(False, 0), case / "reference.log")
            require((case / "reference.trace").read_text().splitlines() == expected,
                    "operation order differs from legacy-loop oracle")
            phases, pending_cuts = set(), 0
            for cut, payloads in snapshots.items():
                phases.add(struct.unpack_from("<Q", payloads[0], 24)[0])
                pending_cuts += struct.unpack_from("<Q", payloads[2], 32)[0] > 0
                for i, payload in enumerate(payloads):
                    require((case / f"cut-{cut}.{i}.owner").read_bytes() == payload, "oracle capture mismatch")
                run(command(True, cut), case / f"restore-{cut}.log")
                require((case / f"restore-{cut}.trace").read_text().splitlines() == expected[cut:],
                        "fresh process changes service order or timing")
                for i, payload in enumerate(final):
                    require((case / f"reference.final.{i}.owner").read_bytes() == payload,
                            "reference final owner mismatch")
                    require((case / f"restore-{cut}.final.{i}.owner").read_bytes() == payload,
                            "restore final owner mismatch")
                summary["fresh_continuations"] += 1
                summary["matched_operations"] += len(expected) - cut
            # A malformed first owner must reject before opening the trace or
            # advancing any component edge. Restore the valid test input after.
            valid = snapshots[0][0]
            for label, malformed in (("phase", valid[:24] + words(7) + valid[32:]),
                                     ("truncated", valid[:-1])):
                negative = case / f"negative-{label}"
                negative.mkdir(exist_ok=True)
                for i, payload in enumerate(snapshots[0]):
                    (negative / f"cut-0.{i}.owner").write_bytes(malformed if i == 0 else payload)
                run(command(True, 0, negative), negative / "restore.log", expected=None)
                require(not (negative / "restore-0.trace").exists(),
                        "negative restore opened a trace before rejecting")
                summary["fresh_negative_restores"] += 1
            summary["cases"].append(dict(backend=backend, bridges=bridges, stop=stop, horizon=horizon,
                                         boundaries=len(snapshots), phases=sorted(phases), pending_cuts=pending_cuts))
        result = run(command(2, 0), out / f"negative-{backend}.log")
        require("PASS:" in result, "negative guards did not pass")
        summary[f"negative_result_{backend}"] = result.split("PASS:", 1)[1].splitlines()[0].strip()
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
