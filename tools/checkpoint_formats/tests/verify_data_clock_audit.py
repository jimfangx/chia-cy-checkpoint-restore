"""Independent semantic tamper checks for computed token clock bindings."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.tests.audit_multiple_clocks import audit
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import ROOT, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--synthesis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    original = audit(args.capture.resolve(), args.synthesis.resolve())
    require(original['data_clock_ports_verified'] == 8, 'computed token fixture required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='tamper-', dir=args.out))
    rejected = []
    for name in ('healthy-copy', 'missing', 'changed-origin', 'changed-expression', 'invented-root', 'both-origins',
                 'invalid-gate', 'duplicate', 'reordered', 'unknown-origin', 'boolean', 'null', 'empty', 'numeric', 'extra-origin-field'):
        receipts = []
        for label, source in [('eda', args.capture.resolve()), ('native', args.synthesis.resolve())]:
            document = json.loads(source.read_text())
            destination = out / name / label
            destination.mkdir(parents=True)
            for filename in document['files']:
                target = destination / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source.parent / filename, target)
            for command in document.get('commands', []):
                command['argv'] = [arg.replace(str(source.parent), str(destination)) for arg in command['argv']]
            binding_file = destination / 'generated/generated-bank-binding.json'
            binding = json.loads(binding_file.read_text())
            domains = binding['functional_clock_domains']
            index = next(i for i, row in enumerate(domains) if 'data_clock' in row)
            row = domains[index]
            if name == 'missing':
                domains.pop(index)
            elif name == 'changed-origin':
                row['data_clock']['hierarchy'] = 'MultiClockStorage.static_one'
            elif name == 'changed-expression':
                row['data_clock']['expression'] = 'eq(data, UInt<17>(\"h0\"))'
            elif name == 'invented-root':
                row.pop('data_clock')
                row['root_clock'] = 'clock_a'
            elif name == 'both-origins':
                row['root_clock'] = 'clock_a'
            elif name == 'invalid-gate':
                row['gate_chain'] = ['MultiClockStorage.fabricated']
            elif name == 'duplicate':
                domains.append(dict(row))
            elif name == 'reordered':
                domains.reverse()
            elif name == 'unknown-origin':
                row.pop('data_clock')
                row['unknown_clock'] = True
            elif name == 'boolean':
                row['data_clock'] = True
            elif name == 'null':
                row['data_clock'] = None
            elif name == 'empty':
                row['data_clock'] = ''
            elif name == 'numeric':
                row['data_clock'] = 0
            elif name == 'extra-origin-field':
                row['data_clock']['fabricated'] = True
            # Change both immutable-input copies consistently and refresh outer
            # hashes: rejection must come from the semantic clock contract.
            binding_file.write_text(json.dumps(binding, indent=2) + '\n')
            document['files']['generated/generated-bank-binding.json'] = sha(binding_file)
            receipt = destination / 'summary.json'
            receipt.write_text(json.dumps(document, indent=2) + '\n')
            receipts.append(receipt)
        if name == 'healthy-copy':
            require(audit(*receipts)['data_clock_ports_verified'] == 8, 'copied control failed')
            continue
        try:
            audit(*receipts)
        except FormatError as error:
            require('incomplete clock provenance' in str(error), 'rejected before semantic clock audit')
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('accepted computed token clock corruption: ' + name)
    result = dict(status='pass', scope='offline computed token clock semantic auditor negatives only',
                  physical_fpga_capture=False, healthy_copy_verified=True, rejected=rejected,
                  original_capture_sha256=sha(args.capture), original_synthesis_sha256=sha(args.synthesis))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
