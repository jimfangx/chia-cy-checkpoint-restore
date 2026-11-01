"""Independent raw-register audit of the stateless, held readout capture port."""
from pathlib import Path
import re
from tools.checkpoint_formats.codec import require


def audit(path, *, top='live_readout_restore_tb.', owner='dut.', owner_bit=None, broken=False):
    names=('clock','reset','capture_hold','capture_address','capture_valid','capture_error','capture_data',
           'permission','request_valid','response_ready','restore_hold','restore_load','restore_ready',
           'request_ready','response_valid','original_request_valid','original_response_ready')
    registers=('pending','snapshot_owner','snapshot_bank.saved_data','snapshot_bank.saved_error',
               'snapshot_bank.pending','snapshot_bank.failed')
    targets={n:top+n for n in names}
    targets.update({n:top+owner+n for n in registers})
    codes,values,scopes,previous={},{},[],{}
    captures=held=acks=0
    seen=set();first=None
    def sample():
        nonlocal previous,captures,held,acks,first
        now={n:int(values[c],2) for n,c in codes.items() if re.fullmatch('[01]+',values.get(c,'x'))}
        p=previous
        # Inspect settled low-phase observations too: a first-word corruption
        # must stop before the next accepting raw clock edge.
        if now.get('capture_valid')==1 and now.get('capture_error')==0:
            require(all(n in now for n in registers),'unknown settled original capture register')
            packed=(now['pending']|now['snapshot_owner']<<1|now['snapshot_bank.saved_data']<<2|
                    now['snapshot_bank.saved_error']<<66|now['snapshot_bank.pending']<<67|
                    now['snapshot_bank.failed']<<68)^(0 if owner_bit is None else 1<<owner_bit)
            address=now.get('capture_address')
            require(address in (0,1),'settled capture admitted an invalid word')
            if now.get('capture_data')!=((packed>>(64*address))&((1<<64)-1)):
                require(broken,'omitted or corrupted settled original capture bit')
                if first is None:first=dict(word=address,acknowledgements_before=acks)
        if now.get('clock')==1 and p.get('clock')==0:
            if p.get('response_valid') and p.get('response_ready'):
                require(first is None,'acknowledgement after first capture divergence')
                acks+=1
            if p.get('capture_hold'):
                require(all(p.get(n)==0 for n in ('request_ready','response_valid','original_request_valid',
                    'original_response_ready','restore_ready')),'capture hold acknowledged a bank/load edge')
                def pack(x):
                    require(all(n in x for n in registers),'unknown original capture register')
                    return (x['pending']|x['snapshot_owner']<<1|x['snapshot_bank.saved_data']<<2|
                            x['snapshot_bank.saved_error']<<66|x['snapshot_bank.pending']<<67|
                            x['snapshot_bank.failed']<<68)
                if not p.get('reset'):
                    require(pack(now)==pack(p),'capture hold changed original owner')
                    held+=1
                safe=not any(p.get(n) for n in ('reset','permission','request_valid','response_ready','restore_hold','restore_load'))
                require(p.get('capture_valid')==int(safe),'unsafe capture qualification')
                address=p.get('capture_address')
                require(address is not None,'unknown capture address')
                error=not safe or address>=2
                require(p.get('capture_error')==int(error),'missing explicit capture error')
                data=0
                if not error:
                    packed=pack(p)^(0 if owner_bit is None else 1<<owner_bit)
                    data=(packed>>(64*address))&((1<<64)-1)
                    captures+=1;seen.add(address)
                if p.get('capture_data')!=data:
                    require(broken and not error,'omitted or corrupted original capture bit')
                    if first is None:
                        first=dict(word=address,acknowledgements_before=acks)
        previous=now
    for line in Path(path).read_text().splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='$scope':scopes.append(parts[2])
        elif parts[0]=='$upscope':scopes.pop()
        elif parts[0]=='$var':
            name='.'.join(scopes+[parts[4].lstrip('\\')])
            for role,target in targets.items():
                if target==name:codes[role]=parts[3]
        elif line.startswith('#'):sample()
        elif line[0] in 'bB' and len(parts)==2:values[parts[1]]=parts[0][1:].lower()
        elif line[0] in '01xXzZ':values[line[1:].strip()]=line[0].lower()
    sample()
    require(codes.keys()==targets.keys(),'missing raw capture fields '+str(targets.keys()-codes.keys()))
    if broken:
        require(first==dict(word=0,acknowledgements_before=0) and acks==0,'capture corruption missed first word')
    else:require(captures>=2 and seen=={0,1} and held>=2 and first is None,'incomplete two-word capture')
    return dict(bits=69,original_registers=6,capture_word_samples=captures,held_edges=held,
                acknowledgements=acks,first_divergence=first)
