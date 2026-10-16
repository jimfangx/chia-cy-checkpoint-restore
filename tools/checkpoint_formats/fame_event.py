"""Read-only native VCS event capture for a retained, unthreaded FAME boundary.

Storage identities come from the compiler map. The actual emitted clocks and
all original ports are audited independently. Unsupported flattening, derived
clocks or replicated boundaries reject; this grants no Level-1 CPU support.
"""
import hashlib
import json
import re

from .codec import canonical, encode, event_phase, keys, require
from .multiclock_inventory import boundary_ports, sequential_blocks
from .multiclock_replay import document, ports_with_aliases, validate_signals
from .replay import IDENT, RANGE, builds
from .semantic import encode_semantic


def audit_event_boundary(manifest, boundary, mapping, generated, rtl, bufgce, gate):
    """Call after audit_mapping: bind every storage clock and complete boundary."""
    from .replay import modules
    boundary_ports(manifest, boundary)
    mods = modules(rtl + bufgce + gate)
    expected = {b['rtl_path']: e for b, e in zip(mapping['state'], manifest['state'])}
    owners, scopes = {}, {}

    class Scope:
        def __init__(self, module, path, parent=None, pins=None, ancestors=frozenset()):
            require(module in mods and module not in ancestors, 'missing/recursive event module ' + module)
            self.module, self.path, self.parent, self.pins = module, path, parent, pins or {}
            scopes[path] = self
            header, self.body = mods[module]
            self.ports = [dict(name=n, direction=d, width=int(w) + 1 if w else 1)
                          for d, w, n in re.findall(rf'\b(input|output)\s+(?:reg\s+)?{RANGE}({IDENT})', header)]
            self.inputs = {p['name'] for p in self.ports if p['direction'] == 'input'}
            self.aliases = dict(re.findall(rf'\bassign\s+({IDENT})\s*=\s*([^;]+);', self.body))
            self.aliases.update({n: e for w, n, e in re.findall(rf'\bwire\s+{RANGE}({IDENT})\s*=\s*([^;]+);', self.body)})
            self.children, self.outputs = {}, {}
            for child, instance, connections in re.findall(rf'^[ \t]*({IDENT})[ \t]+({IDENT})\s*\((.*?)\);', self.body, re.M | re.S):
                pins = dict(re.findall(rf'\.({IDENT})\s*\(([^()]*)\)', connections))
                scope = Scope(child, path + '.' + instance, self, pins, ancestors | {module})
                self.children[instance] = scope
                for port in scope.ports:
                    if port['direction'] == 'output' and port['name'] in pins:
                        self.outputs[pins[port['name']].strip()] = (scope, port['name'])

        def clock(self, expression, seen=frozenset()):
            expression = expression.strip(); key = self.path + '::' + expression
            require(key not in seen and re.fullmatch(IDENT, expression), 'unsupported/cyclic event clock ' + key)
            seen = seen | {key}
            if self.module in ('BUFGCE', 'AbstractClockGate') and expression == 'O':
                return self.path + '.O'
            if expression in self.inputs:
                if self.parent is None:
                    return self.path + '.' + expression
                require(expression in self.pins, 'unconnected event clock ' + key)
                return self.parent.clock(self.pins[expression], seen)
            if expression in self.outputs:
                scope, port = self.outputs[expression]
                return scope.clock(port, seen)
            require(expression in self.aliases, 'undriven event clock ' + key)
            return self.clock(self.aliases[expression], seen)

        def walk(self):
            for clock, body in sequential_blocks(self.body):
                for storage in re.findall(rf'^[ \t]*({IDENT})(?:\[[^\n;]+?\])?\s*<=', body, re.M):
                    path = self.path + '.' + storage
                    if path in expected:
                        domain = self.clock(clock)
                        require(path not in owners or owners[path] == domain, 'multiple event storage clocks ' + path)
                        owners[path] = domain
            for child in self.children.values():
                child.walk()

    root = Scope(generated['root_module'], generated['root_module']); root.walk()
    candidates = [s for s in scopes.values() if s.module == boundary['dut_module']]
    require(len(candidates) == 1 and candidates[0].parent is not None,
            'event capture requires one retained original boundary')
    dut = candidates[0]; parent = dut.parent
    require(sum(s.module == parent.module for s in scopes.values()) == 1, 'replicated event monitor parent')
    ports = ports_with_aliases(manifest, boundary)
    clocks = {c: dut.clock(c[len(manifest['dut_root']) + 1:]) for c in manifest['clock_inputs']}
    require(sorted(dut.ports, key=lambda p: p['name']) == sorted(ports + [
        dict(name=c[len(manifest['dut_root']) + 1:], direction='input', width=1) for c in clocks], key=lambda p: p['name']),
        'incomplete/reshaped retained event boundary')
    for alias in boundary['clock_aliases']:
        require(dut.clock(alias['name']) == clocks[manifest['dut_root'] + '.' + alias['source']],
                'wrong retained output clock alias')
    for path, e in expected.items():
        require(path.startswith(dut.path + '.'), 'mapped owner outside retained event boundary')
        if e['clock_domain'] == 'initial':
            owners[path] = 'initial'
        else:
            require(owners.get(path) == clocks[e['clock_domain']], 'wrong/missing emitted semantic clock ' + path)
    require(set(owners) == set(expected), 'incomplete emitted event state ownership')
    gate_paths = sorted(set(clocks.values()))
    host_clocks, host_pins = set(), set()
    for path in gate_paths:
        scope = scopes[path.rsplit('.', 1)[0]]
        require(scope.module == 'BUFGCE' and scope.parent == parent, 'unsupported event gate placement/model')
        host_clocks.add(parent.clock(scope.pins['I']))
        pin = scope.pins['I'].strip()
        seen = set()
        while pin not in parent.inputs:
            require(pin not in seen and re.fullmatch(IDENT, pin) and pin in parent.aliases,
                    'event host clock is not a direct parent input alias')
            seen.add(pin); pin = parent.aliases[pin].strip()
        host_pins.add(pin)
    require(len(host_clocks) == 1, 'event gates have different host clocks')
    require(len(host_pins) == 1 and next(iter(host_pins)) in parent.inputs,
            'event host clock is not a direct parent input')
    host_clock = parent.path + '.' + next(iter(host_pins))
    return dict(scope='native read-only retained FAME event boundary', dut_path=dut.path,
                parent_path=parent.path, parent_module=parent.module, host_clock=host_clock,
                clocks=clocks, gate_paths=gate_paths, semantic_entries=len(owners),
                semantic_words=sum(e['depth'] for e in manifest['state']), boundary_ports=len(dut.ports),
                CPU_level1_verified=False, CPU_level2_verified=False)


