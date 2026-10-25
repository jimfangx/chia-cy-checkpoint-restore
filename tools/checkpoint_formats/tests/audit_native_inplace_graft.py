"""Reconstruct an existing-root readout graft from independently audited input.

No hardware checkpoint, owner-completeness or CPU restore admission is granted.
"""
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_native_inplace_access import audit as audit_original, PREFIX
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha


def audit(directory):
    directory = Path(directory)
    original = directory/'original'
    checked = audit_original(original)
    path = lambda suffix: directory/(PREFIX+suffix)
    native = json.loads((original/'binding.json').read_text())
    context = json.loads((original/'context/binding.json').read_text())
    root = re.search(r'(?m)^circuit (\w+) :', (original/'host.fir').read_text())[1]
    old = parse_modules((original/'instrumented.fir').read_text())
    new = parse_modules((directory/'grafted.fir').read_text())
    adapter_name, instance = root+'CheckpointReadoutAdapter', 'checkpoint_readout_adapter'
    require(set(new) == set(old)|{adapter_name}, 'changed execution definitions')
    for name in old:
        if name != root:
            require(new[name] == old[name], 'changed executing module '+name)
    def annotations(p):
        return sorted(json.dumps(a,sort_keys=True) for a in json.loads(p.read_text()))
    require(annotations(directory/'grafted-annotations.json') ==
            annotations(original/'context/instrumented-annotations.json'), 'changed original annotations')
    access = {n:p for n,p in old[root]['ports'].items() if n.startswith('checkpoint_inplace_')}
    host_ports = {n:p for n,p in old[root]['ports'].items() if n not in access}
    gates = checked['physical_clock_gates']
    clock = native['enclosing_raw_clock']
    capture = {n:('input' if direction=='i' else 'output',f'UInt<{w}>') for n,w,direction in (
        ('capture_reset',1,'i'),('capture_clock_mask',1,'i'),('capture_read_enable',1,'i'),
        ('capture_captured_ce',gates,'i'),('capture_logical_ce',gates,'o'),
        ('capture_descriptor_entry',32,'i'),('capture_descriptor_valid',1,'o'),('capture_descriptor_bank',8,'o'),
        ('capture_descriptor_slot',16,'o'),('capture_descriptor_width',16,'o'),('capture_descriptor_depth',32,'o'),
        ('capture_request_valid',1,'i'),('capture_request_ready',1,'o'),('capture_bank',8,'i'),('capture_slot',16,'i'),
        ('capture_address',32,'i'),('capture_response_valid',1,'o'),('capture_response_ready',1,'i'),
        ('capture_response_data',64,'o'),('capture_response_error',1,'o'))}
    require(new[root]['ports']==host_ports|capture, 'changed graft interface')
    adapter_ports = {clock:('input','Clock')}|{n:('output' if d=='input' else 'input',t) for n,(d,t) in access.items()}|capture
    require(new[adapter_name]['kind']=='extmodule' and new[adapter_name]['ports']==adapter_ports and
            f'defname = {adapter_name}' in new[adapter_name]['body'], 'changed readout adapter definition')
    require(new[root]['instances']==old[root]['instances']|{instance:adapter_name}, 'duplicated or moved execution')
    extra = {f'{instance}.{n}':n for n,(d,_) in adapter_ports.items() if d=='input'}
    extra.update({n:f'{instance}.{n}' for n,(d,_) in adapter_ports.items() if d=='output'})
    require(not (set(old[root]['drivers']) & set(extra)), 'duplicate capture driver')
    require(new[root]['drivers']==old[root]['drivers']|extra, 'changed clock or transaction connection')
    require(new[root]['aliases']==old[root]['aliases']|set(access), 'changed graft wires')
    def body_lines(module):
        return [l.strip() for l in module['body'].splitlines()[1:] if l.strip() and
                not re.match(r'\s*(input|output) \w+ :',l)]
    additions = [f'wire {n} : {t}' for n,(_,t) in access.items()]+[f'inst {instance} of {adapter_name}']
    additions += [f'{lhs} <= {rhs}' for lhs,rhs in extra.items()]
    # Connection order does not affect semantics, but every other statement and
    # its order is retained, including effects and the original sequential body.
    old_lines, new_lines = body_lines(old[root]), body_lines(new[root])
    require(len(new_lines)==len(old_lines)+len(additions) and
            [l for l in new_lines if l not in additions]==old_lines and
            sorted(l for l in new_lines if l in additions)==sorted(additions),
            'unexpected graft logic or sequential changes')
    adapter = path('.native-inplace-graft.sv').read_text()
    template = (original/(PREFIX+'.native-inplace-access.sv')).read_text()
    def sv_port(n,d,t):
        if t in ('Clock','Reset','AsyncReset'): signed,width='',1
        else:
            m=re.fullmatch(r'(UInt|SInt)<(\d+)>',t);require(m,'unsupported adapter type')
            signed,width=('signed ' if m[1]=='SInt' else ''),int(m[2])
        return f'  {d} wire {signed}'+(f'[{width-1}:0] ' if width>1 else '')+n
    header = 'module '+adapter_name+' (\n'+',\n'.join(sv_port(n,d,t) for n,(d,t) in
        adapter_ports.items() if n not in capture)+','
    expected = re.sub(r'module \w+ \(.*?,\n  input wire capture_reset',
        lambda _:header+'\n  input wire capture_reset',template,count=1,flags=re.S)
    pairs = dict(checkpoint_physical_mask='capture_clock_mask',checkpoint_physical_logical_ce='capture_logical_ce',
        ckpt_reset='capture_reset',ckpt_freeze='capture_clock_mask',ckpt_bank='endpoint_bank',ckpt_slot='endpoint_slot',
        ckpt_address='endpoint_address',ckpt_req_valid='functional_request_valid',ckpt_req_ready='functional_request_ready',
        ckpt_resp_valid='functional_response_valid',ckpt_resp_ready='functional_response_ready',
        ckpt_resp_data='functional_response_data',ckpt_resp_error='functional_response_error')
    assignments=[]
    for n,w in pairs.items():
        n='checkpoint_inplace_'+n
        assignments.append(f'assign {w} = {n};' if adapter_ports[n][0]=='input' else f'assign {n} = {w};')
    expected = re.sub(r'  '+re.escape(root)+r' network\(.*?\);',lambda _:'  '+'\n  '.join(assignments),expected,flags=re.S)
    require(adapter==expected, 'changed immutable ROM, raw clock, bank routing or adapter logic')
    require(path('.native-inplace-graft-router.sv').read_bytes()==
            (original/(PREFIX+'.native-inplace-access-router.sv')).read_bytes(), 'changed router')
    require(path('.native-inplace-graft-ce.sv').read_bytes()==
            (original/(PREFIX+'.native-inplace-access-ce.sv')).read_bytes(), 'changed physical bank')
    require(path('.native-inplace-graft-descriptors.json').read_bytes()==
            (original/'global-identity.json').read_bytes(), 'changed global identities')
    binding=json.loads(path('.native-inplace-graft.json').read_text())
    require(binding==dict(graft_version=1,scope='existing_root_readout_adapter_only',root=root,
        adapter_module=adapter_name,adapter_instance=instance,raw_clock=clock,target=context['target'],
        context_binding_sha256=sha(original/'context/binding.json'),source_sha256=sha(original/'host.fir'),
        instrumented_sha256=sha(original/'instrumented.fir'),grafted_sha256=sha(directory/'grafted.fir'),
        descriptor_manifest_sha256=sha(path('.native-inplace-graft-descriptors.json')),
        descriptor_binding_sha256=sha(original/'global-identity-binding.json'),adapter_sha256=sha(path('.native-inplace-graft.sv')),
        router_sha256=sha(path('.native-inplace-graft-router.sv')),physical_bank_sha256=sha(path('.native-inplace-graft-ce.sv')),
        pre_link_path='host',post_link_path='host',
        constraint_files={'.native-inplace-graft.'+suffix+'.xdc':sha(path('.native-inplace-graft.'+suffix+'.xdc'))
                          for suffix in ('synthesis','implementation')},
        original_execution_duplicated=False,original_constraints_relocated=False,in_place_checkpoint_widget_connected=False,
        production_freeze_owners_bound=False,complete_fpga_capture=False,deployable_capture_image=False,metasim_restore_supported=False),
        'changed graft provenance or capture admission')
    # Compare all original correlated constraints. Only the companion's literal
    # placement hop is removed; Tcl generation itself uses original annotations.
    for suffix in ('synthesis','implementation'):
        old_xdc=(original/(PREFIX+'.native-state-access.'+suffix+'.xdc')).read_text()
        new_xdc=path('.native-inplace-graft.'+suffix+'.xdc').read_text()
        require(new_xdc==old_xdc.replace('host/network/','host/'), 'changed original constraint placement')
    return dict(checked, grafted_existing_root=root, original_execution_duplicated=False)


