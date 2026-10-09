"""Compare actual parked rising/falling cuts; no full runtime restore claim.

Both input trees must come from verify_settled_boundary_vcs, using the same
generated build, cuts and timing configuration. This audits every software
owner and generated word, rather than relying on a target-cycle counter alone.
"""
import argparse
import filecmp
import json
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import canonical, require, unique_object
from tools.checkpoint_formats.generated_restore import generated_build_identity
from tools.checkpoint_formats.harness_restore import harness_layout
from tools.checkpoint_formats.simulator import validate_generated_stream
from tools.checkpoint_formats.tests.verify_driver_boundary_vcs import read_diagnostic
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--high', type=Path, required=True)
    parser.add_argument('--low', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    generated = args.build / 'f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config'
    manifest = json.loads((generated / 'FireSim-generated.simulator-state.json').read_text())
    verilog = ROOT / 'sims/firesim/sim/midas/src/main/verilog'
    identity = generated_build_identity(manifest,
        (generated / 'FireSim-generated.simulator-reference.fir').read_text(),
        (generated / 'FireSim-generated.sv').read_text(), (verilog / 'BUFGCE.v').read_text())
    layout = harness_layout((verilog / 'top.sv').read_text(),
        (generated / 'FireSim-generated.const.vh').read_text(),
        (generated / 'FireSim-generated.defines.vh').read_text(), identity)
    high = json.loads((args.high / 'summary.json').read_text())
    low = json.loads((args.low / 'summary.json').read_text())
    require(high['sample_phase'] == 'settled_host_posedge_parked_driver'
            and low['sample_phase'] == 'settled_host_negedge_parked_driver', 'wrong phase evidence')
    require([(c['timing'], c['cut']) for c in high['cases']] ==
            [(c['timing'], c['cut']) for c in low['cases']], 'different cuts/configurations')
    results = []
    for case in low['cases']:
        relative = Path(case['timing']) / f"cut-{case['cut']}"
        hdir, ldir = args.high / relative, args.low / relative
        for name in ('ports.trace', 'generated.jsonl'):
            require(filecmp.cmp(hdir / name, ldir / name, shallow=False), 'phase changed uninterrupted trace')
        hcut, howners = read_diagnostic(hdir / 'software.diag')
        lcut, lowners = read_diagnostic(ldir / 'software.diag')
        require(hcut == lcut == case['cut'] and list(howners) == list(lowners), 'owner inventory changed')
        compared = 0
        for owner in howners:
            hs, hp = howners[owner]; ls, lp = lowners[owner]
            require(hs == ls, 'owner schema changed')
            if owner == 'diagnostic/harness-banks':
                magic, bits = struct.unpack_from('<QQ', lp)
                require(magic == 0x3153424F534E5248 and len(lp) == 16 + 4*((bits+31)//32), 'bad harness payload')
                packed = int.from_bytes(lp[16:], 'little')
                bank_bits = sum(r['width'] for r in layout['records'][:-2])
                require(bits == bank_bits + 67 and packed >> (bits - 64) == 0
                        and (packed >> bank_bits) & 7 == 0, 'wrong bank geometry/phase/reset/finish')
                continue
            if owner == 'runtime/simulation/base':
                # Historical wall-clock timestamp affects elapsed-time reporting
                # only. Phase, completion and start host cycle must still match.
                require(len(hp) == len(lp) and hp[:-16] == lp[:-16] and hp[-8:] == lp[-8:],
                        'base lifecycle changed beyond wall-clock timestamp')
            else:
                require(hp == lp, f'parked software owner advanced: {owner}')
            compared += bool(hs)
        hp = hdir / 'settled.generated.jsonl'; lp = ldir / 'settled.generated.jsonl'
        hsample, = validate_generated_stream(manifest, hp, 1, high['sample_phase'])
        lsample, = validate_generated_stream(manifest, lp, 1, low['sample_phase'])
        require(hsample['host_sample'] == lsample['host_sample'], 'extra rising edge before capture')
        words = gates = 0
        with hp.open() as hstream, lp.open() as lstream:
            hstream.readline(); lstream.readline()
            for entry in manifest['state']:
                hrow = json.loads(hstream.readline(), object_pairs_hook=unique_object)
                lrow = json.loads(lstream.readline(), object_pairs_hook=unique_object)
                if entry['adapter'] == 'metasim-bufgce-v1':
                    require(lrow['values'] == ['0'] and hrow['values'] in (['0'], ['1']), 'clock gate did not fall')
                    gates += 1
                else:
                    require(hrow == lrow, f'generated state advanced while parked: {entry["hierarchy"]}')
                words += entry['depth']
            require(not hstream.read() and not lstream.read(), 'extra generated records')
        results.append(dict(timing=case['timing'], cut=lcut, identical_software_owners=compared,
            generated_words=words, fallen_clock_gates=gates, harness_banks=len(layout['records']),
            same_host_sample=lsample['host_sample'], target_cycles=case['target_cycles']))
    result = dict(cases=results, generated_build_hash=identity, harness_layout=layout,
        whole_runtime_restore_verified=False, physical_fpga_validated=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical(result))
    print('PASS: every parked software/generated owner agrees across the natural falling edge', results)


if __name__ == '__main__':
    main()
