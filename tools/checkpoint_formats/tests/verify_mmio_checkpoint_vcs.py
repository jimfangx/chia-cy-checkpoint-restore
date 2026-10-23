"""MMIO/CPU-AXI + functional memory component cuts, not full metasim restore.

Source both env.sh files, then vcs-env.sh LAST. All diagnostics go to --out.
Fresh native ASan/UBSan and VCS DPI processes compare every component edge and
every captured byte against an independent Python AXI/byte scoreboard.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import shutil
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
TESTS = Path(__file__).resolve().parent
CUTS = (0, 1, 3, 6, 9, 12, 16, 19, 23, 27, 35, 42, 55)
BEATS = (4, 8, 32, 64)
STEPS = 88


def packed(*values):
    return struct.pack("<" + "Q" * len(values), *values)


def oracle(beat):
    memory = bytearray((i * 17 + 3) & 255 for i in range(4096))
    ar, aw, w, r, b, mr, mb = [], [], [], [], [], [], []
    ri = wi = mi = False
    maddr = mid = msize = mcount = cycle = 0
    traces, snapshots, observations = [], {}, []
    size = beat.bit_length() - 1
    for c in range(STEPS):
        if c in CUTS:
            mmio = (packed(0x3154504B434F494D, 1, 4, 32, beat * 8, ri, wi) + bytes(beat) +
                    packed(len(ar)) + b"".join(packed(*q) for q in ar) +
                    packed(len(aw)) + b"".join(packed(*q) for q in aw) +
                    packed(len(w)) + b"".join(packed(strb, last) + data for strb, last, data in w) +
                    packed(len(r)) + b"".join(packed(ident, last) + data for ident, last, data in r) +
                    packed(len(b)) + b"".join(packed(ident) for ident in b))
            mem = (packed(0x3154504B434D4D46, 1, 4, 32, beat * 8, 4096, 64,
                          cycle, mi, maddr, mid, msize, mcount) + memory + bytes(beat) +
                   packed(len(mb)) + b"".join(packed(ident) for ident in mb) +
                   packed(len(mr)) + b"".join(packed(ident, last) + data for ident, last, data in mr))
            snapshots[c] = (mmio, mem)
            observations.append(dict(cut=c, read_inflight=ri, write_inflight=wi,
                                     queued_ar=len(ar), queued_aw=len(aw), queued_w=len(w),
                                     queued_r=len(r), queued_b=len(b),
                                     peer_write_beats_remaining=mcount if mi else 0,
                                     peer_queued_r=len(mr), peer_queued_b=len(mb)))
        if c <= 3:
            ar.append((0, 64 + c * 128, size, (3, 2, 0, 1)[c]))
        if c in (0, 1, 4, 6):
            length = 3 if c == 0 else 2 if c == 1 else 0 if c == 4 else 1
            aw.append((0, 64 + c * 128, size, length))
            payload = bytes((i * 13 + c * 7 + 5) & 255 for i in range((length + 1) * beat))
            strb = (1 << beat) - 1
            if c == 1:
                strb &= 0xAAAAAAAAAAAAAAAA
            w.extend((strb, int(i == length), payload[i * beat:(i + 1) * beat])
                     for i in range(length + 1))
        response, write = "-", False
        if c >= 18 and c % 7 == 4 and ar and len(r) > ar[0][3]:
            count = ar.pop(0)[3] + 1
            response = (b"".join(r.pop(0)[2] for _ in range(count)) +
                        bytes([0xA5]) * ((4 - count) * beat)).hex()
            ri = False
        if c >= 20 and c % 7 == 6 and aw and b:
            aw.pop(0)
            b.pop(0)
            wi, write = False, True
        arv, awv, wv = bool(ar) and not ri, bool(aw) and not wi, bool(w)
        a = ar[0] if arv else (0, 0, 0, 0)
        d = aw[0] if awv else (0, 0, 0, 0)
        strb, last, data = w[0] if wv else (0, 0, bytes(beat))
        traces.append(" ".join(map(str, (c, int(response != "-"), response, int(write), int(arv),
                                        *a, int(awv), *d, int(wv), strb, last, data.hex(),
                                        int(ri), int(wi), memory.hex()))))
        # Evaluate all handshakes from pre-edge values, as with two RTL peers.
        reset = c < 2
        arf = not reset and arv and c >= 2 and c % 4 != 0
        awf = not reset and awv and not mi and c >= 3 and c % 2 != 0
        wf = not reset and wv and mi and c >= 5 and c % 3 != 0
        rf = not reset and bool(mr) and ri and c >= 10 and c % 3 != 1
        bf = not reset and bool(mb) and wi and c >= 15 and c % 4 != 2
        if arf:
            ri = True
            address = a[1] // beat * beat
            mr.extend((a[0], int(i == a[3]), bytes(memory[address + i * beat:address + (i + 1) * beat]))
                      for i in range(a[3] + 1))
        if awf:
            wi, mi = True, True
            mid, maddr, msize, mcount = d[0], d[1], 1 << d[2], d[3] + 1
        if wf:
            w.pop(0)
            for i, byte in enumerate(data):
                if strb & (1 << i):
                    memory[maddr + i] = byte
            maddr += msize
            mcount -= 1
            if mcount == 0:
                mi = False
                mb.append(mid)
        if rf:
            r.append(mr.pop(0))
        if bf:
            b.append(mb.pop(0))
        cycle += 1
        if reset:
            mr.clear()
            mb.clear()
            cycle = 0
    require(not (ar or aw or w or r or b or mr or mb or ri or wi or mi), "oracle workload incomplete")
    return traces, snapshots, observations


def compare(case, beat, backend):
    traces, snapshots, observations = oracle(beat)
    observed = (case / "reference.trace").read_text().splitlines()
    require(observed == traces, f"{backend} beat={beat} differs from independent AXI/byte oracle")
    matched = 0
    for cut in CUTS:
        for owner, expected in zip(("mmio", "memory"), snapshots[cut]):
            require((case / f"cut-{cut}.{owner}.owner").read_bytes() == expected,
                    f"{backend} incomplete/different {owner} capture at {cut}")
            require((case / f"restore-{cut}.final.{owner}.owner").read_bytes() ==
                    (case / f"reference.final.{owner}.owner").read_bytes(),
                    f"{backend} final {owner} state differs")
        resumed = (case / f"restore-{cut}.trace").read_text().splitlines()
        require(resumed == observed[cut:], f"{backend} fresh continuation differs at cut={cut}")
        matched += len(resumed)
    require(any(o["queued_r"] and o["queued_w"] and o["read_inflight"] and o["write_inflight"]
                for o in observations), "missing overlapping transport traffic at a cut")
    require(any(o["peer_write_beats_remaining"] and o["peer_queued_r"] for o in observations),
            "missing simultaneous memory burst/read responses at a cut")
    return dict(backend=backend, beat_bytes=beat, fresh_continuations=len(CUTS),
                matched_edges=matched, cuts=observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ["VCS_HOME"]) / "bin/vcs"
    cxx = os.environ["CXX"]
    require(str(vcs) == _toolchain.VCS and cxx == _toolchain.CXX,
            "source vcs-env.sh LAST and keep its compiler settings")
    sources = [TESTS / "mmio_checkpoint.cc", CC / "emul/mmio.cc", CC / "emul/mm.cc"]
    native = out / "mmio-native"
    run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-g",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer", f"-I{CC}", *sources, "-o", native],
        out / "native-build.log", cwd=out)
    simv = out / "mmio-simv"
    run([vcs, "-full64", "-sverilog", "-timescale=1ns/1ps", "-top", "mmio_checkpoint_tb",
         "-cc", os.environ["CC"], "-cpp", cxx, f"-Mdir={out / 'mmio-csrc'}", "-CFLAGS",
         f"-std=c++17 -DMMIO_CHECKPOINT_DPI -I{CC}", "-o", simv,
         TESTS / "mmio_checkpoint_tb.sv", *sources], out / "vcs-build.log", cwd=out)
    summary = dict(scope="MMIO/CPU-AXI + functional-memory component owners; not full metasim restore", cases=[])
    for backend in ("native-sanitized", "vcs-dpi"):
        for beat in BEATS:
            case = out / f"{backend}-{beat}"
            case.mkdir(exist_ok=True)
            def command(restore, cut):
                if backend == "native-sanitized":
                    return [native, "restore" if restore else "reference", case, cut, beat]
                return [simv, "-no_save", f"+outdir={case}", f"+cut={cut}",
                        f"+beat={beat}", f"+restore={int(restore)}"]
            run(command(False, 0), case / "reference.log", cwd=case)
            for cut in CUTS:
                run(command(True, cut), case / f"restore-{cut}.log", cwd=case)
            negative = out / f"negative-{backend}-{beat}"
            negative.mkdir(exist_ok=True)
            for owner in ("mmio", "memory"):
                name = f"cut-16.{owner}.owner"
                shutil.copyfile(case / name, negative / name)
            result = run([native, "negative", negative, 16, beat], negative / "negative.log", cwd=negative)
            require("PASS:" in result, "negative checks did not pass")
            summary["cases"].append(compare(case, beat, backend))
    for beat in BEATS:
        for cut in CUTS:
            for owner in ("mmio", "memory"):
                name = f"cut-{cut}.{owner}.owner"
                require((out / f"native-sanitized-{beat}" / name).read_bytes() ==
                        (out / f"vcs-dpi-{beat}" / name).read_bytes(), "backend capture mismatch")
    summary["fresh_continuations"] = sum(c["fresh_continuations"] for c in summary["cases"])
    summary["matched_edges"] = sum(c["matched_edges"] for c in summary["cases"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
