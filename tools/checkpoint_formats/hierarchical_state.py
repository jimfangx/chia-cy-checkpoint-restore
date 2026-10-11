"""Complete compact storage inventory for hierarchical mapped netlists.

This enumerates physical shapes, not proven StateID relationships. Large
memories are kept as complete width/depth spans without allocating a Python
object per bit. Every instantiated leaf must have a concrete hash-bound model;
an empty synthesis stub or an unexplained module is never a state model.
"""

import re

from .codec import canonical, keys, require
from .formal_state_map import NAME, sha, unescape
from .replay import IDENT, RANGE, inventory_rtl, modules


def hierarchical_inventory(netlist, models_text, adapter, top):
    keys(adapter, {'hierarchy_adapter_version', 'models_sha256', 'cells'})
    require(type(adapter['hierarchy_adapter_version']) is int and adapter['hierarchy_adapter_version'] == 1,
            'unsupported hierarchical cell adapter')
    require(adapter['models_sha256'] == sha(models_text.encode()), 'unaudited hierarchical cell models')
    model_mods = modules(models_text)
    require(set(model_mods) == set(adapter['cells']) and
            len(model_mods) == len(re.findall(r'\bmodule\b', re.sub(r'//[^\n]*', '', models_text))),
            'incomplete/duplicate hierarchical cell models')
    for cell, spec in adapter['cells'].items():
        keys(spec, {'storage'})
        expected = {}
        require(type(spec['storage']) is list, 'unsupported hierarchical storage spec')
        for storage in spec['storage']:
            keys(storage, {'name', 'width', 'depth', 'kind'})
            name, width, depth, kind = (storage[k] for k in ('name', 'width', 'depth', 'kind'))
            require(re.fullmatch(IDENT, name) and type(width) is int and 0 < width < 2**31 and
                    type(depth) is int and 0 < depth < 2**31 and kind in ('register', 'memory') and
                    (kind == 'memory' or depth == 1) and name not in expected, 'unsupported hierarchical storage shape')
            expected[name] = width, depth, kind
        header, body = model_mods[cell]
        body = re.sub(r'/\*.*?\*/|//[^\n]*', '', body, flags=re.S)
        require(not re.search(r'\b(reg|logic|bit|integer|int|parameter)\b', header), 'stateful cell model ports')
        require(not re.search(r'\b(logic|bit|int|integer|shortint|longint|byte|real|time|event|typedef|enum|struct|union|parameter|localparam|generate|initial|assume|restrict|force|function|task|always_latch|always_comb|always_ff|negedge)\b', body),
                'unsupported/initialized hierarchical model state')
        require(inventory_rtl(model_mods, cell) == expected and len(re.findall(r'\breg\b', body)) == len(expected),
                'hidden/incomplete hierarchical model state')
        events = re.findall(r'@\s*\(([^)]*)\)', body)
        require(all(event.strip() == 'posedge CP' for event in events) and
                len(re.findall(r'\balways\b', body)) == len(events) and (expected or not events),
                'unsupported hierarchical model clock')
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', netlist, flags=re.S)
    parsed, emitted_stubs, cursor = {}, {}, 0
    pattern = re.compile(rf'\s*module\s+({NAME})\s*\(([^;]*)\);(.*?)endmodule\b', re.S)
    while text[cursor:].strip():
        match = pattern.match(text, cursor)
        require(match is not None, 'unsupported hierarchical netlist syntax')
        name, header, body = match.groups()
        name = unescape(name)
        require(name not in parsed and name not in emitted_stubs, 'duplicate/ambiguous netlist module')
        if name in model_mods:
            # Genus writes interfaces for explicit preserved RAM abstracts.
            # These are NOT simulation/formal models. Accept only an exact,
            # declaration-only interface backed by the concrete audited RAM.
            require(adapter['cells'][name]['storage'] and
                    all(s['kind'] == 'memory' for s in adapter['cells'][name]['storage']),
                    'unexpected emitted standard-cell model stub')
            ports = {}
            for statement in body.split(';'):
                statement = statement.strip()
                if not statement:
                    continue
                decl = re.fullmatch(rf'(input|output|wire)\s+(?:\[(\d+):(\d+)\]\s*)?({NAME}(?:\s*,\s*{NAME})*)', statement)
                require(decl is not None, 'stateful/behavioral emitted memory stub')
                direction, high, low, names = decl.groups()
                require(low in (None, '0'), 'unsupported emitted memory stub range')
                width = int(high) + 1 if high is not None else 1
                for port in names.split(','):
                    port = unescape(port)
                    if direction != 'wire':
                        require(port not in ports, 'duplicate emitted memory stub port')
                        ports[port] = [direction, width]
            model_ports = {p: [d, int(w) + 1 if w else 1] for d, w, p in
                           re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', model_mods[name][0])}
            require(ports == model_ports and set(unescape(n) for n in header.split(',')) == set(ports),
                    'emitted memory stub differs from concrete model interface')
            emitted_stubs[name] = ports
        else:
            parsed[name] = header, body
        cursor = match.end()
    require(top in parsed, 'missing mapped DUT top')
    decoded = {}
    declaration = re.compile(rf'(?:input|output|wire)\s+(?:\[\d+:\d+\]\s*)?{NAME}(?:\s*,\s*{NAME})*')
    for module, (header, body) in parsed.items():
        instances, seen = [], set()
        for statement in body.split(';'):
            statement = statement.strip()
            if not statement or declaration.fullmatch(statement):
                continue
            if statement.startswith('assign '):
                require(re.fullmatch(r"assign\s+[^=;]+=[A-Za-z0-9_$'\\\s\[\]:{},.~!&|^()+*/?<>-]+", statement),
                        'unsupported hierarchical assignment')
                continue
            match = re.fullmatch(rf'({NAME})\s+({NAME})\s*\((.*)\)', statement, re.S)
            require(match is not None, 'unsupported hierarchical netlist statement: ' + statement[:120])
            cell, instance, connections = match.groups()
            cell, instance = unescape(cell), unescape(instance)
            require(instance not in seen, 'duplicate hierarchical instance')
            seen.add(instance)
            require(cell in parsed or cell in model_mods, 'unsupported cell/memory without concrete model: ' + cell)
            port_list = re.findall(r'\.(' + IDENT + r')\s*\(([^()]*)\)', connections)
            residue = re.sub(r'\.' + IDENT + r'\s*\([^()]*\)', '', connections)
            require(not residue.replace(',', '').strip() and len(port_list) == len({p for p, _ in port_list}),
                    'unsupported/duplicate hierarchical instance ports')
            if cell in model_mods:
                port_names = set(re.findall(rf'\b(?:input|output)\s+{RANGE}({IDENT})', model_mods[cell][0]))
                port_names = {name for _, name in port_names}
                require({p for p, _ in port_list} == port_names, 'incomplete concrete cell/memory ports')
                if adapter['cells'][cell]['storage']:
                    require(dict(port_list).get('CP') == 'clock', 'unsupported mapped storage clock')
            instances.append((cell, instance, dict(port_list)))
        decoded[module] = instances
    records, counts, active = [], {}, set()

    def walk(module, components=(), clock_connected=True):
        require(module not in active, 'recursive mapped hierarchy')
        active.add(module)
        for cell, instance, ports in decoded[module]:
            path = (*components, instance)
            if cell in parsed:
                child_header, child_body = parsed[cell]
                has_clock = bool(re.search(r'\binput\s+(?:\[0:0\]\s*)?clock\b', child_header + ';' + child_body))
                walk(cell, path, clock_connected and has_clock and ports.get('clock') == 'clock')
            else:
                counts[cell] = counts.get(cell, 0) + 1
                for storage in adapter['cells'][cell]['storage']:
                    require(clock_connected, 'mapped storage outside the connected target clock')
                    records.append(dict(instance_components=list(path), cell=cell, **storage))
        active.remove(module)
    walk(top)
    require(records, 'empty mapped storage inventory')
    require(len({(*r['instance_components'], r['name']) for r in records}) == len(records), 'duplicate mapped storage')
    return dict(inventory_version=1, top=top, netlist_sha256=sha(netlist.encode()),
                models_sha256=sha(models_text.encode()), storage=records, cell_instances=counts,
                emitted_memory_interfaces=emitted_stubs,
                mapped_modules=sorted(parsed),
                physical_bits=sum(r['width'] * r['depth'] for r in records),
                physical_words=sum(r['depth'] for r in records), proof_status='unproven')


def bind_concrete_models(netlist, models_text, adapter, top):
    """Select exact emitted design definitions and complete concrete RAM models.

    Keep the raw Genus netlist immutable. Its declaration-only RAM interfaces
    conflict with the real model definitions in ordinary Verilog compilation.
    The build source omits only those independently checked empty interfaces;
    every emitted logic definition remains byte-for-byte unchanged. Both raw
    and selected source hashes must be bound by any future formal state map.
    This model binding does not prove state correspondence or permit deposits.
    """
    inventory = hierarchical_inventory(netlist, models_text, adapter, top)
    pattern = re.compile(rf'\bmodule\s+({NAME})\s*\([^;]*\);.*?\bendmodule\b', re.S)
    matches = list(pattern.finditer(netlist))
    names = [unescape(m[1]) for m in matches]
    require(len(names) == len(set(names)) and set(names) ==
            set(inventory['mapped_modules']) | set(inventory['emitted_memory_interfaces']),
            'unsupported raw netlist definition selection')
    selected = netlist
    for match in reversed(matches):
        if unescape(match[1]) in inventory['emitted_memory_interfaces']:
            selected = selected[:match.start()] + selected[match.end():]
    bound_inventory = hierarchical_inventory(selected, models_text, adapter, top)
    require(bound_inventory['storage'] == inventory['storage'] and
            bound_inventory['cell_instances'] == inventory['cell_instances'], 'model binding changed physical logic/state')
    binding = dict(binding_version=1, raw_netlist_sha256=sha(netlist.encode()),
                   selected_netlist_sha256=sha(selected.encode()), models_sha256=sha(models_text.encode()),
                   cell_adapter_sha256=sha(canonical(adapter)),
                   removed_declaration_only_memory_interfaces=sorted(inventory['emitted_memory_interfaces']),
                   proof_status='unproven', gate_restore_authorized=False)
    return selected, binding


def architecture_cell_adapter(candidate, standard_adapter, standard_models, memory_models):
    """Combine previously audited CK cells with regenerated concrete RAM shapes."""
    require(standard_adapter['models_sha256'] == sha(standard_models.encode()), 'changed standard cell models')
    cells = {}
    for cell, spec in standard_adapter['cells'].items():
        cells[cell] = dict(storage=[dict(name=s['rtl_path'], width=1, depth=1, kind='register') for s in spec['storage']])
    for entry in candidate['entries']:
        if entry['kind'] == 'memory':
            memory = entry['memory']
            cells[memory['cell']] = dict(storage=[dict(name='contents', width=entry['width'], depth=entry['depth'], kind='memory')])
    text = standard_models + '\n' + memory_models
    return text, dict(hierarchy_adapter_version=1, models_sha256=sha(text.encode()), cells=cells)
