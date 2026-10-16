"""Independent actual provider archive, state/trace and case-coverage audit."""
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input


def coverage(report):
    cases = report['cases']
    counts = {'capture':72, 'restore':144, 'reject':300, 'guard':40, 'publish':72,
              'abandon':6, 'second':4, 'corrupt':6, 'thread-capture':6, 'thread-restore':12, 'thread-guard':24}
    require(len(cases) == 686 and len({c['case']['name'] for c in cases}) == 686, 'missing/duplicate signal process')
    require({k:sum(c['case']['mode'] == k for c in cases) for k in counts} == counts, 'wrong signal scopes')
    for backend in ('native', 'vcs-dpi'):
        for kind in ('none', 'int', 'term'):
            for present, raw in ((0,0),(1,0),(1,1),(1,3),(1,2147483649),(1,4294967295)):
                for stopped in (0,1):
                    require(sum(c['case']['backend'] == backend and c['case']['mode'] == 'capture' and
                                c['case']['scenario'] == kind and c['case']['detail'] == f'{present},{raw},{stopped}'
                                for c in cases) == 1, 'missing/duplicate actual signal capture')
        for signum in (2, 15, 6):
            for guard in ('pending', 'mask', 'handler', 'flags', 'handler-mask'):
                require(sum(c['case']['backend'] == backend and c['case']['mode'] == 'guard' and
                            c['case']['scenario'] == guard and c['case']['detail'] == str(signum)
                            for c in cases) == 1, 'missing/duplicate native signal policy guard')
    for backend in ('native', 'vcs-dpi'):
        for kind, sig in (('none',0), ('int',2), ('term',15)):
            require(sum(c['case']['backend'] == backend and c['case']['mode'] == 'thread-capture' and
                        c['case']['scenario'] == kind and c['case']['detail'] == str(sig)
                        for c in cases) == 1, 'missing/duplicate parked-worker capture')
            for producer in ('native', 'vcs-dpi'):
                require(sum(c['case']['backend'] == backend and c['case']['mode'] == 'thread-restore' and
                            c['case']['scenario'] == kind and c['case']['name'].startswith(producer+'-')
                            for c in cases) == 1, 'missing/duplicate cross-backend threaded restore')
        for guard in ('worker-mask','worker-pending','second-worker-pending','shared-pending'):
            for sig in (2,15,6):
                require(sum(c['case']['backend'] == backend and c['case']['mode'] == 'thread-guard' and
                            c['case']['scenario'] == guard and c['case']['detail'] == str(sig)
                            for c in cases) == 1, 'missing/duplicate actual worker signal guard')
    return counts


def decode(path):
    payload = Path(path).read_bytes()
    require(len(payload) == 88, 'wrong provider state length')
    values = struct.unpack('<11Q', payload)
    require(values[:7] == (0x3154504b43474457,1,33,3,1,32,1), 'wrong provider schema/configuration')
    present, raw, stopped, delivered = values[7:]
    require(present in (0,1) and raw < 2**32 and stopped in (0,1) and delivered in (0,1) and
            (present or not raw), 'invalid raw provider state')
    return present, raw, stopped, delivered


def observations(state):
    present, raw, stopped, delivered = state
    raw_signed = raw - (2**32 if raw >= 2**31 else 0)
    return [present, raw, stopped, delivered, int(bool(present or delivered)), stopped, raw_signed >> 1, 0]


