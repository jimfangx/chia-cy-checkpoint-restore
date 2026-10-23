"""Actual Make/profile/CLI rejection checks, preserving compiled inventory."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    production = args.production.resolve()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    inputs = json.loads((production/'native-build-inputs.json').read_text())
    require(inputs['make_profile'] == 'fcfs-fased-v1', 'requires a real normal Make build')
    source = Path(next(name for name in inputs['sources'] if name.endswith('FireSim-generated.const.h')))
    source = source if source.is_absolute() else ROOT/source
    generated = source.parent
    inventory = generated/'checkpoint-native'
    files = [p for p in inventory.iterdir() if p.is_file()]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    make = ['make', '-n', 'TARGET_PROJECT=fasedtests', 'DESIGN=AXI4Fuzzer',
            'TARGET_CONFIG=FCFSConfig', 'PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config',
            'FS_CHECKPOINT_PROFILE=fcfs-fased-v1', f'GENERATED_DIR={generated}']
    invalid = [('profile', ['FS_CHECKPOINT_PROFILE=unknown', 'vcs']),
               ('driver', ['DESIGN=GCD', 'vcs']),
               ('inventory', ['SIMULATOR_CHECKPOINT_INVENTORY=FPGATop.FASEDMemoryTimingModel_0', 'vcs']),
               ('debug', ['vcs-debug']), ('gate-level', ['vcs-post-synth']),
               ('verilator', ['verilator']), ('xcelium', ['xcelium']), ('fpga', ['driver'])]
    for name, controls in invalid:
        text = run([*make, *controls], out/(name+'.log'), ROOT/'sims/firesim/sim', expected=2)
        require('***' in text and 'CHECKPOINT_BUILD_INVENTORY' not in text,
                'unsupported Make configuration reached inventory generation')
    # The generator must reject bad compiler/profile/flags/driver arguments
    # before touching even an existing destination, with no VCS invocation.
    destination = out/'preserved'; destination.mkdir(exist_ok=True)
    sentinel = destination/'generated-restore-table.h'
    sentinel.write_bytes(b'preserve compiled inventory\n')
    generator = [sys.executable, '-m', 'tools.checkpoint_formats.metasim_build',
                 '--profile=fcfs-fased-v1', '--driver-name=AXI4Fuzzer-checkpoint',
                 '--generated='+str(generated), '--out='+str(destination),
                 '--cflags='+inputs['cflags'], '--ldflags='+inputs['ldflags'],
                 '--sources', *[ROOT/p for p in inputs['translation_units']],
                 '--driver', ROOT/'sims/firesim/sim/src/main/cc/fasedtests/fasedtests_top.cc']
    invalid = [('generator-profile', ['--profile=unknown']),
               ('generator-binary', ['--driver-name=AXI4Fuzzer']),
               ('generator-flags', ['--vcs-flags=+define+DEBUG']),
               ('generator-driver', ['--driver', ROOT/'sims/firesim/sim/src/main/cc/fasedtests/not-a-driver.cc'])]
    for name, controls in invalid:
        text = run([*generator, *controls], out/(name+'.log'), ROOT, expected=1)
        require('FormatError:' in text and sentinel.read_bytes() == b'preserve compiled inventory\n' and
                sorted(p.name for p in destination.iterdir()) == [sentinel.name],
                'unsupported generator changed compiled output')
    require(before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'rejections changed the real compiled inventory')
    summary = dict(make_rejections=8, generator_rejections=4, inventory_preserved=before)
    (out/'summary.json').write_bytes(canonical(summary))
    print('PASS: eight Make and four generator rejections; all compiled inventory preserved')


if __name__ == '__main__':
    main()
