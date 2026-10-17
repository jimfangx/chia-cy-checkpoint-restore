"""Independent complete-owner/serial-boundary audit of production bridge imports."""
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
from tools.checkpoint_formats.tests.audit_tsi_context_image import canonical

BACKENDS = ('native', 'vcs-dpi')


def audit(path, report=None):
    path = path.resolve(); out = path.parent
    r = json.loads(path.read_text()) if report is None else report
    require(r['status'] == 'passed' and r['level1_verified'] is False and r['level2_verified'] is False, 'bridge scope')
    require(json.loads((out/'source-inputs.json').read_text()) == r['source_inputs'], 'bridge source membership')
    require(json.loads((out/'commands.json').read_text()) == r['commands'], 'bridge command membership')
    bindings = {b['path']:b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate bridge sources')
    for name in ('tsibridge.cc','tsibridge.h','tsi_bridge_state.h','tsi_context_image.h','firesim_tsi.h',
                 'tsi_bridge_context.cc','tsi_bridge_context_tb.sv','verify_tsi_bridge_context_vcs.py','audit_tsi_bridge_context.py'):
        require(any(p.endswith('/'+name) for p in bindings), 'missing bridge source '+name)
    for b in bindings.values(): require(file_sha(b['snapshot']) == b['sha256'], 'bridge source snapshot drift')
    if r.get('creator_worker_reserved'):
        require(any(p.endswith('/emul/driver_thread.h') for p in bindings), 'missing creator worker source')
    require({b['snapshot'] for b in bindings.values()} == {str(p) for p in (out/'sources').iterdir()}, 'bridge snapshots membership')
    binding = json.loads((out/'build-binding.json').read_text())
    require(binding['sources'] == {b['path']:b['sha256'] for b in r['source_inputs']} and
            binding['cxx'] == '/usr/bin/g++-13' and binding['vcs_home'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'bridge build binding')
    build = bytes.fromhex(file_sha(out/'build-binding.json'))
    require(r['build_sha256'] == build.hex() and (out/'build.sha256').read_bytes() == build, 'bridge build digest')
    parent = Path(r['context_summary']); require(file_sha(parent) == r['context_sha256'], 'bridge parent changed')
    parent_audit(parent)
    identity_path = Path(r['recipe_build_identity']); identity = json.loads(identity_path.read_text())
    require(binding['recipe_identity_sha256'] == file_sha(identity_path) == bindings[str(identity_path)]['sha256'] and
            identity['htif_lifecycle_provider_linked'], 'bridge provider recipe')
    library = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    require(str(library) in bindings and file_sha(library) == file_sha(out/'libfesvr-checkpoint.a') == bindings[str(library)]['sha256'], 'bridge provider archive')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'bridge artifact membership')
    for p, h in r['artifact_sha256'].items(): require(file_sha(p) == h, 'bridge artifact drift '+p)
    commands = {c['log']:c for c in r['commands']}; results = r['restores']+r['invalids']+r['specials']+r['faults']
    require(len(commands) == len(r['commands']) == len(results)+2 and len({c['log'] for c in results}) == len(results), 'bridge result membership')
    require(set(commands) == {c['log'] for c in results} | {str(out/'native-build.log'),str(out/'vcs-build.log')}, 'missing bridge results')
    used = set()
    def command(c):
        require(c['log'] in commands and all(c[k] == commands[c['log']][k] for k in ('argv','cwd','expected_exit')) and c['log'] not in used, 'bridge command binding')
        used.add(c['log']); text = Path(c['log']).read_text(); lines = text.splitlines()
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1] == 'exit=0' and c['expected_exit'] == 0, 'bridge native process')
        require(c['argv'][:2] == ['bash','-lc'] and 'source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'bridge native environment')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'bridge sanitizer')
        if c.get('backend') == 'vcs-dpi': require('BRIDGE_CONTEXT_VCS_ZERO_EDGES time=0 edges=0' in text, 'bridge VCS edge check')
        if r.get('creator_worker_reserved') and 'scenario' in c:
            require('BRIDGE_RESERVED_CREATOR same_thread=1 preparation_complete=1 target_edges=0' in text,
                    'missing reserved creator continuation')
        if 'scenario' in c:
            args = shlex.split(c['argv'][2]); native = c['backend'] == 'native'
            require(str(out/('native' if native else 'simv')) in args and all(
                (c[key] if native else '+'+flag+'='+c[key]) in args
                for key,flag in (('mode','mode'),('image','image_path'),('destination','destination'))), 'bridge runtime arguments')
        return text
    states = {}; cuts = {}; metadata = {}; plans = {}
    for i in range(8):
        folder = parent.parent/f'scenario-{i}'; plans[i] = (folder/'plan').read_text().splitlines()
        last = len(plans[i]); states[i] = [images(folder/'native-capture'/f'cut-{c}') for c in range(last+1)]
        phases = [s['syscall'][88] for s in states[i]]; active = phases.index(3) if 3 in phases else phases.index(1)
        cuts[i] = sorted({0,6,active,last}); metadata[i] = (folder/'native-capture/startup.metadata').read_bytes()
    require(r['cuts'] == {str(i):v for i,v in cuts.items()}, 'bridge cuts')
    wanted = {(i,c,b) for i,cs in cuts.items() for c in cs for b in BACKENDS}
    require(len(r['restores']) == len(wanted) and {(c['scenario'],c['cut'],c['backend']) for c in r['restores']} == wanted, 'bridge restores')
    boundaries = comparisons = words = 0
    for c in r['restores']:
        text = command(c); i,cut = c['scenario'],c['cut']; dest = Path(c['destination'])
        require('BRIDGE_CONTEXT_READBACK owners=17 context_entries=0 mmio=0 republish_rejections=3 target_edges=0' in text, 'bridge preedge receipt')
        expected = canonical(build, metadata[i], states[i][cut])
        require(Path(c['image']).read_bytes() == (dest/'readback.context').read_bytes() == expected, 'bridge complete preedge readback')
        control = (dest/'readback.control').read_bytes()
        require(struct.unpack('<2Q',control[-16:]) == (0,1), 'bridge wait/init/fast phase')
        stop = next((op for op in range(cut,len(plans[i])+1) if states[i][op]['lifecycle'][-8:] == struct.pack('<Q',1)), len(plans[i]))
        ops = [op for op in range(cut+1,stop+1) if not plans[i][op-1].startswith('SEND ')]
        require((dest/'boundaries.txt').read_text().splitlines() == list(map(str,ops)), 'bridge boundary membership')
        require({p.name for p in dest.glob('operation-*.context')} == {f'operation-{op}.context' for op in ops}, 'bridge owner readbacks missing')
        for op in ops:
            require((dest/f'operation-{op}.context').read_bytes() == canonical(build,metadata[i],states[i][op]), 'bridge first owner mismatch at operation '+str(op))
        packets = sum(len(plans[i][op-1].split())-1 for op in ops if plans[i][op-1].startswith('PACKET '))
        m = re.search(r'BRIDGE_CONTEXT_CONTINUED operations=(\d+) comparisons=(\d+) words=(\d+) exit=(-?\d+) startup_replays=0 target_edges=0',text)
        require(m and tuple(map(int,m.groups()[:3])) == (len(ops),17*len(ops),packets), 'bridge continuation receipt')
        # The owner stores normalized 32-bit result bits in an eight-byte word;
        # the production bridge exposes the provider's signed int return.
        require(int(m[4]) == struct.unpack('<i',states[i][-1]['outer'][-8:-4])[0], 'bridge exit differs')
        boundaries += len(ops); comparisons += 17*(len(ops)+1); words += packets
    invalid_names = {f'header-{o}' for o in range(0,48,8)} | {f'build-{o}' for o in range(32)} | {'metadata','trailing','metadata-length'}
    invalid_names |= {n+'-'+s for n in NAMES for s in ('missing','duplicate','identity','payload-truncated','payload-config','identity-length','payload-length')}
    invalid_names |= {n+'-order' for n in NAMES[:-1]}
    require(len(r['invalids']) == 2*len(invalid_names) and {(c['case'],c['backend']) for c in r['invalids']} == {(n,b) for n in invalid_names for b in BACKENDS}, 'bridge invalid membership')
    invalid_payloads = [(out/'invalid-images'/name).read_bytes() for name in invalid_names]
    require(len(set(invalid_payloads)) == len(invalid_names) and
            all(payload != (out/f'source-1-{cuts[1][2]}.context').read_bytes() for payload in invalid_payloads),
            'bridge malformed cases reused or unchanged')
    for c in r['invalids']:
        text = command(c)
        require(c['image'] == str(out/'invalid-images'/c['case']) and
                'BRIDGE_CONTEXT_REJECT unpublished=1 mmio=0 target_edges=0' in text and not list(Path(c['destination']).iterdir()), 'bridge invalid publication')
    require(len(r['specials']) == 8 and {(c['mode'],c['backend']) for c in r['specials']} == {(m,b) for m in ('atomic','foreign','guard-mask','guard-control') for b in BACKENDS}, 'bridge special membership')
    allocations = truncations = 0
    for c in r['specials']:
        text = command(c); dest = Path(c['destination'])
        require((dest/'readback.context').read_bytes() == Path(c['image']).read_bytes(), 'bridge special readback')
        if c['mode'] == 'atomic':
            m = re.search(r'BRIDGE_CONTEXT_ATOMIC truncations=(\d+) cross=2 allocations=(\d+) unpublished_on_failure=1 mmio=0 target_edges=0',text)
            require(m and int(m[1]) == (dest/'readback.control').stat().st_size and int(m[2]) > 0, 'bridge atomic receipt')
            truncations += int(m[1]); allocations += int(m[2])
        elif c['mode'] == 'foreign':
            require('BRIDGE_CONTEXT_FOREIGN rejected=1 creator_retry=1' in text and
                    'BRIDGE_CONTEXT_FOREIGN_RESTORED rejected=4 mmio=0 creator_retry=1' in text, 'bridge foreign guard')
        elif c['mode'] == 'guard-control': require('BRIDGE_CONTEXT_CONTROL_GUARD unpublished=1 creator_retry=1' in text, 'bridge control guard')
        else: require('BRIDGE_CONTEXT_LATE_GUARD unpublished=1 creator_retry=1' in text, 'bridge mask guard')
    expected_faults = json.loads(parent.read_text())['faults']
    require(len(r['faults']) == len(expected_faults) and
            {(c['scenario'],c['backend']) for c in r['faults']} ==
            {(c['scenario'],c['backend']) for c in expected_faults}, 'bridge semantic fault membership')
    for c in r['faults']:
        text = command(c); i,cut = c['scenario'],c['cut']; dest = Path(c['destination'])
        reference = next(f for f in expected_faults if (f['scenario'],f['backend']) == (i,c['backend']))
        require(c['cut'] == reference['cut'] and c['divergence'] == reference['divergence'] and
                text.count(c['divergence']) == 1 and 'BRIDGE_CONTEXT_CONTINUED' not in text, 'bridge first semantic divergence')
        altered = dict(states[i][cut]); altered['syscall'] = (parent.parent/f'scenario-{i}/native-capture'/f'cut-{cut}.fault').read_bytes()
        require(altered != states[i][cut] and Path(c['image']).read_bytes() ==
                (dest/'readback.context').read_bytes() == canonical(build,metadata[i],altered), 'bridge actual semantic mutation')
        first = int(re.search(r'operation=(\d+)',c['divergence'])[1])
        require(all(int(p.name.split('-')[1].split('.')[0]) < first for p in dest.glob('operation-*.context')), 'bridge acknowledged divergent boundary')
    for log in ('native-build.log','vcs-build.log'): command(commands[str(out/log)])
    require(used == set(commands), 'bridge unused command')
    return dict(status='passed',fresh_bridge_restores=len(r['restores']),complete_owner_comparisons=comparisons,
                serial_boundaries=boundaries,serial_words=words,invalid_processes=len(r['invalids']),
                control_truncations=truncations,allocation_failures=allocations,foreign_rejections=10,late_guards=4,
                first_divergences=len(r['faults']),
                level1_verified=False,level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary',type=Path,required=True); a=p.parse_args()
    result = audit(a.summary); r=json.loads(a.summary.read_text()); rejected=[]
    for field in ('restores','invalids','specials','faults','commands','source_inputs'):
        for kind in ('missing','duplicate'):
            bad=copy.deepcopy(r)
            if kind=='missing': bad[field].pop()
            else: bad[field].append(copy.deepcopy(bad[field][0]))
            try: audit(a.summary,bad)
            except (FormatError,KeyError,ValueError,AssertionError): rejected.append(field+'-'+kind)
            else: raise AssertionError('bridge evidence admitted '+field+'-'+kind)
    for index in range(len(r['source_inputs'])):
        bad=copy.deepcopy(r); bad['source_inputs'].pop(index)
        try: audit(a.summary,bad)
        except (FormatError,KeyError,ValueError,AssertionError): pass
        else: raise AssertionError('bridge source omission admitted')
    result.update(incomplete_evidence_rejections=rejected,individual_source_omission_rejections=len(r['source_inputs']))
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
