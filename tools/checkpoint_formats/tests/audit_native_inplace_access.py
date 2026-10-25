"""Independently reconstruct routing around the existing simulator execution.

The complete enclosing inventory and original annotations remain authoritative;
this readout attachment grants neither all-owner admission nor a restore path.
"""
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_native_inplace_context import audit as audit_context
from tools.checkpoint_formats.tests.audit_native_constraints import audit as audit_constraints
from tools.checkpoint_formats.tests.verify_native_inplace import audit as audit_inplace
from tools.checkpoint_formats.tests.verify_native_functional_bank import FLAGS, sha

PREFIX = 'FireSim-generated'


def audit(directory):
    directory = Path(directory)
    path = lambda s: directory / (PREFIX + s)
    load = lambda s: json.loads(path(s).read_text())
    audit_inplace(directory)
    constraints = audit_constraints(directory, in_place=True)
    context = audit_context(directory / 'context')
    native = json.loads((directory / 'binding.json').read_text())
    host = parse_modules((directory / 'host.fir').read_text())
    identity = json.loads((directory / 'global-identity.json').read_text())
    context_binding = directory / 'context/binding.json'
    root = re.search(r'(?m)^circuit (\w+) :', (directory / 'host.fir').read_text())[1]
    # The descriptor manifest must be the existing globally reconstructed
    # identity, not the selected subtree's old local StateIDs.
    require(load('.native-inplace-access-descriptors.json') == identity, 'changed enclosing descriptor identities')
    identity_binding = directory / 'global-identity-binding.json'
    require(sha(path('.native-inplace-access-descriptor-binding.json')) ==
            sha(identity_binding),
            'changed global identity binding')
    state = identity['state']
    functional = [r for r in state if r['domain'] == 'functional']
    gates = identity['physical_clock_gates']
    clock = native['enclosing_raw_clock']
    binding = load('.native-inplace-access.json')
    require(binding == dict(binding_version=1, scope='existing_instance_native_state_router_only',
        module=root+'CheckpointStateAccess', network_module=root, network_instance='network',
        common_source_clock=clock, target=native['target'], sideband_prefix='checkpoint_inplace_',
        functional_entries=len(functional), physical_clock_gates=gates,
        context_binding_sha256=sha(context_binding), instrumented_sha256=sha(directory/'instrumented.fir'),
        identity_binding_sha256=sha(path('.native-inplace-access-descriptor-binding.json')),
        descriptor_manifest_sha256=sha(path('.native-inplace-access-descriptors.json')),
        endpoint_sha256=sha(path('.native-inplace-access.sv')), router_sha256=sha(path('.native-inplace-access-router.sv')),
        physical_bank_sha256=sha(path('.native-inplace-access-ce.sv')),
        reset_contract='shared_raw_controller_reset_distinct_from_functional_reset',
        sample_contract='common_low_phase_unmasked_captured_ce_with_read_enable',
        external_inputs_require_freeze=load('.native-functional-dependencies.json')['external_inputs_require_freeze'],
        in_place_ce_endpoint_connected=True, in_place_checkpoint_widget_connected=False, **FLAGS),
        'changed in-place attachment binding or capture admission')
    require(sha(path('.native-inplace-access-router.sv')) == sha(Path(__file__).resolve().parents[3]/
        'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv'), 'changed transaction router')
    require(path('.native-inplace-access-ce.sv').read_bytes() == path('.native-descriptors-physical-bank.sv').read_bytes(),
            'changed physical CE bank implementation')
    rtl = path('.native-inplace-access.sv').read_text()
    body = rtl
    def remove(pattern, expected=None, reason='unexpected attachment syntax'):
        nonlocal body
        matches = list(re.finditer(pattern, body, re.S))
        require(len(matches) == 1 and (expected is None or matches[0][0] == expected), reason)
        value = matches[0]
        body = body[:value.start()] + body[value.end():]
        return value
    # Match every original port and every added port, including direction/width.
    ports = host[root]['ports']
    original = []
    for name, (direction, kind) in ports.items():
        if kind in ('Clock', 'Reset', 'AsyncReset'): signed, width = '', 1
        else:
            shape = re.fullmatch(r'(UInt|SInt)<(\d+)>', kind)
            require(shape, 'unsupported enclosing port')
            signed, width = ('signed ' if shape[1] == 'SInt' else ''), int(shape[2])
        original.append(f'  {direction} wire {signed}'+(f'[{width-1}:0] ' if width>1 else '')+name)
    capture = f'''  input wire capture_reset, capture_clock_mask, capture_read_enable,
  input wire [{gates-1}:0] capture_captured_ce,
  output wire [{gates-1}:0] capture_logical_ce,
  input wire [31:0] capture_descriptor_entry,
  output wire capture_descriptor_valid,
  output wire [7:0] capture_descriptor_bank,
  output wire [15:0] capture_descriptor_slot, capture_descriptor_width,
  output wire [31:0] capture_descriptor_depth,
  input wire capture_request_valid,
  output wire capture_request_ready,
  input wire [7:0] capture_bank,
  input wire [15:0] capture_slot,
  input wire [31:0] capture_address,
  output wire capture_response_valid,
  input wire capture_response_ready,
  output wire [63:0] capture_response_data,
  output wire capture_response_error'''
    remove(r'module \w+ \(.*?\n\);', 'module '+root+'CheckpointStateAccess (\n'+',\n'.join(original)+',\n'+capture+'\n);',
           'changed enclosing/public port contract')
    def instance(module, name, pins, parameters='', wildcard=False):
        m = remove(r'\b'+re.escape(module)+r'(?:\s*#\(([^;]+?)\))?\s+'+name+r'\s*\((.*?)\);')
        require((m[1] or '') == parameters, 'changed router geometry')
        pairs = re.findall(r'\.([A-Za-z_][A-Za-z0-9_$]*)\(([^()]*)\)', m[2])
        require(len(pairs) == len(dict(pairs)) and dict(pairs) == pins, 'changed existing-host connection '+name)
        residue = re.sub(r'\.[A-Za-z_][A-Za-z0-9_$]*\([^()]*\)', '', m[2]).replace(',', '').strip()
        require(residue == ('.*' if wildcard else ''), 'unexpected pin or duplicate execution')
    network = dict((n,n) for n in ports)
    sideband = dict(checkpoint_physical_mask='capture_clock_mask', checkpoint_physical_logical_ce='capture_logical_ce',
        ckpt_reset='capture_reset', ckpt_freeze='capture_clock_mask', ckpt_bank='endpoint_bank',
        ckpt_slot='endpoint_slot', ckpt_address='endpoint_address', ckpt_match='', ckpt_data='',
        ckpt_req_valid='functional_request_valid', ckpt_req_ready='functional_request_ready',
        ckpt_resp_valid='functional_response_valid', ckpt_resp_ready='functional_response_ready',
        ckpt_resp_data='functional_response_data', ckpt_resp_error='functional_response_error')
    network.update({'checkpoint_inplace_'+k:v for k,v in sideband.items()})
    instance(root, 'network', network)
    ce = {n:'ce_'+n for n in ('descriptor_entry','descriptor_valid','descriptor_bank','descriptor_slot',
        'descriptor_width','descriptor_depth','request_valid','request_ready','response_valid','response_ready',
        'response_data','response_error')}
    ce.update(clock=clock, reset='capture_reset', read_enable='capture_read_enable', captured_ce='capture_captured_ce',
        bank='endpoint_bank', slot='endpoint_slot', address='endpoint_address')
    selected = native['target'].split(':')[-1]
    instance(selected+'CheckpointPhysicalCEBank', 'ce_endpoint', ce)
    router = {n:'capture_'+n for n in ('descriptor_entry','descriptor_valid','descriptor_bank','descriptor_slot',
        'descriptor_width','descriptor_depth','request_valid','request_ready','bank','slot','address',
        'response_valid','response_ready','response_data','response_error')}
    router.update(clock=clock, reset='capture_reset')
    instance('CheckpointPhysicalStateRouter', 'router', router,
             f'.ENTRIES({len(functional)}),.GATES({gates})', True)
    rows = []
    for i,r in enumerate(functional):
        rows.append(f"      32'd{i}: begin functional_descriptor_valid=1; functional_descriptor_bank=8'd{r['bank']}; "
            f"functional_descriptor_slot=16'd{r['slot']}; functional_descriptor_width=16'd{r['width']}; "
            f"functional_descriptor_depth=32'd{r['depth']}; end")
    rom = '''  always @* begin
    functional_descriptor_valid=0; functional_descriptor_bank=0;
    functional_descriptor_slot=0; functional_descriptor_width=0; functional_descriptor_depth=0;
    case (functional_descriptor_entry)
'''+ '\n'.join(rows)+'''
      default: begin end
    endcase
  end'''
    remove(r'  always @\* begin.*?\n  end', rom, 'changed descriptor selector/order/geometry')
    # No unparsed logic, nets with initializers, or additional execution may hide
    # between the verified blocks. Validate all remaining declarations exactly.
    declarations = '''wire [31:0] functional_descriptor_entry, ce_descriptor_entry;
reg functional_descriptor_valid;
reg [7:0] functional_descriptor_bank;
reg [15:0] functional_descriptor_slot, functional_descriptor_width;
reg [31:0] functional_descriptor_depth;
wire ce_descriptor_valid;
wire [7:0] ce_descriptor_bank;
wire [15:0] ce_descriptor_slot, ce_descriptor_width;
wire [31:0] ce_descriptor_depth;
wire functional_request_valid, functional_request_ready, functional_response_valid, functional_response_ready;
wire functional_response_error, ce_request_valid, ce_request_ready, ce_response_valid, ce_response_ready, ce_response_error;
wire [63:0] functional_response_data, ce_response_data;
wire [7:0] endpoint_bank;
wire [15:0] endpoint_slot;
wire [31:0] endpoint_address;
endmodule'''
    body = re.sub(r'//[^\n]*', '', body)
    require([l.strip() for l in body.splitlines() if l.strip()] == declarations.splitlines(),
            'unexpected logic or storage in in-place attachment')
    return dict(status='pass', functional_entries=len(functional), physical_clock_gates=gates,
        transfer_words=sum(r['depth'] for r in state), context=context, constraints=constraints, existing_executions=1,
        uncovered_functional_entries=len(identity['uncovered_functional_state']),
        uncovered_physical_gates=len(identity['uncovered_physical_gates']),
        physical_fpga_capture=False, in_place_checkpoint_widget_connected=False)


