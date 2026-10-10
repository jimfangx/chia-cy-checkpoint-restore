"""Native sanitizer checks for the opt-in, restore-only shadow argument contract."""
import argparse
import json
import os
from pathlib import Path

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    compiler = os.environ['CXX']
    source = ROOT / 'tools/checkpoint_formats/tests/shadow_controls_native.cc'
    for name, flags in [('ordinary', []), ('shadow', ['-DFS_CHECKPOINT_SHADOW'])]:
        run([compiler, '-std=c++17', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
             *flags, source, '-o', out / name], out / (name + '-build.log'))
    valid = ['+shadow-socket=/tmp/shadow-control-test', '+shadow-identity=' + 'a'*64,
             '+shadow-first-cycle=524453', '+shadow-level1-cycle=524402']
    cases = [('ordinary-empty', 'ordinary', 'capture', [], 0),
             ('ordinary-rejects-shadow', 'ordinary', 'restore', valid, 1),
             ('shadow-capture-empty', 'shadow', 'capture', [], 0),
             ('shadow-restore', 'shadow', 'restore', valid, 0),
             ('capture-rejects-shadow', 'shadow', 'capture', valid, 1),
             ('partial', 'shadow', 'restore', valid[:-1], 1),
             ('duplicate', 'shadow', 'restore', valid + [valid[0]], 1),
             ('unknown', 'shadow', 'restore', valid + ['+shadow-invented=x'], 1)]
    for name, index, value in [('missing-equals', 0, '+shadow-socket'),
                             ('empty', 0, '+shadow-socket='),
                             ('long-socket', 0, '+shadow-socket=/' + 'x'*107),
                             ('relative-socket', 0, '+shadow-socket=relative'),
                             ('multiline-socket', 0, '+shadow-socket=/tmp/\nx'),
                             ('bad-identity', 1, '+shadow-identity=' + 'z'*64),
                             ('short-identity', 1, '+shadow-identity=a'),
                             ('negative-cycle', 2, '+shadow-first-cycle=-1'),
                             ('padded-cycle', 2, '+shadow-first-cycle=01'),
                             ('suffix-cycle', 2, '+shadow-first-cycle=42x'),
                             ('overflow-cycle', 2, '+shadow-first-cycle=18446744073709551616'),
                             ('terminal-cycle', 2, '+shadow-first-cycle=18446744073709551615'),
                             ('bad-level1-cycle', 3, '+shadow-level1-cycle=bad')]:
        argv = valid.copy()
        argv[index] = value
        cases.append((name, 'shadow', 'restore', argv, 1))
    results = []
    for name, binary, mode, argv, code in cases:
        text = run([out / binary, mode, *argv], out / (name + '.log'), out, expected=code)
        require(('PASS:' if code == 0 else 'REJECT:') in text and
                'AddressSanitizer' not in text and 'runtime error:' not in text, 'native control failure')
        results.append(dict(name=name, exit=code))
    (out / 'summary.json').write_bytes(canonical(dict(status='pass', results=results)))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