def prepare_monitor(manifest, boundary, mapping, binding, cuts, events, out):
    require(type(cuts) is list and cuts and cuts == sorted(set(cuts)) and
            all(type(c) is int and c >= 0 for c in cuts) and type(events) is int and events > 0,
            'invalid native event capture windows')
    require(all(b - a > events for a, b in zip(cuts, cuts[1:])), 'overlapping capture windows')
    prefix = binding['parent_path'] + '.'
    relative = lambda path: path[len(prefix):] if path.startswith(prefix) else None
    require(all(relative(b['rtl_path']) for b in mapping['state']), 'capture storage outside monitor parent')
    plan = []
    for e, b in zip(manifest['state'], mapping['state']):
        for address in range(e['depth']):
            plan.append(f"{relative(b['rtl_path'])}" + (f'[{address}]' if e['kind'] == 'memory' else '') + f" {e['width']}")
    out.mkdir(parents=True, exist_ok=True)
    (out / 'capture-plan.txt').write_text('\n'.join(plan) + '\n')
    clocks = manifest['clock_inputs']; gates = binding['gate_paths']; ports = ports_with_aliases(manifest, boundary)
    n = len(clocks); cycle_index = clocks.index(manifest['clock_inputs'][0])
    declarations = ['input wire host_clock'] + [f'input wire g{i}, ce{i}' for i in range(len(gates))]
    declarations += [f"input wire [{p['width'] - 1}:0] p{i}" for i, p in enumerate(ports)]
    pins = ['.host_clock(' + relative(binding['host_clock']) + ')']
    pins += [f'.g{i}({relative(g)}), .ce{i}({relative(g.rsplit(".", 1)[0] + ".CE")})' for i, g in enumerate(gates)]
    pins += [f".p{i}({relative(binding['dut_path'])}.{p['name']})" for i, p in enumerate(ports)]
    levels = '{' + ', '.join('g' + str(gates.index(binding['clocks'][c])) for c in clocks) + '}'
    enabled = '{' + ', '.join('ce' + str(gates.index(binding['clocks'][c])) for c in clocks) + '}'
    source = ['`timescale 1ps/1ps', 'module semantic_fame_event_monitor(' + ',\n'.join(declarations) + ');',
              'import "DPI-C" context function int fame_capture_init(input string plan, input string scope, input int unsigned words);',
              'import "DPI-C" context function int fame_capture_save(input string path);',
              'import "DPI-C" context function int fame_capture_verify();',
              'import "DPI-C" context function void semantic_fail(input string message);',
              f'bit [{n-1}:0] prior = 0, planned = 0, actual, upcoming;',
              f'longint unsigned counts [0:{n-1}];', 'longint unsigned event_index = 0;',
              'bit initialized = 0, enabled = 0, verify_state = 0;',
              f'bit captured [0:{len(cuts)-1}];', 'integer remaining = 0, fd = 0;',
              'string prefix, filename; longint unsigned window_cycle;',
              *[f"reg [{p['width']-1}:0] saved{i};" for i, p in enumerate(ports) if p['name'] not in {a['name'] for a in boundary['clock_aliases']}],
              'initial begin', '  enabled = $value$plusargs("fame_capture=%s", prefix);',
              f'  for (integer i=0; i<{n}; i=i+1) counts[i] = 0;',
              f'  for (integer i=0; i<{len(cuts)}; i=i+1) captured[i] = 0;',
              '  if (enabled && fame_capture_init(' + json.dumps(str(out / 'capture-plan.txt')) + ', $sformatf("%m"), ' + str(len(plan)) + ')) semantic_fail("CAPTURE_PLAN_REJECTED");', 'end',
              '// Inactive region precedes original register NBAs. Both directions',
              '// check the previous settled sample, including all non-clock ports.',
              'always @(host_clock) if (enabled && initialized) begin', '  #0;',
              f'  if ({levels} !== planned) semantic_fail("CAPTURE_UNPREDICTED_CLOCK_EVENT");']
    for i, p in enumerate(ports):
        if p['name'] not in {a['name'] for a in boundary['clock_aliases']}:
            source += [f'  if (p{i} !== saved{i}) semantic_fail("CAPTURE_UNSETTLED_BOUNDARY_{p["name"]}");']
    source += ['  if (verify_state && fame_capture_verify()) semantic_fail("CAPTURE_STATE_MOVED_BEFORE_EDGE");',
               '  verify_state = 0;', 'end',
               '// Observe actual gates after each host transition; never infer a',
               '// target rise from a driver credit or a host-cycle counter.',
               'always @(host_clock) if (enabled) begin', '  #1;', f'  actual = {levels};',
               '  if (initialized) begin',
               '    if (actual !== planned) semantic_fail("CAPTURE_CLOCK_PHASE_CHANGED");',
               '    if (actual != prior) begin',
               f'      for (integer i=0; i<{n}; i=i+1) if (!prior[{n-1}-i] && actual[{n-1}-i]) counts[i] = counts[i] + 1;',
               '      event_index = event_index + 1;', '    end',
               '  end else if (actual !== 0) semantic_fail("CAPTURE_INITIAL_CLOCK_HIGH");',
               f"  upcoming = host_clock ? {n}'b0 : {enabled};", '  prior = actual; planned = upcoming; initialized = 1;']
    # The first clock is explicit and retained in the layout, not a frequency guess.
    source += ['  if (!host_clock && actual == 0 && upcoming != 0) begin']
    for i, cut in enumerate(cuts):
        source += [f'    if (counts[{cycle_index}] == {cut} && !captured[{i}]) begin',
                   '      if (remaining) semantic_fail("CAPTURE_OVERLAPPING_WINDOW");',
                   f'      captured[{i}] = 1; remaining = {events}; window_cycle = {cut};',
                   '      filename = $sformatf("%s.%0d.state", prefix, window_cycle);',
                   '      if (fame_capture_save(filename)) semantic_fail("CAPTURE_STATE_FAILED"); verify_state = 1;',
                   '      filename = $sformatf("%s.%0d.jsonl", prefix, window_cycle);',
                   '      fd = $fopen(filename, "w"); if (!fd) semantic_fail("CAPTURE_TRACE_OPEN");',
                   '    end']
    source += ['  end']
    fmt = '{"event_index":%0d,"cycle":%0d,"before":{' + ','.join(json.dumps(c) + ':%0d' for c in clocks) + '},"rising_edges":{' + ','.join(json.dumps(c) + ':%0d' for c in clocks) + '},"clock_levels":{' + ','.join(json.dumps(c) + ':%0d' for c in clocks) + '}'
    args = ['event_index', f'counts[{cycle_index}]'] + [f'actual[{n-1-i}]' for i in range(n)] + [f'counts[{i}]' for i in range(n)] + [f'upcoming[{n-1-i}]' for i in range(n)]
    for direction in ('input', 'output'):
        fmt += ',"' + direction + 's":{' + ','.join(json.dumps(p['name']) + ':{"width":' + str(p['width']) + ',"value":"%h"}' for p in ports if p['direction'] == direction) + '}'
        args += [f'p{i}' for i, p in enumerate(ports) if p['direction'] == direction]
    fmt += '}'
    source += ['  if (remaining && upcoming != actual) begin',
               '    $fdisplay(fd, ' + json.dumps(fmt) + ', ' + ', '.join(args) + '); $fflush(fd);',
               '    remaining = remaining - 1;',
               '    if (!remaining) begin $fclose(fd); fd = 0; $display("CAPTURE_WINDOW cycle=%0d events=' + str(events) + '", window_cycle); end',
               '  end']
    for i, p in enumerate(ports):
        if p['name'] not in {a['name'] for a in boundary['clock_aliases']}:
            source += [f'  saved{i} = p{i};']
    source += ['end', 'final if (enabled) begin', '  if (remaining) semantic_fail("CAPTURE_INCOMPLETE_WINDOW");']
    source += [f'  if (!captured[{i}]) semantic_fail("CAPTURE_MISSING_CUT_{cut}");' for i, cut in enumerate(cuts)]
    source += ['  $display("CAPTURE_COMPLETE events=%0d counts0=%0d", event_index, counts[0]);', 'end', 'endmodule',
               f'bind {binding["parent_module"]} semantic_fame_event_monitor semantic_event_monitor(' + ',\n'.join(pins) + ');']
    (out / 'capture.sv').write_text('\n'.join(source) + '\n')
    (out / 'capture-layout.json').write_bytes(canonical(dict(binding=binding, cuts=cuts, events=events, cycle_clock=clocks[cycle_index])))


