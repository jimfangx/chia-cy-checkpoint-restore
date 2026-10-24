"""Independent clock/consumer reconstruction for the native cut prerequisite.

Only lowered, ground FIRRTL is understood. A topology plan never proves state
capture or permits physical bank generation. No simulator runs in this audit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require

IDENT = r'[A-Za-z_][A-Za-z0-9_$]*'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def arguments(text):
    """Split FIRRTL's parenthesized expressions, including nested operators."""
    result, start, depth, quoted = [], 0, 0, False
    for i, ch in enumerate(text):
        if ch == '"':
            quoted = not quoted
        if quoted:
            continue
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth -= 1
        elif ch == ',' and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    require(depth == 0 and not quoted, 'unbalanced clock expression')
    return result + [text[start:].strip()]


def parse_modules(text):
    """Parse lowered ground netlist connectivity, including emitter connectors."""
    headers = list(re.finditer(r'^  (extmodule|module) (' + IDENT + r') :[^\n]*', text, re.M))
    require(headers and len({h[2] for h in headers}) == len(headers), 'missing/duplicate module')
    modules = {}
    for index, header in enumerate(headers):
        body = text[header.start():headers[index+1].start() if index+1 < len(headers) else len(text)].rstrip('\n')
        lines = [re.sub(r' @\[.*$', '', line[2:] if line.startswith('  ') else line) for line in body.splitlines()]
        ports = {}
        for line in lines:
            p = re.fullmatch(r'  (input|output) (' + IDENT + r') : (.*)', line)
            if p:
                require(p[2] not in ports, 'duplicate port')
                ports[p[2]] = (p[1], p[3])
        instances, drivers, aliases, consumers, events = {}, {}, set(), [], []

        def driver(name, expression):
            require(name not in drivers, 'duplicate net driver ' + name)
            drivers[name] = expression

        for line_index, line in enumerate(lines):
            inst = re.fullmatch(r'  inst (' + IDENT + r') of (' + IDENT + r')(.*)', line)
            if inst:
                require(inst[1] not in instances, 'duplicate instance')
                instances[inst[1]] = inst[2]
                if inst[3]:
                    connector = re.fullmatch(r' with \{(.*)\} connected to \((.*)\)', inst[3])
                    require(connector is not None, 'unsupported connector syntax')
                    fields = arguments(connector[1])
                    values = arguments(connector[2])
                    require(len(fields) == len(values), 'incomplete connector')
                    for field, value in zip(fields, values):
                        f = re.fullmatch(r'(flip )?(' + IDENT + r') : (.*)', field)
                        require(f is not None, 'unsupported connector field')
                        if f[1]:
                            driver(inst[1] + '.' + f[2], value)
                        else:
                            driver(value, inst[1] + '.' + f[2])
            node = re.fullmatch(r'  node (' + IDENT + r') = (.*)', line)
            if node:
                aliases.add(node[1]); driver(node[1], node[2])
            wire = re.fullmatch(r'  wire (' + IDENT + r') : .*', line)
            if wire:
                aliases.add(wire[1])
            connect = re.fullmatch(r'  ([^ ]+) <= (.*)', line)
            if connect:
                driver(connect[1], connect[2])
            invalid = re.fullmatch(r'  ([^ ]+) is invalid', line)
            if invalid:
                driver(invalid[1], None)
            reg = re.fullmatch(r'  reg (' + IDENT + r') : [^,]+, (.*?)(?: with :)??', line)
            if reg:
                clk = reg[2].removesuffix(' with :')
                consumers.append((reg[1], 'register', clk))
                events.append((line_index, reg[1], 'register', clk))
        # Port clocks, rather than RAM depth words, own each memory pipeline.
        for mem in re.finditer(r'^  mem (' + IDENT + r') :\n((?:    [^\n]*\n?)*)', '\n'.join(lines), re.M):
            attributes = re.findall(r'^    ([\w-]+) => (.*)$', mem[2], re.M)
            latency = [v for k, v in attributes if k == 'read-latency']
            require(len(latency) == 1, 'missing memory read latency')
            for kind, port in attributes:
                if kind in ('writer', 'readwriter') or kind == 'reader' and int(latency[0]) > 0:
                    name = mem[1] + '.' + port
                    require(name + '.clk' in drivers, 'missing sequential memory clock')
                    consumers.append((name, 'memory_port', drivers[name + '.clk']))
                    events.append(('\n'.join(lines)[:mem.start()].count('\n'), name,
                                   'memory_port', drivers[name + '.clk']))
        # Every clocked effect is an independent freeze obligation too.
        effects = []
        for line_index, line in enumerate(lines):
            effect = re.match(r'  (printf|stop|assert|assume|cover)\((.*)\)', line)
            if effect:
                kind = 'print' if effect[1] == 'printf' else 'stop' if effect[1] == 'stop' else 'verification'
                effects.append((kind, arguments(effect[2])[0]))
                events.append((line_index, None, kind, arguments(effect[2])[0]))
        modules[header[2]] = dict(kind=header[1], body='\n'.join(line[2:] if line.startswith('  ') else line for line in body.splitlines()),
                                  ports=ports, instances=instances, drivers=drivers, aliases=aliases,
                                  consumers=consumers, effects=effects, events=events)
    return modules


