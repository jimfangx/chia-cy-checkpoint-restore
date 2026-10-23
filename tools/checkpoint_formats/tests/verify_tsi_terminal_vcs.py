"""Fresh sealed-terminal/BCD component continuations and production routing.

This does not certify a coherent CPU cut, target-cycle replay or CPU admission.
"""
from tools.checkpoint_formats import toolchain as _toolchain
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
from tools.checkpoint_formats.tests.fesvr_overlay import build_overlay, overlay_inputs
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf
from tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs import canonical, pristine_peers
from tools.checkpoint_formats.tests.verify_tsi_polling_cut_vcs import OWNERS, audit_components

INPUT = bytes([65, 0, 255])
READ = 1 << 56


def image(cursor, output=b''):
    return config(27, 1, 1048576, len(INPUT)) + INPUT + words(cursor, len(output)) + output


def oracle():
    cursor = pending = 0
    output = b''
    terminal, bcd, events = [image(0)], [config(26, 1, 1048576) + words(0)], []
    for event in range(1, 13):
        lines = [f'EVENT {event}\n']
        if event in (1, 3, 11):
            pending += 1
        elif event == 7:
            pending += 2
        elif event in (2, 5, 6, 8, 10) and pending and cursor < len(INPUT):
            lines.append(f'RESPONSE {READ | 0x100 | INPUT[cursor]}\n')
            pending -= 1
            cursor += 1
        elif event in (4, 9, 12):
            ch = {4: 90, 9: 0, 12: 255}[event]
            output += bytes([ch])
            lines.append(f'OUTPUT {ch}\n')
        terminal.append(image(cursor, output))
        bcd.append(config(26, 1, 1048576) + words(pending, *([READ] * pending)))
        events.append(''.join(lines).encode())
    return terminal, bcd, events


