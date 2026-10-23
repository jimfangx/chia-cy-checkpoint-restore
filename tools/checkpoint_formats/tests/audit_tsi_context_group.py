"""Independent audit of actual wrapper/context continuation and missing evidence.

Uses retained, separately executed fifteen-owner parent bytes, without importing
production adapters or the context suite's scenario/continuation generator.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import json
from pathlib import Path
import re
import shlex
import struct

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha

NAMES = ('poll', 'program', 'init', 'host', 'read', 'serial', 'loadmem-read', 'loadmem-queues',
         'bcd', 'terminal', 'identity', 'write', 'syscall', 'lifecycle', 'outer', 'wrapper')
BACKENDS = ('native', 'vcs-dpi')
GUARDS = ('wrapper', 'peer', 'exit', 'stop', 'mask', 'pending')
RESOURCES = ('thread', 'allocation', 'resume-mask', 'resume-pending')


def words(*values):
    return struct.pack('<'+'Q'*len(values), *values)


def wrapper(phase):
    return words(0x3154504b43474457, 1, 36, 1, 1, phase)


def images(prefix, names=NAMES):
    return {name: Path(str(prefix)+'.'+name).read_bytes() for name in names}


def audit(path, report=None):
    path = path.resolve(); r = json.loads(path.read_text()) if report is None else report; out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'context scope')
    bindings = {b['path']: b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate context sources')
    for suffix in ('tsi_context_group.h', 'tsi_host_wrapper.h', 'owned_fesvr_tsi.cc', 'owned_context.cc', 'firesim_tsi.cc', 'tsi_context_group_fesvr.cc'):
        require(any(p.endswith('/'+suffix) for p in bindings), 'missing context source '+suffix)
    parent = Path(r['host_summary']); require(file_sha(parent) == r['host_sha256'], 'changed host parent')
    previous = json.loads(parent.read_text()); require(previous['status'] == 'passed', 'parent incomplete')
    polling = Path(previous['polling_summary']); require(file_sha(polling) == previous['polling_sha256'], 'changed polling parent')
    scenarios = {}; total_cuts = 0
    for i in range(8):
        lower = polling.parent/f'scenario-{i}'; count = len((lower/'plan').read_text().splitlines())+1
        states = []
        for cut in range(count):
            a = images(parent.parent/f'scenario-{i}/native-capture'/f'cut-{cut}', NAMES[:-1])
            b = images(parent.parent/f'scenario-{i}/vcs-dpi-capture'/f'cut-{cut}', NAMES[:-1])
            require(a == b, 'parent backend source disagreement')
            states.append(dict(a, wrapper=wrapper(1)))
        returned = images(parent.parent/f'scenario-{i}/native-capture/live-returned', NAMES[:-1])
        require(returned['outer'][48:56] == words(4) and returned['lifecycle'][72:80] == words(1), 'parent not returned/stopped')
        packet = ([1, 0x20004000, 0, 1, 0, 0x80002000, 0] if i >= 4 else [])+[1, 0x80002008, 0, 1, 0, 1, 0]
        serial = returned['serial'][:64]+words(len(packet), *packet, 0)
        states.append(dict(returned, serial=serial, wrapper=wrapper(2)))
        final = dict(returned, wrapper=wrapper(2)); states.extend([final, final])
        raw = int.from_bytes(returned['outer'][56:64], 'little'); code = raw if raw < 0x80000000 else raw-0x100000000
        scenarios[i] = states, code; total_cuts += len(states)
    expected = {(i, p, b, c) for i, (states, _) in scenarios.items() for p in BACKENDS for b in BACKENDS for c in range(len(states))}
    require(len(r['restores']) == len(expected) and {(c['scenario'], c['producer'], c['backend'], c['cut']) for c in r['restores']} == expected, 'restore membership')
    require(len(r['invalids']) == 102 and {(Path(c['destination']).name, c['backend']) for c in r['invalids']} ==
            {(f'invalid-{n}-{b}', b) for n in range(51) for b in BACKENDS}, 'invalid membership')
    require(len(r['guards']) == 12 and {(c['mode'], c['backend']) for c in r['guards']} == {('guard-'+g, b) for g in GUARDS for b in BACKENDS}, 'guard membership')
    require(len(r['resources']) == 8 and {(c['mode'], c['backend']) for c in r['resources']} == {(g, b) for g in RESOURCES for b in BACKENDS}, 'resource membership')
    require(len(r['faults']) == 8 and {(c['scenario'], c['backend']) for c in r['faults']} == {(i, b) for i in (1, 3, 5, 7) for b in BACKENDS}, 'fault membership')
    count = len(expected)+16+2+102+12+8+8+2
    commands = {c['log']: c for c in r['commands']}
    require(len(commands) == len(r['commands']) == count, 'native command membership')
    require(r['recipe_build_identity'], 'context suite needs current exact recipe binding')
    identity_path = Path(r['recipe_build_identity']); require(str(identity_path) in bindings, 'missing recipe identity binding')
    identity = json.loads(identity_path.read_text()); require(identity['htif_lifecycle_provider_linked'], 'missing exact provider')
    actual_archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(file_sha(actual_archive) == file_sha(out/'libfesvr-checkpoint.a'), 'provider archive mismatch')
    for p, h in identity['sources_sha256'].items():
        if p in bindings: require(bindings[p]['sha256'] == h, 'native context/recipe source mismatch')
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'changed context source snapshot')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'artifact membership')
    for p, h in r['artifact_sha256'].items(): require(file_sha(p) == h, 'changed context artifact')
    used = set()
    def command(c):
        log = c['log']; require(log in commands and c['argv'] == commands[log]['argv'] and c['cwd'] == commands[log]['cwd'], 'unbound native result'); used.add(log)
        lines = Path(log).read_text().splitlines(); text = '\n'.join(lines)
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0, 'actual native process binding')
        require(lines[-1] == 'exit=0' and c['argv'][:2] == ['bash', '-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'native exit/environment')
        if '/bin/vcs ' in c['argv'][2]: require(_toolchain.VCS + ' -full64' in c['argv'][2], 'VCS release')
        require(not any(x in text for x in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'sanitizer error')
        return text
    comparisons = operations = 0
    for i, (states, code) in scenarios.items():
        for b in BACKENDS:
            dest = out/f'scenario-{i}'/(b+'-capture'); text = command(commands[str(dest.with_suffix('.log'))])
            require('fresh=0' in text, 'source is not production coroutine')
            for cut, state in enumerate(states): require(images(dest/f'cut-{cut}') == state, 'source differs from independent parent')
    for c in r['restores']:
        states, code = scenarios[c['scenario']]; cut = c['cut']; dest = Path(c['destination']); text = command(c)
        require(images(dest/'preedge') == states[cut], 'zero-entry complete state differs')
        require((dest/'continuation.bin').read_bytes() == b''.join(s[n] for s in states[cut+1:] for n in NAMES), 'fresh coroutine continuation differs')
        require('COMPLETE_CONTEXT_READBACK owners=16 services=0 target_edges=0 context_entries=0' in text and f'operations={len(states)-cut-1}' in text and
                'tail_ticks=3 startup_replays=0' in text and f'return={code}' in text, 'context continuation receipt')
        source = out/f'scenario-{c["scenario"]}'/(c['producer']+'-capture')/f'cut-{cut}'
        args = shlex.split(c['argv'][2]); require(str(source) in args or '+source='+str(source) in args, 'cross-backend source binding')
        comparisons += 16*(len(states)-cut); operations += len(states)-cut-1
    for c in r['invalids']:
        require('REJECTED owners=16 unpublished=1 context_entries=0 target_edges=0' in command(c) and not list(Path(c['destination']).glob('preedge.*')), 'invalid context publication')
    for c in r['guards']: require('CONTEXT_LATE_GUARD '+c['mode']+' unpublished=1 services=0 target_edges=0 context_entries=0' in command(c), 'late guard receipt')
    for c in r['resources']:
        expected_receipt = ('FOREIGN_CREATOR rejected=1 unpublished=1 context_entries=0 target_edges=0' if c['mode'] == 'thread' else
                            'CONTEXT_ALLOCATION stack_bytes=1048576 rejected=1 unchanged=1 retry=1' if c['mode'] == 'allocation' else
                            'CONTEXT_RESUME_GUARD '+c['mode']+' boundaries=2 unchanged=1 services=0 target_edges=0')
        require(expected_receipt in command(c), 'context resource receipt')
    for c in r['faults']:
        text = command(c); d = c['divergence']; require(d.startswith('FIRST_DIVERGENCE operation=') and d in text and 'acknowledged=0 fresh_context=1' in d, 'first divergent boundary')
    for b in BACKENDS:
        dest = out/('atomic-'+b); command(commands[str(dest.with_suffix('.log'))])
        m = re.fullmatch(r'malformed=(\d+) membership=64 cross=2 allocation_failures=(\d+) unchanged_on_failure=1 context_entries=0\n', (dest/'atomic.txt').read_text())
        require(m and int(m[1]) > 1800 and int(m[2]) > 40, 'atomic format/membership/allocation scope')
    for name in ('native-build', 'vcs-build'): command(commands[str(out/(name+'.log'))])
    require(used == set(commands), 'unclassified native commands')
    return dict(status='passed', cuts=total_cuts, fresh_restores=len(expected), complete_owner_comparisons=comparisons, host_operations=operations,
                actual_source_coroutines=16, invalid_processes=102, late_guards=12, resource_checks=8, first_divergences=8, level1_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', type=Path, required=True); a = p.parse_args(); path = a.summary.resolve()
    result = audit(path); base = json.loads(path.read_text()); rejected = []
    for field in ('restores', 'invalids', 'guards', 'resources', 'faults', 'commands', 'source_inputs'):
        for kind in ('missing', 'duplicate'):
            changed = copy.deepcopy(base)
            if kind == 'missing':
                if field == 'source_inputs': changed[field] = [b for b in changed[field] if not b['path'].endswith('/tsi_context_group.h')]
                else: changed[field].pop(0)
            else: changed[field].append(copy.deepcopy(changed[field][0]))
            try: audit(path, changed)
            except (FormatError, KeyError, ValueError): rejected.append(field+'-'+kind)
            else: raise RuntimeError('incomplete context evidence admitted '+field+'-'+kind)
    result.update(summary=str(path), summary_sha256=file_sha(path), rejected_incomplete_evidence=rejected)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
