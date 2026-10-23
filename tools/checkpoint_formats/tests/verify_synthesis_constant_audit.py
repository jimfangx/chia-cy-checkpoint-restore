"""Offline tamper tests for the synthesis-constant execution auditor."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_synthesis_constant import audit
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import ROOT, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--synthesis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    audit(args.capture.resolve(), args.synthesis.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='tamper-', dir=args.out))
    rejected = []
    cases = ('wrong-backend', 'hardware-claim', 'missing-constant-owner', 'wrong-model',
             'different-default', 'original-circuit', 'missing-synthesis-define', 'missing-override',
             'corrupt-capture', 'missing-cut', 'input-oracle', 'input-cycle',
             'missing-waveform', 'negative-accepted', 'wrong-dcp', 'failed-synthesis')
    for name in cases:
        case = out / name
        receipts = []
        for label, original in [('eda', args.capture), ('native', args.synthesis)]:
            document = json.loads(original.read_text())
            destination = case / label
            destination.mkdir(parents=True)
            for filename in document['files']:
                target = destination / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original.parent / filename, target)
            receipts.append((destination / 'summary.json', document))
        capture, run = receipts[0]
        synthesis, native = receipts[1]

        def edit(label, filename, change):
            path, document = receipts[label]
            target = path.parent / filename
            target.write_text(change(target.read_text()))
            document['files'][filename] = sha(target)  # test semantic audit beyond the outer file digest

        if name == 'wrong-backend':
            run['backend'] = 'f2'
        elif name == 'hardware-claim':
            run['physical_fpga_capture'] = True
        elif name == 'missing-constant-owner':
            edit(0, 'generated/generated-bank-manifest.json', lambda text: text.replace(
                'SynthesisConstantStorage.b', 'SynthesisConstantStorage.missing'))
        elif name == 'wrong-model':
            for label in (0, 1):
                edit(label, 'generated/plusarg_reader.v', lambda text: text + '\n')
        elif name == 'different-default':
            for label in (0, 1):
                edit(label, 'generated/prepared-annotations.json', lambda text: text.replace('"default":341', '"default":340'))
        elif name == 'original-circuit':
            for label in (0, 1):
                edit(label, 'generated/original-input.fir', lambda text: text + '\n')
        elif name == 'missing-synthesis-define':
            run['commands'][0]['argv'].remove('+define+SYNTHESIS')
        elif name == 'missing-override':
            run['commands'][1]['argv'].remove('+checkpoint_constant=99')
        elif name == 'corrupt-capture':
            edit(0, 'healthy/capture.words', lambda text: '\n'.join(
                line if i else line.rsplit(' ', 1)[0] + ' 0000000000000001'
                for i, line in enumerate(text.splitlines())) + '\n')
        elif name == 'missing-cut':
            edit(0, 'healthy/capture.words', lambda text: '\n'.join(text.splitlines()[:-1]) + '\n')
        elif name == 'input-oracle':
            edit(0, 'healthy/run.log', lambda text: text.replace('reset=0 data=', 'reset=1 data=', 1))
        elif name == 'input-cycle':
            edit(0, 'healthy/run.log', lambda text: text.replace('INPUT cycle=3 ', 'INPUT cycle=4 ', 1))
        elif name == 'missing-waveform':
            edit(0, 'healthy/debug.vcd', lambda text: 'missing\n')
        elif name == 'negative-accepted':
            run['commands'][2]['returncode'] = 0
        elif name == 'wrong-dcp':
            (synthesis.parent / 'SynthesisConstantStorage.dcp').write_bytes(b'not a DCP')
            native['files']['SynthesisConstantStorage.dcp'] = sha(synthesis.parent / 'SynthesisConstantStorage.dcp')
        elif name == 'failed-synthesis':
            native['command']['returncode'] = 1
        for path, document in receipts:
            path.write_text(json.dumps(document, indent=2) + '\n')
        try:
            audit(capture, synthesis)
        except Exception as error:
            rejected.append(dict(case=name, error=type(error).__name__, reason=str(error)))
        else:
            raise RuntimeError('auditor accepted corruption: ' + name)
    result = dict(status='pass', scope='offline immutable auditor tamper checks only', physical_fpga_capture=False,
                  rejected=rejected, original_capture_sha256=sha(args.capture), original_synthesis_sha256=sha(args.synthesis))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
