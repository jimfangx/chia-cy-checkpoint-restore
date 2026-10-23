"""EDA-only complete chunked/deep storage capture via production transport.

Component evidence only; no CPU or physical FPGA capture is implied.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.banked import validate_binding
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import encode_transport_semantic
from tools.checkpoint_formats.semantic import decode_semantic, manifest_hash

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ('generated-bank.sv', 'reference.sv', 'generated-bank.fir', 'generated-bank-input.fir',
             'generated-bank-semantic.json', 'generated-bank-binding.json', 'generated-bank-simulator.json',
             'generated-bank-simulator-binding.json', 'generated-bank-simulator.fir', 'descriptor-manifest.inc',
             'rom/CheckpointCaptureDescriptorROM.v', 'deep.hex', 'wide.hex')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/ChunkedStateBankSpec.scala',
           'tools/checkpoint_formats/tests/chunked_bank_tb.sv',
           'tools/checkpoint_formats/tests/verify_chunked_bank_vcs.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv',
           'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv',
           'tools/checkpoint_formats/banked.py', 'tools/checkpoint_formats/fpga_transport.py')
ORACLE = {'ChunkedStorage.' + name: (kind, width, depth) for kind, (name, width, depth) in enumerate((
    ('deepMem', 9, 65537), ('wideMem', 129, 5), ('signedReg', 65, 1), ('exactReg', 128, 1), ('vectorReg', 512, 1)))}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def logical_oracle(cut):
    deep = [(i * 37 + 11) & 511 for i in range(65537)]
    wide = [(1 << 128) | ((i + 1) << 64) | (17 + i * 29) for i in range(5)]
    signed, exact, vector = (1 << 65) - 1, 0, 0
    for phase in range(cut):
        for i in range((40, 95)[phase]):
            address = 65536 if i % (2, 3)[phase] == 0 else i % 5
            hi, lo = (i * 97 + 13, i * 83 + 9) if phase == 0 else (i * 113 + 29, i * 53 + 19)
            data = ((1 << 128) if phase == 0 else 0) | (hi << 64) | lo
            signed, exact = data & ((1 << 65) - 1), data & ((1 << 128) - 1)
            vector = sum(exact << (128 * n) for n in range(4))
            if phase == 0 or i % 4 != 0:
                deep[address] = data & 511
                wide[address & 7] = data
    return (deep, wide, [signed], [exact], [vector])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
            'run on EDA with vcs-env.sh sourced LAST')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='chunked-bank-', dir=base))
    hashes = {}
    for directory, source, names in (('source-snapshots', ROOT, SOURCES),
                                     ('generated-snapshots', args.generated.resolve(), GENERATED)):
        hashes[directory] = {}
        for name in names:
            dest = out / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((source / name).read_bytes())
            hashes[directory][name] = sha(dest)
    snapshots = out / 'generated-snapshots'
    binding = json.loads((snapshots / 'generated-bank-binding.json').read_text())
    manifest = json.loads((snapshots / 'generated-bank-semantic.json').read_text())
    require(binding['reference_sha256'] == sha(snapshots / 'generated-bank-input.fir') and
            binding['instrumented_sha256'] == sha(snapshots / 'generated-bank.fir') and
            binding['manifest_sha256'] == manifest_hash(manifest), 'unbound storage')
    require(binding['access_version'] == 2 and binding['protocol'] == 'latched-banked64-chunked-v2',
            'explicit chunk mapping required')
    entries = binding['state']
    require(len(entries) == 5 and {e['hierarchy'] for e in entries} == set(ORACLE), 'incomplete wide/deep ownership')
    sim = json.loads((snapshots / 'generated-bank-simulator-binding.json').read_text())
    require(sim['manifest_sha256'] == sha(snapshots / 'generated-bank-simulator.json') and
            sim['instrumented_sha256'] == sha(snapshots / 'generated-bank-simulator.fir') and
            not ({e['state_id'] for e in entries} & {e['state_id'] for e in sim['state']}),
            'simulator and semantic owners must remain independent')
    narrow_keys = ('state_id', 'bank', 'slot', 'width', 'depth', 'chunks', 'transfer_width', 'transfer_depth')
    transport_binding = dict(access_version=2, protocol='banked64-chunked-v2', dut_root=manifest['dut_root'],
                             state_manifest_sha256=manifest_hash(manifest),
                             state=[{k: e[k] for k in narrow_keys} for e in entries])
    validate_binding(manifest, transport_binding)
    (out / 'binding.json').write_text(json.dumps(transport_binding, indent=2) + '\n')
    words = sum(e['transfer_depth'] for e in entries)
    require(words == 65564, 'incomplete physical transfer')
    header = [f'localparam integer ENTRY_COUNT=5,WORD_COUNT={words};',
              f"localparam [255:0] MANIFEST_HASH=256'h{manifest_hash(manifest)};",
              'integer banks[0:4],slots[0:4],widths[0:4],depths[0:4],kinds[0:4];', 'initial begin']
    for i, e in enumerate(entries):
        kind, width, depth = ORACLE[e['hierarchy']]
        require((e['width'], e['depth']) == (width, depth), 'reshaped logical state')
        header.append(f"banks[{i}]={e['bank']};slots[{i}]={e['slot']};widths[{i}]={e['transfer_width']};depths[{i}]={e['transfer_depth']};kinds[{i}]={kind};")
    (out / 'chunked_bindings.svh').write_text('\n'.join(header + ['end']) + '\n')
    for name in ('deep.hex', 'wide.hex'):
        (out / name).write_bytes((snapshots / name).read_bytes())
    commands = []

    def run(argv, name, expected=0, cwd=None):
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd or out), log=str(out / name))
        commands.append(row)
        with (out / name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=row['cwd'], stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == expected, f'command failed; inspect {out / name}')
        return (out / name).read_text()

    native = out / 'source-snapshots'
    run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
         '-top', 'chunked_bank_tb', f'+incdir+{out}', f'-Mdir={out / "csrc"}', '-o', out / 'simv',
         snapshots / 'generated-bank.sv', snapshots / 'reference.sv',
         snapshots / 'rom/CheckpointCaptureDescriptorROM.v', native / SOURCES[7], native / SOURCES[8],
         native / SOURCES[4], native / SOURCES[6]], 'compile.log')
    log = run([out / 'simv', '-no_save'], 'run.log')
    match = re.search(r'CHUNKED_BANK_PASS checks=(\d+) captures=(\d+) reads=(\d+) stalls=(\d+) observations=(\d+)', log)
    require(match is not None and int(match[2]) == 3 and int(match[3]) == words * 3,
            'complete capture regression missing')
    cuts = [tuple(map(int, m)) for m in re.findall(r'CHUNKED_CAPTURE cut=(\d+) target_cycle=(\d+) words=65564', log)]
    require(len(cuts) == 3 and cuts[0][1] == 1, 'cut label mismatch')
    receipts = []
    for cut, cycle in cuts:
        raw = (out / f'cut{cut}.bin').read_bytes()
        encoded = encode_transport_semantic(raw, manifest, transport_binding, 'ChunkedStorage', cycle)
        path = out / f'cut{cut}.rtlckpt'; path.write_bytes(encoded)
        build = dict(target_configuration='ChunkedStorage', rtl_build_hash=manifest['reference_sha256'],
                     state_manifest_hash=manifest_hash(manifest))
        doc = decode_semantic(encoded, build, manifest)
        oracle = logical_oracle(cut)
        for e, record in zip(entries, doc['records']):
            values = oracle[ORACLE[e['hierarchy']][0]]
            require([int(v, 16) for v in record['values']] == values, f'independent complete logical oracle: {e["hierarchy"]}')
        receipts.append(dict(cut=cut, cycle=cycle, transfer_words=words, logical_words=65545,
                             frames_sha256=sha(out / f'cut{cut}.bin'), image_sha256=sha(path)))
    # Keep the healthy full waveform intact when running the semantic negative.
    (out / 'chunked.vcd').rename(out / 'healthy.vcd')
    negative = out / 'negative'; negative.mkdir()
    for name in ('deep.hex', 'wide.hex'):
        (negative / name).write_bytes((snapshots / name).read_bytes())
    bad = run([out / 'simv', '-no_save', '+corrupt-state'], 'semantic-corruption.log', expected=1, cwd=negative)
    require('functional-input chunk oracle' in bad and 'frame=1 freeze=1' in bad and 'CHUNKED_CAPTURE' not in bad,
            'corruption must stop at its first divergent word before publication')
    require((out / 'healthy.vcd').stat().st_size > 1000, 'full debug waveform missing')
    summary = dict(status='pass', backend='eda', original_root=str(ROOT), host=socket.gethostname(),
                   observed_utc=datetime.now(timezone.utc).isoformat(), physical_fpga_capture=False,
                   scope='complete generated wide/deep fixture transport only; no CPU migration', hashes=hashes,
                   checks=int(match[1]), captures=int(match[2]), reads=int(match[3]), stalls=int(match[4]),
                   observations=int(match[5]), cuts=receipts, commands=commands,
                   artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ('.log', '.vcd', '.bin', '.rtlckpt', '.svh')})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
