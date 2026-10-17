"""Fresh creator-side bound TSI images in native C++ and zero-edge VCS.

Host-component evidence only; complete simulator/CPU admission remains disabled.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.audit_tsi_context_group import audit as parent_audit, images, NAMES, words

BACKENDS = ('native', 'vcs-dpi')


def encode(build, metadata, owners):
    def blob(data): return words(len(data))+data
    return (words(0x3154504b43474457, 1, 37, 2, 1, 16)+build+blob(metadata)+
            b''.join(blob(name.encode())+blob(payload) for name, payload in owners.items()))


def malformed(build, metadata, owners):
    good = encode(build, metadata, owners)
    result = {}
    for offset in range(0, 48, 8):
        bad = bytearray(good); bad[offset] ^= 1; result[f'header-{offset}'] = bytes(bad)
    for offset in range(32):
        bad = bytearray(good); bad[48+offset] ^= 1; result[f'build-{offset}'] = bytes(bad)
    result['metadata'] = encode(build, metadata[:-1]+bytes([metadata[-1]^1]), owners)
    result['trailing'] = good+b'\0'
    result['metadata-length'] = good[:80]+words(2**64-1)+good[88:]
    records = []; at = 88+len(metadata)
    for name, payload in owners.items():
        size = 8+len(name)+8+len(payload); records.append((at, at+size, at+8+len(name)))
        at += size
    for i, (name, payload) in enumerate(owners.items()):
        first, end, length = records[i]
        result[name+'-missing'] = good[:first]+good[end:]
        result[name+'-duplicate'] = good[:end]+good[first:end]+good[end:]
        bad = bytearray(good); bad[first+8] ^= 1; result[name+'-identity'] = bytes(bad)
        other = dict(owners); other[name] = payload[:-1]
        result[name+'-payload-truncated'] = encode(build, metadata, other)
        other = dict(owners); b = bytearray(payload); b[16] ^= 1; other[name] = bytes(b)
        result[name+'-payload-config'] = encode(build, metadata, other)
        result[name+'-identity-length'] = good[:first]+words(2**64-1)+good[first+8:]
        result[name+'-payload-length'] = good[:length]+words(2**64-1)+good[length+8:]
        if i < len(records)-1:
            _, next_end, _ = records[i+1]
            result[name+'-order'] = good[:first]+good[end:next_end]+good[first:end]+good[next_end:]
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--context-summary', type=Path, required=True)
    p.add_argument('--recipe-build-identity', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    parent = a.context_summary.resolve(); parent_audit(parent)
    r = json.loads(parent.read_text()); host = json.loads(Path(r['host_summary']).read_text())
    polling = Path(host['polling_summary']).parent
    identity_path = a.recipe_build_identity.resolve(); identity = json.loads(identity_path.read_text())
    require(identity['htif_lifecycle_provider_linked'], 'need actual recipe provider')
    for f, h in identity['sources_sha256'].items(): require(file_sha(f) == h, 'changed recipe input '+f)
    archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    source = TESTS/'tsi_context_image.cc'; sv = TESTS/'tsi_context_image_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    inputs = [Path(__file__), TESTS/'audit_tsi_context_image.py', TESTS/'audit_tsi_context_group.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', sv, *sources, parent, identity_path,
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', archive, archive.with_suffix('.json'),
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTS.glob('tsi*.cc')), *sorted(TESTS.glob('tsi*.h'))]
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve())); (out/'sources').mkdir()
    bindings = []
    for f in dict.fromkeys(inputs):
        digest = file_sha(f); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    (out/'source-inputs.json').write_text(json.dumps(bindings, indent=2)+'\n')
    build_binding = dict(recipe_identity_sha256=file_sha(identity_path),
                         sources={b['path']:b['sha256'] for b in bindings},
                         cxx=os.environ['CXX'], vcs_home=os.environ['VCS_HOME'], language='c++17')
    (out/'build-binding.json').write_text(json.dumps(build_binding, sort_keys=True, indent=2)+'\n')
    build = bytes.fromhex(file_sha(out/'build-binding.json')); (out/'build.sha256').write_bytes(build)
    shutil.copyfile(archive, out/'libfesvr-checkpoint.a'); library = out/'libfesvr-checkpoint.a'
    commands = []
    def execute(argv, log):
        log.parent.mkdir(parents=True, exist_ok=True)
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out)
        return dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log), expected_exit=0)
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    commands.append(execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-o', out/'native'], out/'native-build.log'))
    commands.append(execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_context_image_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_CONTEXT_IMAGE_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o', out/'simv', sv, *sources], out/'vcs-build.log'))
    def invoke(i, backend, mode, cut, dest, image):
        scenario = parent.parent/f'scenario-{i}'; folder = polling/f'scenario-{i}'
        reference = scenario/'native-capture'/f'cut-{cut}'
        values = list(map(str, [mode, polling/'polling.elf', folder/('flush.input' if i >= 4 else 'input'),
                      scenario/'native-capture/startup.metadata', reference, scenario/'plan', dest, image, out/'build.sha256']))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k,v in zip(('mode','elf','terminal','metadata','source','plan','destination','image_path','build_path'),values)]]
        return dict(execute(argv, Path(str(dest)+'.log')), scenario=i, backend=backend, mode=mode,
                    cut=cut, destination=str(dest), image=str(image), source=str(reference))
    cuts = {}
    for i in range(8):
        folder = parent.parent/f'scenario-{i}'; last = len((folder/'plan').read_text().splitlines())
        phases = [images(folder/'native-capture'/f'cut-{c}')['syscall'][88] for c in range(last+1)]
        active = phases.index(3) if 3 in phases else phases.index(1)
        cuts[i] = sorted({0, 6, active, last})
    captures = []
    for i, selected in cuts.items():
        for cut in selected:
            for backend in BACKENDS:
                dest = out/f'scenario-{i}'/f'capture-{backend}-{cut}'
                captures.append(invoke(i, backend, 'capture', cut, dest, dest/'context.image'))
    commands.extend(captures)
    jobs = [(c, backend) for c in captures for backend in BACKENDS]
    def restore(job):
        c, backend = job; dest = out/f'scenario-{c["scenario"]}'/f'restore-{c["backend"]}-{backend}-{c["cut"]}'
        return dict(invoke(c['scenario'], backend, 'restore', c['cut'], dest, Path(c['image'])), producer=c['backend'])
    with ThreadPoolExecutor(max_workers=4) as pool: restores = list(pool.map(restore, jobs))
    commands.extend(restores)
    chosen = next(c for c in captures if c['scenario'] == 1 and c['cut'] > 6 and c['backend'] == 'native' and
                  c['cut'] != cuts[1][-1])
    metadata = (parent.parent/'scenario-1/native-capture/startup.metadata').read_bytes()
    invalid_dir = out/'invalid-images'; invalid_dir.mkdir()
    bad_images = malformed(build, metadata, images(Path(chosen['source'])))
    for name, image in bad_images.items(): (invalid_dir/name).write_bytes(image)
    def invalid(job):
        name, backend = job
        return dict(invoke(1, backend, 'invalid', chosen['cut'], out/f'invalid-{name}-{backend}', invalid_dir/name), case=name)
    with ThreadPoolExecutor(max_workers=4) as pool:
        invalids = list(pool.map(invalid, [(name,b) for name in bad_images for b in BACKENDS]))
    commands.extend(invalids)
    specials = []
    for backend in BACKENDS:
        for mode in ('atomic', 'foreign', 'guard-mask'):
            specials.append(invoke(1, backend, mode, chosen['cut'], out/(mode+'-'+backend), Path(chosen['image'])))
    commands.extend(specials)
    faults = []
    for f in r['faults']:
        c = next(c for c in captures if c['scenario'] == f['scenario'] and c['cut'] == f['cut'] and c['backend'] == 'native')
        faults.append(dict(invoke(f['scenario'], f['backend'], 'corrupt', f['cut'],
                                 out/f'fault-{f["scenario"]}-{f["backend"]}', Path(c['image'])), divergence=f['divergence']))
    commands.extend(faults)
    (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'source changed during image execution '+b['path'])
    report = dict(status='passed', scope='bound restricted TSI creator-side images; complete CPU restore pending',
                  context_summary=str(parent), context_sha256=file_sha(parent), recipe_build_identity=str(identity_path),
                  source_inputs=bindings, cuts=cuts, captures=captures, restores=restores, invalids=invalids,
                  specials=specials, faults=faults, commands=commands, build_sha256=build.hex(),
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(f):file_sha(f) for f in out.rglob('*') if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_tsi_context_image import audit
    try: checked = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **checked), indent=2))


if __name__ == '__main__': main()
