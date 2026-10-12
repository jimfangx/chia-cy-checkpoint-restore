"""Check the proposed production opcode predicate at the actual metasim cut."""

import argparse
import json
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.production_register import predicate_checkpoint, reconstruct
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic, encode_semantic
from .verify_production_dut import CONFIGURATION


def verify(architecture, synthesis_evidence, inputs, out, flight_opcode_predicates=False):
    architecture, synthesis_evidence, inputs, out = (Path(p).resolve() for p in
        (architecture, synthesis_evidence, inputs, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, True, flight_opcode_predicates)
    manifest = json.loads((inputs / 'FireSim-generated.semantic-state.json').read_text())
    boundary = json.loads((inputs / 'FireSim-generated.semantic-boundary.json').read_text())
    data = (inputs / 'capture.rtlckpt').read_bytes()
    positive = predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, data)
    require(positive['target_cycle'] == 524453 and positive['complete_semantic_records'] == 1543 and
            positive['complete_words'] == 13503308 and len(positive['predicates']) == (130 if flight_opcode_predicates else 1),
            'predicate check requires complete actual metasim checkpoint')
    checkpoint = decode_semantic(data, builds(manifest, boundary, CONFIGURATION)[0], manifest)
    trials = {}
    indices = (0, 1, 128, 129) if flight_opcode_predicates else (0,)
    for index in indices:
        predicate = binding['optimized_predicates'][index]
        record = next(r for r in checkpoint['records'] if r['state_id'] == predicate['entry']['state_id'])
        original = record['values'][0]
        record['values'][0] = format(int(original, 16) ^ (1 << predicate['bit']), 'x')
        mutated = encode_semantic(checkpoint, manifest)
        path = run / ('wrong-opcode.rtlckpt' if index == 0 else f'wrong-opcode-{index}.rtlckpt')
        path.write_bytes(mutated)
        try:
            predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, mutated)
        except FormatError as error:
            require('violates unproven optimization predicate: ' + predicate['entry']['original_path'] in str(error),
                    'wrong opcode rejected for unrelated reason')
            rejection = str(error)
        else:
            raise AssertionError('Actual semantic opcode corruption was accepted')
        trials[str(index)] = dict(checkpoint=str(path), rejection=rejection, predicate=predicate)
        record['values'][0] = original
    require(predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, data) == positive,
            'negative checkpoint changed original compatibility check')
    summary = dict(status='passed', run=str(run), checkpoint=str(inputs / 'capture.rtlckpt'), positive=positive,
                   wrong_opcode_checkpoint=trials['0']['checkpoint'], wrong_opcode_rejected=trials['0']['rejection'],
                   formal_state_map_complete=False, gate_restore_authorized=False)
    if flight_opcode_predicates:
        summary['flight_opcode_predicates'] = True
        summary['actual_corruptions'] = trials
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'inputs', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--flight-opcode-predicates', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.inputs, args.out,
                            args.flight_opcode_predicates), indent=2))


if __name__ == '__main__':
    main()
