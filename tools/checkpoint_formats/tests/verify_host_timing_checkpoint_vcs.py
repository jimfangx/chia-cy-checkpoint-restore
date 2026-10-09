"""M4 production host timing component continuation; not full metasim acceptance.

Source both env.sh files and vcs-env.sh LAST. An independent MT19937-64 Python
oracle checks every delay/commit and all engine words over repeated twists.
"""
import argparse
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
TESTS = Path(__file__).resolve().parent
CUTS = (0, 1, 2, 3, 5, 17, 310, 311, 312, 313, 623, 624, 625, 626, 1250, 2500, 7199)
CONFIGS = ((1, 0), (7, 1), (17, 2**64 - 1), (7, 2**63))
OPERATIONS = 7200
MASK = 2**64 - 1


class MT19937_64:
    """Integer recurrence and tempering, independently of the C++ stream adapter."""
    def __init__(self, seed):
        self.state = [seed]
        for i in range(1, 312):
            previous = self.state[-1]
            self.state.append((6364136223846793005 * (previous ^ (previous >> 62)) + i) & MASK)
        self.index = 312

    def draw(self):
        if self.index == 312:
            for i in range(312):
                combined = (self.state[i] & 0xFFFFFFFF80000000) | (self.state[(i + 1) % 312] & 0x7FFFFFFF)
                self.state[i] = self.state[(i + 156) % 312] ^ (combined >> 1)
                if combined & 1:
                    self.state[i] ^= 0xB5026F5AA96619E9
            self.index = 0
        value = self.state[self.index]
        self.index += 1
        value ^= (value >> 29) & 0x5555555555555555
        value ^= (value << 17) & 0x71D67FFFEDA60000
        value ^= (value << 37) & 0xFFF7EEE000000000
        value ^= value >> 43
        return value & MASK


def oracle(maximum, seed):
    engine = MT19937_64(seed)
    total, remaining = 0, 0
    trace, snapshots = [], {}
    def owner():
        words = [0x3154504B434D5448, 1, maximum, seed, total, remaining, 312,
                 *engine.state, engine.index]
        return struct.pack("<" + "Q" * len(words), *words)
    for index in range(OPERATIONS):
        if index in CUTS:
            snapshots[index] = owner()
        if remaining == 0:
            total = engine.draw() % maximum + 1
            remaining = total
            trace.append(f"{index} begin {remaining}")
        else:
            remaining -= 1
            trace.append(f"{index} tick {remaining}")
    return trace, snapshots, owner()


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
    sources = [TESTS / "host_timing_checkpoint.cc", CC / "emul/host_timing.cc"]
    native = out / "host-timing-native"
    run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-g", "-no-pie",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer", f"-I{CC}",
         *sources, "-o", native], out / "native-build.log")
    simv = out / "host-timing-simv"
    run([vcs, "-full64", "-sverilog", "-timescale=1ns/1ps", "-top", "host_timing_checkpoint_tb",
         "-cc", os.environ["CC"], "-cpp", cxx, f"-Mdir={out / 'host-timing-csrc'}",
         "-CFLAGS", f"-std=c++17 -DHOST_TIMING_CHECKPOINT_DPI -I{CC}",
         "-o", simv, TESTS / "host_timing_checkpoint_tb.sv", *sources], out / "vcs-build.log")
    summary = dict(scope="host timing component owner; not whole-runtime restore", cases=[])
    for maximum, seed in CONFIGS:
        expected, snapshots, final = oracle(maximum, seed)
        for backend in ("native-sanitized", "vcs-dpi"):
            case = out / f"{backend}-max{maximum}-seed{seed}"
            case.mkdir(exist_ok=True)
            def command(mode, cut, directory=case):
                if backend == "native-sanitized":
                    return [native, mode, directory, cut, maximum, seed]
                return [simv, "-no_save", f"+outdir={directory}", f"+cut={cut}",
                        f"+mode={mode}", f"+maximum={maximum}", f"+seed={seed}"]
            run(command(0, 0), case / "reference.log")
            require((case / "reference.trace").read_text().splitlines() == expected,
                    "delay/commit sequence differs from independent oracle")
            require((case / "reference.final.owner").read_bytes() == final, "final oracle engine mismatch")
            cuts = []
            for cut in CUTS:
                run(command(1, cut), case / f"restore-{cut}.log")
                require((case / f"restore-{cut}.trace").read_text().splitlines() == expected[cut:],
                        f"{backend}: delay/commit mismatch cut={cut}")
                require((case / f"cut-{cut}.owner").read_bytes() == snapshots[cut], "captured engine oracle mismatch")
                require((case / f"restore-{cut}.final.owner").read_bytes() == final, "restored final engine mismatch")
                total, pending = struct.unpack_from("<QQ", snapshots[cut], 32)
                cuts.append(dict(cut=cut, matched_operations=OPERATIONS-cut, total=total, pending=pending))
            negative = run(command(2, 0), case / "negative.log")
            rejected = re.search(r"PASS: (\d+) atomic malformed timing rejections", negative)
            require(rejected is not None, "negative checks did not pass")
            # Real fresh restore processes reject bad components before their
            # first edge, leaving no trace or claimed checkpoint continuation.
            bad_payloads = {"truncated": snapshots[0][:-1], "trailing": snapshots[0] + b"\0"}
            for label, word_index, value in (("index", 319, 313), ("configuration", 2, maximum + 1)):
                corrupt = bytearray(snapshots[0])
                struct.pack_into("<Q", corrupt, word_index * 8, value)
                bad_payloads[label] = corrupt
            for label, payload in bad_payloads.items():
                bad = case / label
                bad.mkdir(exist_ok=True)
                (bad / "cut-0.owner").write_bytes(payload)
                run(command(1, 0, bad), bad / "restore.log", expected=1)
                require(not (bad / "restore-0.trace").exists(), "invalid restore advanced component clock")
            summary["cases"].append(dict(backend=backend, maximum=maximum, seed=seed,
                                        cuts=cuts, malformed_rejections=int(rejected[1]),
                                        fresh_negative_restores=len(bad_payloads)))
    summary.update(fresh_continuations=2*len(CONFIGS)*len(CUTS),
                   matched_operations=2*len(CONFIGS)*sum(OPERATIONS-c for c in CUTS))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
