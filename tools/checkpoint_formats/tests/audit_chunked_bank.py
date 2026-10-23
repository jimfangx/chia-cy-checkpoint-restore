"""Independent wide/deep execution, immutable input, host and native-DCP audit."""
import argparse
import copy
import json
from pathlib import Path
import re
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.fpga_transport import encode_transport_semantic
from tools.checkpoint_formats.tests.verify_chunked_bank_vcs import ROOT, GENERATED, SOURCES, sha
from tools.checkpoint_formats.tests.verify_chunked_host import SOURCES as HOST_SOURCES


def audit(capture_path, synthesis_path, host_path, inventory_path, overrides=None):
    docs = {name: json.loads(path.read_text()) for name, path in
            (('capture', capture_path), ('native', synthesis_path), ('host', host_path), ('inventory', inventory_path))}
    docs.update(overrides or {})
    capture, native, host, inventory = (docs[k] for k in ('capture', 'native', 'host', 'inventory'))
    require(capture['status'] == native['status'] == host['status'] == 'pass', 'incomplete execution')
    require(capture['backend'] == host['backend'] == 'eda' and native['backend'] == 'f2', 'backend mismatch')
    require(not any(d['physical_fpga_capture'] for d in (capture, native, host)) and
            not native['full_rocket_image_build'], 'fixture scope changed')
    count = 0

    def check(path, digest, empty=False):
        nonlocal count
        require(path.is_file() and (empty or path.stat().st_size > 0) and sha(path) == digest, f'file integrity: {path}')
        count += 1

    require(set(capture['hashes']['source-snapshots']) == set(SOURCES) and
            set(capture['hashes']['generated-snapshots']) == set(GENERATED), 'incomplete source inventory')
    for category, names in capture['hashes'].items():
        for name, digest in names.items():
            check(capture_path.parent / category / name, digest)
            if category == 'source-snapshots':
                check(ROOT / name, digest)
    require(native['generated'] == capture['hashes']['generated-snapshots'], 'VCS/native generated inputs differ')
    for name, digest in native['generated'].items():
        check(synthesis_path.parent / 'generated-snapshots' / name, digest)
    for name, digest in native['sources'].items():
        check(synthesis_path.parent / 'source-snapshots' / name, digest)
        # Test harnesses are not synthesis inputs. Bind current compiler/generator
        # sources and Tcl; preserve earlier copied harness bytes as provenance.
        if name in SOURCES[:4] or name.endswith(('capture_chunked_bank_synth.tcl', 'synth_chunked_bank.py')):
            check(ROOT / name, digest)
    for receipt, path in ((capture, capture_path), (native, synthesis_path), (host, host_path)):
        for name, digest in receipt['artifacts'].items():
            require(Path(name).name == name, 'invalid artifact path')
            check(path.parent / name, digest, empty=name in ('build.log', 'ucli.key'))
    require(set(host['sources']) == set(HOST_SOURCES), 'incomplete host source inventory')
    for name, digest in host['sources'].items():
        check(ROOT / name, digest); check(host_path.parent / 'source-snapshots' / name, digest)
    require(host['capture_sha256'] == sha(capture_path), 'host receipt names another capture')
    require(host['descriptor_sha256'] == sha(capture_path.parent / 'generated-snapshots/descriptor-manifest.inc'),
            'host descriptor differs from generated ROM binding')
    require('-fsanitize=address,undefined' in host['commands'][0]['argv'] and
            all(c['returncode'] == 0 for c in host['commands']), 'missing host sanitizer execution')
    for cut in range(3):
        require('CHUNKED_CAPTURE_HOST_PASS checks=13 words=65564' in
                (host_path.parent / f'cut{cut}.log').read_text(), 'incomplete host validation')
    first = capture['commands'][0]
    require('-full64' in first['argv'] and '-debug_access+all' in first['argv'] and
            any('Y-2026.03-SP2/bin/vcs' in a for a in first['argv']), 'incorrect VCS toolchain')
    for name in ('generated-bank.sv', 'reference.sv', 'rom/CheckpointCaptureDescriptorROM.v'):
        require(str(Path(first['cwd']) / 'generated-snapshots' / name) in first['argv'], 'VCS bypassed private snapshots')
    require([r['returncode'] for r in capture['commands']] == [0, 0, 1], 'unexpected VCS process status')
    log = (capture_path.parent / 'run.log').read_text()
    match = re.search(r'CHUNKED_BANK_PASS checks=(\d+) captures=(\d+) reads=(\d+) stalls=(\d+) observations=(\d+)', log)
    require(match is not None and [int(x) for x in match.groups()] ==
            [capture[k] for k in ('checks', 'captures', 'reads', 'stalls', 'observations')], 'unbound check totals')
    require(capture['captures'] == 3 and capture['reads'] == 196692 and capture['stalls'] > 100000 and
            capture['observations'] > 100000, 'wide/deep stress incomplete')
    require([r['cycle'] for r in capture['cuts']] == [1, 42, 138], 'missing target cut')
    snapshots = capture_path.parent / 'generated-snapshots'
    manifest = json.loads((snapshots / 'generated-bank-semantic.json').read_text())
    binding = json.loads((capture_path.parent / 'binding.json').read_text())
    for row in capture['cuts']:
        cut, cycle = row['cut'], row['cycle']
        frames, image = (capture_path.parent / f'cut{cut}.{suffix}' for suffix in ('bin', 'rtlckpt'))
        check(frames, row['frames_sha256']); check(image, row['image_sha256'])
        require(row['transfer_words'] == 65564 and row['logical_words'] == 65545, 'incomplete logical/physical state')
        require(image.read_bytes() == encode_transport_semantic(frames.read_bytes(), manifest, binding,
                'ChunkedStorage', cycle), 'canonical image differs from real fixture transport')
    require('functional-input chunk oracle cut=0 cycle=1 frame=1 freeze=1' in
            (capture_path.parent / 'semantic-corruption.log').read_text(), 'first divergent chunk was not stopped frozen')
    require(not list((capture_path.parent / 'negative').glob('*.rtlckpt')) and
            (capture_path.parent / 'healthy.vcd').stat().st_size > 1000, 'publication/waveform mismatch')
    require(native['command']['returncode'] == 0 and 'CHUNKED_BANK_SYNTH_PASS' in
            (synthesis_path.parent / 'command.log').read_text(), 'native synthesis incomplete')
    with zipfile.ZipFile(synthesis_path.parent / 'ChunkedStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for text in ('<Part Name="xcvu47p-fsvh2892-2-e"', '<Top Name="ChunkedStorage"',
                     '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(text in metadata, 'native DCP identity: ' + text)
    report = (synthesis_path.parent / 'utilization.rpt').read_text()
    for key, label in (('luts', r'CLB LUTs\*'), ('registers', 'CLB Registers')):
        require(int(re.search(r'\| ' + label + r'\s*\|\s*(\d+)\s*\|', report)[1]) == native[key] > 0,
                'resource count differs from native report')
    require(inventory['instances'] == [] and not inventory['metasimulation_enabled'] and
            inventory['build_execution'] == 'localhost', 'resource inventory mismatch')
    require(not any(Path(p['executable']).name in ('java', 'vivado', 'firesim') for p in
                    inventory['local_build_processes']['processes']), 'build jobs remain')
    return dict(files_verified=count, cuts=3, transfer_words_per_cut=65564, logical_words_per_cut=65545,
                luts=native['luts'], registers=native['registers'], receipt_sha256={k: sha(p) for k, p in
                (('capture', capture_path), ('native', synthesis_path), ('host', host_path), ('inventory', inventory_path))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'synthesis', 'host', 'inventory', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    paths = [getattr(args, name).resolve() for name in ('capture', 'synthesis', 'host', 'inventory')]
    result = audit(*paths)
    mutations = [
        ('capture', lambda d: d.update(physical_fpga_capture=True)),
        ('capture', lambda d: d.update(backend='f2')),
        ('capture', lambda d: d.update(reads=1)),
        ('capture', lambda d: d['hashes']['source-snapshots'].pop(next(iter(d['hashes']['source-snapshots'])))),
        ('capture', lambda d: d['cuts'][0].update(cycle=2)),
        ('capture', lambda d: d['cuts'][0].update(transfer_words=65563)),
        ('capture', lambda d: d['cuts'][0].update(image_sha256='0'*64)),
        ('capture', lambda d: d['artifacts'].update({'healthy.vcd': '0'*64})),
        ('native', lambda d: d.update(luts=1)),
        ('native', lambda d: d.update(full_rocket_image_build=True)),
        ('native', lambda d: d['generated'].update({'generated-bank.sv': '0'*64})),
        ('host', lambda d: d.update(capture_sha256='0'*64)),
        ('host', lambda d: d['commands'][0]['argv'].remove('-fsanitize=address,undefined')),
        ('inventory', lambda d: d.update(metasimulation_enabled=True)),
    ]
    doc_paths = dict(zip(('capture', 'native', 'host', 'inventory'), paths))
    for name, mutate in mutations:
        bad = copy.deepcopy(json.loads(doc_paths[name].read_text())); mutate(bad)
        try:
            audit(*paths, overrides={name: bad})
        except FormatError:
            pass
        else:
            raise AssertionError('tampered execution accepted')
    base = args.out.resolve(); require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='chunked-audit-', dir=base)) / 'audit.json'
    out.write_text(json.dumps(dict(status='pass', backend='eda', physical_fpga_capture=False,
        scope='component execution audit only', tamper_rejections=len(mutations), **result), indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
