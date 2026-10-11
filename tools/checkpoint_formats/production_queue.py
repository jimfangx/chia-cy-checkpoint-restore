"""Audited local state/port obligations for retained production queue modules.

The array read word is an unconstrained common input at a documented cut.
Register induction and equality of every memory input compose with a complete
array relation only after hierarchy/boundary composition is discharged. Every
queue output is also checked; failed output obligations stay explicit. This
artifact is never an ASIC state map and cannot authorize gate deposits.
"""

import json
from pathlib import Path
import re

from .codec import canonical, require
from .formal_state_map import NAME, sha, unescape
from .hierarchical_state import architecture_cell_adapter, bind_concrete_models, hierarchical_inventory
from .production_dut import audit_architecture
from .production_memory import reconstruct as memory_binding
from .replay import IDENT, RANGE, modules


SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_QUEUE_BINDING) miter $env(CHECKPOINT_QUEUE_MITER) script $env(CHECKPOINT_QUEUE_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
analyze -sv $env(CHECKPOINT_QUEUE_MITER)
elaborate -top production_queue_miter
clock clock
reset -none
prove -all
report -summary
set out [open queue-results.tsv w]
puts $out "FORMAT\tproduction-queue-v1"
puts "CHECKPOINT_QUEUE_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Queue input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_QUEUE_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_QUEUE_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def port_shapes(header, body):
    """Restricted ANSI/reference and grouped non-ANSI/Genus interfaces."""
    result = {}
    if re.search(r'\binput\b', header):
        declarations = header.split(',')
        for declaration in declarations:
            match = re.fullmatch(rf'\s*(input|output)\s+{RANGE}({IDENT})\s*', declaration)
            require(match is not None, 'unsupported queue ANSI port')
            direction, high, name = match.groups()
            require(name not in result, 'duplicate queue port')
            result[name] = [direction, int(high) + 1 if high else 1]
    else:
        for direction, high, names in re.findall(
                rf'\b(input|output)\s+{RANGE}({IDENT}(?:\s*,\s*{IDENT})*)\s*;', body):
            for name in re.split(r'\s*,\s*', names):
                require(name not in result, 'duplicate queue port')
                result[name] = [direction, int(high) + 1 if high else 1]
        require(set(n.strip() for n in header.split(',')) == set(result), 'incomplete queue ports')
    require(result.get('clock') == ['input', 1] and result.get('reset') == ['input', 1],
            'unsupported queue target clock/reset')
    return result


def instances(body):
    """Decode emitter/Genus named ports; inventory audit checks all statements."""
    result = {}
    pattern = rf'^[ \t]*(?!(?:if|else|begin|end|always|assign|wire|reg)\b)({IDENT})\s+({NAME})\s*\((.*?)\)\s*;'
    for match in re.finditer(pattern, body, re.S | re.M):
        cell, instance, text = match.groups()
        ports = re.findall(rf'\.({IDENT})\s*\(([^()]*)\)', text)
        residue = re.sub(rf'\.{IDENT}\s*\([^()]*\)', '', text)
        require(not residue.replace(',', '').strip() and len(ports) == len({p for p, _ in ports}),
                'unsupported queue instance ports')
        instance = unescape(instance)
        require(instance not in result, 'duplicate queue instance')
        result[instance] = dict(cell=cell, ports={p: v.strip() for p, v in ports},
                                start=match.start(), end=match.end())
    return result


def reconstruct(architecture, synthesis_evidence):
    architecture, evidence = Path(architecture), Path(synthesis_evidence)
    candidate = audit_architecture(architecture)
    memory = memory_binding(architecture)
    models = (evidence / 'models.v').read_text()
    adapter = json.loads((evidence / 'cell-adapter.json').read_text())
    # Evidence produced by the synthesis auditor binds the raw netlist in its
    # audit record and selected source. Its source run supplies immutable raw bytes.
    audit_record = json.loads((evidence / 'audit.json').read_text())
    synthesis_run = Path(audit_record['run'])
    raw = (synthesis_run / 'synthesis/netlist.v').read_text()
    root = Path(__file__).resolve().parents[2]
    fixture = root / 'tools/checkpoint_formats/tests/fixtures/formal'
    expected_models, expected_adapter = architecture_cell_adapter(
        candidate, json.loads((fixture / 'cell-adapter.json').read_text()),
        (fixture / 'cells.v').read_text(), (architecture / 'memory-models.v').read_text())
    require(models == expected_models and adapter == expected_adapter, 'changed concrete production models/adapter')
    synth_paths = dict(rtl=architecture / 'original.sv', architecture=architecture / 'architecture.sv',
                       memory_stubs=architecture / 'memory-stubs.v', memory_models=architecture / 'memory-models.v',
                       candidate=architecture / 'architecture-candidate.json', library=fixture / 'cells.lib',
                       synthesis_script=root / 'tools/checkpoint_formats/production_synth.tcl')
    synth_hashes = {k: sha(p.read_bytes()) for k, p in synth_paths.items()}
    synth_log = (synthesis_run / 'synthesis/synth.log').read_text()
    observed = re.findall(r'^CHECKPOINT_SYNTH_INPUT\t(\S+)\t([0-9a-f]{64})$', synth_log, re.M)
    require(len(observed) == len(synth_hashes) and dict(observed) == synth_hashes and
            re.findall(r'^CHECKPOINT_SYNTH_OUTPUT\t([0-9a-f]{64})$', synth_log, re.M) == [sha(raw.encode())],
            'changed production synthesis inputs/netlist')
    retiming = re.findall(r'^CHECKPOINT_RETIMING\t(\S+)\t(\S+)$', synth_log, re.M)
    require(retiming and all(value == 'false' for _, value in retiming), 'production retiming unsupported')
    selected, model_binding = bind_concrete_models(raw, models, adapter, candidate['top'])
    require(selected.encode() == (evidence / 'netlist-design.v').read_bytes() and
            model_binding == json.loads((evidence / 'model-binding.json').read_text()),
            'changed production model binding')
    inventory = hierarchical_inventory(raw, models, adapter, candidate['top'])
    require(inventory == json.loads((evidence / 'gate-storage-inventory.json').read_text()),
            'changed production storage inventory')
    original = modules((architecture / 'architecture.sv').read_text())
    mapped = modules(selected)
    queue_names = sorted({e['module'] for e in candidate['entries']
                          if e['kind'] == 'memory' and e['module'].startswith('Queue_')})
    specs, pending = {}, []
    for name in queue_names:
        entries = [e for e in candidate['entries'] if e['module'] == name]
        if name not in mapped:
            pending.extend(dict(state_id=e['state_id'], original_path=e['original_path'],
                                width=e['width'], depth=e['depth'], kind=e['kind'],
                                reason='queue flattened into top; hierarchy relation unproven') for e in entries)
            continue
        mems = [e for e in entries if e['kind'] == 'memory']
        regs = [e for e in entries if e['kind'] == 'register']
        require(len(mems) == 1 and regs and len({e['original_path'].rsplit('.', 1)[0] for e in entries}) == 1,
                'unsupported shared/extra queue state')
        mem = mems[0]
        r_header, r_body = original[name]
        i_header, i_body = mapped[name]
        ports = port_shapes(r_header, r_body)
        require(ports == port_shapes(i_header, i_body), 'changed queue interface')
        r_instances, i_instances = instances(r_body), instances(i_body)
        macro = mem['memory']['instance']
        require(set(r_instances) == {macro} and macro in i_instances and
                r_instances[macro]['cell'] == i_instances[macro]['cell'] == mem['memory']['cell'],
                'missing/extra queue memory or child hierarchy')
        mem_ports = set(r_instances[macro]['ports'])
        require(mem_ports == set(i_instances[macro]['ports']) == {'CP', 'WE', 'WA', 'WD', 'RA0', 'Q0'} and
                r_instances[macro]['ports']['CP'] == i_instances[macro]['ports']['CP'] == 'clock',
                'unsupported queue memory ports/clock')
        state = []
        for instance, cell in i_instances.items():
            if instance == macro:
                continue
            require(cell['cell'] in adapter['cells'], 'unknown queue cell')
            if not adapter['cells'][cell['cell']]['storage']:
                continue
            require(cell['cell'] == 'CKDFF' and cell['ports'].keys() == {'CP', 'D', 'Q'} and
                    cell['ports']['CP'] == 'clock', 'unsupported queue sequential cell')
            q = cell['ports']['Q']
            matches = [(reg, bit) for reg in regs for bit in range(reg['width'])
                       if q == reg['original_path'].rsplit('.', 1)[-1] +
                       (f'[{bit}]' if reg['width'] > 1 else '')]
            require(len(matches) == 1, 'unmatched queue physical register')
            reg, bit = matches[0]
            state.append(dict(state_id=reg['state_id'], original_path=reg['original_path'],
                              original_bit=bit, reference_expression=q, gate_instance=instance,
                              gate_storage='state', xor=0, proof_status='unproven'))
        require(len(state) == sum(e['width'] for e in regs) and
                len({(s['state_id'], s['original_bit']) for s in state}) == len(state),
                'missing/duplicate queue semantic register')
        state.sort(key=lambda s: (s['original_path'], s['original_bit']))
        # Module-name/instance-name heuristics are only candidates. No global
        # StateID-to-physical-instance binding is claimed without composition.
        specs[name] = dict(module=name, ports=ports, state=state, memory=mem,
                           reference_source=f'module {name}({r_header});{r_body}endmodule\n',
                           implementation_source=f'module {name}({i_header});{i_body}endmodule\n',
                           memory_connections=dict(reference=r_instances[macro]['ports'],
                                                   implementation=i_instances[macro]['ports']))
    queue_state_ids = {e['state_id'] for e in candidate['entries'] if e['module'] in specs}
    pending.extend(dict(state_id=e['state_id'], original_path=e['original_path'], width=e['width'],
                        depth=e['depth'], kind=e['kind'], reason='outside retained queue proof; composition unproven')
                   for e in candidate['entries'] if e['state_id'] not in queue_state_ids and
                   e['module'] not in queue_names)
    standard = models[:models.index('module CKMEM_')]
    require('module CKDFF(input CP, input D, output Q);\nreg state;\n'
            'always @(posedge CP) state <= D;\nassign Q = state;\nendmodule' in standard,
            'changed queue CKDFF transition/polarity')
    require(not re.search(r'\b(assume|restrict|initial|force)\b', standard), 'constrained queue models')
    return dict(queue_proof_version=1, artifact_type='production_queue_local_obligations',
                original_rtl_sha256=candidate['original_rtl_sha256'],
                architecture_sha256=candidate['architecture_sha256'],
                semantic_manifest_hash=candidate['semantic_manifest_hash'],
                boundary_manifest_sha256=sha((architecture / 'boundary.json').read_bytes()),
                memory_adapter_binding_sha256=sha(canonical(memory)), model_binding=model_binding,
                synthesis_inputs=synth_hashes, synthesis_log_sha256=sha(synth_log.encode()),
                inventory_sha256=sha(canonical(inventory)), cell_adapter_sha256=sha(canonical(adapter)),
                standard_models=standard, queues=specs, pending_state=pending,
                physical_storage_obligations=[dict(s, proof_status='unproven',
                    reason='complete hierarchy/register/memory composition required before initialization')
                    for s in inventory['storage']],
                physical_register_bits=sum(s['width'] for s in inventory['storage'] if s['kind'] == 'register'),
                semantic_register_bits=sum(e['width'] for e in candidate['entries'] if e['kind'] == 'register'),
                retained_queue_register_bits=sum(len(s['state']) for s in specs.values()),
                formal_state_map_complete=False, gate_restore_authorized=False)


def gate_expr(instance):
    return ('\\' + instance + ' ' if not re.fullmatch(IDENT, instance) else instance) + '.state'


def _cut_source(spec, side):
    source = spec[side + '_source']
    parsed = modules(source)
    header, body = parsed[spec['module']]
    macro = instances(body)[spec['memory']['memory']['instance']]
    width, depth = spec['memory']['width'], spec['memory']['depth']
    address_width = max(1, (depth - 1).bit_length())
    ports = macro['ports']
    cut_ports = {'WE': 1, 'WA': address_width, 'WD': width, 'RA0': address_width}
    # Convert both original ANSI and emitted non-ANSI interfaces to a common
    # interface; keep the original/emitted behavioral body otherwise exact.
    if not re.search(r'\binput\b', header):
        body = re.sub(r'\b(?:input|output)\s+[^;]*;', '', body)
        macro = instances(body)[spec['memory']['memory']['instance']]
    replacement = f'assign {ports["Q0"]} = cut_word;\n'
    replacement += '\n'.join(f'assign cut_{p} = {ports[p]};' for p in cut_ports)
    body = body[:macro['start']] + replacement + body[macro['end']:]
    interface = [f'{d} [{w-1}:0] {p}' for p, (d, w) in spec['ports'].items()]
    interface += [f'input [{width-1}:0] cut_word']
    interface += [f'output [{w-1}:0] cut_{p}' for p, w in cut_ports.items()]
    return f'module {side}_{spec["module"]}(' + ', '.join(interface) + ');\n' + body + '\nendmodule\n'


def miter(binding):
    specs = binding['queues']
    texts = [binding['standard_models']]
    texts += [_cut_source(s, side) for s in specs.values() for side in ('reference', 'implementation')]
    ports = ['input clock']
    for name, spec in specs.items():
        ports += [f'input [{w-1}:0] {name}_{p}' for p, (d, w) in spec['ports'].items()
                  if d == 'input' and p != 'clock']
        ports.append(f'input [{spec["memory"]["width"]-1}:0] {name}_word')
    lines = ['module production_queue_miter(' + ',\n'.join(ports) + ');']
    for name, spec in specs.items():
        width, depth = spec['memory']['width'], spec['memory']['depth']
        aw = max(1, (depth - 1).bit_length())
        for side in ('reference', 'implementation'):
            connections = []
            for p, (d, w) in spec['ports'].items():
                signal = 'clock' if p == 'clock' else name + '_' + p
                if d == 'output':
                    signal = side + '_' + signal
                    lines.append(f'wire [{w-1}:0] {signal};')
                connections.append(f'.{p}({signal})')
            for p, w in {'WE': 1, 'WA': aw, 'WD': width, 'RA0': aw}.items():
                signal = f'{side}_{name}_cut_{p}'
                lines.append(f'wire [{w-1}:0] {signal};')
                connections.append(f'.cut_{p}({signal})')
            connections.append(f'.cut_word({name}_word)')
            lines.append(f'{side}_{name} {side}_{name}(' + ', '.join(connections) + ');')
        expressions = [f'(reference_{name}.{s["reference_expression"]} == '
                       f'(implementation_{name}.{gate_expr(s["gate_instance"])} ^ 1\'b{s["xor"]}))'
                       for s in spec['state']]
        lines.append(f'wire {name}_relation = ' + ' && '.join(expressions) + ';')
        for i, expression in enumerate(expressions):
            lines.append(f'{name}_step_{i}: assert property (@(posedge clock) {name}_relation |=> {expression});')
            for value in (0, 1):
                lines.append(f'{name}_bit_{i}_{value}: cover property (@(posedge clock) {name}_relation && '
                             f'implementation_{name}.{gate_expr(spec["state"][i]["gate_instance"])} == 1\'b{value});')
        for p in ('WE', 'WA', 'WD', 'RA0'):
            lines.append(f'{name}_memory_{p}: assert property (@(posedge clock) {name}_relation |-> '
                         f'reference_{name}_cut_{p} == implementation_{name}_cut_{p});')
        for p, (direction, _) in spec['ports'].items():
            if direction == 'output':
                lines.append(f'{name}_output_{p}: assert property (@(posedge clock) {name}_relation |-> '
                             f'reference_{name}_{p} == implementation_{name}_{p});')
        lines += [f'{name}_edge: cover property (@(posedge clock) {name}_relation ##1 {name}_relation);',
                  f'{name}_reset_seen: cover property (@(posedge clock) {name}_relation && {name}_reset);',
                  f'{name}_write: cover property (@(posedge clock) {name}_relation && reference_{name}_cut_WE);',
                  f'{name}_hold: cover property (@(posedge clock) {name}_relation && !reference_{name}_cut_WE);',
                  f'{name}_word_zero: cover property (@(posedge clock) {name}_relation && {name}_word == {width}\'d0);',
                  f'{name}_word_ones: cover property (@(posedge clock) {name}_relation && {name}_word == {{{width}{{1\'b1}}}});']
    return ('\n'.join(texts + lines + ['endmodule', ''])).encode()


def properties(binding):
    text = miter(binding).decode()
    result = {'<embedded>::production_queue_miter.' + name: kind for name, kind in
              re.findall(r'^(\w+): (assert|cover) property', text, re.M)}
    result.update({name + ':precondition1': 'cover' for name, kind in list(result.items()) if kind == 'assert'})
    return result


def validate_proof(binding, proof):
    proof = Path(proof)
    artifacts = dict(binding=canonical(binding), miter=miter(binding), script=SCRIPT.encode())
    require(all((proof / filename).read_bytes() == artifacts[role] for role, filename in
                (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl'))),
            'changed/unbound queue proof inputs')
    rows = (proof / 'queue-results.tsv').read_text().splitlines()
    require(rows[:1] == ['FORMAT\tproduction-queue-v1'] and rows[-1:] == ['END'], 'incomplete queue evidence')
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate queue proof input')
            inputs[row[1]] = row[2]
        elif len(row) == 4 and row[0] == 'PROPERTY':
            require(row[1] not in results, 'duplicate queue proof property')
            results[row[1]] = tuple(row[2:])
        else:
            require(False, 'unsupported queue proof evidence')
    expected = properties(binding)
    require(inputs == {r: sha(a) for r, a in artifacts.items()}, 'stale queue proof identity')
    require(set(results) == set(expected), 'missing/extra queue obligations')
    failures = {'register': {}, 'memory_port': {}, 'output': {}}
    for name, kind in expected.items():
        actual_kind, status = results[name]
        require(actual_kind == kind, 'wrong queue property type')
        if kind == 'assert' and status == 'cex':
            category = 'output' if '_output_' in name else 'memory_port' if '_memory_' in name else 'register'
            failures[category][name] = 'cex: local obligation unproven; hierarchy/invariant composition required'
        else:
            require(status == ('proven' if kind == 'assert' else 'covered'),
                    'undetermined/vacuous queue obligation: ' + name)
    log = (proof / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and
            'CHECKPOINT_QUEUE_RESET=none' in log and 'Exiting the analysis session with status 0.' in log and
            re.search(r'assumptions\s*:\s*0\b', log), 'failed/constrained/blackboxed queue proof')
    raw = re.findall(r'^CHECKPOINT_QUEUE_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == results,
            'raw/machine queue property mismatch')
    raw_inputs = re.findall(r'^CHECKPOINT_QUEUE_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(raw_inputs) == len(artifacts) and dict(raw_inputs) == inputs, 'raw queue input mismatch')
    for prop, (_, status) in results.items():
        name = re.escape(prop.split('::', 1)[1])
        pattern = (r'A counterexample \(cex\).*property "' + name + '"' if status == 'cex' else
                   r'The (?:cover )?property "' + name + '" was ' + status + r' (?:in|at) ')
        require(re.search(pattern, log), 'missing independent queue engine result: ' + prop)
    return dict(audit='passed', proof_scope='retained queue local register induction and complete memory-port congruence',
                retained_modules=len(binding['queues']), register_bits=sum(len(s['state']) for s in binding['queues'].values()),
                assertions_proven=sum(k == 'assert' and s == 'proven' for k, s in results.values()),
                covers=sum(k == 'cover' for k, _ in results.values()),
                unproven_obligations=failures, remaining_state_entries=len(binding['pending_state']),
                hierarchy_composition='unproven', formal_state_map_complete=False, gate_restore_authorized=False)


def audit(architecture, synthesis_evidence, proof):
    binding = reconstruct(architecture, synthesis_evidence)
    require((Path(proof) / 'binding.json').read_bytes() == canonical(binding), 'changed/incomplete queue binding')
    return validate_proof(binding, proof)
