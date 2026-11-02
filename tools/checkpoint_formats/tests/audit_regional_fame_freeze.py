"""Reconstruct regional FAME freeze equations from the original lowered IR.

Hashes and producer role receipts are not an authority for this check. The
original concrete executions, annotations and equations determine the expected
bank holds and native clock masks. This is compiler/component evidence only.
"""
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_native_fame_progress import (
    COMMON, STORED, WIDE, location, metadata,
)
from tools.checkpoint_formats.tests.audit_physical_clock_plan import IDENT, arguments, parse_modules

MASK = 'checkpoint_physical_mask'
RAW = 'checkpoint_physical_source_clock'
ROOT_GATE = 'checkpoint_physical_root_gate'
ZERO = 'UInt<1>("h0")'


def executions(modules, root):
    result = {}

    def walk(name, path, seen):
        require(name in modules and name not in seen, 'invalid freeze hierarchy')
        result[path] = name
        for instance, child in modules[name]['instances'].items():
            walk(child, path + '.' + instance, seen | {name})
    walk(root, root, set())
    return result


def registers(module):
    rows = {}
    lines = [re.sub(r' @\[.*$', '', line) for line in module['body'].splitlines()]
    for index, line in enumerate(lines):
        match = re.fullmatch(r'  reg (' + IDENT + r') : ([^,]+), (.*?)( with :)?', line)
        if match:
            name, tpe, clock = match.groups()[:3]
            require(name not in rows, 'duplicate freeze register')
            reset, init = ZERO, name
            if match[4]:
                require(index + 1 < len(lines) and lines[index + 1].startswith('    reset => ('),
                        'missing freeze register reset')
                values = arguments(lines[index + 1].removeprefix('    reset => (').removesuffix(')'))
                require(len(values) == 2, 'reshaped freeze register reset')
                reset, init = values
            rows[name] = dict(type=tpe, clock=clock, reset=reset, init=init)
    return rows


def call(text, name):
    require(text.startswith(name + '(') and text.endswith(')'), 'expected ' + name + ' expression')
    return arguments(text[len(name) + 1:-1])


def effects(module):
    result = []
    for raw_line in module['body'].splitlines():
        line = re.sub(r' @\[.*$', '', raw_line)
        match = re.fullmatch(r'  (printf|stop|assert|assume|cover)\((.*)\)(.*)', line)
        if match:
            result.append((match[1], arguments(match[2]), match[3]))
    return result


def memories(module):
    result = {}
    for match in re.finditer(r'^  mem (' + IDENT + r') :\n((?:    [^\n]*\n?)*)', module['body'], re.M):
        require(match[1] not in result, 'duplicate original model memory')
        result[match[1]] = re.findall(r'^    ([\w-]+) => (.*)$', match[2], re.M)
    return result


def normalized(module, expression, boundary, seen=frozenset()):
    if expression == boundary:
        return expression
    if expression in module['aliases']:
        require(expression not in seen and expression in module['drivers'], 'invalid freeze observation alias')
        return normalized(module, module['drivers'][expression], boundary, seen | {expression})
    match = re.fullmatch(r'(' + IDENT + r')\((.*)\)', expression)
    if match:
        return match[1] + '(' + ', '.join(normalized(module, a, boundary, seen) for a in arguments(match[2])) + ')'
    return expression


def targets_from(directory, binding):
    if 'regions' in binding:
        return [(r['target'], r['sideband_prefix']) for r in binding['regions']]
    if 'target' in binding:
        ports = binding.get('sideband_ports', [])
        freeze = [p['enclosing'] for p in ports if p['selected'] == 'ckpt_freeze']
        require(len(freeze) == 1 and freeze[0].endswith('ckpt_freeze'), 'missing bound freeze sideband')
        return [(binding['target'], freeze[0][:-len('ckpt_freeze')])]
    path = directory / 'targets.json'
    require(path.exists(), 'missing original freeze targets')
    rows = json.loads(path.read_text())
    # The small directed fixture may supply the exact sideband prefix with its target.
    require(rows and all(isinstance(r, dict) and set(r) == {'target', 'sideband_prefix'} for r in rows),
            'freeze targets require explicit sideband prefixes')
    return [(r['target'], r['sideband_prefix']) for r in rows]


