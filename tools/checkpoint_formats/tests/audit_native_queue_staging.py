"""Independent streaming full-debug audit of the shared native staging graft."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import tempfile
from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.verify_native_queue_staging import ROOT, RUNS, audit, sha


def compiled_mutations(directory, receipt):
    """Reconstruct each compiled fault independently of the mutation launcher.

    A waveform divergence alone cannot identify the RTL fault that was tested.
    Require immutable, receipt-bound source bytes for all three compiled cases.
    """
    original = (directory/'generated/Staged-generated.native-region-graft.sv').read_text()
    cases = {
        'compiled-staging-swap.sv': (
            '.live_state(capture_native_state),',
            '.live_state({capture_native_state[1663:0],capture_native_state[6655:1664]}),'),
        'compiled-premature.sv': (
            'capture_request_valid && staged_permission', 'capture_request_valid'),
        'compiled-busy-release.sv': (
            'capture_response_ready && staged_permission', 'capture_response_ready'),
    }
    result = {}
    for name, (before, after) in cases.items():
        path = directory/name
        require(original.count(before) == 1, 'ambiguous original compiled mutation '+name)
        require(path.is_file() and name in receipt['artifacts'], 'unbound compiled mutation '+name)
        digest = sha(path)
        require(receipt['artifacts'][name] == digest, 'changed compiled mutation '+name)
        require(path.read_text() == original.replace(before, after), 'wrong compiled mutation '+name)
        result[name] = digest
    return result


def wave(path, observations, expected_sha=None, *, broken=None):
    top='native_queue_graft_tb.'
    adapter=top+'dut.checkpoint_region_readout_adapter.'
    wanted={top+n:n for n in ('clock','capture_clock_mask','capture_read_enable','capture_reset',
        'capture_request_valid','capture_request_ready','capture_response_valid','capture_response_ready',
        'capture_response_data','capture_native_state','capture_snapshot_request','capture_snapshot_ready',
        'capture_snapshot_release','capture_snapshot_owners_present','capture_snapshot_target_cycle',
        'capture_snapshot_valid','capture_snapshot_borrow_enable','capture_snapshot_word_address',
        'capture_snapshot_word_data','capture_snapshot_word_error','capture_snapshot_state','capture_snapshot_control_state')}
    wanted.update({adapter+n:n for n in ('raw_request_ready','raw_response_valid','raw_response_data',
        'region_request_valid','region_request_ready','region_response_valid','region_response_ready')})
    wanted.update({adapter+'native_snapshot.'+n:n for n in ('payload','occupied','cut_cycle','error')})
    fields=[]
    for q,obs in enumerate(observations):
        for f in obs['state']:
            role=f'q{q}.'+f['emitted_register'];fields.append((role,q*1664+f['offset'],f['width']))
            wanted[top+'dut.'+role]=role
    fields.sort(key=lambda x:x[1],reverse=True)
    codes,values,scopes,previous={},{},[],{}
    code_set=set();raw_hash=hashlib.sha256();captures=[];seen=[]
    native_checks=owner_checks=permission_checks=acks=live_changes=0
    first=None;initialized=False
    def expand(v,w):return v.rjust(w,v[0] if v[0] in 'xz' else '0')
    def vector(d):return ''.join(expand(d[n],w) for n,_,w in fields)
    def integer(d,n):
        require(n in d and re.fullmatch('[01]+',d[n]) is not None,'unknown control '+n)
        return int(d[n],2)
    def stop(why,d):
        nonlocal first
        if first is None:first=dict(signal=why,target_cycle=integer(d,'capture_snapshot_target_cycle'),acknowledged_words=acks)
        require(broken is not None,why)
    def sample():
        nonlocal previous,native_checks,owner_checks,permission_checks,acks,live_changes,first,initialized
        now={n:values[c] for n,c in codes.items() if c in values}
        if not now:return
        if len([n for n,_,_ in fields if n in now])==56 and 'capture_native_state' in now:
            require(vector(now)==expand(now['capture_native_state'],6656),'live vector differs from all 56 original native register fields')
            native_checks+=1
        if now.get('clock')=='1' and previous.get('clock')=='0':
            if previous.get('capture_response_valid')==previous.get('capture_response_ready')=='1':acks+=1
            if previous.get('capture_reset')=='1':initialized=True
            elif previous.get('capture_snapshot_request')==previous.get('capture_snapshot_ready')=='1':
                expected=vector(previous)
                if expand(now['payload'],6656)!=expected:stop('one preedge vector and cut',previous)
                require(integer(now,'cut_cycle')==integer(previous,'capture_snapshot_target_cycle'),'wrong preedge cut label')
                captures.append(dict(target_cycle=integer(now,'cut_cycle'),native_msb_first=expected,
                    unresolved_fields=[n for n,_,_ in fields if re.search('[xz]',previous[n])]))
                seen.append(set())
        if initialized and all(n in now for n in ('payload','occupied','cut_cycle','error')):
            packed=expand(now['error'],6)+expand(now['cut_cycle'],64)+now['occupied']+expand(now['payload'],6656)
            require(packed==expand(now['capture_snapshot_control_state'],6727),'readback omitted original staging/control storage')
            require(expand(now['capture_snapshot_state'],6656)==expand(now['payload'],6656),'saved output differs from actual payload registers')
            owner_checks+=1
            if now.get('occupied')=='1' and captures:
                if expand(now['payload'],6656)!=captures[-1]['native_msb_first']:stop('staged vector changed',now)
                if expand(now['capture_native_state'],6656)!=captures[-1]['native_msb_first']:live_changes+=1
            if now.get('capture_snapshot_valid') in ('0','1'):
                permission=integer(now,'capture_snapshot_valid')
                require(integer(now,'capture_snapshot_borrow_enable')==permission,'borrow permission differs from staging validity')
                require(integer(now,'capture_request_ready')==permission*integer(now,'raw_request_ready') and
                    integer(now,'capture_response_valid')==permission*integer(now,'raw_response_valid'),'ungated outer handshake')
                require(expand(now['capture_response_data'],64)==(expand(now['raw_response_data'],64) if permission else '0'*64),
                    'response payload escaped staging permission')
                internal=(integer(now,'region_request_valid') & integer(now,'region_request_ready')) | (
                    integer(now,'region_response_valid') & integer(now,'region_response_ready'))
                if not permission and internal:stop('hidden endpoint acknowledgement',now)
                if permission:
                    require(now['capture_clock_mask']==now['capture_read_enable']==now['capture_snapshot_owners_present']=='1' and
                        now['capture_reset']==now['capture_snapshot_release']=='0' and integer(now,'error')==0 and
                        integer(now,'cut_cycle')==integer(now,'capture_snapshot_target_cycle'),'unsafe staging permission')
                address=integer(now,'capture_snapshot_word_address')
                readable=permission and address<104
                require(integer(now,'capture_snapshot_word_error')==int(not readable),'wrong staged word error')
                expected=expand(now['payload'],6656)[6656-(address+1)*64:6656-address*64] if readable else '0'*64
                require(expand(now['capture_snapshot_word_data'],64)==expected,'staged serial word differs from original payload register')
                if readable and captures:seen[-1].add(address)
                permission_checks+=1
        previous=now
    with (gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')) as stream:
        for raw in stream:
            raw_hash.update(raw);kind=raw[:1]
            if kind==b'$':
                p=raw.decode('ascii').split()
                if p[0]=='$scope':scopes.append(p[2])
                elif p[0]=='$upscope':scopes.pop()
                elif p[0]=='$var':
                    n='.'.join(scopes+[p[4].lstrip('\\')])
                    if n in wanted:codes[wanted[n]]=p[3];code_set.add(p[3].encode())
            elif kind==b'#':sample()
            elif kind in (b'b',b'B'):
                value,_,code=raw.rstrip().rpartition(b' ')
                if code in code_set:values[code.decode()]=value[1:].decode().lower()
            elif kind in (b'0',b'1',b'x',b'X',b'z',b'Z'):
                code=raw[1:].rstrip()
                if code in code_set:values[code.decode()]=kind.decode().lower()
    sample()
    require(codes.keys()==set(wanted.values()),'missing independent original waveform owners '+str(set(wanted.values())-codes.keys()))
    if expected_sha:require(raw_hash.hexdigest()==expected_sha,'archive does not contain the original debug waveform bytes')
    if broken:
        require(first is not None and first['acknowledged_words']==0 and first['target_cycle']==9001,'compiled fault escaped first cut before any acknowledgement')
        if broken=='semantic':require(first['signal']=='one preedge vector and cut','wrong first semantic divergence')
        else:require(first['signal']=='hidden endpoint acknowledgement','wrong first handshake divergence')
    else:
        require(first is None and [c['target_cycle'] for c in captures]==[9001,9033,9065,9097] and
            all(s==set(range(104)) for s in seen) and acks==196624 and live_changes>100 and native_checks>1000000,
            'incomplete independent native capture/readback/continuation scope')
    return dict(status='pass',original_native_fields=56,native_bits=6656,control_bits=6727,
        captures=captures,serial_words_per_cut=[len(s) for s in seen],original_word_acknowledgements=acks,
        native_vector_samples=native_checks,staging_owner_samples=owner_checks,permission_samples=permission_checks,
        changed_live_samples=live_changes,first_divergence=first,raw_sha256=raw_hash.hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--eda',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS),'evidence must be under runs');a.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='audit-',dir=a.out.resolve()));receipt=a.eda/'summary.json';d=json.loads(receipt.read_text())
    require(d['status']=='pass' and d['backend']=='eda','successful fresh EDA staging receipt required')
    require(all(sha(ROOT/n)==h for n,h in d['sources'].items()),'stale staging verification sources')
    for group in ('inputs','artifacts'):
        for n,h in d[group].items():require(sha(a.eda/n)==h,'changed staging evidence '+n)
    extra=compiled_mutations(a.eda,d)
    _,obs=audit(a.eda/'generated')
    results={}
    results['healthy']=wave(a.eda/'native-queue-staging.vcd.gz',obs,d['waveform']['original_sha256'])
    for name,kind in (('mutation','semantic'),('mutation-premature','request'),('mutation-busy-release','response')):
        results[name]=wave(a.eda/(name+'.vcd'),obs,broken=kind)
    doc=dict(status='pass',backend='eda',scope='independent complete original-field/staging/control/permission debug audit; no physical FPGA capture',
        physical_fpga_capture=False,results=results,eda_receipt=dict(path=str(receipt),sha256=sha(receipt)),
        compiled_mutation_sources=extra,sources={str(Path(__file__).relative_to(ROOT)):sha(__file__)})
    (out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__':main()
