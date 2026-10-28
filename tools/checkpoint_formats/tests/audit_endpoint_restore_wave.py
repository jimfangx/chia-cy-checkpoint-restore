"""Independent raw-register/handshake audit for the opt-in widget endpoint."""
from pathlib import Path
import re
from tools.checkpoint_formats.codec import require


def audit(path, ident, *, broken=False):
    top = 'checkpoint_endpoint_restore_tb'
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
    roles = {n:top+'.'+n for n in ('clock','reset','restore_hold','restore_load','restore_state',
        'restore_accepted','restore_error','ownersQuiescent','ownerError','epoch','control_state',
        'awready','wready','arready','bvalid','rvalid','requestValid','responseReady','dmaReady','streamValid')}
    roles.update({'original'+str(i):n for i,(n,_) in enumerate(originals)})
    scopes,codes,values=[],{},{}
    previous={}
    loads=rejects=held=running=0
    seen=cleared=0
    first=None
    mask=0;offset=0
    for name,width in originals:
        actual=32 if name.endswith('_addr') else ident if name.endswith('_id') or name.endswith('.responseId') else width
        mask |= ((1<<actual)-1)<<offset;offset+=width

    def sample():
        nonlocal previous,loads,rejects,held,running,seen,cleared,first
        now={n:int(values[c],2) for n,c in codes.items() if re.fullmatch('[01]+',values.get(c,'x'))}
        if now.get('clock')==1 and previous.get('clock')==0:
            p=previous
            if any('original'+str(i) not in now for i in range(len(originals))):
                require(p.get('reset')==1, 'unknown original endpoint outside reset')
                previous=now
                return
            packed=0; offset=0
            for i,(_,width) in enumerate(originals):
                key='original'+str(i)
                require(key in now, 'unknown original endpoint state after edge')
                packed |= now[key] << offset; offset += width
            require(offset==758 and now.get('control_state')==packed, 'canonical endpoint vector differs from original registers')
            if not p.get('reset'):
                if p.get('restore_accepted'):
                    require(p['restore_load']==p['restore_hold']==p['ownersQuiescent']==1 and
                            p['ownerError']==0 and p['epoch']==42 and p['restore_error']==0,
                            'accepted endpoint without independent epoch/owner certificate')
                    if packed!=p['restore_state']:
                        require(broken, 'partial original endpoint load')
                        diff=packed ^ p['restore_state']
                        if first is None:
                            first=dict(canonical_bit=(diff & -diff).bit_length()-1,
                                enabled_edges_before=running,hold=p['restore_hold'],load=p['restore_load'],
                                accepted=p['restore_accepted'],interface_acknowledged=False)
                    elif broken:
                        require(first is not None, 'compiled defect did not corrupt first complete load')
                    loads+=1;seen |= packed;cleared |= ~packed & mask
                elif p.get('restore_hold') or p.get('restore_load'):
                    old=0;offset=0
                    for i,(_,width) in enumerate(originals):
                        old |= p['original'+str(i)] << offset; offset += width
                    require(packed==old, 'held/rejected load changed original endpoint registers')
                    held+=1
                else:running+=1
            if p.get('restore_hold') or p.get('restore_load') or p.get('reset'):
                require(all(p.get(n)==0 for n in ('awready','wready','arready','bvalid','rvalid',
                    'requestValid','responseReady','dmaReady','streamValid')), 'parked endpoint acknowledged an interface')
            if p.get('restore_load') and not p.get('restore_accepted'):
                require(p.get('restore_error')==1, 'rejected load missing error')
                rejects+=1
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
    require(codes.keys()==roles.keys(), 'missing original endpoint wave fields '+str(roles.keys()-codes.keys()))
    if broken:
        require(first is not None and first['canonical_bit']==195 and first['enabled_edges_before']==0 and
                first['hold']==first['load']==first['accepted']==1,
                'compiled local restore defect escaped first held original-register load')
        return dict(original_registers=len(originals),bits=758,first_divergence=first,
                    accepted_edges=loads,enabled_edges=running)
    require(first is None, 'unexpected original endpoint load divergence')
    require(loads>=34 and rejects==2*32+4*(64-ident)+5 and held>=2*32+4*(64-ident)+10, 'incomplete common epoch load/hold/rejection waveform')
    require(seen==cleared==mask, 'incomplete per-bit original endpoint load coverage')
    return dict(original_registers=len(originals),bits=758,implemented_bits=bin(mask).count('1'),accepted_edges=loads,rejected_edges=rejects,
                held_edges=held,enabled_edges=running)