def corruptions(directory,out):
    mutations={
        'masked-router':('.clock(clock),.reset(capture_reset)','.clock(capture_clock_mask),.reset(capture_reset)'),
        'live-ce':('.captured_ce(capture_captured_ce)','.captured_ce(capture_logical_ce)'),
        'functional-reset':('assign checkpoint_inplace_ckpt_reset = capture_reset;','assign checkpoint_inplace_ckpt_reset = capture_clock_mask;'),
        'freeze-bypass':('assign checkpoint_inplace_ckpt_freeze = capture_clock_mask;',"assign checkpoint_inplace_ckpt_freeze = 1'b0;"),
        'descriptor-depth':("functional_descriptor_depth=32'd1;","functional_descriptor_depth=32'd2;"),
        'extra-execution':('endmodule','NativeHost hidden();\nendmodule'),
    }
    rejected=[]
    for name,(old,new) in mutations.items():
        dest=Path(out)/name;shutil.copytree(directory,dest)
        p=dest/(PREFIX+'.native-inplace-graft.sv');text=p.read_text();changed=text.replace(old,new,1)
        require(changed!=text,'ineffective graft mutation '+name);p.write_text(changed)
        b=dest/(PREFIX+'.native-inplace-graft.json');doc=json.loads(b.read_text());doc['adapter_sha256']=sha(p);b.write_bytes(canonical(doc))
        try:audit(dest)
        except ValueError as error:rejected.append(dict(name=name,error=str(error)))
        else:raise ValueError('accepted rehashed graft mutation '+name)
    return rejected
