"""Independent bound-image bytes, complete-owner continuation and receipt audit."""
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
from tools.checkpoint_formats.tests.audit_tsi_context_group import audit as parent_audit, images, NAMES

BACKENDS = ('native', 'vcs-dpi')


def canonical(build, metadata, owners):
    def word(n): return struct.pack('<Q', n)
    def blob(data): return word(len(data))+data
    result = struct.pack('<6Q', 0x3154504b43474457, 1, 37, 2, 1, 16)+build+blob(metadata)
    for name in NAMES: result += blob(name.encode())+blob(owners[name])
    return result


def audit(path, report=None):
    path = path.resolve(); out = path.parent
    r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and r['level1_verified'] is False and r['level2_verified'] is False, 'image scope')
    require(json.loads((out/'source-inputs.json').read_text()) == r['source_inputs'], 'image source membership')
    require(json.loads((out/'commands.json').read_text()) == r['commands'], 'image command membership')
    require({b['snapshot'] for b in r['source_inputs']} ==
            {str(p) for p in (out/'sources').iterdir() if p.is_file()}, 'image source file membership')
    commands = {c['log']:c for c in r['commands']}
    results = r['captures']+r['restores']+r['invalids']+r['specials']+r['faults']
    require(len(commands) == len(r['commands']) == len(results)+2 and
            len({c['log'] for c in results}) == len(results), 'image result membership')
    require(set(commands) == {c['log'] for c in results} | {str(out/'native-build.log'),str(out/'vcs-build.log')}, 'missing image result')
    bindings = {b['path']:b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate image sources')
    for name in ('tsi_context_image.h', 'tsi_context_group.h', 'tsi_host_group.h', 'firesim_tsi.cc',
                 'tsi_context_image.cc', 'tsi_context_image_tb.sv', 'verify_tsi_context_image_vcs.py',
                 'audit_tsi_context_image.py', 'tsi_context_group_fesvr.cc', 'tsi_terminal_allocations.cc'):
        require(any(p.endswith('/'+name) for p in bindings), 'missing image source '+name)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'image source snapshot drift')
    parent = Path(r['context_summary']); require(file_sha(parent) == r['context_sha256'], 'image parent changed')
    parent_audit(parent)
    p = json.loads(parent.read_text())
    identity_path = r['recipe_build_identity']; require(identity_path in bindings, 'image recipe unbound')
    identity = json.loads(Path(identity_path).read_text())
    require(file_sha(identity_path) == bindings[identity_path]['sha256'] and identity['htif_lifecycle_provider_linked'], 'image recipe changed')
    library = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(str(library) in bindings and file_sha(library) == file_sha(out/'libfesvr-checkpoint.a'), 'image provider mismatch')
    for name, digest in identity['sources_sha256'].items():
        if name in bindings: require(bindings[name]['sha256'] == digest, 'image recipe input mismatch')
    binding = json.loads((out/'build-binding.json').read_text())
    require(binding['recipe_identity_sha256'] == file_sha(identity_path) and
            binding['sources'] == {b['path']:b['sha256'] for b in r['source_inputs']} and
            binding['cxx'] == _toolchain.CXX and binding['vcs_home'] == _toolchain.VCS_HOME, 'image build binding')
    build = bytes.fromhex(file_sha(out/'build-binding.json'))
    require(build.hex() == r['build_sha256'] and (out/'build.sha256').read_bytes() == build, 'image build digest')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'image artifact membership')
    for name, digest in r['artifact_sha256'].items(): require(file_sha(name) == digest, 'image artifact drift '+name)
    used = set()
    def command(c):
        require(c['log'] in commands and all(c[k] == commands[c['log']][k] for k in ('argv','cwd','expected_exit')),
                'image command binding')
        require(c['log'] not in used, 'reused image result'); used.add(c['log'])
        lines = Path(c['log']).read_text().splitlines(); text = '\n'.join(lines)
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0 and lines[-1] == 'exit=0', 'image native process')
        require(c['expected_exit'] == 0 and c['argv'][:2] == ['bash','-lc'] and
                'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'image native environment')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'image sanitizer failure')
        if c.get('backend') == 'vcs-dpi': require('CONTEXT_IMAGE_VCS_ZERO_EDGES time=0 edges=0' in text, 'image VCS edge check')
        if 'scenario' in c:
            args = shlex.split(c['argv'][2]); native = c['backend'] == 'native'
            require(str(out/('native' if native else 'simv')) in args and
                    (c['image'] if native else '+image_path='+c['image']) in args and
                    (c['destination'] if native else '+destination='+c['destination']) in args and
                    (c['source'] if native else '+source='+c['source']) in args and
                    (c['mode'] if native else '+mode='+c['mode']) in args, 'image runtime arguments')
        return text
    states = {}; cuts = {}
    for i in range(8):
        folder = parent.parent/f'scenario-{i}'; last = len((folder/'plan').read_text().splitlines())
        states[i] = [images(folder/'native-capture'/f'cut-{c}') for c in range(last+1)]
        phases = [s['syscall'][88] for s in states[i]]
        active = phases.index(3) if 3 in phases else phases.index(1)
        cuts[i] = sorted({0, 6, active, last})
    require(r['cuts'] == {str(i):c for i,c in cuts.items()}, 'image cuts')
    wanted = {(i,c,b) for i, selected in cuts.items() for c in selected for b in BACKENDS}
    require(len(r['captures']) == len(wanted) and {(c['scenario'],c['cut'],c['backend']) for c in r['captures']} == wanted, 'image captures')
    captures = {}
    for c in r['captures']:
        text = command(c); i,cut,b = c['scenario'],c['cut'],c['backend']; dest = Path(c['destination'])
        require(f'CONTEXT_IMAGE_CAPTURE owners=16 live=1 cut={cut} target_edges=0' in text, 'image live source missing')
        require(images(dest/'source') == states[i][cut], 'image source oracle mismatch')
        metadata = (parent.parent/f'scenario-{i}/native-capture/startup.metadata').read_bytes()
        require(Path(c['image']).read_bytes() == canonical(build, metadata, states[i][cut]), 'image canonical bytes/owners mismatch')
        captures[i,cut,b] = c
    wanted = {(i,c,p,b) for i,selected in cuts.items() for c in selected for p in BACKENDS for b in BACKENDS}
    require(len(r['restores']) == len(wanted) and {(c['scenario'],c['cut'],c['producer'],c['backend']) for c in r['restores']} == wanted, 'image fresh restores')
    comparisons = operations = 0
    def continuation(c):
        nonlocal comparisons, operations
        text = command(c); i,cut = c['scenario'],c['cut']; dest = Path(c['destination'])
        require('CONTEXT_IMAGE_READBACK owners=16 services=0 context_entries=0 target_edges=0 republish_rejections=2' in text, 'image preedge receipt')
        require(images(dest/'preedge') == states[i][cut], 'image complete preedge mismatch')
        require((dest/'continuation.bin').read_bytes() == b''.join(s[n] for s in states[i][cut+1:] for n in NAMES), 'image continuation oracle mismatch')
        count = len(states[i])-cut-1
        require(f'CONTEXT_IMAGE_CONTINUED operations={count} owners=16 startup_replays=0 tail_ticks=3' in text, 'image continuation missing')
        comparisons += 16*(count+1); operations += count
        return text
    for c in r['restores']:
        require(c['image'] == captures[c['scenario'],c['cut'],c['producer']]['image'], 'image fresh source binding')
        continuation(c)
    invalid_names = {f'header-{o}' for o in range(0,48,8)} | {f'build-{o}' for o in range(32)} | {'metadata','trailing','metadata-length'}
    invalid_names |= {n+'-'+s for n in NAMES for s in ('missing','duplicate','identity','payload-truncated','payload-config','identity-length','payload-length')}
    invalid_names |= {n+'-order' for n in NAMES[:-1]}
    require(len(r['invalids']) == 2*len(invalid_names) and {(c['case'],c['backend']) for c in r['invalids']} ==
            {(n,b) for n in invalid_names for b in BACKENDS}, 'image invalid membership')
    # Verify each external malformed file is a distinct, actually changed
    # canonical image; identity/build/record cases cannot reuse one bad file.
    invalid_payloads = {n:(out/'invalid-images'/n).read_bytes() for n in invalid_names}
    require(len(set(invalid_payloads.values())) == len(invalid_payloads), 'reused malformed image')
    for c in r['invalids']:
        text = command(c)
        require(c['image'] == str(out/'invalid-images'/c['case']) and
                'CONTEXT_IMAGE_REJECT unpublished=1 context_entries=0 target_edges=0' in text and
                not list(Path(c['destination']).glob('preedge.*')), 'image invalid publication')
    require(len(r['specials']) == 6 and {(c['mode'],c['backend']) for c in r['specials']} ==
            {(m,b) for m in ('atomic','foreign','guard-mask') for b in BACKENDS}, 'image special membership')
    allocation_failures = truncations = 0
    for c in r['specials']:
        if c['mode'] == 'atomic':
            text = command(c)
            m = re.search(r'CONTEXT_IMAGE_ATOMIC truncations=(\d+) allocation_failures=(\d+) unchanged_on_failure=1 owners=16 context_entries=0 target_edges=0', text)
            require(m and int(m[1]) == Path(c['image']).stat().st_size and int(m[2]) > 40, 'image atomic coverage')
            require(images(Path(c['destination'])/'preedge') == states[c['scenario']][c['cut']], 'image atomic readback')
            truncations += int(m[1]); allocation_failures += int(m[2])
        else:
            text = continuation(c)
            require(('CONTEXT_IMAGE_FOREIGN rejected=4 creator_retry=1' if c['mode'] == 'foreign' else
                     'CONTEXT_IMAGE_LATE_GUARD unpublished=1 creator_retry=1') in text, 'image guard missing')
    expected_faults = {(f['scenario'],f['backend'],f['cut'],f['divergence']) for f in p['faults']}
    require(len(r['faults']) == 8 and {(f['scenario'],f['backend'],f['cut'],f['divergence']) for f in r['faults']} == expected_faults, 'image fault membership')
    for c in r['faults']:
        text = command(c); require(c['divergence'] in text and 'CONTEXT_IMAGE_CONTINUED' not in text, 'image first divergence')
        require(images(Path(c['destination'])/'preedge') == states[c['scenario']][c['cut']], 'image prefault readback')
    for name in ('native-build','vcs-build'):
        c = commands[str(out/(name+'.log'))]; command(c); args = shlex.split(c['argv'][2])
        require(any(str(out/'libfesvr-checkpoint.a') in s for s in args), 'image build provider missing')
        if name == 'native-build': require('-fsanitize=address,undefined' in args, 'image sanitizer build missing')
        else: require(_toolchain.VCS in args and '-full64' in args, 'image VCS release')
    require(used == set(commands), 'unclassified image commands')
    return dict(status='passed', captures=len(r['captures']), fresh_restores=len(r['restores']),
                complete_owner_comparisons=comparisons, host_operations=operations, invalid_processes=len(r['invalids']),
                byte_truncations=truncations, allocation_failures=allocation_failures, first_divergences=8,
                foreign_rejections=8, late_guards=2, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary',type=Path,required=True); a = p.parse_args()
    result = audit(a.summary); original = json.loads(a.summary.read_text()); rejected = []
    for field in ('captures','restores','invalids','specials','faults','commands','source_inputs'):
        for kind in ('missing','duplicate'):
            changed = copy.deepcopy(original)
            if kind == 'missing': changed[field].pop()
            else: changed[field].append(copy.deepcopy(changed[field][0]))
            try: audit(a.summary, changed)
            except FormatError: rejected.append(field+'-'+kind)
            else: raise RuntimeError('incomplete image evidence accepted')
    for index in range(len(original['source_inputs'])):
        changed = copy.deepcopy(original); changed['source_inputs'].pop(index)
        try: audit(a.summary, changed)
        except FormatError: pass
        else: raise RuntimeError('omitted image dependency accepted')
    print(json.dumps(dict(result, incomplete_evidence_rejections=rejected,
                         individual_source_omission_rejections=len(original['source_inputs'])), indent=2))


if __name__ == '__main__': main()
