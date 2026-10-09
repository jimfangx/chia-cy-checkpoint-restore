"""Independent artifact/edge/transaction audit, without aggregate decoders."""
import argparse
import hashlib
import json
from pathlib import Path
import re
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
    assert runtime['schema']=='firesim.aggregate.lowclock.v2'
    assert runtime['generated_encoding']=='ascending_nibble_padded_words_v1'
    assert build['simulator_build_hash']==sha((out/'simv').read_bytes())
    assert build['state_manifest_hash']==sha(canonical(runtime))
    assert runtime['generated_manifest_hash']==sha(canonical(manifest))
    assert runtime['harness_layout_hash']==sha(canonical(layout))
    assert len(manifest['state'])==2856 and sum(e['depth'] for e in manifest['state'])==13507456
    assert len(layout['records'])==29 and len(runtime['native_owners'])==16
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
        assert 'Y-2026.03-SP1_Full64' in capture and 'Y-2026.03-SP1_Full64' in restored
        assert 'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in restored
        assert 'PRODUCTION_BOOTSTRAP zero_edges=1' in restored and '*** PASSED ***' in restored
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
        results.append(dict(timing=case['timing'],cut=operation,generated_words=words,native_owners=16,
                            continuation_rows=len(continuation),memories=memories))
    assert len(summary['malformed_processes'])==21
    for label in summary['malformed_processes']:
        text=process(out/'negative'/label/'run.log')
        assert 'native_loads=0 deposits=0' in text and 'PRODUCTION_NEGATIVE zero_edges=1' in text
        assert 'PRODUCTION_AGGREGATE_LOADED' not in text and 'PRODUCTION_BOOTSTRAP' not in text
        if label=='late-harness-shape': assert 'prepared 13507456 words without deposits' in text
    text=process(out/'unsupported/run.log')
    assert 'PRODUCTION_AGGREGATE_ENTRY_ERROR' in text and 'unsupported' in text
    assert len(set(pids))==len(pids)==34
    result=dict(cases=results,fresh_processes=len(pids),generated_word_comparisons=5*13507456,
                native_owner_comparisons=80,malformed_processes=21,all_transaction_ports=40,
                production_plusargs_enabled=False,physical_fpga_validated=False)
    (out/'independent-evidence.json').write_bytes(canonical(result))
    print('PASS: independently audited full production aggregate test-entry restart',json.dumps(result))


if __name__=='__main__':main()
