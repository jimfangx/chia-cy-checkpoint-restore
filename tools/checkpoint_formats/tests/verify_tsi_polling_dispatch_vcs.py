"""Active twelve-owner atomic preparation and first divergent serial requests.

Host component operations only; no complete CPU checkpoint acceptance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats import native_input_guard
from tools.checkpoint_formats.tests import verify_tsi_polling_prepare_vcs as base
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT


def word(b, at):
    return int.from_bytes(b[at:at+8], 'little')


def selected(images):
    # Both merge phases with a complete retained low word, across a source
    # identity whose selector is zero and whose address has residue one.
    return [next(i for i, s in enumerate(images) if word(s['write'], 64) == phase and
                 word(s['write'], 72) % 8 == 1 and word(s['identity'], 80) & 255 == 0 and
                 word(s['write'], 104+word(s['write'], 88)+88) == 1) for phase in (1, 2)]


def fault_boundary(plan, cut, mode):
    packets = [i for i in range(cut, len(plan)) if plan[i].startswith('PACKET ')]
    # The first packet consumes four header words; the next starts with the
    # fifth header word and the changed head merge's first data word.
    require(len(plan[packets[0]].split()) == 5, 'wrong merge header boundary')
    operation = packets[1]+1
    expected = int(plan[packets[1]].split()[2])
    actual = expected ^ 1 if mode == 'merge-corrupt' else expected & 255
    require(actual != expected, 'ineffective semantic corruption')
    return dict(operation=operation, request_word=1, expected=expected, actual=actual)


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong dispatch scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed dispatch artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed dispatch artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed dispatch source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    native_input_guard.audit_reused_input_guard(
        ROOT, report, Path(__file__).resolve(),
        compiled=[name for name in bindings if Path(name).suffix != '.py'])
    base.audit(Path(report['preparation_summary']))
    plan, images = base.scenario(True)
    cuts = selected(images)
    expected = {(p, b, c) for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for c in cuts}
    require(len(report['invalids']) == len(expected) and {(c['producer'], c['backend'], c['cut']) for c in report['invalids']} == expected, 'incomplete active allocation/backend cases')
    malformed = allocations = 0
    for c in report['invalids']:
        match = re.search(r'DISPATCH_ATOMIC membership=49 malformed=(\d+) cross=13 allocation_failures=(\d+) unchanged=1 owners=12 context_entries=0 target_edges=0', Path(c['log']).read_text())
        image = images[c['cut']]
        require(match and int(match[1]) == sum(len(v)+2 for v in image.values()) and int(match[2]) >= 30, 'incomplete active rejection coverage')
        malformed += int(match[1]); allocations += int(match[2])
        for n in base.NAMES:
            require((Path(c['destination'])/('preedge.'+n)).read_bytes() == image[n], 'wrong active complete readback')
    faults = {(p,b,m) for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for m in ('merge-corrupt', 'command-corrupt')}
    require(len(report['corruptions']) == len(faults) and {(c['producer'],c['backend'],c['mode']) for c in report['corruptions']} == faults, 'incomplete semantic fault pairings')
    for c in report['corruptions']:
        require(c['cut'] == cuts[0], 'changed semantic fault cut')
        f = fault_boundary(plan, c['cut'], c['mode'])
        line = 'FIRST_DIVERGENCE '+' '.join(f'{k}={v}' for k,v in f.items())+' acknowledged=0 owners=12 context_entries=0'
        require(line in Path(c['log']).read_text(), 'wrong first divergent boundary')
        image = images[c['cut']].copy()
        image['write'] = bytearray(image['write'])
        if c['mode'] == 'merge-corrupt':
            image['write'][104+word(image['write'],88)+96] ^= 1
        else:
            image['poll'] = bytearray(image['poll']); image['identity'] = bytearray(image['identity'])
            image['poll'][64] ^= 2; image['identity'][80] ^= 2
            image['write'][96:160] = bytes(64)
        for n in base.NAMES:
            require((Path(c['destination'])/('preedge.'+n)).read_bytes() == image[n], 'fault did not change actual restored owner')
    pids=[]
    for c in report['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2] == ['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'), 'unbound dispatch native environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'dispatch sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)',log)[1]))
    require(len(pids) == len(set(pids)), 'dispatch reused process')
    return dict(status='passed', active_invalid_processes=len(expected), malformed_rejections=malformed,
                membership_rejections=49*len(expected), cross_owner_rejections=13*len(expected),
                allocation_failures=allocations, fresh_complete_readbacks=12*len(expected), first_divergence_cases=8,
                fault_boundaries={m:fault_boundary(plan,cuts[0],m) for m in ('merge-corrupt','command-corrupt')},
                level1_verified=False, level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path); p.add_argument('--preparation-summary',type=Path); p.add_argument('--audit',type=Path)
    args=p.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit),indent=2)); return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13','source vcs-env LAST')
    summary=args.preparation_summary.resolve(); base.audit(summary)
    original=json.loads(summary.read_text()); prepared=summary.parent
    args.out.mkdir(parents=True,exist_ok=True); out=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    sources=[base.TESTS/'tsi_polling_dispatch_fesvr.cc', base.STUBS/'fesvr/firesim_tsi.cc',base.STUBS/'fesvr/owned_fesvr_tsi.cc',
             base.TESTCHIP/'testchip_tsi.cc',base.TESTCHIP/'testchip_htif.cc',base.TESTS/'tsi_terminal_allocations.cc']
    bindings=list(original['source_inputs'])
    snapshots=out/'sources';snapshots.mkdir()
    for name in [sources[0],Path(__file__).resolve(),Path(native_input_guard.__file__).resolve()]:
        snapshot=snapshots/file_sha(name);shutil.copyfile(name,snapshot)
        bindings.append(dict(path=str(name),sha256=file_sha(name),snapshot=str(snapshot)))
    # C++/SV, transitive headers, native libraries and environment scripts must
    # still match the prerequisite build. Only Python harness evolution can be
    # inherited here: the new native commands compile from these live paths.
    invocation_inputs=native_input_guard.pin_reused_inputs(
        ROOT,bindings,out/'invocation-sources',
        compiled=[b['path'] for b in bindings if Path(b['path']).suffix != '.py'])
    commands=[]
    def execute(argv,log):
        command=['bash','-lc',ENVIRONMENT+shlex.join(map(str,argv))];run(command,log,cwd=out)
        return dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log))
    # Reuse only the independently source-bound overlay archive, never a
    # simulator process or native C++ object from the prerequisite invocation.
    library=prepared/'libfesvr-checkpoint.a'
    include=f'-std=c++17 -I{base.CC} -I{base.STUBS} -I{base.TESTCHIP} -I{base.FESVR/"include"}'
    commands.append(execute([os.environ['CXX'],*shlex.split(include),'-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',*sources,library,'-lpthread','-o',out/'dispatch-native'],out/'native-build.log'))
    commands.append(execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_polling_prepare_fesvr_tb',
                            '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-Mdir='+str(out/'csrc'),'-CFLAGS',include+' -DTSI_POLLING_PREPARE_DPI',
                            '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',out/'simv',base.TESTS/'tsi_polling_prepare_fesvr_tb.sv',*sources],out/'vcs-build.log'))
    plan,images=base.scenario(True);cuts=selected(images)
    def invoke(producer,backend,mode,cut):
        name=f'{producer}-{backend}-{mode}-{cut}'; dest=out/name
        source=prepared/(producer+f'-capture/cut-{cut}');metadata=prepared/(producer+'-capture/startup.metadata')
        argv=[out/'dispatch-native',mode,prepared/'polling.elf',prepared/'terminal.bin',metadata,source,prepared/'plan.txt',dest] if backend=='native' else [
            out/'simv','-no_save','+mode='+mode,'+elf='+str(prepared/'polling.elf'),'+terminal='+str(prepared/'terminal.bin'),'+metadata='+str(metadata),'+source='+str(source),'+plan='+str(prepared/'plan.txt'),'+destination='+str(dest)]
        return dict(execute(argv,out/(name+'.log')),producer=producer,backend=backend,mode=mode,cut=cut,destination=str(dest))
    jobs=[(p,b,'invalid',c) for p in ('native','vcs-dpi') for b in ('native','vcs-dpi') for c in cuts]
    jobs += [(p,b,m,cuts[0]) for p in ('native','vcs-dpi') for b in ('native','vcs-dpi') for m in ('merge-corrupt','command-corrupt')]
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda j:invoke(*j),jobs))
    commands.extend(results)
    native_input_guard.require_live_inputs_unchanged(invocation_inputs)
    report=dict(status='passed',scope='active twelve-owner host-component preparation and semantic corruption',preparation_summary=str(summary),
                invalids=results[:8],corruptions=results[8:],commands=commands,source_inputs=bindings,
                invocation_source_inputs=invocation_inputs,level1_verified=False,level2_verified=False,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(summary=str(path),**audit(path)),indent=2))


if __name__=='__main__':main()
