"""Audit fresh native/VCS restores of all four production TSI loadmem queues.

The independent byte/queue oracle covers partial write drains, ordered requests
and responses. Component labels are not Rocket target cycles or HTIF restores.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
from collections import deque
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
STUBS = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
SIZES = (4, 8, 64, 1024, 4096)


def oracle(size):
    writes, reads, responses = deque(), deque(), deque()
    data = bytearray()
    active, consumed = (0, 0), 0
    commands, trace, states = [], [], []

    def snapshot():
        image = config(16, 4096, 4) + words(*active, consumed, len(writes))
        image += b''.join(words(*request) for request in writes) + words(len(reads))
        image += b''.join(words(*request) for request in reads) + words(len(data)) + data
        image += words(len(responses), *responses)
        states.append(bytes(image))

    def op(command):
        nonlocal active, consumed
        fields = command.split(); name = fields[0]; result = command
        if name == 'WRITE':
            payload = bytes.fromhex(fields[2]); writes.append((int(fields[1]), len(payload))); data.extend(payload)
        elif name == 'READ': reads.append((int(fields[1]), int(fields[2])))
        elif name == 'TAKEW':
            if writes:
                active = writes.popleft(); consumed = 0
                result += ' 1 ' + ' '.join(map(str, active))
            else: result += ' 0'
        elif name == 'TAKER':
            result += (' 1 ' + ' '.join(map(str, reads.popleft()))) if reads else ' 0'
        elif name == 'DATA':
            count = int(fields[1]); result += ' ' + data[:count].hex(); del data[:count]
            consumed += count
            if consumed == active[1]: active, consumed = (0, 0), 0
        elif name == 'PUSH': responses.append(int(fields[1]))
        elif name == 'POP': result += (' 1 ' + str(responses.popleft())) if responses else ' 0'
        elif name == 'PENDING':
            pending = bool(writes or active[1]); result += f' {int(pending or bool(reads))} {int(pending)}'
        else: raise ValueError(name)
        commands.append(command); trace.append(f'OP {len(commands)} C {100+len(commands)} {result}')
        snapshot()

    snapshot()
    for command in ('PENDING', 'TAKEW', 'TAKER', 'POP'): op(command)
    # Two queued writes plus interleaved reads and responses, before any drain.
    payload = bytes((i * 97 + i // 256) & 255 for i in range(size))
    op('WRITE 2147483648 ' + payload.hex())
    op('WRITE 4294967292 ffffffff00000000')
    op('READ 4294967292 ' + str(size))
    op('READ 18446744073709551612 4')
    for value in (0, 4294967295, 0x12345678): op('PUSH ' + str(value))
    op('PENDING'); op('TAKEW'); corruption_cut = len(commands)
    # Include a byte-granular drain and queued data belonging to the next write.
    for count in (1, 2, size - 3): op('DATA ' + str(count))
    op('PENDING'); op('TAKER'); op('POP'); op('PUSH 2147483648')
    op('TAKEW'); op('DATA 3'); op('DATA 5'); op('PENDING')
    op('TAKER'); op('TAKER')
    for _ in range(5): op('POP')
    op('PENDING'); op('TAKEW')
    return commands, trace, states, corruption_cut


def cuts(states):
    return range(len(states))


def audit(path):
    path = path.resolve(); report = json.loads(path.read_text()); out = path.parent
    require(report['status'] == 'passed' and report['level1_verified'] is False and
            report['level2_verified'] is False, 'component evidence cannot certify CPU checkpoint acceptance')
    artifacts = report['artifact_sha256']
    require(set(artifacts) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed queue native evidence membership')
    for name, digest in artifacts.items(): require(file_sha(name) == digest, 'changed queue evidence ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed queue source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    restored = readbacks = records = 0
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend
        require('ATOMIC_CHECKS ' in (base / 'checks.log').read_text(), 'missing atomic checks')
        for size in SIZES:
            commands, trace, states, cut = oracle(size); case = base / str(size)
            require((case / 'commands.txt').read_text().splitlines() == commands and
                    (case / 'expected.txt').read_text().splitlines() == trace, 'changed independent queue oracle')
            for cursor in cuts(states):
                require((case / 'reference' / f'cut-{cursor}.owner').read_bytes() == states[cursor],
                        'incomplete source queue state')
                restore = case / f'restore-{cursor}'
                require((restore / 'preedge.owner').read_bytes() == states[cursor], 'incomplete zero-edge queue readback')
                require((restore / 'trace').read_text().splitlines() == trace[cursor:], 'changed queue continuation label/data')
                for j in range(cursor, len(states)):
                    require((restore / f'cut-{j}.owner').read_bytes() == states[j], 'changed continued queue state')
                    readbacks += 1
                restored += 1; records += len(trace) - cursor
            require((case / 'reference/trace').read_text().splitlines() == trace, 'changed uninterrupted queue trace')
        for invalid in report['invalid_cases'][backend]:
            target = Path(invalid['output'])
            require('REJECTED_BEFORE_MUTATION' in Path(invalid['log']).read_text() and
                    set(p.name for p in target.iterdir()) == {'unchanged.owner'}, 'invalid image executed or published state')
            # Independent full sentinel payload, not a checksum of a second production save.
            sentinel = config(16,4096,4)+words(0,0,0,1,0x80000000,4,0,4)+bytes.fromhex('04030201')+words(0)
            require((target / 'unchanged.owner').read_bytes() == sentinel, 'partial invalid-image queue restore')
        case = base / '64'; _, trace, _, cut = oracle(64)
        failure = json.loads((base / 'corruption/first-divergence.json').read_text())
        require(failure == dict(operation=cut+1, fixture_cycle=101+cut, acknowledged=0,
                                expected=trace[cut], actual=trace[cut][:-2]+'01'),
                'corruption was not detected at first byte boundary')
        require((base / 'corruption/trace').read_bytes() == b'', 'divergent operation acknowledged')
    for command in report['commands']:
        require(command['argv'][:2] == ['bash','-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                Path(command['log']).read_text().rstrip().endswith('exit='+str(command['expected_exit'])),
                'unbound queue native command/environment/result')
    return dict(status='passed', summary=str(path), fresh_component_restores=restored,
                complete_state_readbacks=readbacks, continuation_records=records,
                invalid_processes=sum(map(len, report['invalid_cases'].values())),
                first_divergence_cases=2, level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path); parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit: print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'queue diagnostics must be under runs')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    sources = [TESTS / 'loadmem_queues_checkpoint.cc']
    inputs = [*sources, Path(__file__), TESTS / 'loadmem_queues_checkpoint_tb.sv',
              TESTS / 'verify_loadmem_read_checkpoint_vcs.py', STUBS / 'fesvr/loadmem_queues.h',
              STUBS / 'fesvr/firesim_tsi.h', STUBS / 'fesvr/firesim_tsi.cc', CC / 'core/checkpoint.h',
              CC / 'core/widget_checkpoint.h', ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh',
              ROOT / 'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out / 'source-snapshots'; snapshots.mkdir(); bindings = []
    for p in inputs:
        digest = file_sha(p); snapshot = snapshots / digest
        if not snapshot.exists(): shutil.copyfile(p, snapshot)
        bindings.append(dict(path=str(p),snapshot=str(snapshot),sha256=digest))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash','-lc',ENVIRONMENT + shlex.join([str(a) for a in argv])]
        text = run(command, log, cwd=out, expected=expected)
        commands.append(dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log),
                             pid=int(re.search(r'fresh_process_pid=(\d+)',text)[1]),expected_exit=expected))
        (out / 'commands.json').write_text(json.dumps(commands,indent=2)+'\n')

    include = f'-std=c++17 -I{CC} -I{STUBS}'
    native, simv = out / 'queue-native', out / 'queue-simv'
    execute([os.environ['CXX'], *shlex.split(include), '-Wall','-Wextra','-Werror','-g','-no-pie',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',*sources,'-o',native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','loadmem_queues_checkpoint_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out / "csrc"}','-CFLAGS',include+' -DLOADMEM_QUEUES_CHECKPOINT_DPI',
             '-o',simv,TESTS / 'loadmem_queues_checkpoint_tb.sv',*sources], out / 'vcs-build.log')
    invalid_cases = {}
    for backend in ('native-sanitized','vcs-dpi'):
        base = out / backend; base.mkdir()

        def invoke(mode, target, cmd='unused', expected='unused', image='unused', cut=0, failure=False):
            values = [mode,str(target),str(cmd),str(expected),str(image),str(cut)]
            argv = [native,*values] if backend == 'native-sanitized' else [simv,'-no_save',
                    *['+'+key+'='+value for key,value in zip(('mode','out','commands','expected','image','cut'),values)]]
            log = target.parent / (target.name+'.log'); execute(argv,log,2 if failure else 0)
            return log

        invoke('check',base / 'checks')
        for size in SIZES:
            case = base / str(size); case.mkdir()
            ops, trace, states, _ = oracle(size)
            cmd, wanted = case / 'commands.txt', case / 'expected.txt'
            cmd.write_text('\n'.join(ops)+'\n'); wanted.write_text('\n'.join(trace)+'\n')
            invoke('reference',case / 'reference',cmd,wanted)
            for cursor in cuts(states):
                invoke('restore',case / f'restore-{cursor}',cmd,wanted,
                       case / 'reference' / f'cut-{cursor}.owner',cursor)
        _, trace, states, cut = oracle(64)
        valid = states[cut]
        def alter(offset,value):
            changed = bytearray(valid); struct.pack_into('<Q',changed,offset,value); return bytes(changed)
        # At the selected cut the first write is active, one write and two
        # reads are queued, 72 data bytes and three response words are pending.
        invalids = dict(missing=None,truncated=valid[:-1],trailing=valid+b'\0',magic=alter(0,0),
                        version=alter(8,2),kind=alter(16,99),incompatible=alter(32,2048),
                        active_address=alter(48,1),active_zero=alter(56,0),cursor=alter(64,64),
                        write_count=alter(72,1<<63),write_address=alter(80,1),write_zero=alter(88,0),
                        read_count=alter(96,1<<63),read_alignment=alter(104,1),read_wrap=alter(104,(1<<64)-4),
                        read_size=alter(112,8192),read_zero=alter(112,0),data_count=alter(136,71),
                        response_count=alter(216,1<<63),response_width=alter(224,1<<32))
        rejected=[]
        for name,payload in invalids.items():
            image = base / ('invalid-'+name+'.owner')
            if payload is not None: image.write_bytes(payload)
            target=base / ('invalid-'+name)
            log=invoke('invalid',target,image=image)
            rejected.append(dict(case=name,image=str(image),output=str(target),log=str(log)))
        invalid_cases[backend]=rejected
        corrupt = bytearray(valid); corrupt[144] ^= 1
        image=base / 'corrupted.owner'; image.write_bytes(corrupt)
        invoke('restore',base / 'corruption',base / '64/commands.txt',base / '64/expected.txt',image,cut,True)
    for b in bindings: require(file_sha(b['path']) == b['sha256'],'source changed during queue continuations')
    report = dict(status='passed',scope='production loadmem queue component; complete CPU/HTIF pending',
                  commands=commands,invalid_cases=invalid_cases,source_inputs=bindings,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                  level1_verified=False,level2_verified=False)
    path=out / 'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(audit(path),indent=2))


if __name__ == '__main__': main()
