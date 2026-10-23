"""Actual FESVR ELF partial-write read/merge and suspended read-owner audit.

Runs the production FireSim/TestChip TSI linked to the installed FESVR archive
in both native C++ and VCS. It verifies integration, not full HTIF migration.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import config, words, ENVIRONMENT

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
STUBS = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
TESTCHIP = ROOT / 'generators/testchipip/src/main/resources/testchipip/csrc'
FESVR = ROOT / '.conda-env/riscv-tools'


def elf_bytes():
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    # Two actual PT_LOAD segments: aligned bytes, then an upper-half partial
    # write requiring memif's real read/modify/write through load_mem_read.
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 243, 1, 0x80000000,
                         64, 200, 0, 64, 56, 2, 64, 1, 0)
    segment1 = struct.pack('<IIQQQQQQ', 1, 7, 176, 0x80000000, 0x80000000, 16, 16, 8)
    segment2 = struct.pack('<IIQQQQQQ', 1, 7, 192, 0x80001004, 0x80001004, 4, 4, 4)
    strings = b'\0' * 4
    section = struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, 196, 1, 0, 0, 1, 0)
    return header + segment1 + segment2 + bytes(range(16)) + bytes.fromhex('44556677') + strings + section


def audit(path):
    path = path.resolve(); report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'FESVR integration cannot certify CPU acceptance')
    catalog = report['artifact_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'changed actual FESVR native evidence membership')
    for name,digest in catalog.items(): require(file_sha(name) == digest, 'changed actual FESVR artifact ' + name)
    bindings = {b['path']:b for b in report['source_inputs']}
    queue_checked = str(STUBS/'fesvr/loadmem_queues.h') in bindings
    host_checked = str(STUBS/'fesvr/tsi_host_control.h') in bindings
    program_checked = str(STUBS/'fesvr/tsi_program_loader.h') in bindings
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed FESVR source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    require((path.parent / 'partial-write.elf').read_bytes() == elf_bytes(), 'changed integration ELF')
    expected = [config(14,4096,4)+words(0,0,0,0)] * 2
    expected += [config(14,4096,4)+words(1,0x80001000,8,0),
                 config(14,4096,4)+words(3,0x80001000,8,0),
                 config(14,4096,4)+words(3,0x80001000,8,1,0xaabbccdd)]
    expected += [config(14,4096,4)+words(0,0,0,0)] * 2
    def queues(active=(0,0), consumed=0, writes=(), reads=(), data=b'', responses=()):
        return (config(16,4096,4)+words(*active,consumed,len(writes))+
                b''.join(words(*request) for request in writes)+words(len(reads))+
                b''.join(words(*request) for request in reads)+words(len(data))+data+
                words(len(responses),*responses))
    empty=queues()
    merged=bytes.fromhex('ddccbbaa44556677')
    expected_queues=[empty,empty,queues(writes=((0x80000000,16),),data=bytes(range(16))),
                     queues(reads=((0x80001000,8),)),empty,
                     queues(writes=((0x80001000,8),),data=merged),empty]
    extra_queues={'write0-popped':queues(active=(0x80000000,16),data=bytes(range(16))),
                  'write0-partial':queues(active=(0x80000000,16),consumed=1,data=bytes(range(1,16))),
                  'write1-popped':queues(active=(0x80001000,8),data=merged),
                  'response-queued':queues(responses=(0xaabbccdd,))}
    for backend in ('native','vcs-dpi'):
        for cut,payload in enumerate(expected):
            require((path.parent / backend / f'suspended-{cut}.owner').read_bytes() == payload,
                    'actual FESVR suspended read owner mismatch ' + str((backend,cut)))
            if program_checked:
                require((path.parent/backend/f'suspended-{cut}.program').read_bytes() ==
                        config(23,1,0)+words([0,1,2,2,2,3,3][cut]), 'actual loader phase/configuration differs')
            if queue_checked:
                require((path.parent / backend / f'suspended-{cut}.queues').read_bytes() == expected_queues[cut],
                        'actual FESVR suspended queue owner mismatch ' + str((backend,cut)))
        for name,payload in (extra_queues.items() if queue_checked else ()):
            require((path.parent / backend / (name+'.queues')).read_bytes() == payload,
                    'actual FESVR partial-write/queued-response owner mismatch ' + name)
        require('REAL_FESVR_LOADMEM_READ partial_words=1 merged_bytes=8 reset_words=6 suspended_cuts=7' in
                (path.parent / (backend+'.log')).read_text(), 'actual FESVR did not complete read/merge/reset')
        if host_checked:
            hosts={f'suspended-{i}.host':config(18,10)+words(0,0,0) for i in range(5)}
            hosts.update({'suspended-5.host':config(18,10)+words(2,0,2),
                          'suspended-6.host':config(18,10)+words(1,9,6)})
            hosts.update({f'reset-wait-{i}.host':config(18,10)+words(2,0,2) for i in range(2)})
            hosts.update({f'idle-yield-{i}.host':config(18,10)+words(1,(9-i)%10,6) for i in range(1,26)})
            for name,payload in hosts.items():
                require((path.parent/backend/name).read_bytes()==payload,'actual suspended host control differs '+name)
            require('REAL_FESVR_HOST_CONTROL reset_waits=2 idle_yields=26 host_images=34' in
                    (path.parent/(backend+'.log')).read_text(),'actual idle/reset control did not execute')
    for command in report['commands']:
        require(Path(command['log']).read_text().rstrip().endswith('exit=0') and
                command['argv'][:2] == ['bash','-lc'] and command['argv'][2].startswith(ENVIRONMENT),
                'unbound real FESVR command/environment/result')
    return dict(status='passed', summary=str(path), actual_fesvr_suspended_owner_checks=14,
                actual_fesvr_complete_queue_checks=22 if queue_checked else 0,
                actual_fesvr_complete_host_checks=68 if host_checked else 0,
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--audit',type=Path)
    args = parser.parse_args()
    if args.audit: print(json.dumps(audit(args.audit),indent=2)); return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'FESVR diagnostics must be under runs')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX,'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True,exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    elf=out/'partial-write.elf'; elf.write_bytes(elf_bytes())
    sources=[TESTS/'firesim_tsi_loadmem_integration.cc',STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',
             TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    library=FESVR/'lib/libfesvr.a'
    inputs=[*sources,library,Path(__file__),TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            TESTS/'firesim_tsi_loadmem_integration_tb.sv',STUBS/'fesvr/firesim_tsi.h',STUBS/'fesvr/loadmem_read.h',
            STUBS/'fesvr/loadmem_queues.h',
            STUBS/'fesvr/tsi_host_control.h',STUBS/'fesvr/tsi.h',STUBS/'fesvr/tsi_serial_state.h',
            STUBS/'fesvr/tsi_program_loader.h',
            STUBS/'fesvr/tsi_htif_poll.h',
            TESTCHIP/'testchip_tsi.h',TESTCHIP/'testchip_htif.h',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            *sorted((FESVR/'include/fesvr').glob('*.h')),
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
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
    library = build_overlay(out, execute)
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR / "include"}'
    native,simv=out/'tsi-native',out/'tsi-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','firesim_tsi_loadmem_integration_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out / "csrc"}','-CFLAGS',include+' -DFIRESIM_TSI_LOADMEM_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,
             TESTS/'firesim_tsi_loadmem_integration_tb.sv',*sources],out/'vcs-build.log')
    execute([native,elf,out/'native'],out/'native.log')
    execute([simv,'-no_save','+elf='+str(elf),'+out='+str(out/'vcs-dpi')],out/'vcs-dpi.log')
    for binding in bindings: require(file_sha(binding['path']) == binding['sha256'],'source changed during FESVR integration')
    report=dict(status='passed',scope='actual FESVR loadmem read integration, not complete CPU/HTIF migration',
                commands=commands,source_inputs=bindings,elf_sha256=file_sha(elf),fesvr_library_sha256=file_sha(library),
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
