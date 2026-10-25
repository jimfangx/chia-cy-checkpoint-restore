"""Reconstruct local-selector/global-StateID projection from the original FIRRTL.

This audit establishes metadata coverage, never complete FPGA capture or restore.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import HASH, keys, natural, require
from tools.checkpoint_formats.simulator import PLUSARG_MODEL_SHA256, validate_generated_manifest
from tools.checkpoint_formats.tests.audit_physical_clock_plan import arguments, parse_modules, audit_source
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies
from tools.checkpoint_formats.tests.verify_native_functional_bank import digest, sha, FLAGS


def validate_native_constants(manifest, modules, annotations):
    """Validate FPGA constants without admitting them to metasim inventories.

    The native producer hashes the concrete module, not the adapter (the latter
    convention belongs to metasim's stateful plusarg model). Check source
    annotations and every original definition before validating a storage-only
    view with the unchanged generic schema. No original input is modified.
    """
    contracts = {}
    for annotation in annotations:
        if annotation.get('class') != 'midas.checkpoint.SynthesisPlusArgConstantAnnotation':
            continue
        keys(annotation, {'class','target','sourceSHA256','originalCircuitSHA256','width','default','format'})
        require(isinstance(annotation['target'],str), 'invalid native constant target')
        natural(annotation['width']); natural(annotation['default'])
        match = re.fullmatch(r'~'+re.escape(manifest['circuit'])+r'\|([A-Za-z_][A-Za-z0-9_$]*)', annotation['target'])
        require(match and match[1] not in contracts, 'foreign or duplicate native constant annotation')
        contracts[match[1]] = annotation
    view = copy.deepcopy(manifest)
    seen = set()
    original_hashes = set()
    for instance in view['instances']:
        adapter = instance.get('external_adapter')
        if not adapter or adapter.get('adapter') != 'fpga-synthesis-plusarg-constant-v1':
            continue
        keys(adapter, {'adapter','source_sha256','original_circuit_sha256','width','default','format'})
        require(adapter['source_sha256'] == PLUSARG_MODEL_SHA256 and
                isinstance(adapter['original_circuit_sha256'],str) and HASH.fullmatch(adapter['original_circuit_sha256']),
                'unknown native constant source or original circuit')
        width, default = adapter['width'], adapter['default']
        natural(width); natural(default)
        require(0 < width <= 2**31-1 and default.bit_length() <= width and
                isinstance(adapter['format'],str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=%[dbh]',adapter['format']),
                'invalid native constant width/default/format')
        module = instance['module']
        require(module in modules and module in contracts, 'native constant lacks original annotated definition')
        expected = dict(adapter='fpga-synthesis-plusarg-constant-v1',source_sha256=contracts[module]['sourceSHA256'],
            original_circuit_sha256=contracts[module]['originalCircuitSHA256'],width=contracts[module]['width'],
            default=contracts[module]['default'],format=contracts[module]['format'])
        require(adapter == expected, 'native constant differs from source annotation')
        actual = modules[module]
        normalized = [line.strip() for line in re.sub(r' @\[.*$', '', actual['body'],flags=re.M).splitlines() if line.strip()]
        require(actual['kind']=='module' and actual['ports']=={'out':('output',f'UInt<{width}>')} and
                normalized == [f'module {module} :',f'output out : UInt<{width}>',f'out <= UInt<{width}>("h{default:x}")'],
                'native constant has changed output, ports, hidden state or effects')
        require(instance['implementation_sha256']==hashlib.sha256(actual['body'].encode()).hexdigest(),
                'native constant concrete implementation hash changed')
        require(not any(r['hierarchy'].rsplit('.',1)[0]==instance['hierarchy'] for r in manifest['state']),
                'native synthesis constant cannot own runtime state')
        seen.add(module); original_hashes.add(adapter['original_circuit_sha256'])
        del instance['external_adapter']
    require(seen==set(contracts) and len(original_hashes)<=1, 'missing native constant instance or mixed source circuits')
    validate_generated_manifest(view)
    return len([r for r in manifest['instances'] if r.get('external_adapter',{}).get('adapter') ==
                'fpga-synthesis-plusarg-constant-v1'])


def audit(generated):
    generated = Path(generated)
    read = lambda name: json.loads((generated / name).read_text())
    prefix = 'FireSim-generated'
    host_text = (generated / 'host.fir').read_text()
    host = parse_modules(host_text)
    binding = read('binding.json')
    target = binding['target']
    match = re.fullmatch(r'~(\w+)\|\1((?:/\w+:\w+)+)', target)
    require(match is not None, 'global identity target must be root-relative')
    root = match[1]
    path = re.findall(r'/(\w+):(\w+)', match[2])
    scope = root + ''.join('.' + i for i, _ in path)
    selected = path[-1][1]
    local = read(prefix + '.native-functional-inventory.json')
    local_bank = read(prefix + '.native-functional-binding.json')
    local_plan = read(prefix + '.native-functional-plan.json')
    local_descriptors = read(prefix + '.native-descriptors.json')
    global_manifest = read('global-simulator-state.json')
    global_plan = read('global-physical-clock-plan.json')
    validate_native_constants(global_manifest, host, read('host-annotations.json'))
    require(global_manifest['root_module'] == global_manifest['circuit'] == root and
            global_manifest['reference_sha256'] == sha(generated / 'host.fir'), 'changed global source/root')

    # Enumerate every original concrete register, RAM and emitter-owned read
    # pipeline. Unselected owners receive the same checks as selected owners.
    state = {}
    native = []
    scopes = {}

    def add(hierarchy, module, kind, width, depth, signed, clock, reset, adapter):
        require(hierarchy not in state, 'aliased global storage')
        state[hierarchy] = dict(state_id=digest(dict(namespace='generated-simulator-state-v1',
            hierarchy=hierarchy, kind=kind)), hierarchy=hierarchy, module=module, kind=kind,
            width=width, depth=depth, signed=signed, clock_expression=clock, reset_expression=reset,
            adapter=adapter, bit_order='lsb0', address_order='ascending_zero_based')

    def walk(module, hierarchy, ancestors=frozenset()):
        require(module not in ancestors and hierarchy not in scopes, 'recursive/aliased global execution')
        m = host[module]
        body = re.sub(r' @\[.*$', '', m['body'], flags=re.M)
        scopes[hierarchy] = module
        if m['kind'] == 'extmodule':
            require(m['body'].endswith('defname = BUFGCE'), 'unsupported opaque global owner')
            native.append(hierarchy)
            add(hierarchy + '.O', module, 'register', 1, 1, False, 'posedge/negedge I', 'none', 'metasim-bufgce-v1')
            return
        for reg in re.finditer(r'^  reg (\w+) : (UInt|SInt)<(\d+)>, (.*?) with :\n    reset => \((.*)\)$', body, re.M):
            reset = arguments(reg[5])
            require(len(reset) == 2, 'unsupported register reset')
            add(hierarchy + '.' + reg[1], module, 'register', int(reg[3]), 1,
                reg[2] == 'SInt', reg[4], reset[0], 'firrtl-register-v1')
        declared = re.findall(r'^  reg (\w+) :', body, re.M)
        require(len(declared) == sum(p.startswith(hierarchy + '.') and p.rsplit('.', 1)[0] == hierarchy
            for p in state), 'unparsed global register')
        for mem in re.finditer(r'^  mem (\w+) :\n((?:    [^\n]*\n?)*)', body, re.M):
            attrs = re.findall(r'^    ([\w-]+) => (.*)$', mem[2], re.M)
            fields = dict(attrs)
            data = re.fullmatch(r'(UInt|SInt)<(\d+)>', fields['data-type'])
            require(data is not None, 'unsupported global RAM data')
            width, depth = int(data[2]), int(fields['depth'])
            add(hierarchy + '.' + mem[1], module, 'memory', width, depth,
                data[1] == 'SInt', 'memory-port-clocks', 'none', 'firrtl-memory-v1')
            if int(fields['read-latency']) == 1:
                for kind, port in attrs:
                    if kind not in ('reader', 'readwriter'):
                        continue
                    field = 'rdata' if kind == 'readwriter' else 'data' if fields['read-under-write'] == 'old' else 'addr'
                    pipeline_width = (depth - 1).bit_length() if field == 'addr' else width
                    add(hierarchy + '.' + mem[1] + '_' + port + '_' + field, module, 'register',
                        pipeline_width, 1, field != 'addr' and data[1] == 'SInt',
                        mem[1] + '.' + port + '.clk', 'none', 'firrtl-emitter-memory-pipeline-v1')
        for instance, child in m['instances'].items():
            walk(child, hierarchy + '.' + instance, ancestors | {module})
    walk(root, root)
    require(sorted(global_manifest['state'], key=lambda r: r['hierarchy']) ==
            [state[p] for p in sorted(state)], 'global inventory differs from original storage/shape/reset/adapter')
    require(sorted((r['hierarchy'], r['module']) for r in global_manifest['instances']) == sorted(scopes.items()),
            'incomplete global instance inventory')
    require(sorted(native) == [g['hierarchy'] for g in global_plan['physical_gates']], 'incomplete global physical owners')
    require(global_plan['simulator_manifest_sha256'] == sha(generated / 'global-simulator-state.json') and
            global_plan['reference_sha256'] == sha(generated / 'host.fir'), 'unbound global topology')
    for i, g in enumerate(global_plan['physical_gates']):
        require(g['index'] == i and g['logical_latch_hierarchy'] == g['hierarchy'] + '.CE_latch' and
            g['logical_latch_state_id'] == digest(dict(namespace='physical-bufgce-ce-latch-v1', hierarchy=g['logical_latch_hierarchy'])) and
            g['metasim_output_state_id'] == state[g['hierarchy'] + '.O']['state_id'], 'changed global CE identity/index')
    audit_source(generated / 'host.fir', generated / 'global-simulator-state.json',
        generated / 'global-physical-clock-plan.json')
    audit_dependencies(generated / 'host.fir', generated / 'global-simulator-state.json',
        generated / 'global-physical-clock-plan.json', generated / 'global-physical-clock-dependencies.json')

    def rebase(p):
        require(p.startswith(selected + '.'), 'selected identity escaped its scope')
        return scope + p[len(selected):]
    global_functional = [r for r in global_manifest['state'] if r['adapter'] != 'metasim-bufgce-v1']
    global_physical = {g['logical_latch_hierarchy']: g for g in global_plan['physical_gates']}
    projected = []
    for i, (row, access) in enumerate(zip(local['state'], local_bank['state'])):
        full = rebase(row['hierarchy'])
        expected = dict(row, hierarchy=full, state_id=digest(dict(namespace='generated-simulator-state-v1',
            hierarchy=full, kind=row['kind'])))
        require(state.get(full) == expected, 'selected state disagrees with original global storage')
        projected.append(dict(ordinal=i, domain='functional', selected_state_id=row['state_id'], state_id=expected['state_id'],
            selected_hierarchy=row['hierarchy'], hierarchy=full, storage_hierarchy=rebase(access['storage_hierarchy']),
            bank=access['bank'], slot=access['slot'], width=min(64, row['width']),
            depth=((row['width']+63)//64)*row['depth'], logical_state=expected))
    for i, row in enumerate(local_plan['physical_gates']):
        full = rebase(row['logical_latch_hierarchy'])
        g = global_physical[full]
        require(row['physical_contract'] == g['physical_contract'], 'changed selected/global physical contract')
        projected.append(dict(ordinal=len(local['state'])+i, domain='physical_ce',
            selected_state_id=row['logical_latch_state_id'], state_id=g['logical_latch_state_id'],
            selected_hierarchy=row['logical_latch_hierarchy'], hierarchy=full,
            bank=255, slot=i, width=1, depth=1, ce_bit=i, global_physical_index=g['index'],
            metasim_output_state_id=g['metasim_output_state_id'], restore_adapter='unsupported'))
    covered = {r['hierarchy'] for r in projected}
    uncovered = [r for r in global_functional if r['hierarchy'] not in covered]
    uncovered_ce = [g for g in global_plan['physical_gates'] if g['logical_latch_hierarchy'] not in covered]
    expected = dict(identity_version=1, scope='selected_inplace_global_identities_only', target=target,
        selected_scope=scope, selector_namespace='selected_endpoint_local_order_not_global_inventory_order',
        state=projected, uncovered_functional_state=uncovered, uncovered_physical_gates=uncovered_ce,
        global_functional_entries=len(global_functional), global_physical_gates=len(native),
        physical_clock_gates=len(local_plan['physical_gates']), external_runtime_required=True, **FLAGS)
    require(read('global-identity.json') == expected, 'changed global identities/selectors/order or incomplete uncovered owners')
    expected_binding = dict(identity_binding_version=1, manifest_sha256=digest(expected),
        host_sha256=sha(generated / 'host.fir'), reference_sha256=sha(generated / (prefix + '.native-functional-reference.fir')),
        global_simulator_manifest_sha256=sha(generated / 'global-simulator-state.json'),
        global_clock_plan_sha256=sha(generated / 'global-physical-clock-plan.json'),
        global_dependencies_sha256=sha(generated / 'global-physical-clock-dependencies.json'),
        selected_descriptor_manifest_sha256=digest(local_descriptors),
        selected_descriptor_binding_sha256=sha(generated / (prefix + '.native-descriptors-binding.json')), **FLAGS)
    require(read('global-identity-binding.json') == expected_binding and
            binding['identity_binding_sha256'] == digest(expected_binding), 'unbound global identity projection')
    require(len(projected) == len(covered) and len(local_descriptors['state']) == len(projected), 'duplicate/incomplete selected mapping')
    return dict(functional_entries=len(local['state']), physical_entries=len(local_plan['physical_gates']),
        uncovered_functional_entries=len(uncovered), uncovered_physical_gates=len(uncovered_ce),
        global_functional_entries=len(global_functional), global_physical_gates=len(native),
        global_ce_indices=[r['global_physical_index'] for r in projected if r['domain'] == 'physical_ce'])
