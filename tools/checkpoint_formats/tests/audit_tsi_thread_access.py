"""Independent owner-byte and process audit of TSI foreign-thread rejection."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import shlex

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_tsi_context_group import NAMES, audit as parent_audit

OPERATIONS = (
    'context-prepare', 'context-prepare-invalid', 'context-commit', 'context-capture', 'context-initialized',
    'context-resume-fresh', 'context-resume-live', 'host-prepare', 'host-commit', 'host-capture', 'host-advance',
    'syscall-prepare', 'syscall-commit', 'syscall-capture', 'syscall-advance',
    'polling-prepare', 'polling-commit', 'polling-capture', 'polling-advance',
    'exit-prepare', 'exit-capture', 'exit-completed', 'serial-send', 'serial-recv', 'serial-front',
    'serial-available', 'serial-valid', 'serial-ready', 'serial-owner', 'wrapper-owner',
    'host-tick', 'host-switch', 'host-busy', 'host-loaded', 'host-set-loaded', 'loadmem-send',
    'loadmem-read-request', 'loadmem-write-request', 'loadmem-data', 'loadmem-available',
    'memory-read', 'memory-write', 'memory-interface', 'metadata-save', 'metadata-prepare')


def images(prefix, names=NAMES):
    return {n: Path(str(prefix)+'.'+n).read_bytes() for n in names}


def audit(path, report=None):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'access component scope')
    parent = Path(r['context_summary']); require(file_sha(parent) == r['context_sha256'], 'access parent changed')
    parent_audit(parent)
    require(r['cuts'] == {'execution': 6, 'tail': len((parent.parent/'scenario-1/plan').read_text().splitlines())}, 'access cuts')
    bindings = {b['path']: b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate access inputs')
    for name in ('tsi_thread_access_fesvr.cc', 'tsi_thread_access_fesvr_tb.sv', 'verify_tsi_thread_access_vcs.py',
                 'audit_tsi_thread_access.py', 'tsi_thread_owner.h', 'tsi.h', 'tsi_context_group.h',
                 'tsi_host_group.h', 'tsi_polling_syscall.h', 'tsi_polling_lifecycle.h', 'firesim_tsi.cc'):
        require(any(p.endswith('/'+name) for p in bindings), 'missing access source '+name)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'access source snapshot drift')
    identity_path = r['recipe_build_identity']; require(identity_path in bindings, 'unbound access recipe')
    require(file_sha(identity_path) == bindings[identity_path]['sha256'], 'access recipe changed')
    identity = json.loads(Path(identity_path).read_text())
    require(identity['htif_lifecycle_provider_linked'] and identity['vcs_home'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'wrong access recipe')
    for p,h in identity['sources_sha256'].items():
        if p in bindings: require(bindings[p]['sha256'] == h, 'access recipe/source mismatch')
    archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(str(archive) in bindings and file_sha(archive) == file_sha(out/'libfesvr-checkpoint.a'), 'wrong access provider')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'access artifact membership')
    for p,h in r['artifact_sha256'].items(): require(file_sha(p) == h, 'access artifact drift '+p)
    commands = {c['log']: c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']), 'duplicate access commands')
    def command(c):
        log = c['log']; require(log in commands and all(c[k] == commands[log][k] for k in ('argv','cwd','expected_exit')), 'unbound access result')
        require(log not in used, 'reused access result'); used.add(log)
        lines = Path(log).read_text().splitlines(); text = '\n'.join(lines)
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0, 'access process binding')
        require(c['expected_exit'] == 0 and lines[-1] == 'exit=0' and c['argv'][:2] == ['bash','-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'access exit/environment')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'access sanitizer failure')
        return text
    expected = set(itertools.product(('execution','tail'), OPERATIONS, ('native','vcs-dpi')))
    actual = {(c['boundary'],c['operation'],c['backend']) for c in r['results']}
    require(len(r['results']) == len(expected) and actual == expected, 'access result membership')
    for c in r['results']:
        text = command(c); op = c['operation']; dest = Path(c['destination']); cut = r['cuts'][c['boundary']]
        source = parent.parent/'scenario-1/native-capture'/f'cut-{cut}'
        args = shlex.split(c['argv'][2]); require(c['source'] == str(source), 'access source binding')
        values = [op, str(source), str(dest)]
        if c['backend'] == 'vcs-dpi': values = ['+'+k+'='+v for k,v in zip(('operation','source','destination'), values)]
        require(all(v in args for v in values) and str(out/('native' if c['backend'] == 'native' else 'simv')) in args, 'access runtime argv binding')
        initialized = int(op == 'context-resume-live')
        receipt = (f'THREAD_ACCESS operation={op} rejected=1 unchanged=1 retry=1 initialized={initialized}'
                   ' foreign_services=0 target_edges=0')
        require(receipt in text and (dest/'rejection.txt').read_text() == 'TSI access requires its live original thread\n', 'access rejection cause')
        partial = set(NAMES)-{'poll','bcd'}
        require(images(dest/'before',partial) == images(dest/'after',partial), 'access partial owner mutation')
        pristine = 'prepare' in op or 'commit' in op
        if not pristine:
            wanted = images(parent.parent/'scenario-1/native-capture'/f'cut-{min(cut+initialized,r["cuts"]["tail"])}')
            require(images(dest/'aggregate-before') == images(dest/'aggregate-after') == wanted, 'access aggregate mutation')
        if op in ('host-commit', 'syscall-commit'):
            prefix = op.split('-')[0]
            require(images(dest/(prefix+'-before'), partial) == images(dest/(prefix+'-after'), partial), 'auxiliary candidate mutation')
            names = set(NAMES)-({'wrapper'} if prefix == 'host' else {'outer','wrapper'})
            wanted = images(parent.parent/'scenario-1/native-capture'/f'cut-{cut if prefix == "host" else 6}', names)
            require(images(dest/(prefix+'-source'), names) == images(dest/(prefix+'-retry'), names) == wanted, 'auxiliary candidate retry')
        if op == 'polling-commit':
            names = set(NAMES)-{'poll','bcd','syscall','lifecycle','outer','wrapper'}
            require(images(dest/'ordinary-before', names) == images(dest/'ordinary-after', names), 'ordinary polling mutation')
            names = set(NAMES)-{'syscall','lifecycle','outer','wrapper'}
            require(images(dest/'ordinary-source', names) == images(dest/'ordinary-retry', names), 'ordinary polling candidate retry')
        continued = min(cut+int(op == 'context-resume-fresh')+2*initialized, r['cuts']['tail'])
        require(images(dest/'retry') == images(parent.parent/'scenario-1/native-capture'/f'cut-{continued}'), 'access creator retry differs from oracle')
    for name in ('native-build','vcs-build'):
        require(str(out/(name+'.log')) in commands, 'missing access build command')
        c = commands[str(out/(name+'.log'))]; command(c); args = shlex.split(c['argv'][2])
        require(any(str(out/'libfesvr-checkpoint.a') in token for token in args), 'access build omitted recipe archive')
        if name == 'vcs-build': require('/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs' in args and '-full64' in args, 'access VCS release')
    require(used == set(commands), 'unclassified access commands')
    return dict(status='passed', foreign_entries=len(expected), operations=len(OPERATIONS), boundaries=2,
                backends=2, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', type=Path, required=True); a = p.parse_args()
    path = a.summary.resolve(); result = audit(path); base = json.loads(path.read_text()); rejected = []
    for field in ('results','commands','source_inputs'):
        for kind in ('missing','duplicate'):
            changed = copy.deepcopy(base)
            if kind == 'missing': changed[field].pop(0)
            else: changed[field].append(copy.deepcopy(changed[field][0]))
            try: audit(path, changed)
            except FormatError: rejected.append(field+'-'+kind)
            else: raise AssertionError('incomplete access evidence admitted')
    print(json.dumps(dict(result, incomplete_evidence_rejections=rejected), indent=2))


if __name__ == '__main__': main()