def audit(directory):
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text())
    source_text, actual_text = ((directory / n).read_text() for n in ('host.fir', 'instrumented.fir'))
    roots = [re.search(r'^circuit (' + IDENT + r') :', text, re.M) for text in (source_text, actual_text)]
    require(all(roots) and roots[0][1] == roots[1][1], 'changed freeze circuit root')
    root = roots[0][1]
    source, actual = parse_modules(source_text), parse_modules(actual_text)
    old_paths, new_paths = executions(source, root), executions(actual, root)
    before_models, before = metadata(read('host-annotations.json'))
    after_models, after = metadata(read('instrumented-annotations.json'))
    require(before_models == after_models and set(before) == set(after), 'changed freeze model/role identities')
    binding_path = directory / 'binding.json'
    binding = read('binding.json') if binding_path.exists() else {}
    for key in ('complete_fpga_capture', 'deployable_capture_image', 'production_freeze_owners_bound',
                'metasim_restore_supported'):
        if key in binding:
            require(binding[key] is False, 'changed freeze image admission')
    selected = []
    for target, prefix in targets_from(directory, binding):
        match = re.fullmatch(r'~(' + IDENT + r')\|(' + IDENT + r')((?:/' + IDENT + ':' + IDENT + r')+)', target)
        require(match and match[1] == match[2] == root and re.fullmatch(r'checkpoint_inplace_[A-Za-z0-9_]*', prefix),
                'invalid source freeze target')
        path = root
        for instance, child in re.findall('/(' + IDENT + '):(' + IDENT + ')', match[3]):
            path += '.' + instance
            require(old_paths.get(path) == child and path in new_paths, 'stale source freeze target')
        require(not any(path == p or path.startswith(p + '.') or p.startswith(path + '.') for p, _ in selected),
                'overlapping freeze selections')
        selected.append((path, prefix))
    require(selected, 'empty freeze selections')

    def gates(name):
        rows = []
        for instance, child in source[name]['instances'].items():
            if source[child]['kind'] == 'extmodule':
                if re.search(r'^  defname = BUFGCE$', source[child]['body'], re.M):
                    rows.append(instance)
            else:
                rows.extend(instance + '.' + suffix for suffix in gates(child))
        return rows

    selection_clocks = {}
    for path, prefix in selected:
        owner = actual[new_paths[path]]
        source_owner = source[old_paths[path]]
        require(ROOT_GATE not in source_owner['instances'] and ROOT_GATE in owner['instances'],
                'missing original native root mask')
        primitive = actual[owner['instances'][ROOT_GATE]]
        require(primitive['kind'] == 'extmodule' and
                re.search(r'^  defname = BUFGCE$', primitive['body'], re.M), 'changed native root mask primitive')
        clock = owner['drivers'].get(ROOT_GATE + '.I')
        require(source_owner['ports'].get(clock) == ('input', 'Clock') and
                owner['drivers'].get(ROOT_GATE + '.CE') == 'not(' + MASK + ')', 'changed native root mask equation')
        selection_clocks[path] = clock
        # Bind every original ancestor hop to this region's own exposed input.
        parts = path.split('.')
        for index in range(1, len(parts)):
            parent = actual[new_paths['.'.join(parts[:index])]]
            instance = parts[index]
            pin_prefix = '' if index == len(parts) - 1 else prefix
            for pin in ('ckpt_freeze', MASK):
                require(parent['drivers'].get(instance + '.' + pin_prefix + pin) == prefix + pin,
                        'crossed regional freeze/mask sideband')
                require(parent['ports'].get(prefix + pin) == ('input', 'UInt<1>'),
                        'missing regional freeze/mask input')

    checked_models = checked_registers = stored_bits = 0
    all_role_paths = set()
    mutations = []
    for model in before_models:
        identity = model['model']
        keys = [k for k in before if k[0] == identity]
        located = {}
        for key in keys:
            old_path, old_owner, old_ref = location(source, root, before[key]['target'])
            new_path, new_owner, new_ref = location(actual, root, after[key]['target'])
            require(old_path == new_path and old_ref == new_ref and new_path not in all_role_paths,
                    'aliased or relocated freeze role')
            all_role_paths.add(new_path)
            located[key[1:]] = (old_path, old_owner, old_ref, new_owner)
        host_path = located[('', 'host_clock')][0].rsplit('.', 1)[0]
        require(sum(p == host_path for p in old_paths) == 1 and
                list(old_paths.values()).count(old_paths[host_path]) == 1,
                'replicated source FAME execution')
        old_owner = source[old_paths[host_path]]
        new_owner = actual[new_paths[host_path]]
        old_regs, new_regs = registers(old_owner), registers(new_owner)
        common_refs = {role: located[('', role)][2] for role in COMMON}
        for (domain, role), (path, owner, ref, _) in located.items():
            if role in ('gate_ce', 'gate_output'):
                emitted_gate = located[(domain, role)][3]
                require(path.rsplit('.', 2)[0] == host_path and owner['kind'] == 'extmodule' and
                        re.search(r'^  defname = BUFGCE$', owner['body'], re.M) and
                        ref == ('CE' if role == 'gate_ce' else 'O'), 'changed original native FAME gate')
                require(emitted_gate['kind'] == owner['kind'] and emitted_gate['ports'] == owner['ports'] and
                        emitted_gate['body'].splitlines()[1:] == owner['body'].splitlines()[1:],
                        'changed original native gate definition')
            else:
                require(path.rsplit('.', 1)[0] == host_path, 'split FAME role executions')
                width = 64 if role in WIDE else 1
                expected_type = 'Clock' if role == 'host_clock' else 'UInt<' + str(width) + '>'
                declaration = old_regs.get(ref)
                if role in STORED:
                    require(declaration and declaration['type'] == expected_type, 'reshaped original FAME register')
                    norm = lambda text: normalized(old_owner, text, common_refs['finishing'])
                    require(norm(declaration['clock']) == norm(common_refs['host_clock']), 'changed original observer clock')
                    original_reset = norm(declaration['reset']) == norm(common_refs['host_reset']) and \
                        re.fullmatch(r'UInt<\d+>\("h0"\)', declaration['init'])
                    next_value = old_owner['drivers'][ref]
                    next_args = call(next_value, 'mux') if next_value.startswith('mux(') else []
                    lowered_reset = declaration['reset'] == ZERO and declaration['init'] == ref and \
                        len(next_args) == 3 and norm(next_args[0]) == norm(common_refs['host_reset']) and \
                        re.fullmatch(r'UInt<\d+>\("h0"\)', next_args[1])
                    require(original_reset or lowered_reset, 'changed original observer reset')
                    stored_bits += width
        norm = lambda text: normalized(old_owner, text, common_refs['finishing'])
        for domain in model['domains']:
            gate = located[(domain, 'gate_ce')][0].rsplit('.', 1)[0].rsplit('.', 1)[1]
            require(located[(domain, 'gate_output')][0] == host_path + '.' + gate + '.O' and
                    norm(old_owner['drivers'][gate + '.I']) == norm(common_refs['host_clock']) and
                    norm(old_owner['drivers'][gate + '.CE']) == norm(located[(domain, 'launch')][2]) and
                    norm(located[(domain, 'pending')][2]) == norm(located[(domain, 'pending_flag')][2]),
                    'changed original FAME gate/pending correlation')
        selections = [(p, prefix) for p, prefix in selected if host_path == p or host_path.startswith(p + '.')]
        require(len(selections) <= 1, 'ambiguous frozen FAME execution')
        frozen = bool(selections)
        selected_path = selections[0][0] if frozen else None
        is_root = frozen and host_path == selected_path
        root_clock = selection_clocks.get(selected_path)

        def rewrite(text):
            return re.sub(r'(?<![A-Za-z0-9_$.])' + re.escape(root_clock) + r'(?![A-Za-z0-9_$])',
                          ROOT_GATE + '.O', text) if is_root else text

        require(all(new_owner['ports'].get(n) == p for n, p in old_owner['ports'].items()), 'changed original model port')
        for name, reg in old_regs.items():
            expected = dict(reg, clock=rewrite(reg['clock']))
            if frozen:
                expected.update(reset=ZERO, init=name)
            require(new_regs.get(name) == expected, 'changed FAME owner register declaration: ' + name)
            checked_registers += 1
        old_memories, new_memories = memories(old_owner), memories(new_owner)
        for name, attributes in old_memories.items():
            emitted = list(new_memories.get(name, []))
            if frozen:
                require(emitted.count(('reader', 'ckpt_read')) == 1, 'missing bank memory read port')
                emitted.remove(('reader', 'ckpt_read'))
            require(emitted == attributes, 'changed original FAME owner memory declaration')
        local_gates = gates(old_paths[host_path]) if frozen else []
        native = {i for i, m in old_owner['instances'].items() if source[m]['kind'] == 'extmodule' and
                  re.search(r'^  defname = BUFGCE$', source[m]['body'], re.M)}
        for line in old_owner['body'].splitlines():
            line = re.sub(r' @\[.*$', '', line)
            if re.fullmatch(r'  wire ' + IDENT + r' : .*', line):
                require(line in [re.sub(r' @\[.*$', '', s) for s in new_owner['body'].splitlines()],
                        'changed original model wire declaration')
        expected_effects = []
        for kind, values, suffix in effects(old_owner):
            values = [rewrite(v) for v in values]
            if frozen:
                enable_index = 1 if kind in ('printf', 'stop') else 2
                values[enable_index] = 'and(' + values[enable_index] + ', not(ckpt_freeze))'
            expected_effects.append((kind, values, suffix))
        require(effects(new_owner) == expected_effects, 'changed original FAME clocked effect')
        for name, expression in old_owner['drivers'].items():
            expected = rewrite(expression)
            if frozen and name in old_regs:
                reg = old_regs[name]
                expected = 'mux(ckpt_freeze, ' + name + ', mux(' + rewrite(reg['reset']) + ', ' + \
                    rewrite(reg['init']) + ', ' + expected + '))'
            elif frozen and name.endswith('.I') and name[:-2] in native:
                expected = root_clock if is_root else RAW
            elif frozen and name.endswith('.CE') and name[:-3] in native:
                ce_wire = 'checkpoint_physical_ce_' + str(local_gates.index(name[:-3]))
                require(new_owner['drivers'].get(ce_wire) == expected, 'changed original logical gate enable')
                expected = 'and(' + ce_wire + ', not(' + MASK + '))'
            elif frozen and re.fullmatch(IDENT + r'\.' + IDENT + r'\.en', name):
                # Original memory write enables acquire the bank hold.
                memory, port, _ = name.split('.')
                if re.search(r'^  mem ' + re.escape(memory) + r' :\n(?:    .*\n)*?    (?:writer|readwriter) => ' +
                             re.escape(port) + r'$', old_owner['body'], re.M):
                    expected = 'and(' + expected + ', not(ckpt_freeze))'
            require(new_owner['drivers'].get(name) == expected, 'changed original FAME owner equation: ' + name)
        # Every hop from the selected root to the model must forward the same hold.
        if frozen:
            require(new_owner['ports'].get('ckpt_freeze') == ('input', 'UInt<1>'), 'missing local observer hold')
            parts = host_path.split('.')
            start = len(selected_path.split('.'))
            for index in range(start, len(parts)):
                parent = actual[new_paths['.'.join(parts[:index])]]
                child = parts[index]
                require(parent['drivers'].get(child + '.ckpt_freeze') == 'ckpt_freeze', 'crossed local observer hold')
                child_source = old_paths['.'.join(parts[:index + 1])]
                if gates(child_source):
                    parent_path = '.'.join(parts[:index])
                    raw = selection_clocks[selected_path] if parent_path == selected_path else RAW
                    require(parent['drivers'].get(child + '.' + MASK) == MASK and
                            parent['drivers'].get(child + '.' + RAW) == raw, 'crossed local native clock/mask')
        checked_models += 1
        mutations.append((host_path, old_owner, new_owner, located, frozen))
    require(any(row[-1] for row in mutations), 'no selected FAME observer owner was checked')
    return dict(model_identities=checked_models, roles=len(before), stored_bits=stored_bits,
                original_owner_registers=checked_registers, selected_regions=len(selected),
                complete_fpga_capture=False, deployable_capture_image=False)


