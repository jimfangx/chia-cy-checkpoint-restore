"""Native/VCS mutation checks for the production multi-beat read transport.

Inject faults into a private header copy, preserving production source. Require
the first incorrect response to fail before it is acknowledged. Fixture labels
here are host response boundaries, never Rocket target cycles.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_loadmem_transport_vcs import (
    CC, STUBS, TESTCHIP, FESVR, TESTS, cases, pattern, elf_bytes,
)

MUTATIONS = {
    'repeat-beat': ('host_address += consumed;', 'host_address += 0;'),
    'wrong-word': ('send_word(data[lane + i]);', 'send_word(data[lane + i] ^ 1U);'),
}


def oracle(kind):
    lines = []
    for chunk, mode, size, address, offset in cases():
        lines.append(f'CASE {chunk} {mode} {size} {address} {offset}')
        original = address + offset
        # Enumerate the requested word addresses independently. repeat-beat
        # reuses the first beat; wrong-word flips the least significant bit.
        wanted_addresses = list(range(original, original + size, 4))
        consumed = 0
        while consumed < len(wanted_addresses):
            host = original if kind == 'repeat-beat' else wanted_addresses[consumed]
            base = host // (4*chunk) * (4*chunk)
            lane = (host - base) // 4
            lines += [f'MMIO W 984 {base >> 32}', f'MMIO W 988 {base & 0xffffffff}']
            values = [pattern(base+4*i, mode) for i in range(chunk)]
            lines += [f'MMIO R 992 {v}' for v in values]
            for i in range(min(chunk-lane, len(wanted_addresses)-consumed)):
                expected = pattern(wanted_addresses[consumed], mode)
                actual = values[lane+i] ^ (kind == 'wrong-word')
                if expected != actual:
                    divergence = (f'FIRST_DIVERGENCE response_word={consumed} '
                                  f'host_address={wanted_addresses[consumed]} expected={expected} '
                                  f'actual={actual} acknowledged_words={consumed}')
                    lines.append(divergence)
                    return lines, divergence
                lines.append(f'SEND {actual}')
                consumed += 1
        lines.append('END')
    raise RuntimeError('mutation did not diverge')


def audit(path):
    path = path.resolve(); report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'transport faults cannot certify CPU acceptance')
    catalog = report['artifact_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'changed transport fault evidence membership')
    for name, digest in catalog.items(): require(file_sha(name) == digest, 'changed fault artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed fault source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    header = next(b for b in bindings.values() if b['path'].endswith('/fesvr/loadmem_read_transport.h'))
    original = Path(header['snapshot']).read_text()
    for kind, (before, after) in MUTATIONS.items():
        base = path.parent / kind
        require((base/'include/fesvr/loadmem_read_transport.h').read_text() == original.replace(before,after),
                'unexpected production transport mutation')
        expected, divergence = oracle(kind)
        for backend in ('native','vcs-dpi'):
            output = base / backend
            require((output/'direct.trace').read_text().splitlines() == expected,
                    'incorrect first divergent response or acknowledged word '+str((kind,backend)))
            require(not (output/'direct-result.txt').exists() and not list(output.glob('bridge*')),
                    'divergent transport continued into completion/HTIF')
            log = (base/(backend+'.log')).read_text()
            require('FAIL incorrect response lane/order' in log and not log.rstrip().endswith('exit=0'),
                    'fault did not reject')
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(log.rstrip().endswith('exit='+str(command['returncode'])) and
                command['argv'][:2] == ['bash','-lc'] and command['argv'][2].startswith(ENVIRONMENT),
                'unbound mutation command/environment/result')
        require(not any(v in log for v in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'sanitizer error in transport mutation')
    return dict(status='passed', summary=str(path), native_fault_rejections=4,
                first_divergences={kind:oracle(kind)[1] for kind in MUTATIONS},
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit: print(json.dumps(audit(args.audit),indent=2)); return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),
            'transport fault diagnostics must be under runs')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True,exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    sources=[TESTS/'loadmem_transport.cc',STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',
             TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc',
             STUBS/'bridges/tsibridge.cc',CC/'bridges/loadmem.cc',CC/'core/widget.cc']
    library=FESVR/'lib/libfesvr.a'; header=STUBS/'fesvr/loadmem_read_transport.h'
    # Preserve all transitive native headers and the independent checker.
    inputs=set(sources+[library,header,Path(__file__),TESTS/'verify_loadmem_transport_vcs.py',
                       TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
                       TESTS/'verify_firesim_tsi_loadmem_vcs.py',TESTS/'loadmem_transport_tb.sv',
                       ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh'])
    for directory in (CC/'core',CC/'bridges',STUBS/'fesvr',STUBS/'bridges',TESTCHIP,FESVR/'include/fesvr'):
        inputs.update(directory.glob('*.h'))
    snapshots=out/'source-snapshots';snapshots.mkdir();bindings=[]
    for p in sorted(inputs):
        digest=file_sha(p);snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(p,snapshot)
        bindings.append(dict(path=str(p),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        command=['bash','-lc',ENVIRONMENT+shlex.join([str(v) for v in argv])]
        result=run(command,log,cwd=out,expected=expected)
        commands.append(dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log),
                             pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]),
                             returncode=int(result.rstrip().rsplit('exit=',1)[1])))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    for kind,(before,after) in MUTATIONS.items():
        base=out/kind;include_dir=base/'include';(include_dir/'fesvr').mkdir(parents=True)
        text=header.read_text();require(text.count(before)==1,'mutation not unique')
        (include_dir/'fesvr/loadmem_read_transport.h').write_text(text.replace(before,after))
        elf=base/'partial-write.elf';elf.write_bytes(elf_bytes())
        include=f'-std=c++17 -I{include_dir} -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
        native,simv=base/'tsi-native',base/'tsi-simv'
        execute([os.environ['CXX'],*shlex.split(include),'-g','-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer','-no-pie',*sources,library,'-lpthread','-lgmp','-o',native],base/'native-build.log')
        execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
                 '-top','loadmem_transport_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
                 f'-Mdir={base/"csrc"}','-CFLAGS',include+' -DLOADMEM_TRANSPORT_DPI',
                 '-LDFLAGS','-Wl,--whole-archive '+str(library)+
                 ' -Wl,--no-whole-archive -lpthread -Wl,--no-as-needed -lgmp -Wl,--as-needed',
                 '-o',simv,TESTS/'loadmem_transport_tb.sv',*sources],base/'vcs-build.log')
        execute([native,elf,base/'native'],base/'native.log',expected=2)
        execute([simv,'-no_save','+elf='+str(elf),'+out='+str(base/'vcs-dpi')],base/'vcs-dpi.log',expected=None)
        for backend in ('native','vcs-dpi'):
            require((base/backend/'direct.trace').read_text().splitlines()==oracle(kind)[0],
                    'fault did not stop at first incorrect response')
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'source changed during mutation checks')
    report=dict(status='passed',scope='production transport mutation, not CPU restore corruption',
                commands=commands,source_inputs=bindings,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