def audit(reference, manifest, plan, binding, verilog):
    text = Path(reference).read_text()
    inventory = json.loads(Path(manifest).read_text())
    doc = json.loads(Path(plan).read_text())
    emitted = json.loads(Path(binding).read_text())
    manifest_sha = hashlib.sha256(Path(manifest).read_bytes()).hexdigest()
    plan_sha = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    require(emitted == dict(binding_version=1, scope='physical_clock_topology_only',
                           complete_fpga_capture=False, deployable_capture_image=False,
                           reference_sha256=digest(text), simulator_manifest_sha256=manifest_sha,
                           plan_sha256=plan_sha, emitted_verilog_sha256=hashlib.sha256(Path(verilog).read_bytes()).hexdigest()),
            'unbound physical plan emission')
    require(doc['plan_version'] == 1 and doc['scope'] == 'physical_clock_topology_only' and
            doc['reference_sha256'] == inventory['reference_sha256'] == digest(text) and
            doc['simulator_manifest_sha256'] == manifest_sha and
            doc['root_module'] == inventory['root_module'] == inventory['circuit'], 'unbound plan input')
    require(all(doc[k] is False for k in ('complete_fpga_capture', 'deployable_capture_image',
                                         'clock_rewrite_applied', 'ce_dependency_closure_proven')),
            'clock plan cannot establish capture or owner closure')
    require(doc['remaining_obligations'] == ['all_functional_and_ce_driver_owners_use_generated_gated_clocks',
            'external_ce_and_reset_writers_are_frozen_at_the_same_cut', 'physical_latch_bank_and_metasim_restore_mapping',
            'functional_memory_timing_bridge_host_and_pre_fame_ownership', 'connected_ungated_mmio_dma_transport'],
            'clock plan dropped pending obligations')
    modules = parse_modules(text)
    root = doc['root_module']
    scopes = {}

    def walk(module, path, parent=None, instance=None, ancestors=frozenset()):
        require(module in modules and module not in ancestors and path not in scopes, 'invalid hierarchy')
        definition = modules[module]
        scopes[path] = dict(module=module, parent=parent, instance=instance, **definition)
        for name, child in definition['instances'].items():
            walk(child, path + '.' + name, path, name, ancestors | {module})
    walk(root, root)
    require(sorted((p, s['module']) for p, s in scopes.items()) ==
            sorted((r['hierarchy'], r['module']) for r in inventory['instances']), 'incomplete instance inventory')
    native = []
    for path, scope in sorted(scopes.items()):
        if scope['kind'] == 'extmodule':
            expected = f"extmodule {scope['module']} :\n  input I : Clock\n  input CE : UInt<1>\n  output O : Clock\n  defname = BUFGCE"
            require(scope['body'] == expected, 'unsupported physical primitive or opaque owner')
            native.append(path)
    require(native, 'no native gates')

    def origin(path, expression, visited=frozenset()):
        key = (path, expression)
        require(key not in visited, 'cyclic clock alias')
        seen = visited | {key}
        scope = scopes[path]
        if expression is None:
            raise ValueError('missing clock expression')
        if path in native and expression == 'O':
            result = dict(origin(path, 'I', seen))
            result['gate_chain'] = result.get('gate_chain', []) + [path]
            return result
        if expression in scope['ports'] and scope['ports'][expression][0] == 'input':
            if scope['parent'] is None:
                require(scope['ports'][expression][1] == 'Clock', 'non-clock root')
                return dict(root_clock=expression)
            return origin(scope['parent'], scopes[scope['parent']]['drivers'][scope['instance'] + '.' + expression], seen)
        if expression in scope['drivers'] and (expression in scope['aliases'] or expression in scope['ports']):
            driver_value = scope['drivers'][expression]
            return dict(invalid_clock=path + '.' + expression) if driver_value is None else origin(path, driver_value, seen)
        if expression in ('UInt<1>("h0")', 'UInt<1>("h1")'):
            return dict(constant_clock=int(expression[-3]))
        operator = re.fullmatch(r'(\w+)\((.*)\)', expression)
        if operator:
            args = arguments(operator[2])
            if operator[1] in ('asClock', 'asUInt') and len(args) == 1:
                return origin(path, args[0], seen)
            if operator[1] == 'bits' and args[1:] == ['0', '0']:
                return origin(path, args[0], seen)
            return dict(data_clock=dict(hierarchy=path, expression=expression))
        field = re.fullmatch(r'(' + IDENT + r')\.(' + IDENT + r')', expression)
        if field and field[1] in scope['instances']:
            child = path + '.' + field[1]
            require(field[2] in scopes[child]['ports'], 'unknown clock pin')
            if scopes[child]['ports'][field[2]][0] == 'input':
                return origin(path, scope['drivers'][expression], seen)
            return origin(child, field[2], seen)
        raise ValueError('unresolved clock ' + path + '.' + expression)

    expected_domains, expected_consumers = [], []
    for path, scope in sorted(scopes.items()):
        for name, (_, tpe) in scope['ports'].items():
            if tpe == 'Clock':
                expected_domains.append(dict(clock_hierarchy=path + '.' + name, **origin(path, name)))
    def consumer_walk(path):
        scope = scopes[path]
        for _, name, kind, expression in sorted(scope['events'], key=lambda e: e[0]):
            if name is None:
                name = kind + '_' + str(len(expected_consumers))
            value = expression
            validif = re.fullmatch(r'validif\((.*)\)', value)
            if kind == 'memory_port' and validif:
                args = arguments(validif[1])
                require(args[0] == scope['drivers'][name + '.en'], 'memory clock guard mismatch')
                value = args[1]
            resolved = origin(path, value)
            require(set(resolved) <= {'root_clock', 'gate_chain'} and 'root_clock' in resolved, 'nonfunctional consumer clock')
            expected_consumers.append(dict(hierarchy=path + '.' + name, kind=kind, clock_expression=expression,
                origin=dict(clock_hierarchy=path + '.' + name, **resolved)))
        for child in sorted(scope['instances']):
            consumer_walk(path + '.' + child)
    consumer_walk(root)
    require(doc['clock_domains'] == sorted(expected_domains, key=lambda r: r['clock_hierarchy']), 'changed/missing clock origin')
    require(doc['sequential_consumers'] == sorted(expected_consumers, key=lambda r: r['hierarchy']), 'changed/missing sequential owner')
    consumer_paths = {r['hierarchy'] for r in expected_consumers}
    state_coverage = []
    for row in inventory['state']:
        path, adapter = row['hierarchy'], row['adapter']
        if adapter == 'metasim-bufgce-v1': owners = []
        elif adapter == 'firrtl-register-v1': owners = [path]
        elif adapter == 'firrtl-emitter-memory-pipeline-v1':
            owners = [path.rsplit('.', 1)[0] + '.' + row['clock_expression'].removesuffix('.clk')]
        elif adapter == 'firrtl-memory-v1': owners = sorted(p for p in consumer_paths if p.startswith(path + '.'))
        else: raise ValueError('unsupported clock owner adapter ' + adapter)
        require(set(owners) <= consumer_paths, 'unmapped inventory clock owner')
        state_coverage.append(dict(state_id=row['state_id'], hierarchy=path, clock_consumers=owners,
                                   physical_latch_mapping_required=adapter == 'metasim-bufgce-v1'))
    require(doc['state_clock_coverage'] == state_coverage, 'incomplete state/clock coverage')
    gates = doc['physical_gates']
    require(len(gates) == len(native), 'incomplete physical gates')
    for index, (path, gate) in enumerate(zip(native, gates)):
        scope = scopes[path]
        input_clock, output_clock = origin(path, 'I'), origin(path, 'O')
        require(set(input_clock) == {'root_clock'} and input_clock['root_clock'] == doc['common_source_clock'],
                'cascaded/unrelated physical source')
        logical = path + '.CE_latch'
        state_json = json.dumps(dict(hierarchy=logical, namespace='physical-bufgce-ce-latch-v1'), sort_keys=True, separators=(',', ':'))
        metasim = next((r for r in inventory['state'] if r['hierarchy'] == path + '.O'), None)
        require(metasim is not None and metasim['adapter'] == 'metasim-bufgce-v1', 'missing independent metasim owner')
        expected_contract = dict(contract='xilinx-bufgce-default-sync-v1', definition_sha256=digest(scope['body']),
            ce_type='SYNC', input_inverted=False, enable_inverted=False, state='transparent_low_ce_latch',
            public_pins=['I', 'CE', 'O'], direct_state_readout=False, physical_capture_binding='unsupported',
            required_cut='common_host_low_phase_all_owners_with_enable_latch_mapping', metasim_state_equivalent=False)
        expected = dict(index=index, hierarchy=path, module=scope['module'], physical_contract=expected_contract,
            source_clock=dict(clock_hierarchy=path + '.I', **input_clock), output_clock=dict(clock_hierarchy=path + '.O', **output_clock),
            ce_driver_scope=scope['parent'], ce_driver_expression=scopes[scope['parent']]['drivers'][scope['instance'] + '.CE'],
            logical_latch_hierarchy=logical, logical_latch_state_id=digest(state_json), metasim_output_state_id=metasim['state_id'],
            capture_mapping='pending_common_low_phase_ce_sampler_and_restore_adapter')
        require(gate == expected and gate['logical_latch_state_id'] != metasim['state_id'], 'changed physical latch/source/index mapping')
    require({r['origin']['root_clock'] for r in expected_consumers} == {doc['common_source_clock']}, 'unrelated functional clock')
    return dict(status='pass', scope='independent physical clock topology only', physical_fpga_capture=False,
                common_source_clock=doc['common_source_clock'], physical_gates=len(native),
                sequential_consumers=len(expected_consumers), clock_pins=len(expected_domains),
                reference_sha256=digest(text), plan_sha256=plan_sha)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--verilog', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='clock-plan-', dir=args.out))
    result = audit(args.reference, args.manifest, args.plan, args.binding, args.verilog)
    original_plan = json.loads(args.plan.read_text())
    original_binding = json.loads(args.binding.read_text())
    rejected = []
    for name in ('drop-gate', 'gate-index', 'metasim-state-alias', 'gate-source', 'ce-driver',
                 'drop-consumer', 'consumer-source', 'drop-clock-pin', 'clock-source',
                 'claim-capture', 'claim-ce-closure', 'drop-obligation', 'drop-state', 'state-owner', 'wrong-reference'):
        changed = json.loads(json.dumps(original_plan))
        if name == 'drop-gate': changed['physical_gates'].pop()
        elif name == 'gate-index': changed['physical_gates'][0]['index'] += 1
        elif name == 'metasim-state-alias':
            changed['physical_gates'][0]['logical_latch_state_id'] = changed['physical_gates'][0]['metasim_output_state_id']
        elif name == 'gate-source': changed['physical_gates'][0]['source_clock']['root_clock'] = 'otherClock'
        elif name == 'ce-driver': changed['physical_gates'][0]['ce_driver_expression'] = 'UInt<1>("h1")'
        elif name == 'drop-consumer': changed['sequential_consumers'].pop()
        elif name == 'consumer-source': changed['sequential_consumers'][0]['origin']['root_clock'] = 'otherClock'
        elif name == 'drop-clock-pin': changed['clock_domains'].pop()
        elif name == 'clock-source': changed['clock_domains'][0]['root_clock'] = 'otherClock'
        elif name == 'claim-capture': changed['complete_fpga_capture'] = True
        elif name == 'claim-ce-closure': changed['ce_dependency_closure_proven'] = True
        elif name == 'drop-obligation': changed['remaining_obligations'].pop()
        elif name == 'drop-state': changed['state_clock_coverage'].pop()
        elif name == 'state-owner': changed['state_clock_coverage'][0]['clock_consumers'] = ['missing']
        else: changed['reference_sha256'] = '0' * 64
        plan_file, binding_file = out / (name + '.json'), out / (name + '-binding.json')
        plan_file.write_text(json.dumps(changed, sort_keys=True, separators=(',', ':')))
        changed_binding = dict(original_binding, plan_sha256=digest(plan_file.read_text()))
        binding_file.write_text(json.dumps(changed_binding))
        try:
            audit(args.reference, args.manifest, plan_file, binding_file, args.verilog)
        except ValueError as error:
            rejected.append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('accepted coherently rehashed clock-plan corruption ' + name)
    result['rejected'] = rejected
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
