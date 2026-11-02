"""Exercise final Rocket binding audit against actual compiler output and faults."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_regional_fame_binding import audit
from tools.checkpoint_formats.tests.audit_native_fame_progress import metadata, location
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules


FILES = (
    'identity-binding.json', 'descriptors.json', 'descriptor-binding.json', 'regions.json',
    'regional-instrumented.fir', 'regional-instrumented.anno.json',
    'identity-bound.fir', 'identity-bound.anno.json',
    'connected.fir', 'connected.anno.json', 'grafted.fir',
    'generated.native-region-graft.sv',
    'generated.native-region-graft-0.sv', 'generated.native-region-graft-1.sv',
)


def verify(generated, output):
    generated, output = Path(generated).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='binding-', dir=output))
    source_paths = [Path(__file__), Path(__file__).with_name('audit_regional_fame_binding.py')]
    sources = {str(p.resolve()): file_sha(p) for p in source_paths}
    inputs = {str(generated / name): file_sha(generated / name) for name in FILES}
    result = dict(status='fail', backend='f2', physical_fpga_capture=False,
                  observed_utc=datetime.now(timezone.utc).isoformat(), sources=sources,
                  inputs=inputs, rejected_mutations={})
    try:
        result['healthy'] = audit(generated)
        require(result['healthy']['entries'] == 10916, 'expected exact observed Rocket')
        cases = ('owner-equation', 'root-mask-constant', 'crossed-region',
                 'root-driver', 'endpoint-mask', 'alias-cycle', 'region-mask-port',
                 'transport-digest', 'transport-owner', 'annotation-admission',
                 'header-state-id', 'binding-digest', 'host-selector', 'host-byte-order',
                 'rom-selector', 'image-guard', 'foreign-annotation')
        for name in cases:
            case = out / name
            case.mkdir()
            for filename in FILES:
                shutil.copyfile(generated / filename, case / filename)

            def change(filename, old, new):
                path = case / filename
                text = path.read_text()
                require(text.count(old) == 1, 'ambiguous mutation ' + name)
                path.write_text(text.replace(old, new))

            # Mutate connected and final IR together where possible: coherent
            # identity projection cannot excuse broken original owner/routes.
            if name in ('owner-equation', 'root-mask-constant', 'crossed-region',
                        'root-driver', 'alias-cycle'):
                text = (case / 'identity-bound.fir').read_text()
                if name == 'owner-equation':
                    modules = parse_modules(text)
                    _, roles = metadata(json.loads((case / 'identity-bound.anno.json').read_text()))
                    target = next(r['target'] for k, r in roles.items() if k[2] == 'completed_steps')
                    _, owner, _ = location(modules, 'F1Shim', target)
                    module = next(n for n, m in modules.items() if m is owner)
                    body = re.search(r'^  module ' + re.escape(module) + r' :[^\n]*\n'
                                     r'([\s\S]*?)(?=^  (?:module|extmodule) |\Z)', text, re.M)[1]
                    old = re.search(r'^    checkpoint_fame_completed_steps <= .*$', body, re.M)[0]
                    new = '    checkpoint_fame_completed_steps <= UInt<64>("h0")'
                elif name == 'root-mask-constant':
                    old = 'capture_clock_mask <= top.checkpoint_region_widget_clock_mask'
                    new = 'capture_clock_mask <= UInt<1>("h0")'
                elif name == 'crossed-region':
                    old = 'top.checkpoint_inplace_region0_ckpt_freeze <= checkpoint_inplace_region0_ckpt_freeze'
                    new = old.replace('<= checkpoint_inplace_region0_', '<= checkpoint_inplace_region1_')
                elif name == 'root-driver':
                    old = 'checkpoint_inplace_region0_ckpt_freeze <= checkpoint_region_readout_adapter.checkpoint_inplace_region0_ckpt_freeze'
                    new = old.replace('adapter.checkpoint_inplace_region0_', 'adapter.checkpoint_inplace_region1_')
                else:
                    old = re.search(r'node checkpoint_widget_clock_mask = [^\n]+', text)[0]
                    new = 'node checkpoint_widget_clock_mask = checkpoint_widget_clock_mask'
                for filename in ('connected.fir', 'identity-bound.fir'):
                    change(filename, old, new)
            elif name == 'endpoint-mask':
                change('generated.native-region-graft-0.sv',
                       'assign checkpoint_inplace_region0_ckpt_freeze = capture_clock_mask;',
                       "assign checkpoint_inplace_region0_ckpt_freeze = 1'b0;")
            elif name == 'region-mask-port':
                path = case / 'generated.native-region-graft.sv'
                text = path.read_text()
                block = re.search(r'\bregion0\(([\s\S]*?)\);', text)
                require(block and block[1].count('.capture_clock_mask(capture_clock_mask)') == 1,
                        'missing region zero mutation')
                path.write_text(text[:block.start(1)] + block[1].replace(
                    '.capture_clock_mask(capture_clock_mask)', ".capture_clock_mask(1'b0)") + text[block.end(1):])
            elif name == 'transport-digest':
                digest = int(json.loads((case / 'identity-binding.json').read_text())['descriptor_manifest_sha256'], 16)
                change('identity-bound.fir', 'parameter MANIFEST_SHA256 = ' + str(digest),
                       'parameter MANIFEST_SHA256 = ' + str(digest ^ 1))
            elif name == 'transport-owner':
                for filename in ('connected.fir', 'identity-bound.fir'):
                    change(filename, 'defname = CheckpointPhysicalCaptureTransport\n',
                           'defname = UnownedPhysicalMask\n')
            elif name == 'annotation-admission':
                path = case / 'identity-binding.json'
                binding = json.loads(path.read_text())
                binding['production_annotations_translated'] = True
                path.write_text(json.dumps(binding))
            elif name == 'rom-selector':
                change('generated.native-region-graft.sv',
                       "32'd0: begin capture_descriptor_valid=1; capture_descriptor_bank=8'd0; capture_descriptor_slot=16'd0;",
                       "32'd0: begin capture_descriptor_valid=1; capture_descriptor_bank=8'd0; capture_descriptor_slot=16'd1;")
            else:
                path = case / 'identity-bound.anno.json'
                annotations = json.loads(path.read_text())
                header = next(a for a in annotations if a['class'] ==
                              'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h')
                if name == 'header-state-id':
                    header['body'] = header['body'].replace('// descriptor[0] StateID: ',
                                                          '// descriptor[0] StateID: corrupt-', 1)
                elif name == 'binding-digest':
                    digest = file_sha(case / 'descriptor-binding.json')
                    old = '#define CHECKPOINT_CAPTURE_DESCRIPTOR_BINDING_SHA256 "' + digest + '"'
                    require(header['body'].count(old) == 1, 'missing host binding identity')
                    header['body'] = header['body'].replace(old, old.replace(digest, '0' * 64))
                elif name == 'host-selector':
                    rows = json.loads((case / 'descriptors.json').read_text())['state']
                    row = rows[0]
                    old = '{' + ', '.join(str(row[k]) + 'U' for k in ('bank', 'slot', 'width', 'depth')) + '}'
                    new = '{' + ', '.join(str(row[k] + (1 if k == 'slot' else 0)) + 'U'
                                          for k in ('bank', 'slot', 'width', 'depth')) + '}'
                    require(old in header['body'], 'missing executable host descriptor')
                    header['body'] = header['body'].replace(old, new, 1)
                elif name == 'host-byte-order':
                    old = re.search(r'checkpoint_capture_manifest_t\{\{\{(0x[0-9a-f]{2})', header['body'])[0]
                    byte = int(old[-2:], 16) ^ 1
                    header['body'] = header['body'].replace(old, old[:-2] + f'{byte:02x}', 1)
                elif name == 'image-guard':
                    header['body'] = header['body'].replace('#error Incomplete_checkpoint_hardware_coverage', '')
                else:
                    annotations.append(dict(annotations[0]))
                path.write_text(json.dumps(annotations))
            try:
                audit(case)
            except FormatError as error:
                result['rejected_mutations'][name] = str(error)
            else:
                raise FormatError('accepted final binding corruption ' + name)
        require(all(file_sha(p) == digest for p, digest in {**sources, **inputs}.items()),
                'verification source or compiler input changed')
        result['status'] = 'pass'
    finally:
        result['artifacts'] = {str(p.relative_to(out)): file_sha(p)
                               for p in out.rglob('*') if p.is_file()}
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(out / 'summary.json', flush=True)
    return out / 'summary.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    verify(args.generated, args.out)