def corruptions(directory, out):
    mutations = {
        'masked-router-clock':('.clock(clock),.reset(capture_reset)', '.clock(capture_clock_mask),.reset(capture_reset)'),
        'functional-reset':('.checkpoint_inplace_ckpt_reset(capture_reset)', '.checkpoint_inplace_ckpt_reset(reset)'),
        'freeze-bypass':('.checkpoint_inplace_ckpt_freeze(capture_clock_mask)', ".checkpoint_inplace_ckpt_freeze(1'b0)"),
        'live-ce-sample':('.captured_ce(capture_captured_ce)', '.captured_ce(capture_logical_ce)'),
        'read-permission':('.read_enable(capture_read_enable)', ".read_enable(1'b1)"),
        'response-ready':('.response_ready(capture_response_ready)', ".response_ready(1'b1)"),
        'descriptor-depth':("functional_descriptor_depth=32'd1;", "functional_descriptor_depth=32'd2;"),
        'parent-clock':('.clock(clock),\n', '.clock(capture_clock_mask),\n'),
        'extra-driver':('  wire ce_descriptor_valid;', "  wire ce_descriptor_valid;\n  assign functional_request_valid=1'b1;"),
    }
    rejected = []
    for name,(old,new) in mutations.items():
        dest = Path(out)/name
        shutil.copytree(directory, dest)
        path = dest/(PREFIX+'.native-inplace-access.sv')
        text = path.read_text(); changed = text.replace(old,new,1)
        require(changed != text, 'ineffective access corruption '+name)
        path.write_text(changed)
        binding_path = dest/(PREFIX+'.native-inplace-access.json')
        binding = json.loads(binding_path.read_text()); binding['endpoint_sha256'] = sha(path)
        binding_path.write_bytes(canonical(binding))
        try: audit(dest)
        except ValueError as error: rejected.append(dict(name=name,error=str(error)))
        else: raise ValueError('accepted coherently rehashed in-place attachment corruption '+name)
    dest = Path(out)/'coherent-constraint-change'
    shutil.copytree(directory, dest)
    binding_path = dest/(PREFIX+'.native-state-access-constraints.json')
    binding = json.loads(binding_path.read_text())
    old = binding['constraint_specs'][0]['format']
    new = old.replace('set_max_delay 4', 'set_max_delay 3', 1)
    require(new != old, 'ineffective constraint specification corruption')
    binding['constraint_specs'][0]['format'] = new
    xdc = dest/(PREFIX+'.native-state-access.implementation.xdc')
    changed = xdc.read_text().replace('set_max_delay 4', 'set_max_delay 3', 1)
    xdc.write_text(changed)
    binding['inputs']['.native-state-access.implementation.xdc'] = sha(xdc)
    binding_path.write_bytes(canonical(binding))
    try: audit(dest)
    except ValueError as error: rejected.append(dict(name='coherent-constraint-change',error=str(error)))
    else: raise ValueError('accepted coherently rehashed original-constraint change')
    return rejected
