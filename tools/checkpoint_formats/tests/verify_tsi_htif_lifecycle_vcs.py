"""Actual private HTIF lifecycle readback in fresh native/VCS processes.

Opt-in provider extension only. No session/context/CPU checkpoint acceptance.
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
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, BUILDER
from tools.checkpoint_formats.tests.verify_tsi_htif_exit_vcs import PAYLOADS, FLUSHES, OWNERS, oracle
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf

PROVIDER = ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc'
RAW = (0, 1, 2, 3, 0x7ffffffe, 0x7fffffff, 0x80000000, 0x80000001, 0xfffffffe, 0xffffffff)
GUARDS = ('pending', 'delivered', 'pending-exit', 'delivered-exit', 'mask', 'handler',
          'occupied-exit', 'occupied-stop', 'signature')
TRANSACTIONS = ('commit', 'abandon', 'peer-invalid', 'pending', 'delivered', 'mask',
                'handler', 'occupied-exit', 'occupied-stop', 'signature')
BAD_COMMIT = {
    'copy': 'auto copy = next;',
    'move': 'auto moved = std::move(next);',
    'throwing': 'auto publish = []() {}; next.commit(publish);',
}


def image(present=0, raw=0, stopped=0):
    return config(32, 1, 32, 0)+words(present, raw, stopped)


def fields(present, raw, stopped):
    signed = raw if raw < 0x80000000 else raw-0x100000000
    return f'{present} {raw} {stopped} {stopped} {signed//2}\n'


def bad_images():
    good = image(1, 1)
    result = [good[:n] for n in range(len(good))]+[good+b'\0']
    for n in range(len(config(32, 1, 32, 0))):
        bad = bytearray(good); bad[n] ^= 1; result.append(bytes(bad))
    return result+[image(2, 1), image(0, 1), image(1, 0x100000000), image(1, 1, 2)]


def audit(path):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text())
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong lifecycle scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'lifecycle artifacts changed')
    for p, digest in r['artifact_sha256'].items():
        require(file_sha(p) == digest, 'changed lifecycle artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed lifecycle source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    overlay = json.loads((out/'libfesvr-checkpoint.json').read_text())
    require(overlay['status'] == 'passed' and overlay['output_sha256'] == file_sha(out/'libfesvr-checkpoint.a'), 'wrong provider overlay')
    require({m for m, v in overlay['members'].items() if v['installed'] != v['overlay']} ==
            {'elfloader.o', 'context.o', 'htif.o'}, 'unrelated installed provider changed')
    if r.get('recipe_build_identity'):
        identity = json.loads(Path(r['recipe_build_identity']).read_text())
        require(identity['htif_lifecycle_provider_linked'] and not identity['level1_verified'] and
                not identity['level2_verified'], 'wrong recipe provider scope')
        binary = Path(identity['native_binary'])
        production = binary.parent / 'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        require(identity['sources_sha256'][str(production)] == file_sha(production) ==
                file_sha(out/'libfesvr-checkpoint.a'), 'lifecycle suite did not use actual recipe archive')
        for name in ('owned-htif.o', 'owned-context.o', 'owned-elfloader.o'):
            obj = production.parent / name
            require(identity['sources_sha256'][str(obj)] == file_sha(obj), 'changed actual recipe provider object')
    for p, digest in overlay['lifecycle_inputs'].items():
        if not p.endswith('_sha256'):
            require(bindings[p]['sha256'] == digest, 'unbound lifecycle provider input')
    header = Path(bindings[str(FESVR/'include/fesvr/htif.h')]['snapshot']).read_bytes()
    require(file_sha(bindings[str(PROVIDER.with_suffix('.h'))]['snapshot']) ==
            file_sha(bindings[str(FESVR/'include/fesvr/htif.h')]['snapshot']), 'source/provider header mismatch')
    import hashlib
    adapted = header.replace(b'  friend class syscall_t;', b'  friend class syscall_t;\n  friend struct firesim_htif_lifecycle_access_t;')
    generated = Path(bindings[str(PROVIDER)]['snapshot']).read_bytes()+b'\n'+Path(bindings[str(STUBS/'fesvr/htif_lifecycle_provider.inc')]['snapshot']).read_bytes()
    require(hashlib.sha256(adapted).hexdigest() == overlay['lifecycle_inputs']['adapted_header_sha256'] and
            hashlib.sha256(generated).hexdigest() == overlay['lifecycle_inputs']['generated_provider_sha256'], 'provider source/header rewriting changed')
    require((out/'incompatible-provider/output.a').read_bytes() == b'UNCHANGED ARCHIVE\n' and
            (out/'incompatible-provider/output.json').read_bytes() == b'UNCHANGED REPORT\n', 'invalid provider partially published')
    require('installed/source HTIF header mismatch' in (out/'incompatible-provider.log').read_text(), 'missing incompatible provider rejection')
    captures, restores = 0, 0
    for raw in PAYLOADS:
        for flush in FLUSHES:
            events, states = oracle(raw, flush)
            for backend in ('native', 'vcs-dpi'):
                capture = out/f'{backend}-capture-{raw}-{flush}'
                require((capture/'events.txt').read_text().splitlines() == events, 'lifecycle changed production packet/timing')
                require((capture/'cuts.txt').read_text().splitlines() ==
                        [f'{n} {tick} {done} {code}' for n, (tick, done, code, _) in enumerate(states)], 'production cut labels changed')
                for cut, (_, done, _, owners) in enumerate(states):
                    present = int(owners['exit'][56] > 0)
                    bits = raw & 0xffffffff if present else 0
                    wanted = image(present, bits, done)
                    require((capture/f'cut-{cut}.lifecycle').read_bytes() == wanted and
                            (capture/f'cut-{cut}.fields').read_text() == fields(present, bits, done), 'incomplete actual provider capture')
                    for owner in OWNERS:
                        require((capture/f'cut-{cut}.{owner}').read_bytes() == owners[owner], 'production owner changed '+owner)
                    captures += 1
                    for dest in ('native', 'vcs-dpi'):
                        restored = out/f'{backend}-{dest}-{raw}-{flush}-cut-{cut}'
                        require((restored/'pre-service.lifecycle').read_bytes() == wanted and
                                (restored/'pre-service.fields').read_text() == fields(present, bits, done), 'incomplete fresh private-field readback')
                        require((restored/'final.lifecycle').read_bytes() == image(present, bits, 1) and
                                (restored/'final.fields').read_text() == fields(present, bits, 1), 'restored installed stop differs')
                        restores += 1
    raw_restores = 0
    for backend in ('native', 'vcs-dpi'):
        for tag, present, raw in [('absent', 0, 0), *[(str(raw), 1, raw) for raw in RAW]]:
            for phase, stopped in (('requested', 0), ('stopped', 1)):
                producer = out/f'{backend}-raw-{tag}'
                wanted = image(present, raw, stopped)
                require((producer/f'{phase}.lifecycle').read_bytes() == wanted and
                        (producer/f'{phase}.fields').read_text() == fields(present, raw, stopped), 'lost optional/raw/stopped distinction')
                for dest in ('native', 'vcs-dpi'):
                    target = out/f'{backend}-{dest}-raw-{tag}-{phase}'
                    require((target/'pre-service.lifecycle').read_bytes() == wanted and
                            (target/'pre-service.fields').read_text() == fields(present, raw, stopped) and
                            (target/'final.lifecycle').read_bytes() == image(present, raw, 1), 'raw private-field restore mismatch')
                    raw_restores += 1
        for n, payload in enumerate(bad_images()):
            require((out/f'bad-{n}.lifecycle').read_bytes() == payload and
                    (out/f'{backend}-reject-{n}/unchanged.lifecycle').read_bytes() == image() and
                    (out/f'{backend}-reject-{n}/prepare-rejected.txt').read_text() ==
                    'rejected=1 target_services=0\n', 'non-atomic malformed lifecycle rejection')
        for which in GUARDS:
            target = out/f'{backend}-guard-{which}'
            require((target/'guard.txt').read_text() == f'{which} rejected=1 target_services=0\n', 'missing lifecycle guard')
            if which in ('occupied-exit', 'occupied-stop'):
                require((target/'unchanged.fields').read_text() == fields(int(which == 'occupied-exit'), 0, int(which == 'occupied-stop')), 'occupied destination mutated')
        for raw in RAW:
            target = out/f'{backend}-corrupt-{raw}'
            require((target/'pre-service.lifecycle').read_bytes() == image(1, raw^1) and
                    (target/'first-divergence.txt').read_text() ==
                    f'FIRST_DIVERGENCE boundary=0 signal=exitcode.raw expected={raw} actual={raw^1} acknowledged=0 target_services=0\n', 'wrong first private-field divergence')
    # Every restore/reject/corrupt invocation must leave the whole serial owner
    # unchanged. Audit bytes against the independent empty-FIFO encoding.
    from tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs import serial
    before_peer = serial([0, 0x80001234, 0, 1, 0], [0x11223344])
    replacement_peer = serial([1, 0x87654320, 0x12345678, 1, 0, 0xdeadbeef, 0xfedcba98], [0x5678, 0x99])
    transactions = 0
    for backend in ('native', 'vcs-dpi'):
        for tag, present, raw in [('absent', 0, 0), *[(str(raw), 1, raw) for raw in RAW]]:
            for phase, stopped in (('requested', 0), ('stopped', 1)):
                for which in TRANSACTIONS:
                    target = out/f'{backend}-transaction-{tag}-{phase}-{which}'
                    committed = which == 'commit'
                    require((target/'before.serial').read_bytes() == before_peer and
                            (target/'candidate.serial').read_bytes() == replacement_peer and
                            (target/'after.serial').read_bytes() == (replacement_peer if committed else before_peer),
                            'incomplete transaction peer readback')
                    require((target/'transaction.txt').read_text() ==
                            f'{which} callbacks={int(committed)} target_services=0\n', 'transaction publication count differs')
                    if which not in ('delivered', 'signature'):
                        expected = image(present, raw, stopped) if committed else image(
                            int(which == 'occupied-exit'), 0, int(which == 'occupied-stop'))
                        wanted_fields = fields(present, raw, stopped) if committed else fields(
                            int(which == 'occupied-exit'), 0, int(which == 'occupied-stop'))
                        require((target/'after.lifecycle').read_bytes() == expected and
                                (target/'after.fields').read_text() == wanted_fields, 'transaction provider readback differs')
                    else:
                        require(not (target/'after.lifecycle').exists(), 'unsupported signal/signature readback claimed')
                    transactions += 1
    for name, statement in BAD_COMMIT.items():
        require((out/f'bad-commit-{name}.cc').read_text() == bad_commit_source(statement), 'changed compile rejection input')
        log = (out/f'bad-commit-{name}.log').read_text()
        require('error:' in log and ('deleted' in log if name != 'throwing' else
                'lifecycle peer publication must be noexcept' in log), 'missing commit type rejection')
    for p in out.rglob('unchanged.serial'):
        require(p.read_bytes() == serial([], []), 'lifecycle touched target queues')
    require(r['commands'] and all(Path(c['log']).read_text().rstrip().endswith('exit='+str(c['returncode']))
                                 for c in r['commands']), 'missing native command/exit evidence')
    return dict(status='passed', source_cuts=captures, fresh_provider_restores=restores,
                optional_raw_restores=raw_restores, malformed_processes=2*len(bad_images()),
                guard_rejections=2*len(GUARDS), first_divergences=2*len(RAW),
                atomic_transactions=transactions, compile_rejections=len(BAD_COMMIT),
                level1_verified=False, level2_verified=False)


def bad_commit_source(statement):
    return ('#include "fesvr/tsi_htif_lifecycle.h"\n'
            'void check(firesim_tsi_htif_lifecycle_t &owner, const std::vector<uint8_t> &image) {\n'
            '  auto next = owner.prepare_checkpoint(image);\n  '+statement+'\n}\n')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path); p.add_argument('--audit', type=Path)
    p.add_argument('--recipe-build-identity', type=Path, help='Test the actual linked exact-recipe lifecycle archive')
    a = p.parse_args()
    if a.audit:
        print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    source, sv = (TESTS/n for n in ('tsi_htif_lifecycle_fesvr.cc', 'tsi_htif_lifecycle_fesvr_tb.sv'))
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), TESTS/'tsi_htif_exit_fesvr.cc', TESTS/'verify_tsi_htif_exit_vcs.py',
              TESTS/'verify_tsi_memif_read_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              FESVR/'lib/libfesvr.a', *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *overlay_inputs(),
              PROVIDER, PROVIDER.with_suffix('.h'), STUBS/'fesvr/htif_lifecycle_provider.inc',
              *sorted((FESVR/'include/fesvr').glob('*.h')), *sorted((FESVR/'include/riscv').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'tools/checkpoint_formats/retained_evidence.py', ROOT/'tools/checkpoint_formats/evidence.py',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    production = None
    if a.recipe_build_identity:
        identity_path = a.recipe_build_identity.resolve()
        identity = json.loads(identity_path.read_text())
        require(identity.get('htif_lifecycle_provider_linked') is True, 'recipe provider is not linked')
        production = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        for path, digest in identity['sources_sha256'].items():
            require(file_sha(path) == digest, 'changed exact-recipe build input '+path)
        inputs += [identity_path, production, production.with_suffix('.json')]
        inputs += [production.parent/n for n in ('owned-htif.o', 'owned-context.o', 'owned-elfloader.o')]
    snapshots = out/'sources'; snapshots.mkdir(); bindings, commands = [], []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    def execute(argv, log, expected=0):
        # The launcher sources vcs-env LAST. Invoke children directly so every
        # fresh simulator inherits that exact pinned environment, without
        # re-running Chipyard setup thousands of times in login shells.
        command = list(map(str, argv))
        run(command, log, cwd=out, expected=expected)
        commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), returncode=expected))
    library = out/'libfesvr-checkpoint.a'
    if production:
        shutil.copyfile(production, library)
        shutil.copyfile(production.with_suffix('.json'), library.with_suffix('.json'))
    else:
        execute(['python3', BUILDER, '--library', FESVR/'lib/libfesvr.a', '--include', FESVR/'include',
                 '--out', library, '--cxx', os.environ['CXX'], '--htif-source', PROVIDER], out/'fesvr-overlay-build.log')
    incompatible = out/'incompatible-provider'; incompatible.mkdir()
    (incompatible/'htif.cc').write_bytes(PROVIDER.read_bytes())
    (incompatible/'htif.h').write_bytes(PROVIDER.with_suffix('.h').read_bytes()+b'\n')
    (incompatible/'output.a').write_bytes(b'UNCHANGED ARCHIVE\n')
    (incompatible/'output.json').write_bytes(b'UNCHANGED REPORT\n')
    execute(['python3', BUILDER, '--library', FESVR/'lib/libfesvr.a', '--include', FESVR/'include',
             '--out', incompatible/'output.a', '--cxx', os.environ['CXX'], '--htif-source', incompatible/'htif.cc'],
            out/'incompatible-provider.log', expected=1)
    native, simv = out/'lifecycle-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    for name, statement in BAD_COMMIT.items():
        bad = out/f'bad-commit-{name}.cc'; bad.write_text(bad_commit_source(statement))
        execute([os.environ['CXX'], *shlex.split(include), '-fsyntax-only', bad],
                out/f'bad-commit-{name}.log', expected=1)
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_htif_lifecycle_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_HTIF_LIFECYCLE_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    (out/'polling.elf').write_bytes(polling_elf())
    def invoke(backend, mode, name, source, raw=1, flush=0):
        values = list(map(str, (mode, source, out/name, raw, flush)))
        argv = [native, *values] if backend == 'native' else [simv, '-no_save', *['+'+k+'='+v for k,v in zip(('mode','source','destination','raw','flush'), values)]]
        execute(argv, out/(name+'.log'))
    # Finish every producer before launching any fresh restore process.
    for b in ('native', 'vcs-dpi'):
        for raw in PAYLOADS:
            for flush in FLUSHES:
                invoke(b, 'capture', f'{b}-capture-{raw}-{flush}', out/'polling.elf', raw, flush)
        for tag, raw in [('absent', 0), *[(str(raw), raw) for raw in RAW]]:
            invoke(b, 'raw', f'{b}-raw-{tag}', out/'polling.elf', raw, 'absent' if tag == 'absent' else 0)
    jobs = [(b, 'restore', f'{p}-{b}-{r}-{f}-cut-{c}', out/f'{p}-capture-{r}-{f}/cut-{c}.lifecycle', r, f)
            for p in ('native','vcs-dpi') for b in ('native','vcs-dpi') for r in PAYLOADS for f in FLUSHES
            for c in range(len(oracle(r,f)[1]))]
    jobs += [(b, 'restore', f'{p}-{b}-raw-{tag}-{phase}', out/f'{p}-raw-{tag}/{phase}.lifecycle', r, 0)
             for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi')
             for tag, r in [('absent', 0), *[(str(r), r) for r in RAW]] for phase in ('requested', 'stopped')]
    for n, bad in enumerate(bad_images()):
        (out/f'bad-{n}.lifecycle').write_bytes(bad)
        jobs += [(b, 'reject', f'{b}-reject-{n}', out/f'bad-{n}.lifecycle', 1, 0) for b in ('native','vcs-dpi')]
    for r in RAW:
        (out/f'corrupt-{r}.lifecycle').write_bytes(image(1, r^1))
        jobs += [(b, 'corrupt', f'{b}-corrupt-{r}', out/f'corrupt-{r}.lifecycle', r, 0) for b in ('native','vcs-dpi')]
    jobs += [(b, 'guard', f'{b}-guard-{g}', out/'native-raw-3/requested.lifecycle', g, 0)
             for b in ('native', 'vcs-dpi') for g in GUARDS]
    jobs += [(b, 'transaction', f'{b}-transaction-{tag}-{phase}-{which}',
              out/f'native-raw-{tag}/{phase}.lifecycle', which, 0)
             for b in ('native', 'vcs-dpi')
             for tag in ('absent', *map(str, RAW)) for phase in ('requested', 'stopped')
             for which in TRANSACTIONS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda j: invoke(*j), jobs))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during lifecycle verification')
    report = dict(status='passed', scope='actual private lifecycle fields; opt-in provider; complete HTIF/CPU restore pending',
                  recipe_build_identity=str(a.recipe_build_identity.resolve()) if a.recipe_build_identity else None,
                  source_inputs=bindings, commands=commands, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    try:
        result = audit(path)
    except Exception:
        report['status'] = 'failed'
        path.write_text(json.dumps(report, indent=2)+'\n')
        raise
    print(json.dumps(dict(summary=str(path), **result), indent=2))


if __name__ == '__main__':
    main()
