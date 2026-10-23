"""Fresh syscall-93 parent/transport/actual-provider component restores.

Independent byte oracle plus installed FESVR dispatch differential. This does
not admit a session, polling caller, complete HTIF context or CPU Level 1.
"""
from tools.checkpoint_formats import toolchain as _toolchain
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
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, FESVR
from tools.checkpoint_formats.tests.fesvr_overlay import BUILDER, overlay_inputs
from tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs import reader, child
from tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs import writer, serial, initial

NAMES = ('syscall', 'serial', 'lifecycle')
BACKENDS = ('native', 'vcs-dpi')
SPECS = ((0, 0), (2, 1), (4, 0x7fffffff), (6, 0xffffffffffffffff))
PROVIDER = ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc'


def caller(phase=0, command=0, args=(0,)*8, read=None, write=None):
    read = reader() if read is None else read
    write = writer() if write is None else write
    return config(34, 1, 64, 93, 8, 8, 1024, 0)+words(phase, command, *args, len(read))+read+words(len(write))+write


def lifecycle(executed=False, code=0):
    return config(32, 1, 32, 0)+words(int(executed), ((code << 1) | 1) & 0xffffffff if executed else 0, 0)


def scenario(residue, code, fault=False):
    """Expand installed dispatch/read/write/response order without C++ output."""
    address = 0x1280003000+residue
    args = (93, code, 0x1200340056007800, 3, 0xffffffffffffffff, 0x8000000000000001, 6, 7)
    request = words(*args)
    original = bytearray(initial(address//8*8+i) for i in range(72))
    original[residue:residue+64] = request
    memory = bytearray(original)
    base = address & ~7
    phase, stored = 0, (0,)*8
    rd, wr = reader(), writer()
    requests, responses, plan, expected, states, events = [], [], [], [], [], []

    def snapshot():
        states.append((caller(phase, address if phase else 0, stored, rd, wr), serial(requests, responses),
                       lifecycle(phase >= 3, code)))

    def step(text, result=None):
        plan.append(text); expected.append(result or text); snapshot()

    def drain():
        while requests:
            take = min(3, len(requests)); sent = requests[:take]; del requests[:take]
            step('PACKET '+' '.join(map(str, sent)))

    def enqueue(command, a, data):
        requests.extend([command, a & 0xffffffff, a >> 32, len(data)//4-1, 0])
        if command: requests.extend(int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4))

    snapshot(); phase=1
    rd=reader(1 if residue else 2, address, 0, bytes(64))
    step('BEGIN '+str(address))
    filled=bytearray(64)
    head=8-residue if residue else 0

    def read_chunk(read_phase, a, n, offset, first, count):
        nonlocal rd, phase, stored
        data=bytes(memory[a-base:a-base+n]); values=[int.from_bytes(data[i:i+4], 'little') for i in range(0,n,4)]
        events.append(f'READ {a} {n} {data.hex()}'); enqueue(0,a,bytes(n))
        rd=reader(read_phase,address,0,bytes(filled),child(2,a,n))
        step('ADVANCE','ADVANCE BLOCKED'); drain(); step('ADVANCE','ADVANCE BLOCKED')
        for i,value in enumerate(values):
            responses.append(value); step('SEND '+str(value)); responses.clear()
            if i+1 < len(values):
                rd=reader(read_phase,address,0,bytes(filled),child(2,a,n,values[:i+1]))
                step('ADVANCE','ADVANCE BLOCKED')
            else:
                filled[offset:offset+count]=data[first:first+count]
                if read_phase==1: rd=reader(2,address,0,bytes(filled))
                elif read_phase==2: rd=reader(3,address,0,bytes(filled))
                else: rd=reader(); phase=2; stored=args
                step('ADVANCE','ADVANCE PROGRESS')

    if residue:
        read_chunk(1,base,8,0,residue,head)
        read_chunk(2,address+64-residue,8,64-residue,0,residue)
    else:
        rd=reader(3,address,0,bytes(64)); step('ADVANCE','ADVANCE PROGRESS')
    read_chunk(3,address+head,64-head-residue,head,0,64-head-residue)
    result_args=list(args); result_args[0]=0
    if fault: result_args[2]^=1
    result=words(*result_args); phase=3
    wr=writer(1 if residue else 2,address,0,result)
    step('ADVANCE','ADVANCE PROGRESS'); invoke_cut=len(plan)

    def merge(write_phase,a,offset,first,count):
        nonlocal wr
        data=bytes(memory[a-base:a-base+8]); values=[int.from_bytes(data[i:i+4],'little') for i in (0,4)]
        events.append(f'READ {a} 8 {data.hex()}'); enqueue(0,a,bytes(8))
        wr=writer(write_phase,address,0,result,child(2,a,8))
        step('ADVANCE','ADVANCE BLOCKED'); drain(); step('ADVANCE','ADVANCE BLOCKED')
        responses.append(values[0]); step('SEND '+str(values[0])); responses.clear()
        wr=writer(write_phase,address,0,result,child(2,a,8,values[:1]))
        step('ADVANCE','ADVANCE BLOCKED')
        responses.append(values[1]); step('SEND '+str(values[1])); responses.clear()
        merged=bytearray(data); merged[first:first+count]=result[offset:offset+count]
        memory[a-base:a-base+8]=merged; enqueue(1,a,merged)
        events.append(f'WRITE {a} 8 {merged.hex()}')
        wr=writer(2 if write_phase==1 else 3,address,0,result)
        step('ADVANCE','ADVANCE PROGRESS'); drain()

    if residue:
        merge(1,base,0,residue,head)
        merge(2,address+64-residue,64-residue,0,residue)
    else:
        wr=writer(3,address,0,result); step('ADVANCE','ADVANCE PROGRESS')
    data=result[head:64-residue] if residue else result
    enqueue(1,address+head,data); memory[address+head-base:address+head-base+len(data)]=data
    events.append(f'WRITE {address+head} {len(data)} {data.hex()}')
    wr=writer(); phase=4; step('ADVANCE','ADVANCE PROGRESS'); drain()
    phase=5; events.append('RESPOND 1'); step('ADVANCE','ADVANCE COMPLETE RESPOND 1')
    step('ADVANCE','ADVANCE COMPLETE')
    return dict(plan=plan, expected=expected, states=states, events=events, original=bytes(original),
                memory=bytes(memory), address=address, code=code, invoke_cut=invoke_cut)


def audit(path):
    path=Path(path).resolve(); out=path.parent; r=json.loads(path.read_text())
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong syscall scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path}, 'changed syscall artifact membership')
    for name,digest in r['artifact_sha256'].items(): require(file_sha(name)==digest, 'changed syscall artifact '+name)
    bindings={b['path']:b for b in r['source_inputs']}
    require(len(bindings)==len(r['source_inputs']), 'duplicate syscall source')
    required={str(Path(__file__)),str(TESTS/'tsi_syscall_exit_fesvr.cc'),str(TESTS/'tsi_syscall_exit_fesvr_tb.sv'),
              str(TESTS/'tsi_terminal_allocations.cc'),str(STUBS/'fesvr/tsi_syscall_exit.h'),
              str(STUBS/'fesvr/tsi_memif_read.h'),str(STUBS/'fesvr/tsi_memif_write.h'),
              str(STUBS/'fesvr/tsi_htif_lifecycle.h'),str(STUBS/'fesvr/htif_lifecycle_provider.inc'),
              str(FESVR/'lib/libfesvr.a'),str(PROVIDER)}
    require(required.issubset(bindings),'missing syscall implementation/source ownership binding')
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'], 'changed syscall source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    overlay=json.loads((out/'libfesvr-checkpoint.json').read_text())
    require(overlay['status']=='passed' and overlay['output_sha256']==file_sha(out/'libfesvr-checkpoint.a'), 'unbound syscall provider archive')
    for name,digest in overlay['lifecycle_inputs'].items():
        if not name.endswith('_sha256'): require(bindings[name]['sha256']==digest,'unbound syscall lifecycle provider input')
    require(overlay['members']['syscall.o']['installed']==overlay['members']['syscall.o']['overlay'], 'reference syscall implementation changed')
    wanted=[]; readbacks=operations=0
    for index,spec in enumerate(SPECS):
        s=scenario(*spec); folder=out/f'scenario-{index}'
        require((folder/'plan').read_text().splitlines()==s['plan'] and (folder/'expected').read_text().splitlines()==s['expected'], 'changed syscall schedule')
        for backend in BACKENDS:
            ref=folder/(backend+'-reference')
            require((ref/'events.txt').read_text()=='\n'.join(s['events'])+'\n', 'installed syscall transaction order differs')
            require((ref/'memory.bin').read_bytes()==s['memory'] and (ref/'lifecycle.bin').read_bytes()==lifecycle(True,s['code']), 'installed syscall semantic result differs')
            for cut,state in enumerate(s['states']):
                for name,image in zip(NAMES,state):
                    require((folder/(backend+'-capture')/f'cut-{cut}.{name}').read_bytes()==image, 'producer syscall owner differs')
        for producer in BACKENDS:
            for backend in BACKENDS:
                for cut,state in enumerate(s['states']):
                    name=f'{producer}-{backend}-cut-{cut}'; dest=folder/name
                    wanted.append((index,producer,backend,cut))
                    for owner,image in zip(NAMES,state): require((dest/('preedge.'+owner)).read_bytes()==image, 'incomplete pre-service syscall readback')
                    require((dest/'continuation.bin').read_bytes()==b''.join(b for state in s['states'][cut:] for b in state), 'syscall continuation state differs')
                    require((dest/'trace').read_text()==''.join(f'{i+1} {s["expected"][i]}\n' for i in range(cut,len(s['plan']))), 'syscall continuation service timing differs')
                    readbacks+=3*(len(s['states'])-cut); operations+=len(s['plan'])-cut
    require([(c['scenario'],c['producer'],c['backend'],c['cut']) for c in r['continuations']]==wanted, 'missing/reordered/duplicate syscall continuation')
    require(len(r['invalids'])==18 and len(r['faults'])==4, 'incomplete syscall negative evidence')
    for c in r['faults']:
        require((Path(c['destination'])/'first-divergence.txt').read_text()==c['divergence'], 'wrong first syscall divergence')
    require([(Path(c['destination']).name,c['backend']) for c in r['invalids']]==
            [(f'{b}-invalid-{n}',b) for n in range(9) for b in BACKENDS], 'missing/duplicate syscall invalid pairing')
    for c in r['invalids']:
        for owner,image in zip(NAMES,(caller(),serial(),lifecycle())):
            require((Path(c['destination'])/('unchanged.'+owner)).read_bytes()==image,'invalid image partially restored owner')
        require('REJECTED owners=3 restore_services=0 target_edges=0' in Path(c['log']).read_text(), 'invalid syscall group admitted')
    atomic=[]
    for backend in BACKENDS:
        require((out/'scenario-0'/(backend+'-guard')/'guards.txt').read_text()=='rejections=15 command=3 endian=2 selector=2 hostile=8 provider_unchanged=1\n', 'missing syscall guards')
        text=(out/(backend+'-check')/'atomic.txt').read_text()
        require(re.fullmatch(r'malformed=\d+ membership=12 cross=8 allocation_failures=\d+ occupied=1 unchanged_on_failure=1\n',text) is not None, 'incomplete atomic syscall coverage')
        atomic.append(text)
    require(atomic[0]==atomic[1], 'atomic syscall backend coverage differs')
    command_map={c['log']:c for c in r['commands']}
    require(len(command_map)==len(r['commands']), 'duplicate syscall process log')
    used=set()
    def process(index,backend,mode,name,producer='native',cut=0,source=None,exit_code=0):
        folder=out/f'scenario-{index}'; dest=(out/name) if mode=='check' else folder/name
        values=list(map(str,(mode,dest,folder/('reference-spec' if mode=='reference' else 'plan'),
                            folder/('original.bin' if mode=='reference' else 'expected'),
                            source or folder/(producer+'-capture')/f'cut-{cut}',cut)))
        argv=[str(out/'native'),*values] if backend=='native' else [str(out/'simv'),'-no_save',
             *['+'+k+'='+v for k,v in zip(('mode','out','plan','expected','source','cut'),values)]]
        log=str(dest.with_suffix('.log')); require(log in command_map,'missing syscall process command')
        c=command_map[log]
        require(c['argv']==['bash','-lc',ENVIRONMENT+shlex.join(argv)] and c['expected_exit']==exit_code and
                c['cwd']==str(out.relative_to(ROOT)), 'unbound syscall process command')
        text=Path(log).read_text()
        marker={'capture':'SYSCALL_CONTINUATION','restore':'SYSCALL_CONTINUATION',
                'invalid':'REJECTED owners=3','corrupt':'FAIL FIRST_DIVERGENCE',
                'reference':'INSTALLED_SYSCALL selector=93'}.get(mode)
        if marker: require(marker in text,'missing actual syscall execution')
        used.add(log)
        return c
    for index,spec in enumerate(SPECS):
        s=scenario(*spec)
        for backend in BACKENDS:
            process(index,backend,'reference',backend+'-reference')
            process(index,backend,'capture',backend+'-capture')
    for c in r['continuations']:
        actual=process(c['scenario'],c['backend'],'restore',Path(c['destination']).name,c['producer'],c['cut'])
        require(all(c[k]==actual[k] for k in actual),'changed continuation process binding')
    for n in range(9):
        for backend in BACKENDS: process(0,backend,'invalid',f'{backend}-invalid-{n}',source=out/f'bad-{n}')
    require([(c['scenario'],c['backend']) for c in r['faults']]==[(i,b) for i in (0,1) for b in BACKENDS], 'missing semantic fault pairing')
    for c in r['faults']:
        index=c['scenario']; cut=scenario(*SPECS[index])['invoke_cut']
        process(index,c['backend'],'corrupt',c['backend']+'-corrupt',cut=cut,
                source=out/f'scenario-{index}/native-capture'/f'cut-{cut}',exit_code=2)
    candidate=out/'scenario-0/native-capture'/f'cut-{scenario(*SPECS[0])["invoke_cut"]}'
    for backend in BACKENDS:
        process(0,backend,'check',backend+'-check',source=candidate)
        process(0,backend,'guard',backend+'-guard')
    build_logs={str(out/n) for n in ('native-build.log','vcs-build.log')}
    if not r['recipe_build_identity']: build_logs.add(str(out/'overlay-build.log'))
    require(set(command_map)==used|build_logs,'extra/missing native syscall builds or processes')
    vcs_command=command_map[str(out/'vcs-build.log')]['argv']
    require(vcs_command[:2]==['bash','-lc'] and vcs_command[2].startswith(ENVIRONMENT),'unbound VCS environment')
    vcs=shlex.split(vcs_command[2][len(ENVIRONMENT):])
    require(vcs[0]==_toolchain.VCS and '-full64' in vcs and
            vcs[vcs.index('-cc')+1]==_toolchain.CC and vcs[vcs.index('-cpp')+1]==_toolchain.CXX, 'wrong VCS/compiler configuration')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(log.rstrip().endswith('exit='+str(c['expected_exit'])), 'syscall process unfinished')
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT), 'missing native environment binding')
        require(not any(v in log for v in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'syscall sanitizer failure')
    return dict(status='passed', scenarios=len(SPECS), cuts=sum(len(scenario(*s)['states']) for s in SPECS),
                fresh_restores=len(wanted), owner_readbacks=readbacks, host_operations=operations,
                installed_dispatch_differentials=8, invalid_processes=18, semantic_first_divergences=4,
                atomic_per_backend=atomic[0].strip(), level1_verified=False, level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path); p.add_argument('--audit',type=Path)
    p.add_argument('--recipe-build-identity',type=Path); a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX, 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True); out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source,sv=[TESTS/n for n in ('tsi_syscall_exit_fesvr.cc','tsi_syscall_exit_fesvr_tb.sv')]; alloc=TESTS/'tsi_terminal_allocations.cc'
    inputs=[Path(__file__),source,sv,alloc,PROVIDER,PROVIDER.with_suffix('.h'),
            ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/syscall.cc',
            STUBS/'fesvr/htif_lifecycle_provider.inc',*overlay_inputs(),*sorted((STUBS/'fesvr').glob('*.h')),
            *sorted((FESVR/'include/fesvr').glob('*.h')),FESVR/'lib/libfesvr.a',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            Path(__file__).with_name('verify_tsi_memif_read_vcs.py'),Path(__file__).with_name('verify_tsi_memif_write_vcs.py'),
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    production=None
    if a.recipe_build_identity:
        identity=json.loads(a.recipe_build_identity.read_text()); require(identity['htif_lifecycle_provider_linked'], 'recipe missing actual provider')
        for name,digest in identity['sources_sha256'].items(): require(file_sha(name)==digest,'changed recipe input '+name)
        production=Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        inputs += [a.recipe_build_identity.resolve(),production,production.with_suffix('.json')]
    (out/'sources').mkdir(); bindings=[]
    for path in dict.fromkeys(inputs):
        digest=file_sha(path); snapshot=out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path,snapshot)
        bindings.append(dict(path=str(path),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        command=['bash','-lc',ENVIRONMENT+shlex.join(map(str,argv))]; run(command,log,cwd=out,expected=expected)
        c=dict(argv=command,cwd=str(out.relative_to(ROOT)),log=str(log),expected_exit=expected); commands.append(c); return c
    library=out/'libfesvr-checkpoint.a'
    if production:
        shutil.copyfile(production,library); shutil.copyfile(production.with_suffix('.json'),library.with_suffix('.json'))
    else:
        execute(['python3',BUILDER,'--library',FESVR/'lib/libfesvr.a','--include',FESVR/'include','--out',library,'--cxx',os.environ['CXX'],'--htif-source',PROVIDER],out/'overlay-build.log')
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{FESVR/"include"}'
    native,simv=out/'native',out/'simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',source,alloc,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_syscall_exit_fesvr_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-Mdir='+str(out/'csrc'),'-CFLAGS',include+' -DTSI_SYSCALL_EXIT_DPI','-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,source,alloc],out/'vcs-build.log')
    def invoke(index,backend,mode,name,producer='native',cut=0,source=None,expected=0,**extra):
        folder=out/f'scenario-{index}'; dest=(out/name) if mode=='check' else folder/name
        values=list(map(str,(mode,dest,folder/('reference-spec' if mode=='reference' else 'plan'),folder/('original.bin' if mode=='reference' else 'expected'),source or folder/(producer+'-capture')/f'cut-{cut}',cut)))
        argv=[native,*values] if backend=='native' else [simv,'-no_save',*['+'+k+'='+v for k,v in zip(('mode','out','plan','expected','source','cut'),values)]]
        return dict(execute(argv,dest.with_suffix('.log'),expected),mode=mode,scenario=index,backend=backend,producer=producer,cut=cut,destination=str(dest),**extra)
    for index,spec in enumerate(SPECS):
        s=scenario(*spec); folder=out/f'scenario-{index}'; folder.mkdir()
        (folder/'plan').write_text('\n'.join(s['plan'])+'\n'); (folder/'expected').write_text('\n'.join(s['expected'])+'\n')
        (folder/'original.bin').write_bytes(s['original']); (folder/'reference-spec').write_text(f'{s["address"]} {s["code"]}\n')
        for backend in BACKENDS:
            invoke(index,backend,'reference',backend+'-reference'); invoke(index,backend,'capture',backend+'-capture')
    jobs=[(i,b,'restore',f'{p}-{b}-cut-{c}',p,c) for i,spec in enumerate(SPECS) for p in BACKENDS for b in BACKENDS for c in range(len(scenario(*spec)['states']))]
    with ThreadPoolExecutor(max_workers=8) as pool: continuations=list(pool.map(lambda j:invoke(*j),jobs))
    s=scenario(*SPECS[0]); candidate=out/'scenario-0/native-capture'/f'cut-{s["invoke_cut"]}'
    for backend in BACKENDS:
        invoke(0,backend,'check',backend+'-check',source=candidate)
        invoke(0,backend,'guard',backend+'-guard')
    invalids=[]; faults=[]
    for n in range(9):
        prefix=out/f'bad-{n}'
        images=list(s['states'][s['invoke_cut']]); bad=bytearray(images[n%3])
        if n<3: bad=bad[:-1]
        elif n<6: bad[16]^=1
        else: bad+=b'\0'
        images[n%3]=bytes(bad)
        for owner,image in zip(NAMES,images): prefix.with_suffix('.'+owner).write_bytes(image)
        for backend in BACKENDS: invalids.append(invoke(0,backend,'invalid',f'{backend}-invalid-{n}',source=prefix))
    # Post-restore semantic edit of an argument and its copied write payload.
    # The provider stays unchanged. Catch the first outgoing data word, leaving
    # that word at FIFO head; never acknowledge a divergent packet boundary.
    for index in (0,1):
        s=scenario(*SPECS[index]); cut=s['invoke_cut']; prefix=out/f'scenario-{index}/native-capture'/f'cut-{cut}'
        bad=bytearray(s['states'][cut][0]); bad[120]^=1
        read_size=int.from_bytes(bad[168:176],'little'); write_start=176+read_size+8
        bad[write_start+96+16]^=1
        Path(str(prefix)+'.fault').write_bytes(bad)
        damaged=scenario(*SPECS[index],fault=True)
        divergence=None
        for operation,(good_line,bad_line) in enumerate(zip(s['plan'][cut:],damaged['plan'][cut:]),cut+1):
            if good_line!=bad_line:
                require(good_line.startswith('PACKET ') and bad_line.startswith('PACKET '),'unexpected fault boundary')
                for word,(wanted,actual) in enumerate(zip(good_line.split()[1:],bad_line.split()[1:])):
                    if wanted!=actual:
                        divergence=f'operation={operation} word={word} expected={wanted} actual={actual} acknowledged=0\n'; break
                break
        require(divergence is not None,'fault boundary not located')
        for backend in BACKENDS:
            faults.append(invoke(index,backend,'corrupt',backend+'-corrupt',cut=cut,source=prefix,expected=2,divergence=divergence))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'syscall source changed during execution')
    report=dict(status='passed',scope='syscall-93 component only; session/context/CPU pending',source_inputs=bindings,commands=commands,
                continuations=continuations,invalids=invalids,faults=faults,recipe_build_identity=str(a.recipe_build_identity.resolve()) if a.recipe_build_identity else None,level1_verified=False,level2_verified=False,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n')
    try: result=audit(path)
    except Exception:
        report['status']='failed'; path.write_text(json.dumps(report,indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path),**result),indent=2))


if __name__=='__main__': main()