def package_window(manifest, boundary, configuration, rows, values):
    """Package one complete all-low captured window, retaining original labels."""
    require(type(rows) is list and rows, 'empty captured event window')
    clocks = manifest['clock_inputs']; ports = ports_with_aliases(manifest, boundary)
    first = rows[0]
    keys(first, {'event_index', 'cycle', 'before', 'rising_edges', 'clock_levels', 'inputs', 'outputs'})
    phase = dict(event_index=first['event_index'], cycle_clock=clocks[0],
                 clock_levels=dict(first['before']), rising_edges=dict(first['rising_edges']))
    event_phase(phase, first['cycle'])
    require(set(phase['clock_levels']) == set(clocks), 'unknown/missing captured window clocks')
    levels, counts = dict(phase['clock_levels']), dict(phase['rising_edges'])
    records = []
    for index, row in enumerate(rows):
        keys(row, {'event_index', 'cycle', 'before', 'rising_edges', 'clock_levels', 'inputs', 'outputs'})
        require(type(row['before']) is dict and type(row['rising_edges']) is dict and
                all(type(v) is int for v in [*row['before'].values(), *row['rising_edges'].values()]),
                'invalid captured window clock levels/counts')
        require(row['before'] == levels and row['rising_edges'] == counts and
                type(row['event_index']) is int and row['event_index'] == phase['event_index'] + index and
                type(row['cycle']) is int and row['cycle'] == counts[clocks[0]], 'captured window phase discontinuity')
        validate_signals(row, ports)
        for alias in boundary['clock_aliases']:
            require(int(row['outputs'][alias['name']]['value'], 16) == levels[manifest['dut_root'] + '.' + alias['source']],
                    'captured clock alias phase mismatch')
        upcoming = row['clock_levels']
        require(type(upcoming) is dict and set(upcoming) == set(clocks) and upcoming != levels and
                all(type(v) is int and v in (0, 1) for v in upcoming.values()), 'invalid captured window event')
        for c in clocks:
            counts[c] += int(levels[c] == 0 and upcoming[c] == 1)
        levels = dict(upcoming)
        records.append({k: row[k] for k in ('event_index', 'cycle', 'clock_levels', 'inputs', 'outputs')})
    require(type(values) is list and len(values) == sum(e['depth'] for e in manifest['state']), 'incomplete captured window state')
    iterator = iter(values)
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    ckpt = document('rtlckpt', rtl_build, phase, first['cycle'], [
        dict(state_id=e['state_id'], width=e['width'], depth=e['depth'], values=[next(iterator) for _ in range(e['depth'])])
        for e in manifest['state']])
    trace = document('trace', trace_build, phase, first['cycle'], records)
    return encode_semantic(ckpt, manifest), encode('trace', trace)
