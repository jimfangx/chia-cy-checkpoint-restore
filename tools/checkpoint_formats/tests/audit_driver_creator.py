"""Independent audit of reserved driver creator and VCS harness receipts."""
import argparse
import copy
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha


def audit(path, report=None):
    path = Path(path).resolve(); out = path.parent
    r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and r['level1_verified'] is False and r['level2_verified'] is False,
            'creator component scope')
    require(json.loads((out/'source-inputs.json').read_text()) == r['source_inputs'], 'creator sources membership')
    bindings = {b['path']:b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate creator source')
    for name in ('driver_thread.h', 'simif_emul.h', 'simif_emul.cc', 'driver_creator_reservation.cc',
                 'driver_creator_reservation_tb.sv', 'harness_dispatcher_checkpoint.cc',
                 'verify_harness_dispatcher_vcs.py', 'verify_driver_creator_vcs.py', 'audit_driver_creator.py'):
        require(any(p.endswith('/'+name) for p in bindings), 'missing creator source '+name)
    require(len(r['commands']) == 8 and len({c['log'] for c in r['commands']}) == 8, 'creator commands membership')
    require({Path(c['log']).name for c in r['commands']} == {
        'native-build.log','vcs-build.log','native.log','vcs.log',
        'harness-legacy.log','harness-reserved.log','harness-aggregate-legacy.log','harness-aggregate-reserved.log'},
        'missing creator native/harness mode')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'creator artifact membership')
    for p,h in r['artifact_sha256'].items(): require(file_sha(p) == h, 'creator artifact drift '+p)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'creator source snapshot drift')
    continuations = reserved = malformed = lifecycle = aggregate_invalids = guards = 0
    for c in r['commands']:
        text = Path(c['log']).read_text(); lines = text.splitlines()
        require(lines[0].startswith('cwd=') and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1]=='exit=0', 'creator command/result binding')
        require(c['argv'][:2] == ['bash','-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2],
                'creator native environment')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'creator sanitizer')
        name = Path(c['log']).name
        if name in ('native.log', 'vcs.log'):
            require('DRIVER_CREATOR_PASS tasks=512 exceptions=512 launches=17 cancellations=16 rejections=1296' in text,
                    'creator lifecycle receipt')
            if r.get('creator_resource_retained'):
                require('DRIVER_RESIDENT_PASS destroyed=32 launches=16 cancellations=16 exceptions=32 rejections=176 capture_order=1' in text,
                        'creator retained lifetime receipt')
            if r.get('creator_launch_prepared'):
                require('DRIVER_PREPARED_LAUNCH_PASS destroyed=32 launches=16 cancellations=16 allocation_failures=32 rejections=208 allocation_free_commit=1 capture_order=1' in text,
                        'creator prepared launch receipt')
            if name == 'vcs.log': require('DRIVER_CREATOR_ZERO_EDGES time=0 edges=0' in text, 'creator VCS edges')
        if 'summary' not in c: continue
        folder = Path(c['summary']).parent; h = json.loads(Path(c['summary']).read_text())
        is_reserved = '-reserved' in folder.name; aggregate = '-aggregate' in folder.name
        require({v['cut'] for v in h['cases']} == {13,14,16,31,32} and len(h['cases']) == 5,
                'creator harness cuts')
        for cut in (13,14,16,31,32):
            case = folder/f'cut-{cut}'; ref = case/'reference'; dst = case/'restore'
            trace = (dst/'run.log').read_text()
            require(trace.rstrip().endswith('exit=0') and
                    'HARNESS_DISPATCHER_BOOTSTRAP zero_edges=1 refreshes=1' in trace and
                    'HARNESS_DISPATCHER_NATIVE_UNCHANGED' in trace, 'creator harness bootstrap')
            if is_reserved:
                require(trace.count('HARNESS_RESERVED_CREATOR_PREPARED guards=13 exceptions=1 mmio=0 native_ticks=0') == 1 and
                        trace.count('HARNESS_RESERVED_CREATOR_CONTINUED same_thread=1') == 1,
                        'creator thread identity/preparation checks')
                require(trace.index('HARNESS_RESERVED_CREATOR_PREPARED') < trace.index('HARNESS_DISPATCHER_BOOTSTRAP'),
                        'creator preparation after bootstrap')
                if r.get('creator_launch_prepared'):
                    require(trace.count('HARNESS_PREPARED_LAUNCH guards=6 allocation_failures=1 mmio=0 native_ticks=0')==1 and
                            trace.index('HARNESS_PREPARED_LAUNCH') < trace.index('HARNESS_DISPATCHER_BOOTSTRAP'),
                            'dispatcher launch was not prepared under the clock hold')
                if r.get('creator_resource_retained'):
                    require(trace.count('HARNESS_CREATOR_RESOURCE_LIVE same_thread=1 finalized=1')==1 and
                            trace.count('HARNESS_CREATOR_RESOURCE_DESTROYED same_thread=1 finalized=1')==1 and
                            trace.index('HARNESS_CREATOR_RESOURCE_LIVE') < trace.index('HARNESS_CREATOR_RESOURCE_DESTROYED'),
                            'actual harness resource lifetime missing')
                reserved += 1; guards += 13
            require((ref/'rows.jsonl').read_bytes() == (dst/'rows.jsonl').read_bytes(), 'creator generated/harness continuation')
            require(json.loads((ref/'cut.jsonl').read_text()) == json.loads((dst/'loaded.jsonl').read_text()),
                    'creator complete preedge RTL/bank readback')
            for i in range(7):
                require((ref/f'owner-{i}').read_bytes() == (dst/f'initial-{i}').read_bytes(), 'creator preedge native readback')
            for owner in ('mmio','memory'):
                require((ref/f'final.{owner}').read_bytes() == (dst/f'final.{owner}').read_bytes(), 'creator final native state')
            final = ['W 36 1','R 28 42','R 32 0','W 24 1','R 16 23','R 20 0']
            require((dst/'driver.trace').read_text().splitlines() == [f'OP {i}' for i in range(cut,32)]+final,
                    'creator operation order or repeated initialization')
            if cut == 32: require('HARNESS_DISPATCHER_TERMINAL zero_edges=1' in trace, 'creator terminal edge')
            else:
                a = re.search(r'HARNESS_DISPATCHER_CUT edges=(\d+)',(ref/'run.log').read_text())
                b = re.search(r'HARNESS_DISPATCHER_DONE edges=(\d+) target_edges=(\d+)',(ref/'run.log').read_text())
                d = re.search(r'HARNESS_DISPATCHER_DONE edges=(\d+) target_edges=(\d+)',trace)
                require(a and b and d and b[1] == b[2] and d[1] == d[2] and int(d[1])+int(a[1]) == int(b[1]),
                        'creator target edge continuation labels')
            for name in [f'malformed-{i}' for i in range(7)]+['unsupported','reset','finish','repeat']+(
                    ['manifest','schema','generated-last','harness-last','trailing','truncated','commit-order'] if aggregate else []):
                failed = case/name; rejection = (failed/'run.log').read_text()
                require(rejection.rstrip().endswith('exit=1'), 'creator native rejection missing')
                if name.startswith('malformed-') or name in ('unsupported','manifest','schema','generated-last','harness-last','trailing','truncated','commit-order'):
                    require(not list(failed.glob('initial-*')) and not (failed/'driver.trace').exists(), 'creator partial publication')
                if aggregate and name not in ('unsupported','reset','finish','repeat'):
                    require('AGGREGATE_REJECTED_UNCHANGED deposits=0 native_loads=0 driver_calls=0 poisoned=1' in rejection,
                            'creator aggregate rejection modified peers')
            continuations += 1; malformed += 7; lifecycle += 4
            if aggregate: aggregate_invalids += 14
    counts = dict(harness_continuations=continuations, reserved_creator_continuations=reserved,
                  malformed_native_processes=malformed, lifecycle_negative_processes=lifecycle,
                  aggregate_prevalidation_rejections=aggregate_invalids, creator_preparation_guards=guards)
    require(all(r[k] == v for k,v in counts.items()), 'creator reported counts')
    return dict(status='passed', **counts, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', type=Path, required=True)
    p.add_argument('--out', type=Path); a = p.parse_args(); result = audit(a.summary)
    original = json.loads(a.summary.read_text()); rejected = []
    for key in ('commands','source_inputs'):
        for mode in ('missing','duplicate'):
            changed = copy.deepcopy(original)
            if mode == 'missing': changed[key].pop()
            else: changed[key].append(changed[key][0])
            try: audit(a.summary, changed)
            except FormatError: rejected.append(key+'-'+mode)
            else: raise RuntimeError('incomplete creator evidence admitted')
    result['incomplete_receipt_rejections'] = rejected
    if a.out: a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