def mutation_probes(directory):
    """Exercise the independent checker against changed raw files, ignoring hashes.

    Mutations keep producer sidecars untouched on purpose: no digest is consulted
    by audit(), so recomputing every digest gives the same structural rejection.
    Original evidence files are never changed.
    """
    directory = Path(directory)
    audit(directory)
    files = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    text = files['instrumented.fir'].decode()
    annotations = json.loads(files['instrumented-annotations.json'])
    _, roles = metadata(annotations)
    root = re.search(r'^circuit (' + IDENT + r') :', text, re.M)[1]
    modules = parse_modules(text)
    candidates = [(a, location(modules, root, a['target'])) for key, a in roles.items() if key[2] == 'completed_steps']
    frozen = [(a, loc) for a, loc in candidates if loc[1]['drivers'].get(loc[2], '').startswith('mux(ckpt_freeze, ')]
    require(frozen, 'mutation fixture must select a FAME model')
    stored, (_, owner, ref) = frozen[0]
    driver = owner['drivers'][ref]
    reg = registers(owner)[ref]
    changed = {
        'freeze-condition': text.replace(ref + ' <= ' + driver, ref + ' <= ' + driver.replace('mux(ckpt_freeze, ', 'mux(' + ZERO + ', ', 1), 1),
        'hold-value': text.replace(ref + ' <= ' + driver, ref + ' <= ' + driver.replace('mux(ckpt_freeze, ' + ref + ', ', 'mux(ckpt_freeze, UInt<64>("h0"), ', 1), 1),
        'functional-next': text.replace(ref + ' <= ' + driver, ref + ' <= mux(ckpt_freeze, ' + ref + ', UInt<64>("h0"))', 1),
        'register-clock': text.replace('reg ' + ref + ' : ' + reg['type'] + ', ' + reg['clock'],
                                       'reg ' + ref + ' : ' + reg['type'] + ', asClock(UInt<1>("h0"))', 1),
        'register-reset': text.replace('reset => (' + reg['reset'] + ', ' + reg['init'] + ')',
                                       'reset => (UInt<1>("h1"), ' + reg['init'] + ')', 1),
    }
    # Original output/alias writers are checked as well as observer registers.
    _, source_roles = metadata(json.loads(files['host-annotations.json']))
    source_role = source_roles[(stored['model'], stored['domain'], stored['role'])]
    source_modules = parse_modules(files['host.fir'].decode())
    _, original_owner, _ = location(source_modules, root, source_role['target'])
    node = next((name for name in sorted(original_owner['aliases']) if name in owner['drivers'] and
                 'node ' + name + ' = ' + owner['drivers'][name] in text), None)
    if node:
        old = owner['drivers'][node]
        changed['original-alias'] = text.replace('node ' + node + ' = ' + old, 'node ' + node + ' = not(' + old + ')', 1)
    else:
        connect = next((name for name, port in sorted(original_owner['ports'].items()) if port[0] == 'output' and
                        port[1].startswith('UInt<') and name in owner['drivers'] and
                        name + ' <= ' + owner['drivers'][name] in text), None)
        # Wires remain eligible when emitter preparation converted every node.
        if connect is None:
            connect = next((name for name in sorted(original_owner['aliases']) if name in owner['drivers'] and
                            name + ' <= ' + owner['drivers'][name] in text), None)
        require(connect is not None, 'missing original alias/output mutation site')
        old = owner['drivers'][connect]
        changed['original-alias'] = text.replace(connect + ' <= ' + old, connect + ' <= not(' + old + ')', 1)
    ce = next((name for name in owner['drivers'] if name.endswith('.CE') and
               owner['drivers'][name].startswith('and(checkpoint_physical_ce_')), None)
    if ce:
        changed['native-ce-mask'] = text.replace(ce + ' <= ' + owner['drivers'][ce], ce + ' <= UInt<1>("h1")', 1)
    rejected = {}
    with tempfile.TemporaryDirectory(prefix='regional-fame-freeze-') as temporary:
        target = Path(temporary)
        for name, payload in files.items():
            (target / name).write_bytes(payload)
        for name, mutated in changed.items():
            require(mutated != text, 'missing freeze mutation site: ' + name)
            (target / 'instrumented.fir').write_text(mutated)
            try:
                audit(target)
            except ValueError as error:
                rejected[name] = str(error)
            else:
                raise ValueError('regional FAME freeze mutation was accepted: ' + name)
        (target / 'instrumented.fir').write_bytes(files['instrumented.fir'])
        bad = copy.deepcopy(annotations)
        bad.append(copy.deepcopy(stored))
        (target / 'instrumented-annotations.json').write_text(json.dumps(bad))
        try:
            audit(target)
        except ValueError as error:
            rejected['duplicated-role'] = str(error)
        else:
            raise ValueError('duplicated regional FAME role was accepted')
    return rejected
