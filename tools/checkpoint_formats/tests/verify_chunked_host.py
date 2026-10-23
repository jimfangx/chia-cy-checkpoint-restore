"""EDA ASan/UBSan production host-frame validation on retained complete VCS cuts."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_chunked_bank_vcs import ROOT, sha

SOURCES = ('sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.h',
           'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.cc',
           'tools/checkpoint_formats/tests/chunked_capture_host.cc',
           'tools/checkpoint_formats/tests/verify_chunked_host.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME', '').endswith('/Y-2026.03-SP2'), 'run on EDA with vcs-env.sh sourced LAST')
    base = args.out.resolve(); base.mkdir(parents=True, exist_ok=True)
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    out = Path(tempfile.mkdtemp(prefix='chunked-host-', dir=base))
    capture = args.capture.resolve(); receipt = json.loads(capture.read_text())
    require(receipt['status'] == 'pass' and receipt['captures'] == 3, 'complete capture required')
    for name in SOURCES:
        dest = out / 'source-snapshots' / name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
    manifest = capture.parent / 'generated-snapshots/descriptor-manifest.inc'
    (out / manifest.name).write_bytes(manifest.read_bytes())
    commands = []

    def run(argv, name):
        row = dict(argv=[str(a) for a in argv], cwd=str(out), log=str(out / name)); commands.append(row)
        with (out / name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == 0, f'host failure; inspect {out / name}')
        return (out / name).read_text()

    native = out / 'source-snapshots'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
         '-fno-omit-frame-pointer', '-fsanitize=address,undefined',
         '-I' + str(native / 'sims/firesim/sim/midas/src/main/cc'), '-I' + str(out),
         native / SOURCES[1], native / SOURCES[2], '-o', out / 'host'], 'build.log')
    for cut in receipt['cuts']:
        image = capture.parent / f"cut{cut['cut']}.bin"
        require(sha(image) == cut['frames_sha256'], 'captured stream changed')
        log = run([out / 'host', image, str(cut['cycle'])], f"cut{cut['cut']}.log")
        require(re.search(r'CHUNKED_CAPTURE_HOST_PASS checks=13 words=65564', log), 'host check scope incomplete')
    summary = dict(status='pass', backend='eda', physical_fpga_capture=False,
                   scope='production C++ physical-frame validator; canonical chunk reconstruction is independently Python-audited',
                   original_root=str(ROOT), capture_path=str(capture), capture_sha256=sha(capture),
                   descriptor_sha256=sha(manifest), commands=commands,
                   sources={n: sha(native / n) for n in SOURCES},
                   artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n'); print(out / 'summary.json')


if __name__ == '__main__':
    main()
