"""Fresh-process malformed TracerV owner rejection using a retained native build.

The complete in-process unchanged-owner audit lives in the positive verifier.
These checks separately prove malformed requests exit before any VCS fixture edge
or readback publication, preserving the fresh output endpoint sentinel.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_tracerv_checkpoint_vcs import ENVIRONMENT, SENTINEL, configuration, oracle, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = args.summary.resolve()
    retained = json.loads(source.read_text())
    require(retained['status'] == 'passed', 'positive native run must finish first')
    original = source.parent
    for path, digest in retained['artifacts_sha256'].items():
        require(file_sha(path) == digest, 'changed original positive native artifact')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    settings = retained['constructors'][0]
    good, queue = oracle(settings, 0)[1][3]
    config = len(configuration(settings, 0))
    unknown = bytearray(good); unknown[16] = 255
    other_hart = configuration(retained['constructors'][1],0) + good[config:]
    length = good[:config+16] + words((1<<64)-1) + good[config+24:]
    flags = good[:config] + words(2) + good[config+8:]
    mutations = {'missing': None, 'truncated': good[:-1], 'trailing': good+b'\0',
                 'unknown-schema': bytes(unknown), 'incompatible-hart': other_hart,
                 'invalid-length': length, 'invalid-lifecycle': flags, 'missing-owner': b''}
    commands = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend; base.mkdir()
        for name, image in mutations.items():
            case = base / name; case.mkdir()
            if image is not None:
                (case / 'cut-3.owner').write_bytes(image)
            (case / 'cut-3.queue').write_bytes(queue)
            argv = [original / 'tracerv-native', 'restore', case, 3, 0, 0] if backend == 'native-sanitized' else [
                original / 'tracerv-simv', '-no_save', f'+outdir={case}', '+restore=1', '+cut=3', '+mode=0', '+hart=0']
            shell = ['bash', '-lc', ENVIRONMENT + shlex.join(map(str, argv))]
            log = case / 'run.log'
            text = run(shell, log, cwd=out, expected=1)
            require('READBACK edges=0' not in text and 'PASS:' not in text and
                    not (case / 'restore-3.initial.owner').exists() and not (case / 'restore-3.trace').exists() and
                    (case / 'TRACEFILE-C0').read_bytes() == SENTINEL, 'malformed image advanced/published partial restore')
            commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=shell, log=str(log), expected_exit=1,
                                 pid=int(re.search(r'fresh_process_pid=(\d+)',text)[1]), backend=backend, case=name))
    # Seal native input hashes and original source checker bytes for recovery.
    snapshots = out / 'source-snapshots'; snapshots.mkdir()
    sources = [Path(__file__).resolve(), Path(__file__).with_name('verify_tracerv_checkpoint_vcs.py'),
               Path(__file__).with_name('verify_semantic_vcs.py')]
    bindings = []
    for p in sources:
        digest=file_sha(p); target=snapshots/digest;shutil.copyfile(p,target)
        bindings.append(dict(path=str(p),snapshot=str(target),sha256=digest))
    for path, digest in retained['artifacts_sha256'].items():
        require(file_sha(path) == digest, 'fresh invalid checks overwrote positive evidence')
    report = dict(status='passed', scope='malformed TracerV host-owner requests; CPU acceptance pending',
                  source_summary=str(source), source_summary_sha256=file_sha(source),
                  source_native_inputs={str(original/n):file_sha(original/n) for n in ('tracerv-native','tracerv-simv')},
                  commands=commands, source_inputs=bindings, malformed_fresh_processes=16,
                  level1_verified=False, level2_verified=False,
                  artifacts_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out.resolve()/'latest.json').write_text(json.dumps(dict(summary=str(out/'summary.json')))+'\n')
    print(json.dumps(dict(status='passed',summary=str(out/'summary.json'),malformed_fresh_processes=16),indent=2))


if __name__=='__main__':
    main()
