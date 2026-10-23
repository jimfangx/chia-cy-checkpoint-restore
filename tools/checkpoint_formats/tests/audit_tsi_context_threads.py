"""Independent archived-state/process audit for aggregate worker admission."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import itertools
import json
from pathlib import Path
import shlex

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_tsi_context_group import NAMES, audit as parent_audit


def images(prefix, names=NAMES):
    return {n:Path(str(prefix)+'.'+n).read_bytes() for n in names}


def audit(path, report=None):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'thread component scope')
    parent = Path(r['context_summary']); require(file_sha(parent) == r['context_sha256'], 'thread parent changed')
    parent_audit(parent)
    require(r['cuts'] == {'execution':6, 'tail':len((parent.parent/'scenario-1/plan').read_text().splitlines())}, 'thread cut membership')
    bindings = {b['path']:b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate thread inputs')
    for suffix in ('tsi_context_threads_fesvr.cc', 'tsi_context_threads_fesvr_tb.sv', 'verify_tsi_context_threads_vcs.py',
                   'tsi_context_group.h', 'htif_lifecycle_provider.inc', 'htif_signal_threads.h'):
        require(any(p.endswith('/'+suffix) for p in bindings), 'missing thread source '+suffix)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'thread snapshot drift')
    versions = set(r['identities']); require('current' in versions and versions <= {'current','prior'}, 'thread provider versions')
    for version, identity_path in r['identities'].items():
        require(identity_path in bindings and file_sha(identity_path) == bindings[identity_path]['sha256'], 'unbound thread recipe')
        identity = json.loads(Path(identity_path).read_text())
        require(identity['htif_lifecycle_provider_linked'] and identity['vcs_home'] == _toolchain.VCS_HOME, 'wrong thread recipe provider')
        archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        require(str(archive) in bindings and file_sha(archive) == file_sha(out/version/'libfesvr-checkpoint.a'), 'thread archive differs from recipe')
        if version == 'current':
            for f, h in identity['sources_sha256'].items():
                if f in bindings: require(bindings[f]['sha256'] == h, 'thread current recipe/source mismatch')
            extension = next(Path(b['snapshot']).read_text() for f,b in bindings.items() if f.endswith('/htif_lifecycle_provider.inc'))
            guard = extension.split('static void guard(const htif_t &htif) {',1)[1].split('static firesim_htif_lifecycle_state_t read',1)[0]
            require('signal_guard(htif);' in guard and 'if (signal_exit)' in guard, 'thread lifecycle guard not connected')
    if 'prior' in versions:
        require(file_sha(out/'prior/libfesvr-checkpoint.a') != file_sha(out/'current/libfesvr-checkpoint.a'), 'identical witness providers')
    require(set(r['artifact_sha256']) == {str(f) for f in out.rglob('*') if f.is_file() and f != path}, 'thread artifact membership')
    for f,h in r['artifact_sha256'].items(): require(file_sha(f) == h, 'thread artifact drift '+f)
    commands = {c['log']:c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']), 'duplicate thread commands')
    def command(c):
        log = c['log']; require(log in commands and all(c[k] == commands[log][k] for k in ('argv','cwd','expected_exit')), 'unbound thread result')
        require(log not in used, 'reused thread native result'); used.add(log)
        lines = Path(log).read_text().splitlines(); text = '\n'.join(lines)
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0, 'thread process binding')
        require(lines[-1] == 'exit='+str(c['expected_exit']) and c['argv'][:2] == ['bash','-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'thread exit/environment')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'thread sanitizer error')
        return text
    expected = set(itertools.product(versions, ('execution','tail'), ('prepare','commit','capture','resume-fresh','resume-live'),
                   ('worker-mask','worker-pending','second-worker-pending','shared-pending','action-flags','action-mask'), (2,15,6), ('native','vcs-dpi')))
    actual = {(c['version'],c['boundary'],c['operation'],c['fault'],c['signal'],c['backend']) for c in r['results']}
    require(len(r['results']) == len(expected) and actual == expected, 'thread result membership')
    for c in r['results']:
        text = command(c); op = c['operation']; dest = Path(c['destination']); cut = r['cuts'][c['boundary']]
        source = parent.parent/'scenario-1/native-capture'/f'cut-{cut}'
        args = shlex.split(c['argv'][2]); require(c['source'] == str(source) and (str(source) in args or '+source='+str(source) in args), 'thread source binding')
        executable = out/c['version']/('native' if c['backend'] == 'native' else 'simv')
        require(str(executable) in args, 'thread backend binding')
        if c['version'] == 'prior' and c['fault'] != 'shared-pending':
            require(c['expected_exit'] == 2 and 'FAIL aggregate admission ignored actual worker/action fault' in text, 'prior provider not sensitivity witness')
            continue
        require(c['expected_exit'] == 0, 'current thread result failed')
        initialized = int(op == 'resume-live')
        receipt = (f'CONTEXT_THREAD_GUARD operation={op} fault={c["fault"]} signal={c["signal"]}'
                   f' rejected=1 owners=16 unchanged=1 retry=1 initialized={initialized} services_on_rejection=0 target_edges=0')
        require(receipt in text, 'thread rejection receipt')
        reason = (dest/'rejection.txt').read_text()
        require(('unowned HTIF signal mask/pending/handler state' if c['version'] == 'prior' else
                 'unsupported HTIF signal mask/pending/handler state' if c['fault'] == 'shared-pending' else
                 'unblocked HTIF signal in thread:' if c['fault'] == 'worker-mask' else
                 'pending HTIF signal' if 'pending' in c['fault'] else
                 'unsupported HTIF signal action flags' if c['fault'] == 'action-flags' else
                 'unsupported HTIF signal action mask') in reason, 'wrong thread rejection cause')
        names = [p.name.removeprefix('before-unprepared.') for p in dest.glob('before-unprepared.*')]
        require(set(names) == set(NAMES)-{'poll','bcd','syscall','lifecycle'} and
                images(dest/'before-unprepared',names) == images(dest/'after-unprepared',names), 'thread partial owner mutation')
        verified_names = set(NAMES)-{'poll','bcd'}
        require(images(dest/'before-verified',verified_names) == images(dest/'after-verified',verified_names), 'thread syscall/provider peer mutation')
        if op not in ('prepare','commit'):
            before_cut = min(cut+initialized, r['cuts']['tail'])
            wanted = images(parent.parent/'scenario-1/native-capture'/f'cut-{before_cut}')
            require(images(dest/'before') == images(dest/'after') == wanted, 'thread sixteen-owner mutation')
        retry_cut = min(cut+int(op == 'resume-fresh')+2*int(op == 'resume-live'), r['cuts']['tail'])
        wanted = images(parent.parent/'scenario-1/native-capture'/f'cut-{retry_cut}')
        require(images(dest/'retry') == wanted, 'thread retry differs from independent coroutine oracle')
    for version in versions:
        for name in ('native-build','vcs-build'):
            c = commands[str(out/version/(name+'.log'))]; command(c)
            args = shlex.split(c['argv'][2]); library = str(out/version/'libfesvr-checkpoint.a')
            require(any(library in token for token in args), 'thread build omitted archive')
            if name == 'vcs-build': require(_toolchain.VCS in args and '-full64' in args, 'thread VCS release')
    require(used == set(commands), 'unclassified thread command')
    return dict(status='passed', current_admission_cases=360, prior_provider_witnesses=300 if 'prior' in versions else 0,
                prior_shared_pending_controls=60 if 'prior' in versions else 0,
                operations=5, boundaries=2, signal_kinds=3, faults=6, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', type=Path, required=True); a = p.parse_args()
    path = a.summary.resolve(); result = audit(path); base = json.loads(path.read_text()); rejected = []
    for field in ('results','commands','source_inputs'):
        for kind in ('missing','duplicate'):
            changed = copy.deepcopy(base)
            if kind == 'missing': changed[field].pop(0)
            else: changed[field].append(copy.deepcopy(changed[field][0]))
            try: audit(path,changed)
            except (FormatError,KeyError,ValueError): rejected.append(field+'-'+kind)
            else: raise RuntimeError('incomplete thread evidence admitted '+field+'-'+kind)
    print(json.dumps(dict(result, summary=str(path), rejected_incomplete_evidence=rejected),indent=2))


if __name__ == '__main__': main()
