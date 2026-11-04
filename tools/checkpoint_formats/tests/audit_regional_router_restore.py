"""Independent wiring and raw-register audits for generated multi-router restore."""
import json
from pathlib import Path
import re
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_native_regions import audit as audit_regions, digest
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha


def audit(directory):
    directory = Path(directory)
    result = audit_regions(directory)
    binding = json.loads((directory/'FireSim-generated.native-region-graft.json').read_text())
    observation = binding['router_state_observation']
    restore = binding['router_state_restore']
    n = result['regions']
    owner_bits = max(1, (n-1).bit_length())
    shared = owner_bits + 2
    bits = shared + 2*n
    require(not result['local_shells'] and observation['bits'] == restore['bits'] == bits and
            observation['restore_supported'] is True and restore['version'] == 1 and
            restore['scope'] == 'complete_shared_and_physical_router_registers_only' and
            restore['port_prefix'] == 'capture_router_restore_' and
            restore['observation_port'] == 'capture_router_state' and
            restore['endpoint_state_restored'] is False and restore['global_cut_restored'] is False and
            restore['extra_storage_bits'] == 0, 'changed router-only restore ownership')
    instance=binding['adapter_instance']
    expected_owners=[dict(instance=instance+'.router',definition='CheckpointRegionStateRouter',offset=0,
        bits=shared,fields_lsb0=['pending','invalid','owner'])]
    expected_owners += [dict(instance=instance+f'.region{i}.router',definition='CheckpointPhysicalStateRouter',
        offset=shared+2*i,bits=2,fields_lsb0=['pending','selected_ce']) for i in range(n)]
    require(observation['owners']==expected_owners, 'incomplete, aliased or overlapping router owner')
    require(restore['load_contract']=='one_raw_positive_edge_all_routers_after_hold_mask_read_permission_and_complete_owner_validation' and
        restore['rejection_contract']=='no_partial_router_load_or_router_handshake_on_unsafe_load' and
        restore['readback_contract']=='retain_hold_deassert_load_compare_entire_observation_before_release',
        'changed complete load/readback contract')
    root=Path(__file__).resolve().parents[3]
    for generated,source in [('router','CheckpointRegionStateRouter'),('physical-router','CheckpointPhysicalStateRouter')]:
        require(sha(directory/f'FireSim-generated.native-region-graft-{generated}.sv') ==
                sha(root/f'sims/firesim/sim/midas/src/main/verilog/{source}.sv'), 'router resource differs from current implementation')
    modules = parse_modules((directory/'grafted.fir').read_text())
    for name in (binding['root'],binding['adapter_module']):
        ports=modules[name]['ports']
        for pin,direction,width in [('hold','input',1),('load','input',1),('state','input',bits),
                                     ('ready','output',1),('error','output',1)]:
            require(ports.get('capture_router_restore_'+pin)==(direction,f'UInt<{width}>'), 'changed restore port shape')
    rtl=(directory/'FireSim-generated.native-region-graft.sv').read_text()
    fragments=[
        'wire router_restore_active = capture_router_restore_hold || capture_router_restore_load;',
        f"wire router_restore_owner_valid = {{1'b0,capture_router_restore_state[2 +: {owner_bits}]}} < {owner_bits+1}'d{n};",
        'assign capture_router_restore_ready = capture_router_restore_hold && capture_clock_mask &&\n    capture_read_enable && router_restore_owner_valid && !capture_reset;',
        'wire router_restore_accept = capture_router_restore_load && capture_router_restore_ready;',
        'assign capture_router_restore_error =\n    (router_restore_active && (!capture_clock_mask || !capture_read_enable)) ||\n    (capture_router_restore_load && !capture_router_restore_ready) ||\n    shared_restore_error || (|physical_restore_error);',
        '.RESTORE_SUPPORTED(1)) router(',
        '.restore_hold(router_restore_active), .restore_load(router_restore_accept),',
        f'.restore_state(capture_router_restore_state[0 +: {shared}]), .restore_error(shared_restore_error),',
        f'.capture_state(capture_router_state[0 +: {shared}]),']
    for fragment in fragments:require(rtl.count(fragment)==1, 'unqualified shared restore: '+fragment)
    for i in range(n):
        for fragment in ['.capture_router_restore_hold(router_restore_active)',
                         '.capture_router_restore_load(router_restore_accept)',
                         f'.capture_router_restore_state(capture_router_restore_state[{shared+2*i} +: 2])',
                         f'.capture_router_restore_error(physical_restore_error[{i}])']:
            require(rtl.count(fragment)==(n if 'state[' not in fragment and 'error[' not in fragment else 1),
                    'crossed physical restore connection: '+fragment)
        leaf=(directory/f'FireSim-generated.native-region-graft-{i}.sv').read_text()
        for fragment in ['.RESTORE_SUPPORTED(1)) router(',
                         '.restore_hold(capture_router_restore_hold)', '.restore_load(capture_router_restore_load)',
                         '.restore_state(capture_router_restore_state)', '.restore_error(capture_router_restore_error)',
                         '.capture_state(capture_router_state)']:
            require(leaf.count(fragment)==1,'disabled/crossed physical restore: '+fragment)
    result.update(router_bits=bits,restore_owners=n+1,endpoint_restore=False,global_cut_restore=False)
    return result


