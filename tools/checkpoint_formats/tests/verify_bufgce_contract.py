"""EDA VCS comparison of native Vivado BUFGCE, MIDAS abstract and metasim models.

--models is an immutable manager-side snapshot beneath runs. This program
never treats vendor model state observations as physical FPGA capture.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
MODELS = ('BUFGCE.v', 'glbl.v', 'AbstractClockGate.v', 'metasim-BUFGCE.v')
SOURCES = ('tools/checkpoint_formats/tests/bufgce_contract_tb.sv',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'tools/checkpoint_formats/tests/verify_bufgce_contract.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),
            'run on EDA with vcs-env.sh sourced last')
    require(args.models.resolve().is_relative_to(RUNS) and args.out.resolve().is_relative_to(RUNS),
            'all model snapshots and evidence must be beneath runs')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='bufgce-contract-', dir=args.out.resolve()))
    metadata = json.loads((args.models/'model-origins.json').read_text())
    for name in MODELS:
        require(sha(args.models/name) == metadata['files'][name]['sha256'], 'unbound native model '+name)
        target=out/'models'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((args.models/name).read_bytes())
    (out/'model-origins.json').write_bytes((args.models/'model-origins.json').read_bytes())
    for name in SOURCES:
        target=out/'sources'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    # Preserve the exact metasim bytes above. Only namespace this copy so the
    # stock model can coexist with the unmodified native vendor primitive.
    model = (out/'models/metasim-BUFGCE.v').read_text()
    require(model.count('module BUFGCE(')==1, 'unexpected metasim declaration')
    (out/'metasim-namespaced.v').write_text(model.replace('module BUFGCE(', 'module CheckpointMetasimBUFGCE('))
    commands=[]

    def run(argv, cwd, log, expected=0):
        row=dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(out/log))
        commands.append(row)
        with (out/log).open('w') as stream:
            result=subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode']=result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode==expected, 'native compiler/runtime failure: '+str(out/log))
        return (out/log).read_text()

    healthy=out/'healthy'; healthy.mkdir()
    run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
         '-top', 'bufgce_contract_tb', '-top', 'glbl', '-Mdir='+str(healthy/'csrc'), '-o', healthy/'simv',
         out/'models/BUFGCE.v', out/'models/glbl.v', out/'models/AbstractClockGate.v', out/'metasim-namespaced.v',
         out/'sources'/SOURCES[0], out/'sources'/SOURCES[1]], healthy, 'compile.log')
    text=run([healthy/'simv', '-no_save'], healthy, 'healthy.log')
    match=re.search(r'BUFGCE_CONTRACT_PASS checks=(\d+) source_edges=256 cuts=(\d+) physical_edges=(\d+) '
                    r'abstract_edges=(\d+) metasim_edges=(\d+) hardsync_edges=(\d+) abstract_only_pulses=(\d+) '
                    r'high_changes=(\d+) low_changes=256', text)
    require(match is not None and int(match[3])==int(match[5]) and int(match[4])>int(match[3]),
            'missing complete native/abstract differential experiment')
    corrupt=out/'corrupt'; corrupt.mkdir()
    negative=run([healthy/'simv', '-no_save', '+corrupt'], corrupt, 'corrupt.log', expected=1)
    require('BUFGCE_CONTRACT_MISMATCH source_edge=4' in negative and 'BUFGCE_CONTRACT_PASS' not in negative,
            'corrupt oracle did not stop at first changed expectation')
    summary=dict(status='pass', backend='eda', observed_utc=datetime.now(timezone.utc).isoformat(),
        host=socket.gethostname(), original_root=str(ROOT), scope='native clock primitive model contract only',
        physical_fpga_capture=False, full_rocket_image_build=False, commands=commands,
        source_edges=256, checks=int(match[1]), phase_observations=int(match[2]),
        physical_model_edges=int(match[3]), abstract_model_edges=int(match[4]), metasim_model_edges=int(match[5]),
        hardsync_model_edges=int(match[6]), abstract_only_pulses=int(match[7]), high_changes=int(match[8]),
        model_origins=metadata, sources={n:sha(out/'sources'/n) for n in SOURCES},
        artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*')
                   if p.is_file() and p.suffix in ('.log','.vcd','.v','.sv','.cc')})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