def audit(path):
    path = Path(path).resolve(); out = path.parent; report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong component scope')
    counts = coverage(report)
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed artifact membership')
    for p, digest in report['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed native artifact '+p)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed native source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    require(report.get('thread_guards') is True, 'thread scope not selected')
    require(report['recipe_build_identity'], 'must test actual exact-recipe archive')
    identity = json.loads(Path(report['recipe_build_identity']).read_text())
    binary = Path(identity['native_binary']); archive = binary.parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(identity['htif_lifecycle_provider_linked'] is True and not identity['level1_verified'] and
            file_sha(binary) == identity['sources_sha256'][str(binary)], 'wrong recipe provider executable')
    require((out/'libfesvr-checkpoint.a').read_bytes() == archive.read_bytes(), 'consumer did not use linked Rocket archive')
    obj = archive.parent/'owned-htif.o'
    require(obj.read_bytes() == subprocess.check_output(['ar','p',archive,'htif.o']), 'Rocket HTIF object differs from archive')
    symbols = subprocess.check_output(['nm','-C',binary], text=True)
    for name in ('firesim_htif_signal_read(', 'firesim_htif_signal_validate_restore(', 'firesim_htif_signal_publish('):
        require(any(' T '+name in line for line in symbols.splitlines()), 'signal provider not defined by actual CPU binary')
    seen = set()
    for record in report['cases']:
        c = record['case']; folder = out/c['name']; log = Path(record['log']).read_text()
        require(record['log'] not in seen, 'reused process log'); seen.add(record['log'])
        require('argv='+json.dumps(record['argv'])+'\n' in log and 'fresh_process_pid=' in log and
                log.rstrip().endswith('exit='+str(c['expected'])), 'process command/log/exit mismatch')
        mode = c['mode']
        if mode in ('capture','restore','publish'):
            kind = c['scenario']; prefix = {'capture':'captured','restore':'readback','publish':'after'}[mode]
            state = decode(folder/(prefix+'.signal'))
            require(state[3] == int(kind in ('int','term')), 'handler latch not restored')
            actual = list(map(int, (folder/(prefix+'.fields')).read_text().split()))
            require(actual == observations(state), 'raw fields or actual public HTIF observations differ')
            if mode == 'capture':
                require(state[:3] == tuple(map(int, c['detail'].split(','))), 'actual capture differs from requested state')
            if mode == 'restore':
                require((folder/'readback.signal').read_bytes() == Path(c['source']).read_bytes() and
                        (folder/'continuation.txt').read_bytes() == Path(c['source']).with_name('continuation.txt').read_bytes(),
                        'fresh provider differs from uninterrupted source at first boundary')
                observed = observations(state)
                expected = f'0 {observed[4]} {observed[5]} {observed[6]} 0\n1 {observed[4]} {int(bool(observed[4] or observed[5]))} {observed[6]} 0\n'
                require((folder/'continuation.txt').read_text() == expected, 'wrong independent HTIF stop oracle')
        if mode in ('guard','abandon','publish'):
            require((folder/'transaction.txt').read_text() == f'callbacks={int(mode=="publish")} target_services=0\n', 'peer publication before guard')
            require((folder/'after.serial').read_bytes() == (folder/('candidate.serial' if mode=='publish' else 'before.serial')).read_bytes(), 'partial serial publication')
        if mode == 'reject': require(decode(folder/'unchanged.signal') == (0,0,0,0), 'invalid image changed provider')
        if mode == 'corrupt':
            actual = decode(folder/'corrupted.signal')
            expected = {'delivered':(0,0,0,1), 'stopped':(0,0,1,0), 'raw':(1,4,0,0)}[c['scenario']]
            require(actual == expected and list(map(int,(folder/'corrupted.fields').read_text().split())) == observations(expected), 'fault did not change actual provider')
            signal_name = {'delivered':'should_exit', 'stopped':'stopped', 'raw':'exit_code'}[c['scenario']]
            require((folder/'first-divergence.txt').read_text() == f'FIRST_DIVERGENCE boundary=0 signal={signal_name} acknowledged=0 target_services=0\n', 'late/incorrect fault acknowledgement')
        if mode in ('thread-capture','thread-restore'):
            prefix = 'captured' if mode == 'thread-capture' else 'readback'
            state = decode(folder/(prefix+'.signal'))
            require(state == (1,3,0,int(c['scenario'] != 'none')), 'wrong threaded state')
            require(list(map(int,(folder/(prefix+'.fields')).read_text().split())) == observations(state), 'threaded private readback differs')
            expected = '0 1 0 1 0\n1 1 1 1 0\n'
            require((folder/'continuation.txt').read_text() == expected, 'threaded first boundary differs')
            if mode == 'thread-restore':
                require((folder/'readback.signal').read_bytes() == Path(c['source']).read_bytes() and
                        (folder/'continuation.txt').read_bytes() == Path(c['source']).with_name('continuation.txt').read_bytes(),
                        'threaded continuation differs from uninterrupted source')
        if mode == 'thread-guard':
            require(decode(folder/'unchanged.signal') == (0,0,0,0), 'worker guard partially restored provider')
            require((folder/'before.serial').read_bytes() == (folder/'after.serial').read_bytes(), 'worker guard published peer')
            require((folder/'retry.serial').read_bytes() != (folder/'before.serial').read_bytes() and
                    (folder/'retry.signal').read_bytes() == Path(c['source']).read_bytes(), 'worker retry did not publish atomically')
            require((folder/'transaction.txt').read_text() == 'rejected_callbacks=0 retry_callbacks=1 target_services=0\n', 'worker callback count differs')
            rows = (folder/'rejections.txt').read_text().splitlines()
            require(len(rows) == 3 and [r.split()[0] for r in rows] == ['capture','prepare','commit'], 'missing provider API guard')
            if c['scenario'] != 'shared-pending':
                reason = 'unblocked' if c['scenario'] == 'worker-mask' else 'pending'
                require(all(re.fullmatch(api+' '+reason+r' HTIF signal in thread: [0-9]+', row)
                            for api,row in zip(('capture','prepare','commit'), rows)), 'actual kernel worker was not audited')
        if mode == 'second':
            require(c['expected'] == (255 if c['scenario']=='int' else 0), 'wrong real handler exit expectation')
            require(('SECOND_SIGNAL before=1' if c['scenario']=='int' else 'FIRST_SIGNAL delivered=1') in log, 'missing actual second-signal delivery')
    rejected = 0
    for mode in ('capture','restore','guard','corrupt','thread-capture','thread-restore','thread-guard'):
        for duplicate in (False, True):
            bad = copy.deepcopy(report); index = next(i for i,c in enumerate(bad['cases']) if c['case']['mode'] == mode)
            if duplicate: bad['cases'].append(copy.deepcopy(bad['cases'][index]))
            else: bad['cases'].pop(index)
            try: coverage(bad)
            except ValueError: rejected += 1
            else: raise ValueError('independent auditor accepted incomplete/duplicate evidence')
    return dict(status='passed', processes=len(report['cases']), scopes=counts,
                missing_duplicate_evidence_rejections=rejected, exact_recipe_archive_verified=True,
                actual_first_boundary_faults=6, thread_guard_transactions=24, CPU_level1_verified=False)


if __name__ == '__main__': print(json.dumps(audit(sys.argv[1]),indent=2))