def negatives(directory, out):
    directory,out=Path(directory),Path(out)
    name='FireSim-generated.native-region-graft.sv'
    defects=[(name,'capture_router_restore_load && capture_router_restore_ready','capture_router_restore_load'),
             (name,'capture_router_restore_hold && capture_clock_mask','capture_router_restore_hold || capture_clock_mask'),
             (name,'capture_read_enable && router_restore_owner_valid','capture_read_enable || router_restore_owner_valid'),
             (name,'capture_router_restore_state[0 +: 3]','capture_router_restore_state[1 +: 3]'),
             (name,'.capture_router_restore_load(router_restore_accept)','.capture_router_restore_load(1\'b1)'),
             (name,'capture_router_restore_state[3 +: 2]','capture_router_restore_state[4 +: 2]'),
             ('FireSim-generated.native-region-graft-0.sv','.RESTORE_SUPPORTED(1)','.RESTORE_SUPPORTED(0)'),
             ('FireSim-generated.native-region-graft-0.sv','.restore_hold(capture_router_restore_hold)',".restore_hold(1'b0)")]
    out.mkdir(parents=True,exist_ok=True)
    rejected=[]
    for i,(file,old,new) in enumerate(defects):
        dest=out/str(i);dest.mkdir()
        for source in directory.iterdir():
            if source.is_file():(dest/source.name).symlink_to(source.resolve())
        p=dest/file;s=p.read_text();require(old in s,'missing intended negative mutation')
        p.unlink();p.write_text(s.replace(old,new,1))
        b=dest/'FireSim-generated.native-region-graft.json'
        doc=json.loads(b.read_text());doc['files'][file.removeprefix('FireSim-generated')]=sha(p)
        b.unlink();b.write_bytes(canonical(doc))
        try:audit(dest)
        except ValueError:rejected.append(i)
        else:raise ValueError('coherently rehashed restore defect admitted: '+str(i))
    for label in ('owner-alias','partial-admission','endpoint-claim'):
        dest=out/label;dest.mkdir()
        for source in directory.iterdir():
            if source.is_file():(dest/source.name).symlink_to(source.resolve())
        b=dest/'FireSim-generated.native-region-graft.json';doc=json.loads(b.read_text())
        if label=='owner-alias':doc['router_state_observation']['owners'][1]['instance']=doc['router_state_observation']['owners'][0]['instance']
        elif label=='partial-admission':doc['router_state_restore']['load_contract']='partial_load'
        else:doc['router_state_restore']['endpoint_state_restored']=True
        b.unlink();b.write_bytes(canonical(doc))
        try:audit(dest)
        except ValueError:rejected.append(label)
        else:raise ValueError('coherent router metadata defect admitted '+label)
    return rejected


def samples(path, names):
    scopes,codes,values=[],{},{}
    def row():
        require(set(codes)==names,'missing complete router wave fields: '+str(names-set(codes)))
        return {n:int(values[c],2) if c in values and re.fullmatch('[01]+',values[c]) else None for n,c in codes.items()}
    with Path(path).open() as stream:
        for line in stream:
            p=line.split()
            if not p:continue
            if p[0]=='$scope':scopes.append(p[2])
            elif p[0]=='$upscope':scopes.pop()
            elif p[0]=='$var':
                name='.'.join(scopes+[p[4].lstrip('\\')]);prefix='regional_router_restore_tb.'
                if name.startswith(prefix) and name[len(prefix):] in names:codes[name[len(prefix):]]=p[3]
            elif line.startswith('#'):yield row()
            elif line[0] in 'bB' and len(p)==2:values[p[1]]=p[0][1:].lower()
            elif line[0] in '01xXzZ':values[line[1:].strip()]=line[0].lower()
    yield row()


