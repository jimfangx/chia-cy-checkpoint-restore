"""Reconstruct the fifty original registers independently of restore readout."""
from pathlib import Path
import re
from tools.checkpoint_formats.codec import require


def audit(path, ident, shadow_bits, *, broken=False):
    top = 'checkpoint_endpoint_shadow_tb'
    dut = top + '.dut.'
    local = [('invalid',1),('producedFrames',64),('producedSnapshot',64),
             ('hostDrainedFrames',64),('counterOverflow',1),('localValid',1),
             ('localData',32),('localError',1)]
    address = [('addr',64),('len',8),('size',3),('burst',2),('lock',1),
               ('cache',4),('prot',3),('qos',4),('region',4),('id',64),('user',1)]
    adapter = [(prefix+'_'+name,width) for prefix,fields in
               [('aw',address),('wd',[('data',32),('last',1),('id',64),('strb',4),('user',1)]),('ar',address)]
               for name,width in fields]
    adapter += [(n,1) for n in ('haveAW','haveW','haveAR','badW','busy','writing','responseValid','responseError')]
    adapter += [('responseData',32),('responseId',64),('errorReadRemaining',8)]
    originals = [(dut+n,w) for n,w in local] + [(dut+'adapter.'+n,w) for n,w in adapter]
    originals += [(dut+'snapshot.'+n,w) for n,w in
                  [('occupied',1),('saved',shadow_bits),('label',64),('index',32)]]
    roles = {n:top+'.'+n for n in ('clock','reset','restore_hold','restore_load','restore_state',
        'restore_accepted','restore_error','shadow_state','shadow_current','ownersQuiescent',
        'ownerError','epoch','control_state','transport_control','awready','wready','arready','bvalid','rvalid',
        'requestValid','responseReady','dmaReady','streamValid')}
    roles.update({'original'+str(i):n for i,(n,_) in enumerate(originals)})
    roles.update({n:dut+'snapshot.io_'+n for n in ('access','write','address','data','error','cutValid','live')})
    scopes,codes,values=[],{},{}
    previous={};loads=rejects=captures=running=0
    first=None;seen=cleared=0
    # Every physically implemented bit except the constrained index must load
    # both values; index is separately checked against its precise legal range.
    mask=0;offset=0
    for name,width in originals:
        actual=32 if name.endswith('_addr') else ident if name.endswith('_id') or name.endswith('.responseId') else width
        if not name.endswith('snapshot.index'):mask |= ((1<<actual)-1)<<offset
        offset+=width
    bits=offset

    def pack(row):
        value=offset=0
        for i,(_,width) in enumerate(originals):
            require('original'+str(i) in row,'unknown original staging/endpoint register')
            value |= row['original'+str(i)] << offset;offset+=width
        return value

    def sample():
        nonlocal previous,loads,rejects,captures,running,first,seen,cleared
        now={n:int(values[c],2) for n,c in codes.items() if re.fullmatch('[01]+',values.get(c,'x'))}
        if now.get('clock')==1 and previous.get('clock')==0:
            p=previous
            if p.get('reset'):
                require(all(now.get('original'+str(i))==0 for i in range(46,50)), 'staging reset priority failed')
            else:
                actual=pack(now)
                require(actual==now['control_state']|(now['shadow_current']<<758), 'state ports omit original registers')
                if p.get('restore_accepted'):
                    require(p['restore_load']==p['restore_hold']==p['ownersQuiescent']==1 and
                            p['ownerError']==0 and p['epoch']==42 and p['restore_error']==0,
                            'staging accepted without matching owner epoch')
                    expected=p['restore_state']|(p['shadow_state']<<758)
                    if actual!=expected:
                        require(broken,'partial fifty-register restore')
                        diff=actual^expected
                        if first is None:first=dict(canonical_bit=(diff&-diff).bit_length()-1,
                            enabled_edges_before=running,interface_acknowledged=False,hold=p['restore_hold'])
                    loads+=1;seen|=actual;cleared|=~actual&mask
                elif p.get('restore_hold') or p.get('restore_load'):
                    require(actual==pack(p),'rejected staging transaction mutated original registers')
                else:
                    running+=1
                    if p.get('access') and p.get('write') and not p.get('error') and p.get('address')==0x78 and p.get('data')==1:
                        source=p['transport_control']|((pack(p)&((1<<758)-1))<<(shadow_bits-758))
                        require(p.get('cutValid')==1 and p['live']==source and now['original46']==1 and now['original47']==source and
                                now['original48']==42 and now['original49']==0,
                                'actual MMIO capture lost pre-edge payload/label')
                        captures+=1
                if p.get('restore_load') and not p.get('restore_accepted'):
                    require(p.get('restore_error')==1,'missing common rejection error');rejects+=1
            if p.get('restore_hold') or p.get('restore_load') or p.get('reset'):
                require(all(p.get(n)==0 for n in ('awready','wready','arready','bvalid','rvalid',
                    'requestValid','responseReady','dmaReady','streamValid')),'parked staging epoch acknowledged interface')
        previous=now

    for line in Path(path).read_text().splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='$scope':scopes.append(parts[2])
        elif parts[0]=='$upscope':scopes.pop()
        elif parts[0]=='$var':
            name='.'.join(scopes+[parts[4].lstrip('\\')])
            for role,target in roles.items():
                if name==target:codes[role]=parts[3]
        elif line.startswith('#'):sample()
        elif line[0] in 'bB' and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
        elif line[0] in '01xXzZ':values[line[1:].strip()]=line[0].lower()
    sample()
    require(codes.keys()==roles.keys(),'missing original fifty-register fields '+str(roles.keys()-codes.keys()))
    if broken:
        require(first is not None and first['canonical_bit']==759 and first['enabled_edges_before']==0 and first['hold']==1,
                'compiled saved-payload fault escaped first held edge')
    else:
        require(loads>=67 and rejects==39 and seen&mask==cleared&mask==mask,'incomplete common epoch coverage')
    return dict(original_registers=50,bits=bits,accepted_edges=loads,rejected_edges=rejects,
                captures=captures,enabled_edges=running,first_divergence=first)
