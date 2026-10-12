"""Production parent noninterference and live queue-bit obligations.

These are compositional lemmas, never a complete map or loader authorization.
Raw queue counterexamples remain required evidence. Independent child outputs
replace the exact child instance connections; every child input, parent output
and parent register transition is checked. No reset/input assumptions are used.
"""

import json
from pathlib import Path
import re

from .codec import canonical, require
from .formal_state_map import sha
from .production_dut import audit_architecture
from .production_queue import instances, miter as queue_miter, port_shapes, reconstruct as queue_binding, validate_proof
from .replay import IDENT, RANGE, modules


SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_CONTEXT_BINDING) miter $env(CHECKPOINT_CONTEXT_MITER) script $env(CHECKPOINT_CONTEXT_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
analyze -sv $env(CHECKPOINT_CONTEXT_MITER)
elaborate -top $env(CHECKPOINT_CONTEXT_TOP)
clock clock
reset -none
prove -all
report -summary
set out [open context-results.tsv w]
puts $out "FORMAT\tproduction-context-v1"
puts "CHECKPOINT_CONTEXT_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Context input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_CONTEXT_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_CONTEXT_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def ansi_shapes(header):
    """Original emitter interface, including combinational/no-reset children."""
    ports = {}
    for declaration in header.split(','):
        match = re.fullmatch(rf'\s*(input|output)\s+{RANGE}({IDENT})\s*', declaration)
        require(match is not None, 'unsupported production context ANSI interface')
        direction, high, port = match.groups()
        require(port not in ports, 'duplicate production context port')
        ports[port] = (direction, int(high) + 1 if high else 1)
    for port in ('clock', 'reset'):
        require(port not in ports or ports[port] == ('input', 1), 'unsupported context clock/reset shape')
    return ports


def reconstruct(architecture, synthesis_evidence, queue_proof):
    architecture = Path(architecture)
    candidate = audit_architecture(architecture)
    queues = queue_binding(architecture, synthesis_evidence)
    prior = validate_proof(queues, queue_proof)
    require(not prior['unproven_obligations']['register'] and
            not prior['unproven_obligations']['memory_port'], 'unproven queue state/port premise')
    cuts = {}
    for property_name in prior['unproven_obligations']['output']:
        name, port = property_name.split('.')[-1].split('_output_')
        width = queues['queues'][name]['ports'][port][1]
        require((port == 'io_deq_valid' and width == 1) or
                (port in ('io_deq_bits_echo_tl_state_size', 'io_deq_bits_tl_state_size') and width == 4),
                'unsupported failed queue output')
        cuts.setdefault(name, {})[port] = dict(width=width, independent_mask=1 << (width - 1),
                                             raw_obligation=property_name)
    original = modules((architecture / 'architecture.sv').read_text())
    parents, matched = {}, []
    for name, (header, body) in original.items():
        children = instances(body)
        selected = {n: s for n, s in children.items() if s['cell'] in cuts}
        if not selected:
            continue
        ports = port_shapes(header, body)
        regs = {r: int(w) + 1 if w else 1 for w, r in
                re.findall(rf'\breg\s+{RANGE}({IDENT})\s*;', body)}
        entries = [e for e in candidate['entries'] if e['module'] == name]
        require(all(e['kind'] == 'register' for e in entries) and
                {e['original_path'].rsplit('.', 1)[-1]: e['width'] for e in entries} == regs and
                len(re.findall(r'\breg\b', body)) == len(regs), 'unsupported/hidden parent storage')
        require(not re.search(r'\b(initial|force|assume|restrict)\b', body), 'constrained parent context')
        specs = {}
        for instance, child in children.items():
            require(child['cell'] in original, 'unknown context child')
            child_ports = port_shapes(*original[child['cell']])
            require(child_ports.keys() == child['ports'].keys(), 'incomplete parent child connections')
            require(all(re.fullmatch(IDENT, child['ports'][p]) for p, (d, _) in child_ports.items()
                        if d == 'output'), 'unsupported context output connection')
            specs[instance] = dict(child, interface=child_ports, cuts=cuts.get(child['cell'], {}))
            for port, cut in specs[instance]['cuts'].items():
                matched.append(cut['raw_obligation'])
        parents[name] = dict(header=header, body=body, ports=ports, registers=regs, children=specs)
    require(sorted(matched) == sorted(prior['unproven_obligations']['output']),
            'missing/duplicate failed-output parent context')
    return dict(context_version=1, artifact_type='production_composition_lemmas',
                queue_binding=queues, queue_binding_sha256=sha(canonical(queues)),
                prior_queue_proof=str(Path(queue_proof).resolve()), prior_queue_audit=prior,
                prior_queue_artifacts={n: sha((Path(queue_proof) / n).read_bytes()) for n in
                    ('binding.json', 'miter.sv', 'prove.tcl', 'queue-results.tsv', 'jasper.log')},
                cuts=cuts, parents=parents, architecture_source=(architecture / 'architecture.sv').read_text(),
                memory_source=(architecture / 'memory-models.v').read_text(),
                semantic_entries=candidate['entries'], top=candidate['top'],
                formal_state_map_complete=False, gate_restore_authorized=False)


def _parent_source(name, spec, side):
    body = spec['body']
    interface = [f'{d} [{w-1}:0] {p}' for p, (d, w) in spec['ports'].items()]
    for instance, child in sorted(spec['children'].items(), key=lambda kv: kv[1]['start'], reverse=True):
        lines = []
        for port, (direction, width) in child['interface'].items():
            signal = 'child_' + instance + '_' + port
            if direction == 'output':
                interface.append(f'input [{width-1}:0] {signal}')
                lines.append(f'assign {child["ports"][port]} = {signal};')
            else:
                interface.append(f'output [{width-1}:0] {signal}')
                lines.append(f'assign {signal} = {child["ports"][port]};')
        body = body[:child['start']] + '\n'.join(lines) + body[child['end']:]
    require(not instances(body), 'uncut context instance')
    return f'module {side}_{name}(' + ',\n'.join(interface) + ');\n' + body + '\nendmodule\n'


def parent_miter(binding):
    texts, top_ports, lines = [], ['input clock'], []
    for name, spec in binding['parents'].items():
        for side in ('reference', 'implementation'):
            texts.append(_parent_source(name, spec, side))
        signals = {}
        for port, (direction, width) in spec['ports'].items():
            if direction == 'input':
                signal = 'clock' if port == 'clock' else name + '_' + port
                if port != 'clock':
                    top_ports.append(f'input [{width-1}:0] {signal}')
                signals[port] = (signal, signal)
            else:
                signals[port] = tuple(side + '_' + name + '_' + port for side in ('reference', 'implementation'))
                for signal in signals[port]:
                    lines.append(f'wire [{width-1}:0] {signal};')
                lines.append(f'{name}_output_{port}: assert property (@(posedge clock) '
                             f'{signals[port][0]} == {signals[port][1]});')
        for instance, child in spec['children'].items():
            for port, (direction, width) in child['interface'].items():
                key = 'child_' + instance + '_' + port
                signal = name + '_' + key
                if direction == 'output':
                    top_ports.append(f'input [{width-1}:0] {signal}')
                    if port in child['cuts']:
                        mask = child['cuts'][port]['independent_mask']
                        other = 'different_' + signal
                        top_ports.append(f'input [{width-1}:0] {other}')
                        signals[key] = (signal, f'(({signal} & {width}\'d{((1 << width)-1) ^ mask}) | '
                                               f'({other} & {width}\'d{mask}))')
                        for bit in range(width):
                            if mask & (1 << bit):
                                lines.append(f'{signal}_different_{bit}: cover property (@(posedge clock) '
                                             f'{signal}[{bit}] != {other}[{bit}]);')
                    else:
                        signals[key] = (signal, signal)
                else:
                    signals[key] = tuple(side + '_' + signal for side in ('reference', 'implementation'))
                    for tap in signals[key]:
                        lines.append(f'wire [{width-1}:0] {tap};')
                    lines.append(f'{signal}_equal: assert property (@(posedge clock) '
                                 f'{signals[key][0]} == {signals[key][1]});')
        for i, side in enumerate(('reference', 'implementation')):
            connections = ', '.join(f'.{p}({values[i]})' for p, values in signals.items())
            lines.append(f'{side}_{name} {side}_{name}({connections});')
        relation = ' && '.join(f'(reference_{name}.{reg} == implementation_{name}.{reg})'
                              for reg in spec['registers']) or "1'b1"
        lines.append(f'wire {name}_relation = {relation};')
        # Output/tap equality requires only the current complete parent relation.
        lines = [re.sub(r'(@\(posedge clock\) )', rf'\g<1>{name}_relation |-> ', line)
                 if line.startswith(name + '_') and ': assert property' in line else line for line in lines]
        for reg in spec['registers']:
            lines.append(f'{name}_step_{reg}: assert property (@(posedge clock) {name}_relation |=> '
                         f'reference_{name}.{reg} == implementation_{name}.{reg});')
            for value in (0, 1):
                lines.append(f'{name}_state_{reg}_{value}: cover property (@(posedge clock) {name}_relation && '
                             f'reference_{name}.{reg} == {spec["registers"][reg]}\'d{value});')
        lines.append(f'{name}_edge: cover property (@(posedge clock) {name}_relation ##1 {name}_relation);')
        lines.append(f'{name}_reset_seen: cover property (@(posedge clock) {name}_relation && {name}_reset);')
    return ('\n'.join(texts) + '\nmodule production_context_miter(' + ',\n'.join(top_ports) + ');\n' +
            '\n'.join(lines) + '\nendmodule\n').encode()


def live_miter(binding):
    text = queue_miter(binding['queue_binding']).decode()
    lines = []
    for name, cuts in binding['cuts'].items():
        for port, cut in cuts.items():
            width, mask = cut['width'], cut['independent_mask']
            live = ((1 << width) - 1) ^ mask
            if live:
                lines.append(f'{name}_live_{port}: assert property (@(posedge clock) {name}_relation |-> '
                             f'(reference_{name}_{port} & {width}\'d{live}) == '
                             f'(implementation_{name}_{port} & {width}\'d{live}));')
    return (text.rsplit('endmodule', 1)[0] + '\n'.join(lines) + '\nendmodule\n').encode()


def whole_miter(binding):
    """Entire original hierarchy with universal common memory read-word cuts.

    All actual memory input ports (including addresses and clock), all captured
    registers and all top outputs are obligations. Array equality is a separate
    induction premise supplied by the already proven complete memory adapters;
    the word cut does not authorize a gate map or omit content obligations.
    """
    design = modules(binding['architecture_source'])
    memories = modules(binding['memory_source'])
    generated, exposure, active = {}, {}, set()

    def build(name):
        if name in generated:
            return
        require(name not in active, 'recursive context hierarchy')
        active.add(name)
        header, body = design[name]
        require('ckcontext_' not in body + header, 'context identifier collision')
        ports, extras, changes = ansi_shapes(header), {}, []
        for instance, child in instances(body).items():
            cell, connections = child['cell'], dict(child['ports'])
            additions = []
            if cell in memories:
                interface = ansi_shapes(memories[cell][0])
                require(interface.keys() == connections.keys() and
                        interface.get('CP') == ('input', 1) and interface.get('WE') == ('input', 1) and
                        all(p in ('CP', 'WE', 'WA', 'WD', 'RA0', 'RA1', 'Q0', 'Q1') for p in interface),
                        'incomplete/unsupported memory context ports')
                for port, (direction, width) in interface.items():
                    extra = 'ckcontext_' + instance + '_' + port
                    # Array read words are arbitrary common inputs. Actual
                    # writes, read addresses and clocks are independently exposed.
                    extras[extra] = dict(direction='input' if direction == 'output' else 'output',
                                         width=width, role='memory_read' if direction == 'output' else 'memory_input')
                    additions.append(f'assign {connections[port]} = {extra};' if direction == 'output' else
                                     f'assign {extra} = {connections[port]};')
                replacement = '\n'.join(additions)
            else:
                require(cell in design, 'unknown whole-DUT context child')
                require(ansi_shapes(design[cell][0]).keys() == connections.keys(), 'incomplete whole-DUT child ports')
                build(cell)
                for port, info in exposure[cell].items():
                    extra = 'ckcontext_' + instance + '_' + port
                    extras[extra] = info
                    connections[port] = extra
                for port, cut in binding['cuts'].get(cell, {}).items():
                    width, mask = cut['width'], cut['independent_mask']
                    extra = 'ckcontext_inject_' + instance + '_' + port
                    internal = 'ckcontext_original_' + instance + '_' + port
                    extras[extra] = dict(direction='input', width=width, role='independent_output')
                    old = connections[port]
                    require(re.fullmatch(IDENT, old), 'unsupported whole-DUT cut connection')
                    additions.extend([f'wire [{width-1}:0] {internal};',
                                      f'assign {old} = ({internal} & {width}\'d{((1 << width)-1) ^ mask}) | '
                                      f'({extra} & {width}\'d{mask});'])
                    connections[port] = internal
                replacement = f'ckcontext_{cell} {instance}(' + ', '.join(
                    f'.{p}({v})' for p, v in connections.items()) + ');\n' + '\n'.join(additions)
            changes.append((child['start'], child['end'], replacement))
        for start, end, replacement in sorted(changes, reverse=True):
            body = body[:start] + replacement + body[end:]
        interface = [f'{d} [{w-1}:0] {p}' for p, (d, w) in ports.items()]
        interface += [f'{s["direction"]} [{s["width"]-1}:0] {p}' for p, s in extras.items()]
        generated[name] = f'module ckcontext_{name}(' + ',\n'.join(interface) + ');\n' + body + '\nendmodule\n'
        exposure[name] = extras
        active.remove(name)

    top = binding['top']
    build(top)
    require(set(generated) == set(design), 'unreachable/omitted whole-DUT context module')
    registers = [e for e in binding['semantic_entries'] if e['kind'] == 'register']
    all_memories = [e for e in binding['semantic_entries'] if e['kind'] == 'memory']
    extras = exposure[top]
    require(sum(s['role'] == 'independent_output' for s in extras.values()) ==
            sum(len(v) for v in binding['cuts'].values()), 'incomplete whole-DUT injection scope')
    require(sum(s['role'] == 'memory_read' for s in extras.values()) ==
            sum(len(e['memory']['reads']) for e in all_memories), 'incomplete whole-DUT memory cut scope')
    top_ports, lines, connections = ['input clock'], [], [[], []]
    interface = ansi_shapes(design[top][0])
    interface.update({p: (s['direction'], s['width']) for p, s in extras.items()})
    for port, (direction, width) in interface.items():
        if direction == 'input':
            if port == 'clock':
                pair = ['clock', 'clock']
            elif extras.get(port, {}).get('role') == 'independent_output':
                pair = ['reference_' + port, 'implementation_' + port]
                top_ports.extend(f'input [{width-1}:0] {p}' for p in pair)
                lines.append(f'{port}_different: cover property (@(posedge clock) {pair[0]} != {pair[1]});')
            else:
                pair = [port, port]
                top_ports.append(f'input [{width-1}:0] {port}')
        else:
            pair = ['reference_' + port, 'implementation_' + port]
            lines.extend(f'wire [{width-1}:0] {p};' for p in pair)
            lines.append(f'{port}_equal: assert property (@(posedge clock) whole_relation |-> {pair[0]} == {pair[1]});')
        for i in range(2):
            connections[i].append(f'.{port}({pair[i]})')
    for i, side in enumerate(('reference', 'implementation')):
        lines.append(f'ckcontext_{top} {side}(' + ', '.join(connections[i]) + ');')
    relation = ' && '.join(f'(reference.{e["original_path"]} == implementation.{e["original_path"]})' for e in registers)
    require(registers and len(registers) == len({e['state_id'] for e in registers}), 'incomplete context register relation')
    lines.append('wire whole_relation = ' + relation + ';')
    for i, entry in enumerate(registers):
        path, width = entry['original_path'], entry['width']
        lines.append(f'state_{i}_step: assert property (@(posedge clock) whole_relation |=> reference.{path} == implementation.{path});')
        for value in (0, 1):
            lines.append(f'state_{i}_value_{value}: cover property (@(posedge clock) whole_relation && reference.{path} == {width}\'d{value});')
    lines.extend(['whole_edge: cover property (@(posedge clock) whole_relation ##1 whole_relation);',
                  'whole_reset_seen: cover property (@(posedge clock) whole_relation && reset);'])
    return ('\n'.join(generated.values()) + '\nmodule production_context_miter(' + ',\n'.join(top_ports) + ');\n' +
            '\n'.join(lines) + '\nendmodule\n').encode()


def proof_inputs(binding, kind):
    require(kind in ('parent', 'live', 'whole'), 'unsupported context proof')
    return dict(binding=canonical(dict(binding=binding, kind=kind)),
                miter={'parent': parent_miter, 'live': live_miter, 'whole': whole_miter}[kind](binding), script=SCRIPT.encode())


def properties(binding, kind):
    top = 'production_queue_miter' if kind == 'live' else 'production_context_miter'
    text = proof_inputs(binding, kind)['miter'].decode()
    result = {'<embedded>::' + top + '.' + n: k for n, k in
              re.findall(r'^(\w+): (assert|cover) property', text, re.M)}
    result.update({n + ':precondition1': 'cover' for n, k in list(result.items()) if k == 'assert'})
    return result


def read_results(binding, kind, proof):
    """Check exact inputs, complete obligation membership and raw engine records."""
    proof = Path(proof)
    artifacts = proof_inputs(binding, kind)
    require(all((proof / file).read_bytes() == artifacts[role] for role, file in
                (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl'))),
            'changed/unbound context proof inputs')
    rows = (proof / 'context-results.tsv').read_text().splitlines()
    require(rows[:1] == ['FORMAT\tproduction-context-v1'] and rows[-1:] == ['END'], 'incomplete context evidence')
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate context input')
            inputs[row[1]] = row[2]
        else:
            require(len(row) == 4 and row[0] == 'PROPERTY' and row[1] not in results,
                    'unsupported/duplicate context result')
            results[row[1]] = tuple(row[2:])
    expected = properties(binding, kind)
    require(inputs == {r: sha(a) for r, a in artifacts.items()}, 'stale context identity')
    require(set(results) == set(expected), 'missing/extra context obligations')
    for name, property_kind in expected.items():
        require(results[name][0] == property_kind and results[name][1] in
                (('proven', 'cex') if property_kind == 'assert' else ('covered',)),
                'undetermined/vacuous context obligation: ' + name)
    log = (proof / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and
            'CHECKPOINT_CONTEXT_RESET=none' in log and 'Exiting the analysis session with status 0.' in log and
            re.search(r'assumptions\s*:\s*0\b', log), 'failed/constrained/blackboxed context proof')
    raw = re.findall(r'^CHECKPOINT_CONTEXT_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == results, 'raw context result mismatch')
    hashes = re.findall(r'^CHECKPOINT_CONTEXT_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(hashes) == len(artifacts) and dict(hashes) == inputs, 'raw context identity mismatch')
    for prop, (_, status) in results.items():
        name = re.escape(prop.split('::', 1)[1])
        pattern = (r'A counterexample \(cex\).*property "' + name + '"' if status == 'cex' else
                   r'The (?:cover )?property "' + name + '" was ' + status + r' (?:in|at) ')
        require(re.search(pattern, log), 'missing context engine result: ' + prop)
    return results


def validate(binding, kind, proof):
    results = read_results(binding, kind, proof)
    allowed_cex = set(binding['prior_queue_audit']['unproven_obligations']['output']) if kind == 'live' else set()
    if kind == 'parent':
        allowed_cex = {'<embedded>::production_context_miter.' + p for p in (
            'AXI4UserYanker_output_auto_in_b_bits_echo_tl_state_size',
            'AXI4Deinterleaver_output_auto_anon_in_r_bits_echo_tl_state_size')}
    require(allowed_cex <= results.keys(), 'missing retained context counterexamples')
    for name, (property_kind, status) in results.items():
        require(status == ('cex' if name in allowed_cex else 'proven' if property_kind == 'assert' else 'covered'),
                'unproven/changed context obligation: ' + name)
    return dict(audit='passed', kind=kind, assertions_proven=sum(k == 'assert' and s == 'proven' for k, s in results.values()),
                covers=sum(k == 'cover' for k, _ in results.values()), raw_counterexamples_retained=len(allowed_cex),
                complete_parent_contexts=sorted(binding['parents']),
                parent_register_bits=sum(sum(s['registers'].values()) for s in binding['parents'].values()),
                complete_semantic_register_bits=sum(e['width'] for e in binding['semantic_entries'] if e['kind'] == 'register'),
                complete_memory_contents_bits=sum(e['width'] * e['depth'] for e in binding['semantic_entries'] if e['kind'] == 'memory'),
                memory_contents_obligation='separate universal memory induction and netlist composition remain required',
                context_ports=sum(len(v) for v in binding['cuts'].values()),
                hierarchy_to_netlist_composition='unproven', formal_state_map_complete=False, gate_restore_authorized=False)


def audit(architecture, synthesis_evidence, queue_proof, kind, proof):
    return validate(reconstruct(architecture, synthesis_evidence, queue_proof), kind, proof)
