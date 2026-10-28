"""Fresh EDA VCS test of FPGATop registration and real control/CPU DMA paths.

The state donor is an explicitly bounded generated-storage fixture, not Rocket
or an FPGA. No CPU/full-runtime migration admission is implied by this check.
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
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import decode_frames, encode_transport_semantic
from tools.checkpoint_formats.semantic import manifest_hash
from tools.checkpoint_formats.tests.test_fpga_transport import negative_checks

ROOT = Path(__file__).resolve().parents[3]
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/core/FPGATop.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/core/CheckpointCaptureTop.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/core/CheckpointCaptureTopSpec.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv',
    'tools/checkpoint_formats/tests/checkpoint_top_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
    'tools/checkpoint_formats/tests/checkpoint_capture_host.cc',
    'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.cc',
    'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.h',
    'sims/firesim/sim/midas/src/main/cc/bridges/checkpoint_capture.cc',
    'sims/firesim/sim/midas/src/main/cc/bridges/checkpoint_capture.h',
    'tools/checkpoint_formats/tests/verify_checkpoint_top_vcs.py',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
)
GENERATED = ('FPGATop.v', 'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv',
             'top_constants.h', 'generated-bank.sv', 'generated-bank.fir', 'generated-bank-input.fir',
             'generated-bank-semantic.json', 'generated-bank-binding.json', 'manifest.inc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    out = Path(tempfile.mkdtemp(prefix='checkpoint-top-', dir=base))
    generated = args.generated.resolve()
    source_hashes = {n: sha(ROOT / n) for n in SOURCES}
    generated_hashes = {n: sha(generated / n) for n in GENERATED}
    for directory, source, names in (('source-snapshots', ROOT, SOURCES), ('generated-snapshots', generated, GENERATED)):
        for name in names:
            dest = out / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((source / name).read_bytes())
    snapshots = out / 'generated-snapshots'
    manifest = json.loads((snapshots / 'generated-bank-semantic.json').read_text())
    access = json.loads((snapshots / 'generated-bank-binding.json').read_text())
    require(access['reference_sha256'] == manifest['reference_sha256'] == sha(snapshots / 'generated-bank-input.fir'),
            'unbound reference circuit')
    require(access['instrumented_sha256'] == sha(snapshots / 'generated-bank.fir') and
            access['manifest_sha256'] == manifest_hash(manifest), 'unbound generated storage')
    expected = {'CaptureTopStorage.sram': (32, 32, 0), 'CaptureTopStorage.counter': (64, 1, 1)}
    entries = access['state']
    require(len(entries) == 2 and {e['hierarchy'] for e in entries} == set(expected), 'independent fixture inventory required')
    for entry in entries:
        require((entry['width'], entry['depth']) == expected[entry['hierarchy']][:2], 'fixture reshaped')
    for resource in ('CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv'):
        require(sha(snapshots / resource) == sha(ROOT / 'sims/firesim/sim/midas/src/main/verilog' / resource), 'stale transport resource')
    header = (snapshots / 'top_constants.h').read_text()
    prefix, address = re.search(r'#define (CHECKPOINTCAPTUREWIDGET_\d+)_BASE (\d+)ULL', header).groups()
    require(f'{prefix}_DESCRIPTOR_BINDING_SHA256 "{sha(snapshots / "generated-bank-binding.json")}"' in header,
            'driver not bound to generated storage')
    require(f'{prefix}_TO_HOST_STREAM_IDX 1U' in header, 'existing bridge stream index was changed')
    streams = re.findall(r'CPUManagedStreams::StreamParameters\(\s*std::string\(R"ESC\((.*?)\)ESC"\),\s*(\d+)ULL,\s*(\d+)ULL,\s*(\d+),\s*(\d+)', header)
    require(len(streams) == 2 and streams[1][0] == prefix + '_to_cpu_stream' and streams[1][3:] == ('2', '64'),
            'global stream absent from actual stream engine metadata')
    top_header = re.search(r'module FPGATop\((.*?)\);', (snapshots / 'FPGATop.v').read_text(), re.S).group(1)
    ports = re.findall(r'(input|output)\s*(\[\d+:\d+\])?\s*(\w+)', re.sub(r'//[^\n]*', '', top_header))
    declarations = [f'{"reg" if d == "input" else "wire"} {width} {name}{"=0" if d == "input" else ""};'
                    for d, width, name in ports]
    declarations.append('FPGATop dut(' + ','.join(f'.{name}({name})' for _, _, name in ports) + ');')
    (out / 'top_ports.svh').write_text('\n'.join(declarations) + '\n')
    words = [(i, at) for i, e in enumerate(entries) for at in range(e['depth'])]
    include = [f'localparam integer ENTRY_COUNT={len(entries)},WORD_COUNT={len(words)};',
               f'localparam [31:0] CAPTURE_BASE={address},STREAM_COUNT={streams[1][2]};',
               f'localparam [63:0] CAPTURE_DMA={streams[1][1]};',
               f"localparam [255:0] MANIFEST_HASH=256'h{manifest_hash(manifest)};",
               'integer banks[0:ENTRY_COUNT-1],slots[0:ENTRY_COUNT-1],widths[0:ENTRY_COUNT-1],kinds[0:ENTRY_COUNT-1];',
               'integer wordEntries[0:WORD_COUNT-1],wordAddresses[0:WORD_COUNT-1];', 'initial begin']
    for i, entry in enumerate(entries):
        include.append(f"banks[{i}]={entry['bank']};slots[{i}]={entry['slot']};widths[{i}]={entry['width']};kinds[{i}]={expected[entry['hierarchy']][2]};")
    for n, (i, at) in enumerate(words):
        include.append(f'wordEntries[{n}]={i};wordAddresses[{n}]={at};')
    (out / 'top_bindings.svh').write_text('\n'.join(include + ['end']) + '\n')
    binding = dict(access_version=1, protocol='banked64-v1', dut_root=manifest['dut_root'],
                   state_manifest_sha256=manifest_hash(manifest),
                   state=[{k: e[k] for k in ('state_id', 'bank', 'slot', 'width', 'depth')} for e in entries])
    (out / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    commands = []

    def run(argv, log, cwd=None, failure=False):
        command = dict(argv=[str(a) for a in argv], cwd=str(cwd or out), log=str(out / log))
        commands.append(command)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with (out / log).open('w') as stream:
            result = subprocess.run(command['argv'], cwd=command['cwd'], stdout=stream, stderr=subprocess.STDOUT)
        command['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require((result.returncode != 0) if failure else (result.returncode == 0), f'unexpected status; inspect {out / log}')
        return (out / log).read_text()

    run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
         '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS', '-std=c++17',
         '-top', 'checkpoint_top_tb', f'+incdir+{out}', f'-Mdir={out / "csrc"}', '-o', out / 'simv',
         *(snapshots / n for n in ('FPGATop.v', 'generated-bank.sv', 'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv')),
         out / 'source-snapshots' / 'tools/checkpoint_formats/tests/checkpoint_top_tb.sv', out / 'source-snapshots' / 'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'], 'compile.log')
    log = run([out / 'simv', '-no_save'], 'run.log')
    marker = re.search(r'CHECKPOINT_TOP_PASS checks=(\d+) captures=(\d+) dma_stalls=(\d+) frozen_edges=(\d+)', log)
    require(marker is not None and int(marker[2]) == 3 and int(marker[3]) > 20 and int(marker[4]) > 500, 'incomplete top stress')
    cuts = re.findall(r'TOP_CAPTURE index=(\d+) target_cycle=(\d+) words=(\d+)', log)
    require(len(cuts) == 3 and [int(c[0]) for c in cuts] == [0, 1, 2], 'incomplete cut labels')
    negative = out / 'semantic-corruption'; negative.mkdir()
    bad_log = run([out / 'simv', '-no_save', '+corrupt-state'], 'semantic-corruption.log', cwd=negative, failure=True)
    require('TOP_FAIL functional-input state oracle' in bad_log and 'freeze=1 frame=1' in bad_log and
            'TOP_CAPTURE' not in bad_log, 'semantic corruption did not stop frozen at first data word')
    require((out / 'top.vcd').stat().st_size > 1000, 'full RTL waveform missing')
    metadata = ' '.join(str(b) for b in int(manifest_hash(manifest), 16).to_bytes(32, 'little')) + '\n' + str(len(entries)) + '\n'
    metadata += ''.join(f"{e['bank']} {e['slot']} {e['width']} {e['depth']}\n" for e in entries)
    (out / 'manifest.txt').write_text(metadata)
    common = [os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
              '-g', '-O1', '-fno-omit-frame-pointer', '-fsanitize=address,undefined', '-I' + str(CC)]
    run([*common, CC / 'core/checkpoint_capture.cc', ROOT / 'tools/checkpoint_formats/tests/checkpoint_capture_host.cc', '-o', out / 'capture-host'], 'host-build.log')
    (out / 'constructor.cc').write_text('#include "core/widget_registry.h"\n#include "bridges/checkpoint_capture.h"\n'
        'void construct(simif_t &simif, widget_registry_t &registry) {\n#define GET_BRIDGE_CONSTRUCTOR\n'
        '#include "generated-snapshots/top_constants.h"\n#undef GET_BRIDGE_CONSTRUCTOR\n}\n')
    run([*common, '-c', out / 'constructor.cc', '-o', out / 'constructor.o'], 'constructor-build.log')
    results = []
    for index, cycle, count in cuts:
        index, cycle, count = int(index), int(cycle), int(count)
        raw_path = out / f'capture-{index}.frames'
        raw = raw_path.read_bytes()
        decoded = decode_frames(raw, manifest, binding, cycle)
        require(len(decoded) == count == len(words), 'incomplete decoded capture')
        negatives = negative_checks(raw, manifest, binding, cycle)
        image = out / f'capture-{index}.rtlckpt'
        image.write_bytes(encode_transport_semantic(raw, manifest, binding, 'FPGATop-fixture-VCS-only', cycle))
        host = run([out / 'capture-host', raw_path, out / 'manifest.txt', str(cycle)], f'host-cut{index}.log')
        host_match = re.search(r'CHECKPOINT_CAPTURE_HOST_PASS checks=(\d+)', host)
        require(host_match is not None, 'sanitizer host check did not pass')
        results.append(dict(index=index, target_cycle=cycle, words=count, decoder_negatives=negatives,
                            host_sanitizer_checks=int(host_match[1]), frames_sha256=sha(raw_path), rtlckpt_sha256=sha(image)))
    require(all(sha(ROOT / n) == digest for n, digest in source_hashes.items()), 'source changed during verification')
    require(all(sha(generated / n) == digest for n, digest in generated_hashes.items()), 'generated inputs changed during verification')
    summary = dict(status='pass', observed_utc=datetime.now(timezone.utc).isoformat(), backend='eda',
                   host=socket.gethostname(), original_root=str(ROOT), tool=toolchain.VCS,
                   scope='FPGATop fixture, generated banks, real MMIO interconnect and CPUManagedStreamEngine only',
                   physical_fpga_validated=False, rocket_image_integrated=False, complete_runtime_ownership=False,
                   checks=int(marker[1]), dma_stalls=int(marker[3]), frozen_edges=int(marker[4]), captures=results,
                   semantic_corruption=dict(first_data_word_rejected=True, frozen=True, target_cycle=int(cuts[0][1])),
                   sources=source_hashes, generated=generated_hashes, commands=commands,
                   artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file() and p.suffix not in ('.o', '')})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
