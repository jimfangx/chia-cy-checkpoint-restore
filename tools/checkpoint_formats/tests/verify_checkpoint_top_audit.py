"""Offline tamper tests against real immutable fixture execution receipts."""
import argparse
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_checkpoint_top import ROOT, audit, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('top', 'synthesis', 'inventory', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='audit-tamper-', dir=base))
    top = out / 'top'; top.mkdir()
    original = json.loads(args.top.read_text())
    names = set(original['artifacts']) | {'summary.json', 'binding.json'}
    for cut in original['captures']:
        names |= {f"capture-{cut['index']}.frames", f"capture-{cut['index']}.rtlckpt"}
    for name in names:
        shutil.copyfile(args.top.parent / name, top / name)
    for name in ('source-snapshots', 'generated-snapshots', 'semantic-corruption'):
        shutil.copytree(args.top.parent / name, top / name)
    native = out / 'synthesis'
    shutil.copytree(args.synthesis.parent, native)
    inventory = out / 'inventory.json'; shutil.copyfile(args.inventory, inventory)
    top_path = top / 'summary.json'; native_path = native / 'summary.json'
    audit(top_path, native_path, inventory)
    negatives = []

    def reject(name, paths, mutate):
        saved = {p: p.read_bytes() for p in paths}
        try:
            mutate()
            try:
                audit(top_path, native_path, inventory)
            except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
                negatives.append(dict(case=name, rejected=True, reason=str(error)))
            else:
                raise RuntimeError('audit accepted corruption: ' + name)
        finally:
            for path, raw in saved.items():
                path.write_bytes(raw)

    def json_change(path, change):
        doc = json.loads(path.read_text()); change(doc)
        path.write_text(json.dumps(doc, indent=2) + '\n')

    for label, path in (
        ('changed generated snapshot', top / 'generated-snapshots/FPGATop.v'),
        ('changed source snapshot', top / 'source-snapshots/tools/checkpoint_formats/tests/checkpoint_top_tb.sv'),
        ('truncated transport', top / 'capture-0.frames'),
        ('corrupt semantic image', top / 'capture-1.rtlckpt'),
        ('missing host sanitizer output', top / 'host-cut2.log'),
        ('changed waveform', top / 'top.vcd'),
        ('changed native synthesis log', native / 'command.log')):
        reject(label, [path], lambda p=path: p.write_bytes(p.read_bytes()[:-1]))
    reject('hardware claim from fixture', [top_path], lambda: json_change(top_path,
        lambda doc: doc.update(physical_fpga_validated=True)))
    reject('missing active cut', [top_path], lambda: json_change(top_path,
        lambda doc: doc['captures'].pop()))
    reject('failed command', [top_path], lambda: json_change(top_path,
        lambda doc: doc['commands'][0].update(returncode=1)))
    reject('cross-execution generated inputs', [native_path], lambda: json_change(native_path,
        lambda doc: doc['generated'].update({'FPGATop.v': '0' * 64})))
    reject('remaining native build', [inventory], lambda: json_change(inventory,
        lambda doc: doc['local_build_processes']['processes'].append({'executable': '/native/vivado'})))
    dcp_path = native / 'FPGATop.dcp'

    def corrupt_dcp():
        raw = dcp_path.read_bytes(); dcp_path.write_bytes(raw[:100])
        json_change(native_path, lambda doc: doc['artifacts'].update({'FPGATop.dcp': sha(dcp_path)}))

    reject('malformed DCP with updated file hash', [dcp_path, native_path], corrupt_dcp)

    def wrong_part():
        stream = io.BytesIO()
        with zipfile.ZipFile(dcp_path) as source, zipfile.ZipFile(stream, 'w') as dest:
            for info in source.infolist():
                raw = source.read(info.filename)
                if info.filename == 'dcp.xml':
                    raw = raw.replace(b'xcvu47p-fsvh2892-2-e', b'wrong-fpga-part')
                dest.writestr(info, raw)
        dcp_path.write_bytes(stream.getvalue())
        json_change(native_path, lambda doc: doc['artifacts'].update({'FPGATop.dcp': sha(dcp_path)}))

    reject('wrong native part with valid ZIP and updated hash', [dcp_path, native_path], wrong_part)
    final = audit(top_path, native_path, inventory)
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', scope='offline fixture evidence tamper tests',
        negatives=negatives, rejected=len(negatives), repaired_evidence_passes=True, audit=final), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
