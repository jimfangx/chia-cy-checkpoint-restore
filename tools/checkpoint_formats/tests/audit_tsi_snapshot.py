"""Independent bytes, owner membership, native process and source handoff audit."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import itertools
import json
from pathlib import Path
import re
import shlex
import struct

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_tsi_context_group import images, audit as parent_audit

NAMES = ('poll', 'program', 'init', 'host', 'read', 'serial', 'loadmem-read', 'loadmem-queues',
         'bcd', 'terminal', 'identity', 'write', 'memread', 'syscall', 'outer', 'wrapper')
SCHEMAS = tuple('firesim.tsi.'+s+'.v1' for s in (
    'htif-poll', 'program-loader', 'init-accesses', 'host-control', 'serial-read', 'serial-queues',
    'loadmem-read', 'loadmem-queues', 'bcd', 'terminal.sealed', 'bcd-identity', 'memif-write',
    'memif-read', 'syscall-exit', 'host-execution', 'host-wrapper'))


def diagnostic(path):
    data = path.read_bytes(); pos = 8
    require(data[:8] == b'FSDIAG01', 'snapshot diagnostic format')
    def integer():
        nonlocal pos
        require(pos+8 <= len(data), 'truncated snapshot diagnostic')
        value, = struct.unpack_from('<Q', data, pos); pos += 8
        return value
    def blob():
        nonlocal pos
        count = integer(); require(count <= len(data)-pos, 'truncated snapshot record')
        value = data[pos:pos+count]; pos += count
        return value
    require(integer() == 1 and integer() == 16, 'snapshot diagnostic cut/size')
    result = []
    for _ in range(16): result.append((blob().decode(), blob().decode(), blob()))
    require(pos == len(data) and tuple(r[0] for r in result) == NAMES, 'snapshot diagnostic membership')
    return result


def audit(path, report=None):
    path = path.resolve(); out = path.parent
    r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and r['level1_verified'] is False and r['level2_verified'] is False, 'snapshot scope')
    # Bind the complete original list before expensive parent/image audits.
    # Merely requiring selected headers lets an omitted auxiliary dependency
    # retain its orphan snapshot and disappear from the claimed build inputs.
    require((out/'source-inputs.json').is_file() and
            json.loads((out/'source-inputs.json').read_text()) == r['source_inputs'],
            'snapshot source catalog membership')
    require({b['snapshot'] for b in r['source_inputs']} ==
            {str(p) for p in (out/'sources').iterdir() if p.is_file()}, 'snapshot source file membership')
    parent = Path(r['context_summary']); require(file_sha(parent) == r['context_sha256'], 'snapshot parent changed')
    parent_audit(parent)
    require(r['cuts'] == {'execution':6, 'tail':len((parent.parent/'scenario-1/plan').read_text().splitlines())}, 'snapshot cuts')
    bindings = {b['path']:b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate snapshot inputs')
    for name in ('tsi_snapshot_handoff.cc', 'tsi_snapshot_handoff_tb.sv', 'verify_tsi_snapshot_vcs.py',
                 'audit_tsi_snapshot.py', 'driver_boundary_diagnostic.cc', 'driver_boundary_diagnostic.h',
                 'simif_emul.cc', 'simif_emul.h', 'tsi_owner_view.h', 'tsi_context_group.h', 'firesim_tsi.cc'):
        require(any(p.endswith('/'+name) for p in bindings), 'missing snapshot source '+name)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'snapshot source drift')
    identity_path = r['recipe_build_identity']; require(identity_path in bindings, 'unbound snapshot recipe')
    require(file_sha(identity_path) == bindings[identity_path]['sha256'], 'snapshot recipe changed')
    identity = json.loads(Path(identity_path).read_text())
    require(identity['htif_lifecycle_provider_linked'] and identity['vcs_home'] == _toolchain.VCS_HOME, 'snapshot recipe provider')
    for p,h in identity['sources_sha256'].items():
        if p in bindings: require(bindings[p]['sha256'] == h, 'snapshot recipe/source mismatch')
    archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(str(archive) in bindings and file_sha(archive) == file_sha(out/'libfesvr-checkpoint.a'), 'snapshot provider mismatch')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'snapshot artifact membership')
    for p,h in r['artifact_sha256'].items(): require(file_sha(p) == h, 'snapshot artifact drift '+p)
    commands = {c['log']:c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']) == 6, 'snapshot native commands')
    def command(c):
        log = c['log']; require(log in commands and all(c[k] == commands[log][k] for k in ('argv','cwd','expected_exit')), 'unbound snapshot result')
        require(log not in used, 'reused snapshot command'); used.add(log)
        lines = Path(log).read_text().splitlines(); text = '\n'.join(lines)
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0, 'snapshot process binding')
        require(c['expected_exit'] == 0 and lines[-1] == 'exit=0' and c['argv'][:2] == ['bash','-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'snapshot environment/exit')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'snapshot sanitizer failure')
        return text
    expected = set(itertools.product(('execution','tail'), ('native','vcs-dpi')))
    require(len(r['results']) == 4 and {(c['boundary'],c['backend']) for c in r['results']} == expected, 'snapshot result membership')
    allocation_failures = 0
    for c in r['results']:
        text = command(c); dest = Path(c['destination']); source = parent.parent/'scenario-1/native-capture'/f'cut-{r["cuts"][c["boundary"]]}'
        require(c['source'] == str(source) and dest == out/(c['boundary']+'-'+c['backend']), 'snapshot input/output binding')
        argv = shlex.split(c['argv'][2]); binary = out/('native' if c['backend'] == 'native' else 'simv')
        require(str(binary) in argv and (str(source) if c['backend'] == 'native' else '+source='+str(source)) in argv and
                (str(dest) if c['backend'] == 'native' else '+destination='+str(dest)) in argv, 'snapshot runtime argv')
        match = re.search(r'SNAPSHOT_HANDOFF owners=16 readbacks=32 raw_rejections=16 invalid_rejections=32 load_rejections=32 allocation_failures=(\d+) creator_destroyed=1 context_entries=0 target_edges=0', text)
        require(match is not None and int(match[1]) > 0, 'missing snapshot handoff receipt'); allocation_failures += int(match[1])
        if c['backend'] == 'vcs-dpi': require('SNAPSHOT_VCS_ZERO_EDGES time=0 edges=0' in text, 'snapshot VCS edge check missing')
        wanted = images(source); wanted.pop('lifecycle')
        def words(*values): return struct.pack('<'+'Q'*len(values), *values)
        def config(kind,*values): return words(0x3154504b43474457,1,kind,len(values),*values)
        child = config(20,1024,4,2,2)+words(0,0,0,0)
        wanted['memread'] = config(30,1,8,1024,1048576)+words(0,0,0,0,len(child))+child
        for label in ('original','parked','destroyed'):
            require(images(dest/label, NAMES) == wanted, 'snapshot readback differs from independent owner source')
        a, b = diagnostic(dest/'parked.diag'), diagnostic(dest/'destroyed.diag')
        require(a == b and tuple(row[1] for row in a) == SCHEMAS and
                all(payload == wanted[name] for name,schema,payload in a), 'snapshot diagnostic drift')
    for name in ('native-build','vcs-build'):
        c = commands.get(str(out/(name+'.log'))); require(c is not None, 'missing snapshot build'); command(c)
        args = shlex.split(c['argv'][2]); require(any(str(out/'libfesvr-checkpoint.a') in s for s in args), 'snapshot archive absent')
        if name == 'vcs-build': require(_toolchain.VCS in args and '-full64' in args, 'snapshot VCS release')
    require(used == set(commands), 'unclassified snapshot command')
    return dict(status='passed', processes=4, owners=16, owner_readbacks=128, raw_rejections=64,
                invalid_rejections=128, load_rejections=128, allocation_failures=allocation_failures,
                level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary',type=Path,required=True); a = p.parse_args()
    result = audit(a.summary); original = json.loads(a.summary.read_text()); rejected = []
    for field in ('results','commands','source_inputs'):
        for kind in ('missing','duplicate'):
            changed = copy.deepcopy(original)
            if kind == 'missing': changed[field].pop()
            else: changed[field].append(copy.deepcopy(changed[field][0]))
            try: audit(a.summary, changed)
            except FormatError: rejected.append(field+'-'+kind)
            else: raise RuntimeError('incomplete snapshot evidence accepted')
    for index in range(len(original['source_inputs'])):
        changed = copy.deepcopy(original); changed['source_inputs'].pop(index)
        try: audit(a.summary, changed)
        except FormatError: pass
        else: raise RuntimeError('omitted snapshot dependency accepted')
    print(json.dumps(dict(result, incomplete_evidence_rejections=rejected,
                         individual_source_omission_rejections=len(original['source_inputs'])), indent=2))


if __name__ == '__main__': main()
