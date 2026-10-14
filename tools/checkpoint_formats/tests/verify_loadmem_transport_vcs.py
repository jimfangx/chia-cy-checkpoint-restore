"""Audit production multi-beat TSI/loadmem transport in native C++ and VCS.

The independent oracle checks every bus address, full beat, response lane and
actual FESVR ELF merge/reset trace. These are transport components, not CPU cuts.
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import elf_bytes

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
STUBS = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
TESTCHIP = ROOT / 'generators/testchipip/src/main/resources/testchipip/csrc'
FESVR = ROOT / '.conda-env/riscv-tools'


def pattern(address, mode):
    index = address // 4
    return 0 if mode == 0 or (mode == 1 and index % 3 == 0) else (
        0xffffffff if mode == 2 else (0x81234567 + index * 0x10203) & 0xffffffff)


def cases():
    result = []
    for chunk in (1, 2, 4, 16):
        for mode in (0, 1, 2):
            for size in (4, 8, 12, 64, 128, 1024, 4096):
                for lane in (0, chunk - 1):
                    for offset in (0, 0x100004, -0x80000000):
                        host = 0x100000000 - 16 + lane * 4
                        result.append((chunk, mode, size, host - offset, offset))
    return result + [(2, 1, 8, 2**64 - 8, 0), (2, 1, 8, 2**63, -2**63)]


def direct_oracle():
    lines = []
    for chunk, mode, size, address, offset in cases():
        lines.append(f'CASE {chunk} {mode} {size} {address} {offset}')
        host = address + offset
        # Enumerate distinct aligned memory beats independently, then filter
        # addresses in the requested byte interval. No production helper used.
        begin = host // (4*chunk) * (4*chunk)
        end = (host + size - 1) // (4*chunk) * (4*chunk)
        for base in range(begin, end + 1, 4*chunk):
            lines += [f'MMIO W 984 {base >> 32}', f'MMIO W 988 {base & 0xffffffff}']
            lines += [f'MMIO R 992 {pattern(base+4*i, mode)}' for i in range(chunk)]
            lines += [f'SEND {pattern(base+4*i, mode)}' for i in range(chunk)
                      if host <= base+4*i < host+size]
        lines.append('END')
    return lines


def bridge_oracle(chunk):
    lines = ['MMIO W 1048 128', 'MMIO W 1056 1']
    def write(base, data):
        lines.extend([f'MMIO W 960 {base >> 32}', f'MMIO W 964 {base & 0xffffffff}',
                      f'MMIO W 968 {(len(data)+chunk-1)//chunk}'])
        lines.extend(f'MMIO W 976 {v}' for v in data)
    initial = [int.from_bytes(bytes(range(4*i,4*i+4)), 'little') for i in range(4)]
    for tick in range(4):
        lines += [f'TICK {tick}', 'MMIO R 1052 1', 'MMIO R 1040 0']
        if tick == 1:
            write(0, initial)
        if tick == 2:
            for base in range(0x1000, 0x1008, 4*chunk):
                lines += ['MMIO W 984 0', f'MMIO W 988 {base}']
                lines += [f'MMIO R 992 {v}' for v in
                          ([0xaabbccdd,0x11223344] if chunk == 2 else
                           [0xaabbccdd if base == 0x1000 else 0x11223344])]
            write(0x1000, [0xaabbccdd,0x77665544])
            for v in (1,0x02000000,0,0,0,1):
                lines += ['MMIO R 1032 1', f'MMIO W 1024 {v}', 'MMIO W 1028 1']
        lines.append('MMIO W 1056 1')
    return lines


def audit(path):
    path = path.resolve(); report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'transport component cannot certify CPU acceptance')
    catalog = report['artifact_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'changed transport evidence membership')
    for name,digest in catalog.items(): require(file_sha(name) == digest, 'changed transport artifact ' + name)
    bindings = {b['path']:b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    require((path.parent / 'partial-write.elf').read_bytes() == elf_bytes(), 'changed actual integration ELF')
    control_checked = str(STUBS/'bridges/tsi_bridge_state.h') in bindings
    if control_checked:
        require(all((path.parent/backend/f'bridge-{chunk}-control-{cut}.owner').is_file()
                    for backend in ('native','vcs-dpi') for chunk in (1,2) for cut in range(6)),
                'incomplete actual bridge control capture')
    counts = audit_outputs(path.parent)
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(log.rstrip().endswith('exit=0') and command['argv'][:2] == ['bash','-lc'] and
                command['argv'][2].startswith(ENVIRONMENT), 'unbound transport environment/command/result')
        require(not any(marker in log for marker in ('ERROR: AddressSanitizer', 'runtime error:',
                                                     'LeakSanitizer: detected')), 'sanitizer error')
    return dict(status='passed', summary=str(path), **counts,
                actual_bridge_control_readbacks=24 if control_checked else 0,
                level1_verified=False, level2_verified=False)


def audit_outputs(out):
    """Require independent output agreement before publishing a passing report."""
    direct = direct_oracle()
    for backend in ('native','vcs-dpi'):
        base = out / backend
        actual = (base / 'direct.trace').read_text().splitlines()
        if actual != direct:
            first = next((i for i,(a,e) in enumerate(zip(actual,direct)) if a != e), min(len(actual),len(direct)))
            raise RuntimeError('first transport oracle mismatch '+str((backend,first,actual[first:first+1],direct[first:first+1])))
        require((base / 'direct-result.txt').read_text() ==
                f'CASES {len(cases())} REJECTIONS 16 CALLBACK_FAILURES 2\n', 'incomplete transport cases')
        for chunk in (1,2):
            actual = (base / f'bridge-{chunk}.trace').read_text().splitlines()
            expected = bridge_oracle(chunk)
            require(actual == expected, 'actual bridge MMIO/merge/reset mismatch '+str((backend,chunk)))
            require((base / f'bridge-{chunk}-result.txt').read_text() ==
                    f'REAL_BRIDGE chunk={chunk} merged_bytes=8 reset_words=6 ticks=4 unsupported_checkpoint=1\n',
                    'incomplete real bridge test')
            # Historical evidence retains its original transport-only scope.
            # New invocations include complete actual bridge host payloads.
            if (base / f'bridge-{chunk}-control-0.owner').exists():
                args=['firesim_tsi','+permissive','+fesvr-wait-ticks=0',
                      '+fesvr-step-size=128','+permissive-off',str(out/'partial-write.elf')]
                expected=config(17,0,1024,1028,1032,1036,1040,1044,1048,1052,1056,
                                1,(-0x80000000) % 2**64,chunk,len(args))
                for arg in args:
                    encoded=arg.encode();expected+=words(len(encoded))+encoded
                expected+=words(128,2004765,0,0)
                for cut in range(6):
                    require((base/f'bridge-{chunk}-control-{cut}.owner').read_bytes()==
                            expected+words(0,int(cut>0)),
                            'actual TSI bridge complete host control mismatch '+str((backend,chunk,cut)))
    return dict(direct_requests=2*len(cases()), compared_direct_records=2*len(direct),
                actual_bridge_runs=4, invalid_requests_before_io=32, callback_unwind_checks=4)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--audit',type=Path)
    args = parser.parse_args()
    if args.audit: print(json.dumps(audit(args.audit),indent=2)); return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'Transport diagnostics must be under runs')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13','source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True,exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    elf=out/'partial-write.elf'; elf.write_bytes(elf_bytes())
    sources=[TESTS/'loadmem_transport.cc',STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',
             TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc',
             STUBS/'bridges/tsibridge.cc',CC/'bridges/loadmem.cc',CC/'core/widget.cc']
    library=FESVR/'lib/libfesvr.a'
    inputs=[*sources,library,Path(__file__),TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            TESTS/'verify_firesim_tsi_loadmem_vcs.py',TESTS/'verify_semantic_vcs.py',
            TESTS/'loadmem_transport_tb.sv',STUBS/'fesvr/firesim_tsi.h',STUBS/'fesvr/loadmem_read.h',STUBS/'fesvr/loadmem_read_transport.h',
            STUBS/'fesvr/loadmem_queues.h',STUBS/'fesvr/tsi_host_control.h',STUBS/'fesvr/tsi.h',STUBS/'fesvr/tsi_serial_state.h',
            STUBS/'bridges/tsibridge.h',STUBS/'bridges/tsi_bridge_state.h',STUBS/'bridges/serial_data.h',CC/'bridges/loadmem.h',
            CC/'core/simif.h',CC/'core/bridge_driver.h',CC/'core/widget.h',CC/'core/config.h',
            CC/'core/stream_engine.h',CC/'core/widget_registry.h',CC/'core/timing.h',
            TESTCHIP/'testchip_tsi.h',TESTCHIP/'testchip_htif.h',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            *sorted((FESVR/'include/fesvr').glob('*.h')),
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots'; snapshots.mkdir(); bindings=[]
    for p in inputs:
        digest=file_sha(p); snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(p,snapshot)
        bindings.append(dict(path=str(p),snapshot=str(snapshot),sha256=digest))
    commands=[]
    def execute(argv,log):
        command=['bash','-lc',ENVIRONMENT+shlex.join([str(a) for a in argv])]
        result=run(command,log,cwd=out)
        commands.append(dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log),
                             pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1])))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR / "include"}'
    native,simv=out/'tsi-native',out/'tsi-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',*sources,library,'-lpthread','-lgmp','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','loadmem_transport_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out / "csrc"}','-CFLAGS',include+' -DLOADMEM_TRANSPORT_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread -Wl,--no-as-needed -lgmp -Wl,--as-needed','-o',simv,
             TESTS/'loadmem_transport_tb.sv',*sources],out/'vcs-build.log')
    execute([native,elf,out/'native'],out/'native.log')
    execute([simv,'-no_save','+elf='+str(elf),'+out='+str(out/'vcs-dpi')],out/'vcs-dpi.log')
    for binding in bindings: require(file_sha(binding['path']) == binding['sha256'],'source changed during FESVR integration')
    audit_outputs(out)
    report=dict(status='passed',scope='production loadmem read transport and actual TSI bridge; not CPU checkpoint acceptance',
                commands=commands,source_inputs=bindings,elf_sha256=file_sha(elf),fesvr_library_sha256=file_sha(library),
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
