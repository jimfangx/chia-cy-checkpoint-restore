"""Re-audit immutable native/EDA integration evidence and reject substitutions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_physical_capture_transport import ROOT, RUNS, RTL, SOURCES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--eda',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    base=args.out.resolve()
    require(base.is_relative_to(RUNS), 'evidence must be below runs')
    base.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='corruption-',dir=base))
    native=args.native.resolve(); eda=args.eda.resolve()
    require(native.is_relative_to(RUNS) and eda.is_relative_to(RUNS), 'receipts must be below runs')
    original_native=json.loads((native/'summary.json').read_text())
    original_eda=json.loads((eda/'summary.json').read_text())
    original_hashes={str(p):sha(p) for directory in (native,eda) for p in directory.rglob('*') if p.is_file()}
    commands=[]

    def invoke(name, chosen_native, chosen_eda, expected):
        argv=[sys.executable,'-m','tools.checkpoint_formats.tests.verify_physical_capture_transport',
              '--mode','audit','--native',str(chosen_native),'--eda',str(chosen_eda),'--out',str(out/name)]
        log=out/(name+'.log')
        with log.open('w') as stream:
            result=subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        commands.append(dict(name=name,argv=argv,cwd=str(ROOT),log=str(log),returncode=result.returncode))
        require((result.returncode==0)==expected, 'incorrect audit result '+name+'; inspect '+str(log))

    invoke('healthy',native,eda,True)
    rejected=[]
    for name in ('scope','source','source_coherent','gate_model','gate_model_coherent','synth_contract','dcp','vcs_log','waveform','cut_scope'):
        work=out/name; work.mkdir()
        # Only the native receipt is copied for native mutations; EDA mutation
        # copies retain the original native receipt and all immutable originals.
        is_eda=name in ('vcs_log','waveform','cut_scope')
        directory=work/'inputs'
        shutil.copytree(eda if is_eda else native,directory)
        doc=copy.deepcopy(original_eda if is_eda else original_native)
        if name=='scope':
            doc['physical_fpga_capture']=True
        elif name in ('source','source_coherent'):
            source=RTL[-1]; path=directory/'sources'/Path(source).name
            path.write_bytes(path.read_bytes()+b'\n// substituted implementation\n')
            if name=='source_coherent':
                doc['sources'][source]=sha(path)
                doc['inputs'][str(path.relative_to(directory))]=sha(path)
        elif name in ('gate_model','gate_model_coherent'):
            path=directory/'BUFGCE.v'; path.write_bytes(path.read_bytes()+b'\n// changed gate model\n')
            if name=='gate_model_coherent':
                doc['inputs']['BUFGCE.v']=sha(path)
        elif name=='synth_contract':
            path=directory/'synth.tcl'; path.write_bytes(path.read_bytes()+b'\n# substituted gate contract\n')
            doc['inputs']['synth.tcl']=sha(path)
        elif name=='dcp':
            path=directory/'physical-transport.dcp'; path.write_bytes(path.read_bytes()[:-1])
        elif name in ('vcs_log','waveform'):
            suffix='.vcd' if name=='waveform' else '.log'
            path=directory/next(n for n in doc['artifacts'] if n.endswith(suffix))
            path.write_bytes(path.read_bytes()+b'\nchanged evidence\n')
        else:
            doc['cuts']=4
        (directory/'summary.json').write_text(json.dumps(doc,indent=2)+'\n')
        invoke(name,native if is_eda else directory,directory if is_eda else eda,False)
        rejected.append(name)
    require(all(sha(Path(p))==digest for p,digest in original_hashes.items()), 'original evidence changed')
    summary=dict(status='pass',backend='f2',scope='component evidence audit; no hardware capture acceptance',
                 native_receipt=str(native/'summary.json'),eda_receipt=str(eda/'summary.json'),rejections=rejected,
                 original_evidence_files_preserved=len(original_hashes),commands=commands,
                 source_sha256={n:sha(ROOT/n) for n in (*SOURCES,'tools/checkpoint_formats/tests/audit_physical_capture_transport.py')})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
