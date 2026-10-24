"""Independently reject coherent native-bank manifest and RTL substitutions."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.verify_native_functional_bank import audit_generated, digest, sha


def audit_mutations(generated, out):
    generated, out = Path(generated), Path(out)
    audit_generated(generated)
    results = []

    def mutate(name, change):
        path = Path(tempfile.mkdtemp(prefix=name+'-',dir=out))
        shutil.copytree(generated,path/'generated')
        path = path/'generated'
        change(path)
        try:
            audit_generated(path)
        except (FormatError, ValueError, KeyError, AssertionError) as exc:
            results.append(dict(case=name,rejected=True,error=str(exc)))
        else:
            raise AssertionError('coherent native-bank mutation accepted: '+name)

    def doc(path, filename, change):
        value=json.loads((path/filename).read_text());change(value)
        (path/filename).write_bytes(canonical(value))

    def missing_owner(path):
        # Remove a complete owner from both inventories and the bank map, then
        # repair manifest hashes. Independent reference/fixture membership must
        # still reject this plausible, internally coherent subset.
        for name in ('manifest.json','functional-inventory.json','binding.json'):
            doc(path,name,lambda d:d.__setitem__('state',[r for r in d['state']
                if r['hierarchy']!='NativeStorage.ram']))
        inv=json.loads((path/'functional-inventory.json').read_text())
        doc(path,'binding.json',lambda d:d.__setitem__('manifest_sha256',digest(inv)))

    mutate('missing-memory-owner',missing_owner)
    mutate('physical-owner-omitted',lambda p:doc(p,'binding.json',lambda d:d['native_clock_gate_paths'].pop()))
    mutate('selector-alias',lambda p:doc(p,'binding.json',lambda d:d['state'][1].__setitem__('slot',0)))
    mutate('false-ownership-admission',lambda p:doc(p,'binding.json',lambda d:d.__setitem__('production_freeze_owners_bound',True)))

    def rewire(path):
        p=path/'instrumented.sv';text=p.read_text()
        p.write_text(text.replace('assign gate_CE = enable;','assign gate_CE = ~enable;',1))
    mutate('native-gate-rewired',rewire)

    def replace_model(path):
        p=path/'instrumented.sv'
        p.write_text(p.read_text()+'\nmodule BUFGCE(input I,CE,output O); assign O=I; endmodule\n')
    mutate('synthetic-transparent-native',replace_model)
    require(len(results)==6 and all(r['rejected'] for r in results),'incomplete native-bank mutation scope')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    require(args.out.resolve().is_relative_to(root/'automations/checkpoint_loop/runs'),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='audit-',dir=args.out.resolve()))
    results=audit_mutations(args.generated,out)
    result=dict(status='pass',backend='f2',observed_utc=datetime.now(timezone.utc).isoformat(),
        scope='native functional-bank component evidence substitutions only',physical_fpga_capture=False,
        auditor_sha256=sha(__file__),generated_inputs={p.name:sha(p) for p in args.generated.iterdir() if p.is_file()},
        negative_cases=results)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