def audit(path):
    path = path.resolve(); out = path.parent; report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong terminal scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'terminal artifact membership changed')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'terminal artifact changed ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'terminal source snapshot changed')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    require((out/'polling.elf').read_bytes() == polling_elf(), 'production fixture ELF changed')
    terminal, bcd, events = oracle()
    for backend in ('native', 'vcs-dpi'):
        capture = out/(backend+'-capture')
        require((capture/'events.log').read_bytes() == b''.join(events), 'terminal execution differs from independent byte oracle')
        require((capture/'emitted.bin').read_bytes() == b'Z\0\xff', 'terminal output differs')
        for cut in range(13):
            require((capture/f'cut-{cut}.terminal').read_bytes() == terminal[cut], 'incomplete terminal state')
            require((capture/f'cut-{cut}.bcd').read_bytes() == bcd[cut], 'incomplete peer BCD state')
        integration = out/(backend+'-integration')
        for name, expected in [('pristine', image(0)), ('consumed', image(3)), ('written', image(3, b'Z'))]:
            require((integration/(name+'.terminal')).read_bytes() == expected, 'production terminal state differs')
        require((integration/'output.bin').read_bytes() == b'Z', 'actual production BCD output differs')
        metadata_bound = report.get('sealed_metadata_bound', False)
        marker = ('metadata_bound=1 audited_components=12' if metadata_bound else 'metadata_rejected=1')
        require(('ACTUAL_TSI_TERMINAL input_bytes=3 output_bytes=1 source_file_replaced=1 '+marker+' exit=0') in
                (out/(backend+'-integration.log')).read_text(), 'production terminal did not execute')
        if metadata_bound:
            expected = canonical(out/'polling.elf', revision=4, sealed_input=out/'sealed-input.bin', terminal=image(0))
            require((integration/'startup.metadata').read_bytes()==expected, 'sealed startup binding differs from independent oracle')
            for cut, expected_terminal in [('pristine',image(0)),('consumed',image(3)),('written',image(3,b'Z'))]:
                paths=list(integration.glob(cut+'.audit-*'))
                require({p.name.split('.audit-')[1] for p in paths}==OWNERS|{'bcd','terminal','identity','write'}, 'incomplete sealed device audit')
                images={n:(integration/(cut+'.audit-'+n)).read_bytes() for n in OWNERS}
                audit_components(images, msip=False)
                require((integration/(cut+'.audit-terminal')).read_bytes()==expected_terminal and
                        (integration/(cut+'.audit-bcd')).read_bytes()==config(26,1,1048576)+words(0), 'wrong actual sealed device state')
                from tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs import identity_image
                from tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs import writer
                require((integration/(cut+'.audit-identity')).read_bytes()==identity_image(writer()) and
                        (integration/(cut+'.audit-write')).read_bytes()==writer(), 'sealed idle identity/write state differs')
        require('TERMINAL_GUARDS live=3 active=5 interrupted=5 output_limit=1' in (out/(backend+'-guards.log')).read_text(), 'terminal guards incomplete')
    require(len(report['restores']) == 52 and len(report['invalid']) == 4 and len(report['corruptions']) == 4, 'missing terminal fresh processes')
    for case in report['restores']:
        dest = Path(case['destination']); cut = case['cut']
        require((dest/'preedge.terminal').read_bytes() == terminal[cut] and (dest/'preedge.bcd').read_bytes() == bcd[cut], 'fresh complete preedge readback differs')
        require((dest/'events.log').read_bytes() == b''.join(events[cut:]), 'terminal continuation diverges')
        expected_output = bytes({4: 90, 9: 0, 12: 255}[i] for i in (4, 9, 12) if i > cut)
        require((dest/'emitted.bin').read_bytes() == expected_output, 'fresh terminal duplicated output prefix')
        require((dest/'final.terminal').read_bytes() == terminal[-1] and (dest/'final.bcd').read_bytes() == bcd[-1], 'final owner state diverges')
    invalid_count = len(terminal[4]) + 59 + 1 + 2 + 4
    for case in report['invalid']:
        require(f'TERMINAL_ATOMIC_REJECTIONS malformed={invalid_count} incompatible=1 missing_or_invalid_peer=2 services=0' in Path(case['log']).read_text(), 'incomplete atomic rejection')
        require((Path(case['destination'])/'preedge.terminal').read_bytes() == terminal[4], 'valid image failed after rejection')
    for case in report['corruptions']:
        actual = (Path(case['destination'])/'events.log').read_bytes().splitlines()
        expected = b''.join(events[1:]).splitlines()
        mismatch = next((i for i, (left, right) in enumerate(zip(expected, actual)) if left != right), None)
        require(mismatch == 1 and expected[1] == f'RESPONSE {READ | 0x141}'.encode() and
                actual[1] == f'RESPONSE {READ | 0x100}'.encode(), 'wrong first terminal semantic divergence')
        require(case['first_divergence'] == dict(host_event=2, expected=expected[1].decode(), actual=actual[1].decode()), 'unbound first divergence')
    pids = []
    for command in report['commands']:
        text = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and text.rstrip().endswith('exit=0'), 'wrong terminal environment/result')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'terminal sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', text)[1]))
    require(len(pids) == len(set(pids)), 'terminal check reused native process')
    metadata_result={}
    transaction_result={}
    if report.get('atomic_sealed_transaction'):
        require(len(report['transactions'])==4, 'missing fresh transaction backend pairings')
        allocations=0
        for case in report['transactions']:
            dest=Path(case['destination']);text=Path(case['log']).read_text()
            count=len(terminal[4])+len(bcd[4])+4
            match=re.search(r'SEALED_TRANSACTION malformed=(\d+) membership=7 allocation_failures=(\d+) '
                            r'unchanged_on_failure=1 target_edges=0 services_before_readback=0 response=(\d+)',text)
            require(match and int(match[1])==count and int(match[2])>=4 and int(match[3])==READ|0x100,
                    'incomplete atomic transaction/fault coverage')
            allocations+=int(match[2])
            require((dest/'preedge.terminal').read_bytes()==terminal[4] and
                    (dest/'preedge.bcd').read_bytes()==bcd[4], 'transaction omitted pre-service readback')
        transaction_result=dict(atomic_transaction_fresh_readbacks=4, transaction_malformed_rejections=4*count,
                                transaction_membership_rejections=28, transaction_allocation_failures=allocations)
    if report.get('sealed_metadata_bound'):
        expected=canonical(out/'polling.elf',revision=4,sealed_input=out/'sealed-input.bin',terminal=image(0))
        peers=dict(pristine_peers(),terminal=image(0))
        require(len(report['metadata_cases'])==24, 'missing fresh sealed metadata checks')
        malformed=0
        for case in report['metadata_cases']:
            dest=Path(case['destination']);text=Path(case['log']).read_text();mode=case['mode']
            if mode in ('metadata-prepare','metadata-invalid'):
                count=2*len(expected)+1 if mode=='metadata-invalid' else 0
                require(f'SEALED_METADATA_READBACK unchanged_peers=8 target_edges=0 target_services=0 context_entries=0 guards=3 malformed_rejections={count}' in text, 'sealed preparation entered services/missed rejections')
                malformed+=count
                require({p.name for p in dest.iterdir()}=={'preedge.metadata',*{'preedge.'+n for n in peers}}, 'sealed readback omitted peer')
                require((dest/'preedge.metadata').read_bytes()==expected, 'fresh sealed metadata readback differs')
                for n,b in peers.items():require((dest/('preedge.'+n)).read_bytes()==b, 'sealed preparation mutated '+n)
            else:
                require(f'SEALED_METADATA_INCOMPATIBLE mode={mode} unchanged_peers={7 if mode=="metadata-live" else 8} services=0' in text and not list(dest.iterdir()), 'incompatible sealed metadata published a partial owner')
        for kind,options in [('missing-peer',{'omit_terminal':True}),('reordered-peers',{'reorder_peers':True})]:
            require((out/(kind+'-images/startup.metadata')).read_bytes()==canonical(out/'polling.elf',revision=4,sealed_input=out/'sealed-input.bin',terminal=image(0),**options), 'unbound peer membership negative image')
        metadata_result=dict(fresh_sealed_metadata_readbacks=8, unchanged_peer_readbacks=64,
                             sealed_metadata_malformed_rejections=malformed, sealed_metadata_incompatible_rejections=16,
                             sealed_polling_device_audits=6, sealed_polling_component_images=60)
    return dict(status='passed', complete_fresh_pair_readbacks=52, continued_host_events=312,
                atomic_malformed_images=4*invalid_count, incompatible_images=4, incomplete_pairs=8,
                first_semantic_divergences=4, production_TSI_runs=2, service_guards=28,
                **metadata_result, **transaction_result, level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path); parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs destination')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    source = TESTS/'tsi_terminal_checkpoint.cc'; sv = TESTS/'tsi_terminal_checkpoint_tb.sv'
    sources = [source, TESTS/'tsi_terminal_allocations.cc', STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), *overlay_inputs(), FESVR/'lib/libfesvr.a',
              TESTS/'verify_tsi_host_control_fesvr_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              TESTS/'verify_tsi_startup_metadata_vcs.py', TESTS/'verify_tsi_polling_cut_vcs.py',
              TESTS/'verify_tsi_memif_identity_fesvr_vcs.py', TESTS/'verify_tsi_memif_write_vcs.py',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *sorted((FESVR/'include/fesvr').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out)
        record = dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log))
        commands.append(record); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return record
    library = build_overlay(out, execute)
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native, simv = out/'terminal-native', out/'simv'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_terminal_checkpoint_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_TERMINAL_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    elf = out/'polling.elf'; elf.write_bytes(polling_elf())
    def invoke(backend, mode, name, images='unused', cut=-1):
        dest = out/name
        argv = [native, mode, elf, images, dest, cut] if backend == 'native' else [simv, '-no_save', '+mode='+mode, '+source='+str(elf),
                '+images='+str(images), '+destination='+str(dest), '+cut='+str(cut)]
        return dict(execute(argv, out/(name+'.log')), mode=mode, destination=str(dest), images=str(images), cut=cut)
    for backend in ('native', 'vcs-dpi'):
        for mode in ('capture', 'guards', 'integration'):
            invoke(backend, mode, backend+'-'+mode)
    restores, invalid, corruptions, transactions = [], [], [], []
    for producer in ('native', 'vcs-dpi'):
        for backend in ('native', 'vcs-dpi'):
            images = out/(producer+'-capture')
            for cut in range(13):
                restores.append(invoke(backend, 'restore', f'{producer}-{backend}-cut-{cut}', images, cut))
            invalid.append(invoke(backend, 'invalid', f'{producer}-{backend}-invalid', images))
            transactions.append(invoke(backend, 'transaction', f'{producer}-{backend}-transaction', images))
            corruption = out/f'{producer}-{backend}-corrupt-images'; corruption.mkdir()
            # Valid structure and exact config, wrong semantic cursor at cut 1.
            (corruption/'cut-1.terminal').write_bytes(image(1))
            shutil.copyfile(images/'cut-1.bcd', corruption/'cut-1.bcd')
            case = invoke(backend, 'corrupt', f'{producer}-{backend}-corrupt', corruption, 1)
            case['first_divergence'] = dict(host_event=2, expected=f'RESPONSE {READ | 0x141}', actual=f'RESPONSE {READ | 0x100}')
            corruptions.append(case)
    for kind,options in [('missing-peer',{'omit_terminal':True}),('reordered-peers',{'reorder_peers':True})]:
        dest=out/(kind+'-images');dest.mkdir()
        (dest/'startup.metadata').write_bytes(canonical(elf,revision=4,sealed_input=out/'sealed-input.bin',terminal=image(0),**options))
    metadata_cases=[]
    for producer in ('native','vcs-dpi'):
        for backend in ('native','vcs-dpi'):
            for suffix in ('prepare','invalid','wrong-input','live','missing-peer','reordered-peers'):
                images=out/(suffix+'-images') if suffix in ('missing-peer','reordered-peers') else out/(producer+'-integration')
                metadata_cases.append(invoke(backend,'metadata-'+suffix,f'{producer}-{backend}-metadata-{suffix}',images))
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'terminal source changed during execution')
    report = dict(status='passed', scope='sealed terminal/BCD components only; complete CPU restore unsupported', commands=commands,
                  restores=restores, invalid=invalid, corruptions=corruptions, source_inputs=bindings,
                  sealed_metadata_bound=True,metadata_cases=metadata_cases,level1_verified=False, level2_verified=False,
                  atomic_sealed_transaction=True,transactions=transactions,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(audit(path), summary=str(path)), indent=2))


if __name__ == '__main__':
    main()
