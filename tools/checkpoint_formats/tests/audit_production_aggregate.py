"""Independent artifact/edge/transaction audit, without aggregate decoders."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct


def diagnostic(path):
    data=path.read_bytes(); assert data[:8]==b'FSDIAG01'
    pos=8
    def integer():
        nonlocal pos
        value,=struct.unpack_from('<Q',data,pos);pos+=8;return value
    def blob():
        nonlocal pos
        size=integer();value=data[pos:pos+size];assert len(value)==size;pos+=size;return value
    operation=integer();count=integer();owners={}
    for _ in range(count):
        name=blob().decode();schema=blob().decode();payload=blob()
        assert name not in owners;owners[name]=(schema,payload)
    assert pos==len(data)
    return operation,owners


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')
def sha(value): return hashlib.sha256(value).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    summary=json.loads((out/'summary.json').read_text())
    manifest=json.loads((out/'generated-manifest.json').read_text())
    runtime=json.loads((out/'runtime-manifest.json').read_text())
    layout=json.loads((out/'harness-layout.json').read_text())
    build=json.loads((out/'aggregate-build.json').read_text())
    assert runtime['schema'] in ('firesim.aggregate.lowclock.v2','firesim.aggregate.lowclock.v3')
    bound=runtime['schema']=='firesim.aggregate.lowclock.v3'
    owner_count=17 if bound else 16
    live=summary.get('native_live_capture_verified',False)
    if bound:
        native_inputs=json.loads((out/'native-build-inputs.json').read_text())
        assert sha(canonical(native_inputs))==runtime['native_build_hash']
        root=Path(__file__).resolve().parents[3]
        assert native_inputs['compiler']=='/usr/bin/g++-13'
        assert native_inputs['vcs_home']=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1'
        assert native_inputs['generated_build']==layout['generated_build_hash']
        if summary.get('real_production_entry_verified'):
            assert '-DFS_CHECKPOINT_ENTRY' in native_inputs['cflags']
            assert 'sims/firesim/sim/midas/src/main/cc/entry.cc' in native_inputs['translation_units']
            command=json.loads((out/'build.log').read_text().splitlines()[1].removeprefix('argv='))
            assert str(root/'sims/firesim/sim/midas/src/main/cc/entry.cc') in command
            assert '-DFS_CHECKPOINT_ENTRY' in command[command.index('-CFLAGS')+1]
        assert all(sha((root/name).read_bytes())==value for name,value in native_inputs['sources'].items())
        if live:
            for name in ('durable_capture.cc','durable_publish.cc'):
                assert 'tools/checkpoint_formats/'+name in native_inputs['translation_units']
        assert runtime['cut_contract']==dict(
            target_cycle_owner='FPGATop.FASEDMemoryTimingModel_0.model.tCycle',
            target_cycle_path='emul.FPGATop.FASEDMemoryTimingModel_0.model.tCycle',
            target_cycle_semantics='fased_model_tCycle_at_settled_host_negedge',
            host_sample_semantics='completed_host_rising_edges_before_cut')
    assert runtime['generated_encoding']=='ascending_nibble_padded_words_v1'
    assert build['simulator_build_hash']==sha((out/'simv').read_bytes())
    assert build['state_manifest_hash']==sha(canonical(runtime))
    assert runtime['generated_manifest_hash']==sha(canonical(manifest))
    assert runtime['harness_layout_hash']==sha(canonical(layout))
    assert len(manifest['state'])==2856 and sum(e['depth'] for e in manifest['state'])==13507456
    assert len(layout['records'])==29 and len(runtime['native_owners'])==owner_count
    pids=[];results=[]
    def process(path):
        text=path.read_text();pids.append(int(re.search(r'fresh_process_pid=(\d+)',text)[1]));return text
    references={}
    for timing in ('default','randomized'):
        path=out/timing/'reference'
        text=process(path/'run.log');assert '*** PASSED ***' in text
        references[timing]=(path/'ports.trace').read_text().splitlines(keepends=True)
    for case in summary['cases']:
        path=out/case['timing']/f'cut-{case["cut"]}'
        capture=process(path/'capture.log');restored=process(path/'restore.log')
        if live:
            assert case['native_live_capture_verified']
            command=json.loads(capture.splitlines()[1].removeprefix('argv='))
            assert command.count('+test-live-capture='+str(path/'capture.fsckpt'))==1
            publications=re.findall(r'FS_DURABLE_LIVE_CAPTURE_PUBLISHED host_sample=(\d+) no_loads=1 no_deposits=1',capture)
            assert publications==[str(case['host_sample'])]
            assert 'deposited' not in capture and 'PRODUCTION_AGGREGATE_LOADED' not in capture
        assert 'Y-2026.03-SP1_Full64' in capture and 'Y-2026.03-SP1_Full64' in restored
        assert 'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in restored
        assert 'PRODUCTION_BOOTSTRAP zero_edges=1' in restored and '*** PASSED ***' in restored
        if summary.get('real_production_entry_verified'):
            assert restored.index('FS_CHECKPOINT_ENTRY_CONFIGURED before_platform=1') < restored.index(
                'FS_CHECKPOINT_ENTRY_CONSTRUCTED before_run=1') < restored.index(
                'PRODUCTION_AGGREGATE_RESERVED no_workers=1') < restored.index(
                'FS_CHECKPOINT_ENTRY_RESERVED before_run=1') < restored.index(
                'prepared 29 words without deposits')
            assert 'FS_CHECKPOINT_ENTRY_RESERVED' not in capture
        assert restored.index('prepared 29 words without deposits') < restored.index('deposited 29 words')
        assert restored.index('verified 13507456 words before next edge') < restored.index('PRODUCTION_BOOTSTRAP')
        assert restored.index('verified 29 words before next edge') < restored.index('PRODUCTION_BOOTSTRAP')
        data=(path/'capture.fsckpt').read_bytes()
        assert data[:8]==b'FSCKPT\x00\x01' and len(data)==48+struct.unpack('>Q',data[8:16])[0]
        assert hashlib.sha256(data[:-32]).digest()==data[-32:]
        doc=json.loads(data[16:-32]);assert canonical(doc)==data[16:-32] and doc['build']==build
        rows={r['owner']:r for r in doc['records']}
        assert len(rows)==len(doc['records']) and list(rows)==sorted(rows)
        operation,owners=diagnostic(path/'software.diag');assert operation==case['cut']
        if bound:
            identity=(path/'runtime-identity.bin').read_bytes();pos=0
            def u64():
                nonlocal pos
                n,=struct.unpack_from('<Q',identity,pos);pos+=8;return n
            def string():
                nonlocal pos
                size=u64();value=identity[pos:pos+size].decode();pos+=size;return value
            assert string()=='FCFS_RUNTIME1'
            assert [u64() for _ in range(4)]==[4194304,1000000,
                7 if case['timing']=='randomized' else 1,
                2**64-1 if case['timing']=='randomized' else 0]
            elf_files=[]
            for _ in range(u64()):
                filename=string();digest=identity[pos:pos+32];pos+=32
                assert Path(filename).is_absolute() and hashlib.sha256(Path(filename).read_bytes()).digest()==digest
                elf_files.append(filename)
            assert pos==len(identity) and elf_files==sorted(set(elf_files))
            assert str(out/'simv') in elf_files and any('_archive_' in f for f in elf_files)
            assert any('libcrypto.so' in f for f in elf_files) and any('libvcsnew.so' in f for f in elf_files)
            owners['runtime/compatibility']=('firesim.runtime.fcfs-config-and-loaded-elf.v1',identity)
        expected={'cut/host_sample'}
        words=0
        with (path/'generated.jsonl').open() as stream:
            header=json.loads(stream.readline())
            assert header['sample_phase']=='settled_host_negedge_parked_driver'
            sample=header['host_sample'];assert sample==case['host_sample']
            assert sample==int(re.search(r'PRODUCTION_CUT host_edges=(\d+)',capture)[1])
            scalars={}
            for entry in manifest['state']:
                captured=json.loads(stream.readline())
                assert (captured['state_id'],captured['width'],captured['depth'])==(
                    entry['state_id'],entry['width'],entry['depth'])
                assert len(captured['values'])==entry['depth']
                digits=(entry['width']+3)//4
                assert all(len(v)==digits and int(v,16).bit_length()<=entry['width'] for v in captured['values'])
                name='generated-entry/'+entry['hierarchy'];expected.add(name)
                assert rows[name]==dict(owner=name,width=4*digits*entry['depth'],value=''.join(captured['values']))
                if entry['kind']=='register': scalars[entry['hierarchy']]=int(captured['values'][0],16)
                if entry['adapter']=='metasim-bufgce-v1': assert captured['values']==['0']
                words+=entry['depth']
            assert not stream.read()
        assert words==13507456
        assert doc['target_cycle']==scalars['FPGATop.FASEDMemoryTimingModel_0.model.tCycle']==case['target_cycle']
        assert rows['cut/host_sample']==dict(owner='cut/host_sample',width=64,value=f'{sample:016x}')
        loaded=dict(line.split() for line in (path/'loaded-native.txt').read_text().splitlines())
        assert list(loaded)==[r['owner'] for r in runtime['native_owners']]
        memories=[]
        for owner in runtime['native_owners']:
            name=owner['owner'];schema,payload=owners[name];assert schema==owner['schema']
            expected.add('host/'+name)
            assert rows['host/'+name]==dict(owner='host/'+name,width=len(payload)*8,value=payload.hex())
            assert loaded[name]==payload.hex()
            if name.startswith('runtime/functional-memory/'):
                fields=struct.unpack_from('<13Q',payload);assert fields[5]==4*1024*1024
                memories.append(dict(cycle=fields[7],inflight_write=bool(fields[8])))
        magic,bits=struct.unpack_from('<QQ',owners['diagnostic/harness-banks'][1]);assert magic==0x3153424F534E5248
        packed=int.from_bytes(owners['diagnostic/harness-banks'][1][16:],'little')
        offset=sum(r['width'] for r in layout['records'][:-2]);assert bits==offset+67 and packed>>offset==0
        for bank in layout['records']:
            name='harness/'+bank['owner'];expected.add(name)
            if bank['owner'].endswith(('.reset','.fin')):value=0
            else:offset-=bank['width'];value=(packed>>offset)&((1<<bank['width'])-1)
            assert rows[name]==dict(owner=name,width=bank['width'],value=f'{value:0{(bank["width"]+3)//4}x}')
        assert set(rows)==expected
        reference=references[case['timing']]
        assert (path/'capture.trace').read_text().splitlines(keepends=True)==reference
        continuation=(path/'restore.trace').read_text().splitlines(keepends=True)
        assert continuation==reference[sample:] and len(continuation)==case['continuation_rows']
        if operation==699275:
            assert any(m['inflight_write'] for m in memories)
            assert scalars['FPGATop.FASEDMemoryTimingModel_0.model.SatUpDownCounter_1.value']>0
        results.append(dict(timing=case['timing'],cut=operation,generated_words=words,native_owners=owner_count,
                            continuation_rows=len(continuation),memories=memories))
    public=summary.get('public_durable_restore_enabled',False)
    assert len(summary['malformed_processes'])==(0 if public else 23 if bound else 21)
    for label in summary['malformed_processes']:
        text=process(out/'negative'/label/'run.log')
        assert 'native_loads=0 deposits=0' in text and 'PRODUCTION_NEGATIVE zero_edges=1' in text
        assert 'PRODUCTION_AGGREGATE_LOADED' not in text and 'PRODUCTION_BOOTSTRAP' not in text
        if label=='late-harness-shape': assert 'prepared 13507456 words without deposits' in text
    if not public:
        text=process(out/'unsupported/run.log')
        error='FS_CHECKPOINT_ENTRY_ERROR' if summary.get('real_production_entry_verified') else 'PRODUCTION_AGGREGATE_ENTRY_ERROR'
        assert error in text and 'unsupported' in text
        if summary.get('real_production_entry_verified'):
            assert 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text
    if bound and not public:
        assert summary['runtime_compatibility_rejections']==['memory','horizon','host-delay','seed','loaded-library','preload-hook']
        for label in summary['runtime_compatibility_rejections']:
            text=process(out/'runtime-negative'/label/'run.log')
            if label=='preload-hook':
                assert 'unsupported LD_PRELOAD/LD_AUDIT library hooks' in text
                assert 'PRODUCTION_AGGREGATE_RESERVED' not in text
                continue
            errors={'memory':'incompatible AXI/backing-memory geometry',
                    'horizon':'incompatible scheduler configuration',
                    'host-delay':'incompatible timing configuration',
                    'seed':'incompatible timing configuration',
                    'loaded-library':'configuration/loaded ELF changed after entry'}
            assert errors[label] in text
            assert 'native_loads=0 deposits=0' in text and 'PRODUCTION_NEGATIVE zero_edges=1' in text
            assert 'PRODUCTION_AGGREGATE_LOADED' not in text and 'PRODUCTION_BOOTSTRAP' not in text
        text=(out/'negative/target-cycle/run.log').read_text()
        assert 'target cycle disagrees with bound counter' in text
    public_rejections=0
    if public:
        inputs=json.loads((out/'native-build-inputs.json').read_text())
        assert 'tools/checkpoint_formats/durable_restore_entry.cc' in inputs['translation_units']
        assert 'tools/checkpoint_formats/durable_restore.cc' in inputs['translation_units']
        for case in summary['cases']:
            path=out/case['timing']/f'cut-{case["cut"]}'
            text=(path/'restore.log').read_text()
            argv=json.loads(text.splitlines()[1].removeprefix('argv='))
            assert f'+fs-restore={path/"capture.fsckpt"}' in argv
            assert not any(a.startswith('+test-aggregate=') for a in argv)
            assert text.index('FS_DURABLE_RESTORE_VALIDATED before_platform=1')<text.index('FS_CHECKPOINT_ENTRY_CONFIGURED')
        for case in summary['public_restore_rejections']:
            text=process(Path(case['log']))
            assert text.endswith('exit=1\n')
            assert 'PRODUCTION_AGGREGATE_LOADED' not in text and 'PRODUCTION_BOOTSTRAP' not in text
            if case['stage']=='native':
                assert 'native_loads=0 deposits=0' in text and 'PRODUCTION_REJECTION zero_edges=1' in text
            else: assert 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text
            public_rejections+=1
        for name in summary['public_runtime_rejections']:
            text=process(out/'public-runtime-negative'/name/'run.log')
            assert text.endswith('exit=1\n') and 'native_loads=0 deposits=0' in text
            assert 'PRODUCTION_REJECTION zero_edges=1' in text;public_rejections+=1
        for index in range(summary['public_dispatch_rejections']):
            text=process(out/'public-dispatch-negative'/str(index)/'run.log')
            assert text.endswith('exit=1\n') and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text;public_rejections+=1
        for name in ('symlink','fifo','directory'):
            special_inputs=summary.get('public_special_file_inputs')
            if special_inputs is None:
                log=out/'public-special-negative'/name/'run.log'
            else:
                path=Path(special_inputs[name])
                assert path.parent.parent==out/'public-special-negative'/name
                mode=path.lstat().st_mode
                assert {'symlink':stat.S_ISLNK, 'fifo':stat.S_ISFIFO,
                        'directory':stat.S_ISDIR}[name](mode)
                log=path.parent/'run.log'
            text=process(log)
            if special_inputs is not None:
                argv=json.loads(text.splitlines()[1].removeprefix('argv='))
                assert f'+fs-restore={path}' in argv
            assert text.endswith('exit=1\n') and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text;public_rejections+=1
    assert len(set(pids))==len(pids)==(12+public_rejections if public else 42 if bound else 34)
    result=dict(cases=results,fresh_processes=len(pids),generated_word_comparisons=5*13507456,
                native_owner_comparisons=5*owner_count,malformed_processes=len(summary['malformed_processes']),all_transaction_ports=40,
                runtime_compatibility_rejections=len(summary['public_runtime_rejections']) if public else 6 if bound else 0,
                real_production_entry_verified=summary.get('real_production_entry_verified',False),
                native_live_capture_verified=live,live_publications=5 if live else 0,
                production_plusargs_enabled=False,public_durable_restore_enabled=public,
                public_restore_rejections=public_rejections,physical_fpga_validated=False)
    (out/'independent-evidence.json').write_bytes(canonical(result))
    print('PASS: independently audited full production aggregate '+('public durable restore' if public else 'test-entry restart'),json.dumps(result))


if __name__=='__main__':main()
