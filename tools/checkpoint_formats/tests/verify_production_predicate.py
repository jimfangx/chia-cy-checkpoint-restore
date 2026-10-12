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


def verify(architecture, synthesis_evidence, inputs, out):
    architecture, synthesis_evidence, inputs, out = (Path(p).resolve() for p in
        (architecture, synthesis_evidence, inputs, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, True)
    manifest = json.loads((inputs / 'FireSim-generated.semantic-state.json').read_text())
    boundary = json.loads((inputs / 'FireSim-generated.semantic-boundary.json').read_text())
    data = (inputs / 'capture.rtlckpt').read_bytes()
    positive = predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, data)
    require(positive['target_cycle'] == 524453 and positive['complete_semantic_records'] == 1543 and
            positive['complete_words'] == 13503308 and len(positive['predicates']) == 1,
            'predicate check requires complete actual metasim checkpoint')
    checkpoint = decode_semantic(data, builds(manifest, boundary, CONFIGURATION)[0], manifest)
    predicate = binding['optimized_predicates'][0]
    record = next(r for r in checkpoint['records'] if r['state_id'] == predicate['entry']['state_id'])
    record['values'][0] = format(int(record['values'][0], 16) ^ (1 << predicate['bit']), 'x')
    mutated = encode_semantic(checkpoint, manifest)
    (run / 'wrong-opcode.rtlckpt').write_bytes(mutated)
    try:
        predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, mutated)
    except FormatError as error:
        require('violates unproven optimization predicate' in str(error), 'wrong opcode rejected for unrelated reason')
        rejection = str(error)
    else:
        raise AssertionError('Actual semantic opcode corruption was accepted')
    require(predicate_checkpoint(binding, manifest, boundary, CONFIGURATION, data) == positive,
            'negative checkpoint changed original compatibility check')
    summary = dict(status='passed', run=str(run), checkpoint=str(inputs / 'capture.rtlckpt'), positive=positive,
                   wrong_opcode_checkpoint=str(run / 'wrong-opcode.rtlckpt'), wrong_opcode_rejected=rejection,
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'inputs', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.inputs, args.out), indent=2))


if __name__ == '__main__':
    main()
