"""M4 functional-memory owner tests, NOT full metasim restart acceptance.

Source both env.sh files then vcs-env.sh LAST. Checks sanitized native execution
and fresh VCS DPI processes against an independent byte/transaction scoreboard.
All diagnostic files are written to --out under checkpoint_loop/runs.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CUTS = (0, 4, 8, 12, 17, 20, 26, 36)
BEATS = (4, 8, 32, 64)
CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
TESTS = Path(__file__).resolve().parent


def oracle(beat):
    """AXI handshakes evaluated from pre-edge outputs, without the C++ codec."""
    memory = bytearray((i * 17 + 3) & 255 for i in range(4096))
    reads, writes = [], []
    inflight, address, ident, size, remaining, cycle = 0, 0, 0, 0, 0, 0
    traces, snapshots = [], {}
    for c in range(42):
        if c in CUTS:
            fields = (0x3154504B434D4D46, 1, 4, 32, beat * 8, 4096, 64,
                      cycle, inflight, address, ident, size, remaining)
            snapshots[c] = (struct.pack("<13Q", *fields) + memory + bytes(beat) +
                            struct.pack("<Q", len(writes)) +
                            b"".join(struct.pack("<Q", i) for i in writes) +
                            struct.pack("<Q", len(reads)) +
                            b"".join(struct.pack("<QQ", i, last) + data for i, last, data in reads))
        rid, last, rdata = reads[0] if reads else (0, 0, bytes(beat))
        traces.append(" ".join(map(str, (c, 1, 1 - inflight, inflight,
                      int(bool(reads)), rid, 0, last, rdata.hex(),
                      int(bool(writes)), writes[0] if writes else 0, 0, memory.hex()))))
        if c == 35:
            # Match the existing reset contract: response queues/cycle reset;
            # a partially accepted write burst remains active.
            reads.clear()
            writes.clear()
            cycle = 0
            continue
        consume_r = bool(reads) and c >= 20 and c % 2 == 0
        consume_b = bool(writes) and c >= 25 and c % 3 == 1
        accept_w = bool(inflight) and c in (3, 7, 9, 11, 13, 16, 18, 36, 39)
        accept_aw = not inflight and c in (1, 12, 34)
        if c in (2, 10, 14, 37):
            count, read_id = (4, 7) if c == 2 else (3, 8) if c == 10 else (2, 9)
            reads.extend((read_id, int(i == count - 1), bytes(memory[64 + i * beat:64 + (i + 1) * beat]))
                         for i in range(count))
        if accept_aw:
            address, ident, remaining = ((64, 5, 4) if c == 1 else (512, 6, 3)
                                         if c == 12 else (1024 + beat // 2, 6, 2))
            size, inflight = beat // 2 if c == 34 else beat, 1
        if accept_w:
            data = b"".join(struct.pack("<I", (0xA1B2C300 + c * 0x01010101 + i) & 0xFFFFFFFF)
                            for i in range(beat // 4))
            base, offset = address // beat * beat, address % beat
            for i, byte in enumerate(data):
                if offset <= i < offset + size and (c not in (7, 16) or i % 2 == 1):
                    memory[base + i] = byte
            address += size
            remaining -= 1
            if remaining == 0:
                inflight = 0
                writes.append(ident)
        if consume_r:
            reads.pop(0)
        if consume_b:
            writes.pop(0)
        cycle += 1
    return traces, snapshots


def compare(out, beat, backend):
    expected, snapshots = oracle(beat)
    observed = (out / "reference.trace").read_text().splitlines()
    require(observed == expected, f"{backend} beat={beat} differs from independent AXI/byte oracle")
    cases = []
    for cut in CUTS:
        require((out / f"cut-{cut}.owner").read_bytes() == snapshots[cut],
                f"{backend} incomplete/different owner capture at {cut}")
        resumed = (out / f"restore-{cut}.trace").read_text().splitlines()
        require(resumed == observed[cut:], f"{backend} fresh continuation differs at cut={cut}")
        require((out / f"restore-{cut}.final.owner").read_bytes() ==
                (out / "reference.final.owner").read_bytes(), "final memory/queues/counter differ")
        cases.append(dict(cut=cut, matched_edges=len(resumed)))
    return dict(backend=backend, beat_bytes=beat, cases=cases)


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
    sources = [TESTS / "memory_checkpoint.cc", CC / "emul/mm.cc"]
    native = out / "memory-native"
    run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
         "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", f"-I{CC}",
         *sources, "-o", native], out / "native-build.log")
    simv = out / "memory-simv"
    run([vcs, "-full64", "-sverilog", "-timescale=1ns/1ps", "-top", "memory_checkpoint_tb",
         "-cc", os.environ["CC"], "-cpp", cxx, f"-Mdir={out / 'memory-csrc'}",
         "-CFLAGS", f"-std=c++17 -DMEMORY_CHECKPOINT_DPI -I{CC}",
         "-o", simv, TESTS / "memory_checkpoint_tb.sv", *sources], out / "vcs-build.log")
    summary = dict(scope="functional memory owner only; not full FAME/FASED/runtime restore", cases=[])
    for backend in ("native-sanitized", "vcs-dpi"):
        for beat in BEATS:
            case = out / f"{backend}-{beat}"
            case.mkdir(exist_ok=True)
            def command(restore, cut):
                if backend == "native-sanitized":
                    return [native, "restore" if restore else "reference", case, cut, beat]
                return [simv, "-no_save", f"+outdir={case}", f"+cut={cut}",
                        f"+beat={beat}", f"+restore={int(restore)}"]
            run(command(False, 0), case / "reference.log")
            for cut in CUTS:
                run(command(True, cut), case / f"restore-{cut}.log")
            summary["cases"].append(compare(case, beat, backend))
            negative = out / f"negative-{backend}-{beat}"
            negative.mkdir(exist_ok=True)
            shutil.copyfile(case / "cut-17.owner", negative / "cut-17.owner")
            result = run([native, "negative", negative, 17, beat], negative / "negative.log")
            require("PASS:" in result, "negative test did not pass")
    # Both independent processes/backends agree on all captured state, too.
    for beat in BEATS:
        for cut in CUTS:
            require((out / f"native-sanitized-{beat}/cut-{cut}.owner").read_bytes() ==
                    (out / f"vcs-dpi-{beat}/cut-{cut}.owner").read_bytes(), "backend capture mismatch")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
