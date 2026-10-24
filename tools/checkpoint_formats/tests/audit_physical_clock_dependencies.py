"""Independently reconstruct original CE cones; never admit hardware capture.

The separate complete clock-plan and wiring structural audits remain required.
This oracle resolves concrete instance paths rather than the compiler's cached
definition-local summaries, and checks the complete dependency document.
"""
import argparse
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import arguments, digest, parse_modules, IDENT


def audit(reference, manifest, plan, dependencies):
    text = Path(reference).read_text()
    inventory = json.loads(Path(manifest).read_text())
    topology = json.loads(Path(plan).read_text())
    doc = json.loads(Path(dependencies).read_text())
    require(inventory['reference_sha256'] == topology['reference_sha256'] == digest(text), 'stale dependency reference')
    require(topology['simulator_manifest_sha256'] == digest(Path(manifest).read_text()), 'stale dependency inventory')
    modules, scopes = parse_modules(text), {}
    root = inventory['root_module']

    def walk(module, path, parent=None, instance=None, ancestors=frozenset()):
        require(module not in ancestors and path not in scopes, 'invalid hierarchy')
        m = modules[module]
        # Every register reset must already be synchronous in this schema.
        require(re.search(r': AsyncReset(?:\s|$)', m['body']) is None, 'asynchronous resets unsupported')
        memories = {}
        for memory in re.finditer(r'^  mem (' + IDENT + r') :\n((?:    [^\n]*\n?)*)', m['body'], re.M):
            fields = re.findall(r'^    ([\w-]+) => (.*)$', memory[2], re.M)
            memories[memory[1]] = dict(readers=[v for k, v in fields if k == 'reader'],
                readwriters=[v for k, v in fields if k == 'readwriter'],
                latency=int(next(v for k, v in fields if k == 'read-latency')),
                ruw=next(v for k, v in fields if k == 'read-under-write'))
        scopes[path] = dict(module=module, parent=parent, instance=instance, memories=memories, **m)
        for name, child in m['instances'].items():
            walk(child, path + '.' + name, path, name, ancestors | {module})
    walk(root, root)
    states = {r['hierarchy']: r for r in inventory['state']}
    coverage = {r['hierarchy']: r['clock_consumers'] for r in topology['state_clock_coverage']}
    cache, active = {}, set()
    operators = set(('add sub mul div rem lt leq gt geq eq neq pad asUInt asSInt asClock asAsyncReset '
                     'shl shr dshl dshr cvt neg not and or xor andr orr xorr cat bits head tail mux validif '
                     'addw subw dshlw').split())

    def expression(path, value):
        require(value is not None, 'invalid CE dependency')
        if re.fullmatch(r'(?:U|S)Int(?:<\d+>)?\((?:"[hob][0-9a-fA-F_]+"|-?\d+)\)|-?\d+', value):
            return frozenset()
        call = re.fullmatch(r'(\w+)\((.*)\)', value)
        if call:
            require(call[1] in operators, 'unknown combinational operator ' + call[1])
            return frozenset().union(*(expression(path, a) for a in arguments(call[2])))
        return reference_value(path, value)

    def reference_value(path, name):
        key = path, name
        require(key not in active, 'combinational cycle ' + path + '.' + name)
        if key in cache:
            return cache[key]
        active.add(key)
        scope = scopes[path]
        full = path + '.' + name
        registers = {n for n, k, _ in scope['consumers'] if k == 'register'}
        if name in registers:
            result = frozenset({('state', full)})
        elif name in scope['ports'] and scope['ports'][name][0] == 'input':
            if path == root:
                require(scope['ports'][name][1] != 'Clock', 'oscillating clock used as CE data')
                result = frozenset({('input', full)})
            else:
                result = reference_value(scope['parent'], scope['instance'] + '.' + name)
        elif name in scope['drivers']:
            result = expression(path, scope['drivers'][name])
        else:
            parts = name.split('.')
            if len(parts) == 2 and parts[0] in scope['instances']:
                child = scopes[path + '.' + parts[0]]
                require(child['kind'] == 'module' and child['ports'][parts[1]][0] == 'output', 'opaque CE data owner')
                result = reference_value(path + '.' + parts[0], parts[1])
            elif len(parts) == 3 and parts[0] in scope['memories']:
                memory, port, field = parts
                m = scope['memories'][memory]
                state = ('state', path + '.' + memory)
                if port in m['readers'] and field == 'data':
                    if m['latency'] == 0:
                        result = frozenset({state}) | reference_value(path, memory + '.' + port + '.addr') | reference_value(path, memory + '.' + port + '.en')
                    else:
                        require(m['latency'] == 1, 'hidden read pipeline')
                        saved = 'data' if m['ruw'] == 'old' else 'addr'
                        result = frozenset({('state', path + '.' + memory + '_' + port + '_' + saved)})
                        if saved == 'addr':
                            result |= frozenset({state})
                elif port in m['readwriters'] and field == 'rdata' and m['latency'] == 1:
                    result = frozenset({('state', path + '.' + memory + '_' + port + '_rdata')})
                else:
                    raise ValueError('unknown memory dependency ' + full)
            else:
                raise ValueError('unresolved CE dependency ' + full)
        active.remove(key)
        cache[key] = result
        return result

    rows, external = [], set()
    # Reconstruct gate membership and ordering from the original hierarchy.
    gates = sorted(p for p, s in scopes.items() if s['kind'] == 'extmodule')
    require(gates == [r['hierarchy'] for r in topology['physical_gates']], 'incomplete CE gate set')
    for gate in gates:
        require(scopes[gate]['body'].endswith('defname = BUFGCE'), 'unknown physical owner')
        parent, instance = gate.rsplit('.', 1)
        driver = scopes[parent]['drivers'][instance + '.CE']
        terminals = []
        for kind, path in sorted(expression(parent, driver)):
            if kind == 'input':
                external.add(path)
                terminals.append(dict(kind='external_input', hierarchy=path,
                    type=scopes[root]['ports'][path.removeprefix(root + '.')][1], freeze_owner='unbound'))
            else:
                state = states[path]
                require(state['adapter'] != 'metasim-bufgce-v1' and coverage[path], 'unfrozen CE state')
                terminals.append(dict(kind='clocked_state', hierarchy=path, state_id=state['state_id'],
                    adapter=state['adapter'], clock_consumers=coverage[path]))
        rows.append(dict(hierarchy=gate, ce_driver_scope=parent, ce_driver_expression=driver, terminals=terminals,
                         external_inputs_require_freeze=any(t['kind'] == 'external_input' for t in terminals)))
    expected = dict(dependency_version=1, scope='physical_ce_dependency_prerequisites_only', root_module=root,
        reference_sha256=digest(text), simulator_manifest_sha256=digest(Path(manifest).read_text()),
        plan_sha256=digest(Path(plan).read_text()), complete_fpga_capture=False, deployable_capture_image=False,
        production_freeze_owners_bound=False, asynchronous_resets_supported=False,
        analysis='conservative_combinational_cones_to_complete_clocked_state_or_root_inputs', physical_gates=rows,
        external_inputs_require_freeze=sorted(external), remaining_obligations=['bind_external_input_freeze_owners',
            'physical_latch_bank_and_metasim_restore_mapping', 'production_annotation_and_xdc_translation',
            'functional_memory_timing_bridge_host_and_pre_fame_ownership', 'connected_ungated_mmio_dma_transport'])
    require(doc == expected, 'incomplete/changed CE cone, state identity, or unsupported ownership claim')
    return dict(status='pass', scope='independent original CE dependency audit only', physical_fpga_capture=False,
                gates=len(rows), state_terminals=sum(t['kind'] == 'clocked_state' for r in rows for t in r['terminals']),
                external_inputs_require_freeze=sorted(external), dependencies_sha256=digest(Path(dependencies).read_text()))


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ('reference', 'manifest', 'plan', 'dependencies', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='ce-dependencies-', dir=args.out))
    inputs = {name: getattr(args, name) for name in ('reference', 'manifest', 'plan', 'dependencies')}
    result = audit(**inputs)
    original = json.loads(args.dependencies.read_text())
    result['rejected'] = []
    # No checksum-only negative tests: all modified documents are valid JSON,
    # retaining matching reference/manifest/plan hashes.
    for name in ('missing-gate', 'missing-terminal', 'changed-state-id', 'dropped-clock-consumer',
                 'false-input-closure', 'coherent-input-omission', 'claim-terminal-owner',
                 'claim-input-owner', 'claim-capture', 'claim-reset-support', 'dropped-obligation'):
        doc = json.loads(json.dumps(original))
        if name == 'missing-gate': doc['physical_gates'].pop()
        elif name == 'missing-terminal': doc['physical_gates'][0]['terminals'].pop()
        elif name in ('changed-state-id', 'dropped-clock-consumer'):
            row = next(t for r in doc['physical_gates'] for t in r['terminals'] if t['kind'] == 'clocked_state')
            if name == 'changed-state-id': row['state_id'] = '0' * 64
            else: row['clock_consumers'] = []
        elif name == 'false-input-closure': doc['external_inputs_require_freeze'] = ['forged.external.input']
        elif name == 'coherent-input-omission':
            doc['external_inputs_require_freeze'] = []
            for row in doc['physical_gates']:
                row['terminals'] = [t for t in row['terminals'] if t['kind'] != 'external_input']
                row['external_inputs_require_freeze'] = False
        elif name == 'claim-terminal-owner':
            row = next(t for r in doc['physical_gates'] for t in r['terminals'] if t['kind'] == 'external_input')
            row['freeze_owner'] = 'invented-bound-owner'
        elif name == 'claim-input-owner': doc['production_freeze_owners_bound'] = True
        elif name == 'claim-capture': doc['complete_fpga_capture'] = True
        elif name == 'claim-reset-support': doc['asynchronous_resets_supported'] = True
        else: doc['remaining_obligations'].pop()
        require(doc != original, 'ineffective mutation ' + name)
        bad = out / (name + '.json')
        bad.write_text(json.dumps(doc, indent=2) + '\n')
        try:
            audit(**dict(inputs, dependencies=bad))
        except ValueError as error:
            result['rejected'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('accepted CE corruption ' + name)
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