def wave(path, n, image, *, destination=False, corrupt=False, mutate_bit=None):
    require(n in (1,2), 'directed waveform fixture supports one or two regions')
    prefix='dut.host.checkpoint_region_readout_adapter.'
    fields=[('router.pending',0),('router.invalid',1),('router.owner',2)]
    fields += [(f'region{i}.router.{field}',3+2*i+offset) for i in range(n)
               for field,offset in [('pending',0),('selected_ce',1)]]
    endpoint_pins={prefix+f'region{i}.router.'+pin for i in range(n) for pin in
        ('request_ready','response_valid','functional_request_valid','ce_request_valid',
         'functional_response_ready','ce_response_ready')}
    names=endpoint_pins|{prefix+f for f,_ in fields}|{'clock','capture_reset','capture_router_state',
        'capture_router_restore_hold','capture_router_restore_load','capture_router_restore_state',
        'capture_router_restore_ready','capture_router_restore_error','capture_clock_mask','capture_read_enable',
        'capture_request_valid','capture_request_ready','capture_response_valid','capture_response_ready',
        'capture_bank','capture_slot','cycle','snapshots'}
    last=None;expected=None;loads=acks=rows=held=records=0;divergence=None;states=set()
    for v in samples(path,names):
        if any(value is None for value in v.values()):
            require(v['capture_reset']!=0,'unknown original router after reset');continue
        active=v['capture_router_restore_hold'] or v['capture_router_restore_load']
        ready=bool(v['capture_router_restore_hold'] and v['capture_clock_mask'] and v['capture_read_enable'] and
                   ((v['capture_router_restore_state']>>2)&1)<n and not v['capture_reset'])
        error=bool(active and (not v['capture_clock_mask'] or not v['capture_read_enable']) or
                   v['capture_router_restore_load'] and not ready)
        require(v['capture_router_restore_ready']==ready and v['capture_router_restore_error']==error,
                'complete vector restore admission differs')
        if active or v['capture_reset']:
            require(not v['capture_request_ready'] and not v['capture_response_valid'] and
                    all(not v[pin] for pin in endpoint_pins),'router/endpoint handshake on held/rejected edge')
        if last and not last['clock'] and v['clock']:
            if last['capture_reset']:expected=0
            elif last['capture_router_restore_load'] and last['capture_router_restore_ready']:
                expected=image[loads][0] if destination and loads<len(image) else last['capture_router_restore_state']
                loads+=1
            elif not (last['capture_router_restore_hold'] or last['capture_router_restore_load']):
                if last['capture_request_valid'] and last['capture_request_ready']:
                    route=last['capture_bank'] if last['capture_bank']<n else last['capture_slot']//2 if last['capture_bank']==255 and last['capture_slot']<2*n else None
                    expected=(expected&~7)|1|((route or 0)<<2)|(2 if route is None else 0);acks+=1
                    if route is not None:
                        offset=3+2*route
                        expected=(expected&~(3<<offset))|((1|(2 if last['capture_bank']==255 else 0))<<offset)
                if last['capture_response_valid'] and last['capture_response_ready']:
                    if not expected&2:expected &= ~(1 << (3+2*((expected>>2)&1)))
                    expected &= ~1;acks+=1
            else:held+=1
        raw=sum(v[prefix+f]<<offset for f,offset in fields)
        if v['snapshots']!=records:
            require(v['snapshots']==records+1 and records<len(image),'missing/reordered donor capture event')
            require((raw,v['cycle'])==image[records],'donor file differs from actual source/destination record edge')
            records+=1
        observed=v['capture_router_state'] ^ ((1<<mutate_bit) if mutate_bit is not None and loads else 0)
        require(observed==raw,'packed observation differs from raw registers')
        if expected is not None and raw!=expected:
            require(corrupt and loads==1 and acks==0 and active,'original router disagrees with independent donor/transaction')
            divergence=dict(expected=expected,observed=raw,acknowledged_edges=acks,target_cycle=v['cycle'])
        states.add(raw);last=v;rows+=1
    require(rows>20,'empty debug waveform')
    require(records==(0 if corrupt else len(image)),'incomplete independent capture record audit')
    require(divergence is not None if corrupt else acks==4*n+2,'missing divergence or transaction continuation')
    if destination and not corrupt:require(loads==len(image)+(1<<(2+2*n))*n+1 and held>10,'incomplete entire ABI restore')
    return dict(rows=rows,loads=loads,held_edges=held,acknowledged_edges=acks,donor_records=records,states=sorted(states),first_divergence=divergence)
