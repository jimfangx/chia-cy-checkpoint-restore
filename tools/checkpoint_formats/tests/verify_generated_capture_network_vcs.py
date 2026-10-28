"""Fresh EDA VCS check of generated storage, ROM, MMIO/DMA and host metadata.

Finite component regression only. No CPU/F2 origin or migration is implied.
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
from tools.checkpoint_formats.tests.verify_generated_bank_vcs import ORACLE

ROOT = Path(__file__).resolve().parents[3]
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
GENERATED = (
    'generated-bank.sv', 'generated-bank.fir', 'generated-bank-input.fir',
    'generated-bank-binding.json', 'generated-bank-semantic.json',
    'checkpoint_network_constants.h', 'checkpoint_network_manifest.inc',
    'widget/CheckpointCaptureWidget.v', 'widget/CheckpointCaptureTransport.sv',
    'widget/CheckpointCaptureCut.sv',
    'rom/CheckpointCaptureDescriptorROMProbe.v',
)
SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureDescriptorsSpec.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_tb.sv',
    'tools/checkpoint_formats/tests/verify_generated_capture_network_vcs.py',
    'tools/checkpoint_formats/tests/checkpoint_capture_host.cc',
    'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.cc',
    'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.h',
    'sims/firesim/sim/midas/src/main/cc/bridges/checkpoint_capture.cc',
    'sims/firesim/sim/midas/src/main/cc/bridges/checkpoint_capture.h',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
            'run on EDA with vcs-env.sh sourced LAST')
    generated = args.generated.resolve()
    root = args.out.resolve()
    require(root.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='generated-network-', dir=root))
    hashes = {name: sha(ROOT / name) for name in SOURCES}
    generated_hashes = {name: sha(generated / name) for name in GENERATED}
    for directory, base, names in (('source-snapshots', ROOT, SOURCES), ('generated-snapshots', generated, GENERATED)):
        for name in names:
            dest = out / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((base / name).read_bytes())
    snapshots = out / 'generated-snapshots'
    manifest = json.loads((snapshots / 'generated-bank-semantic.json').read_text())
    access = json.loads((snapshots / 'generated-bank-binding.json').read_text())
    require(access['reference_sha256'] == manifest['reference_sha256'] == sha(snapshots / 'generated-bank-input.fir'),
            'unbound reference circuit')
    require(access['instrumented_sha256'] == sha(snapshots / 'generated-bank.fir') and
            access['manifest_sha256'] == manifest_hash(manifest), 'unbound instrumented storage or manifest')
    require(len(access['state']) == len(ORACLE) and {e['hierarchy'] for e in access['state']} == set(ORACLE),
            'independent complete fixture oracle required')
    for entry in access['state']:
        require((entry['width'], entry['depth']) == ORACLE[entry['hierarchy']][1:], 'fixture state reshaped')
    for name, native in ((GENERATED[8], 'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv'), (GENERATED[9], 'sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv')):
        require(sha(snapshots / name) == sha(ROOT / native), 'stale transport resource')
    header = (snapshots / 'checkpoint_network_constants.h').read_text()
    require(f'DESCRIPTOR_BINDING_SHA256 "{sha(snapshots / "generated-bank-binding.json")}"' in header,
            'driver header is not bound to exact descriptor binding')
    binding = dict(access_version=1, protocol='banked64-v1', dut_root=manifest['dut_root'],
                   state_manifest_sha256=manifest_hash(manifest),
                   state=[{k: e[k] for k in ('state_id', 'bank', 'slot', 'width', 'depth')} for e in access['state']])
    (out / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    entries = access['state']
    words = [(i, at) for i, entry in enumerate(entries) for at in range(entry['depth'])]
    include = [f'localparam integer ENTRY_COUNT={len(entries)},WORD_COUNT={len(words)};',
               f"localparam [255:0] MANIFEST_HASH=256'h{manifest_hash(manifest)};",
               'integer banks[0:ENTRY_COUNT-1],slots[0:ENTRY_COUNT-1],widths[0:ENTRY_COUNT-1],depths[0:ENTRY_COUNT-1],kinds[0:ENTRY_COUNT-1];',
               'integer wordEntries[0:WORD_COUNT-1],wordAddresses[0:WORD_COUNT-1];', 'initial begin']
    for i, entry in enumerate(entries):
        include.append(f"banks[{i}]={entry['bank']}; slots[{i}]={entry['slot']}; widths[{i}]={entry['width']}; depths[{i}]={entry['depth']}; kinds[{i}]={ORACLE[entry['hierarchy']][0]};")
    for n, (i, at) in enumerate(words):
        include.append(f'wordEntries[{n}]={i}; wordAddresses[{n}]={at};')
    include.append('end')
    (out / 'generated_network_bindings.svh').write_text('\n'.join(include) + '\n')
    commands = []

    def run(argv, log, cwd=None, expect_failure=False):
        command = dict(argv=[str(a) for a in argv], cwd=str(cwd or out), log=str(out / log))
        commands.append(command)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with (out / log).open('w') as stream:
            result = subprocess.run(command['argv'], cwd=command['cwd'], stdout=stream, stderr=subprocess.STDOUT)
        command['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require((result.returncode != 0) if expect_failure else (result.returncode == 0),
                f'unexpected command status; inspect {out / log}')
        return (out / log).read_text()

    run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
         '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS', '-std=c++17',
         '-top', 'checkpoint_generated_network_tb', f'+incdir+{out}', f'-Mdir={out / "csrc"}', '-o', out / 'simv',
         snapshots / 'generated-bank.sv', snapshots / GENERATED[7], snapshots / GENERATED[8], snapshots / GENERATED[9],
         snapshots / GENERATED[10],
         out / 'source-snapshots' / 'tools/checkpoint_formats/tests/checkpoint_generated_network_tb.sv', out / 'source-snapshots' / 'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'], 'compile.log')
    log = run([out / 'simv', '-no_save'], 'run.log')
    marker = re.search(r'GENERATED_NETWORK_PASS checks=(\d+) captures=(\d+) bank_reads=(\d+) stalls=(\d+) functional_edges=(\d+)', log)
    require(marker is not None and int(marker[2]) == 3 and int(marker[3]) == 3 * len(words), 'incomplete network execution')
    cuts = re.findall(r'NETWORK_CAPTURE cut=(\d+) target_cycle=(\d+) words=(\d+)', log)
    require(len(cuts) == 3 and [int(c[0]) for c in cuts] == [0, 1, 2], 'incomplete cut labels')
    negative = out / 'semantic-corruption'
    negative.mkdir()
    bad_log = run([out / 'simv', '-no_save', '+corrupt-state'], 'semantic-corruption.log',
                  cwd=negative, expect_failure=True)
    require('NETWORK_FAIL functional-input state oracle' in bad_log and
            f'cycle={cuts[0][1]} freeze=1 frame=1' in bad_log and
            'NETWORK_CAPTURE' not in bad_log and 'GENERATED_NETWORK_PASS' not in bad_log,
            'semantic corruption did not stop frozen at its first divergent state word')
    wire_hash = int(manifest_hash(manifest), 16).to_bytes(32, 'little')
    metadata = ' '.join(str(b) for b in wire_hash) + '\n' + str(len(entries)) + '\n'
    metadata += ''.join(f"{e['bank']} {e['slot']} {e['width']} {e['depth']}\n" for e in entries)
    (out / 'manifest.txt').write_text(metadata)
    common = [os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
              '-g', '-O1', '-fno-omit-frame-pointer', '-fsanitize=address,undefined', '-I' + str(CC)]
    run([*common, CC / 'core/checkpoint_capture.cc', out / 'source-snapshots' / 'tools/checkpoint_formats/tests/checkpoint_capture_host.cc',
         '-o', out / 'capture-host'], 'native-build.log')
    # Compile the actual generated registry constructor against production types.
    (out / 'constructor.cc').write_text('#include "core/widget_registry.h"\n#define GET_INCLUDES\n'
        '#include "generated-snapshots/checkpoint_network_constants.h"\n#undef GET_INCLUDES\n'
        'void construct(simif_t &simif, widget_registry_t &registry) {\n#define GET_BRIDGE_CONSTRUCTOR\n'
        '#include "generated-snapshots/checkpoint_network_constants.h"\n#undef GET_BRIDGE_CONSTRUCTOR\n}\n')
    run([*common, '-c', out / 'constructor.cc', '-o', out / 'constructor.o'], 'constructor-build.log')
    # Independently execute the exact C++ initializer printed beside the ROM.
    (out / 'generated-metadata.cc').write_text('#include "core/checkpoint_capture.h"\n#include <fstream>\n#include <iterator>\n'
        '#include <iostream>\nint main(int argc,char **argv) { if(argc!=3)return 2;\n'
        'checkpoint_capture_manifest_t actual =\n#include "generated-snapshots/checkpoint_network_manifest.inc"\n;\n'
        'std::ifstream input(argv[1],std::ios::binary); std::vector<uint8_t> frames((std::istreambuf_iterator<char>(input)),{});\n'
        'checkpoint_capture_session_t::validate_frames(frames,actual,std::stoull(argv[2]));\n'
        'std::cout << "GENERATED_METADATA_PASS entries=" << actual.entries.size() << "\\n"; }\n')
    run([*common, CC / 'core/checkpoint_capture.cc', out / 'generated-metadata.cc',
         '-o', out / 'generated-metadata'], 'generated-metadata-build.log')
    results = []
    for index, cycle, count in cuts:
        index, cycle, count = int(index), int(cycle), int(count)
        raw = (out / f'cut{index}.bin').read_bytes()
        decoded = decode_frames(raw, manifest, binding, cycle)
        require(len(decoded) == count == len(words), 'incomplete decoded state')
        negatives = negative_checks(raw, manifest, binding, cycle)
        (out / f'cut{index}.rtlckpt').write_bytes(encode_transport_semantic(raw, manifest, binding, 'generated-fixture-only', cycle))
        host = run([out / 'capture-host', out / f'cut{index}.bin', out / 'manifest.txt', str(cycle)], f'host-cut{index}.log')
        host_match = re.search(r'CHECKPOINT_CAPTURE_HOST_PASS checks=(\d+)', host)
        require(host_match is not None, 'host sanitizer checks did not pass')
        generated_host = run([out / 'generated-metadata', out / f'cut{index}.bin', str(cycle)], f'metadata-cut{index}.log')
        require(f'GENERATED_METADATA_PASS entries={len(entries)}' in generated_host, 'generated C++ metadata mismatch')
        results.append(dict(index=index, target_cycle=cycle, words=count, decoder_negatives=negatives,
                            host_sanitizer_checks=int(host_match[1]), frames_sha256=sha(out / f'cut{index}.bin'),
                            rtlckpt_sha256=sha(out / f'cut{index}.rtlckpt')))
    require(all(sha(ROOT / n) == d for n, d in hashes.items()), 'source changed during verification')
    require(all(sha(generated / n) == d for n, d in generated_hashes.items()), 'generated input changed during verification')
    summary = dict(status='pass', observed_utc=datetime.now(timezone.utc).isoformat(), backend='eda',
                   host=socket.gethostname(), original_root=str(ROOT), tool=toolchain.VCS,
                   scope='finite generated-storage/ROM/Widget/driver component only',
                   physical_fpga_validated=False, rocket_image_integrated=False, complete_state_ownership=False,
                   checks=int(marker[1]), captures=results, bank_reads=int(marker[3]), stalls=int(marker[4]),
                   semantic_corruption=dict(status='first_word_rejected_before_publication',
                                            target_cycle=int(cuts[0][1]), frozen=True),
                   functional_edges=int(marker[5]), sources=hashes, generated=generated_hashes, commands=commands,
                   artifact_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file() and p.suffix not in ('.o', '')})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
