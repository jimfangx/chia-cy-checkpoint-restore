"""Universal word-transition proofs for the production memory extraction adapter.

This is one component of a production state-map proof, NOT a gate state map.
For the restricted single-write asynchronous-read grammar, each word evolves
independently: write data if enable and write address equal its address, else
hold. Project both actual source fragments onto one arbitrary address and prove
the complete word transition and every read port. The address and old words are
unconstrained inputs, so the theorem covers every address and bit, without
blackboxing an array or selecting a finite set of memory locations. Composition
with surrounding registers and the synthesized netlist remains an obligation.
"""

import json
from pathlib import Path
import re

from .codec import canonical, require
from .production_dut import audit_architecture, sha
from .replay import IDENT, modules


INPUTS = ('binding', 'miter', 'script')
SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_MEMORY_BINDING) miter $env(CHECKPOINT_MEMORY_MITER) script $env(CHECKPOINT_MEMORY_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {
  dict set hashes $role [lindex [exec sha256sum $path] 0]
}
analyze -sv $env(CHECKPOINT_MEMORY_MITER)
elaborate -top production_memory_miter
clock clock
reset -none
prove -all
report -summary
set out [open memory-results.tsv w]
puts $out "FORMAT\tproduction-memory-v1"
puts "CHECKPOINT_MEMORY_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Memory proof input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_MEMORY_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_MEMORY_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def _fragments(original_modules, entry):
    """Locate the exact independently reconstructed original memory statements."""
    _, body = original_modules[entry['module']]
    name = entry['original_path'].rsplit('.', 1)[-1]
    width, depth = entry['width'], entry['depth']
    decl = re.findall(rf'\breg\s+(?:\[{width-1}:0\]\s*)?{name}\s*\[0:{depth-1}\]\s*;', body)
    write = re.findall(rf'\bif\s*\(({re.escape(entry["memory"]["write"]["enable"])})\)\s*begin\s*'
                       rf'{name}\[({IDENT})\]\s*<=\s*({IDENT})\s*;\s*end\b', body)
    reads = re.findall(rf'\bassign\s+({IDENT})\s*=\s*{name}\[({IDENT})\]\s*;', body)
    require(len(decl) == len(write) == 1 and
            write[0][1:] == (entry['memory']['write']['address'], entry['memory']['write']['data']) and
            reads == [(r['data'], r['address']) for r in entry['memory']['reads']],
            'unbound original memory fragment')
    return dict(declaration=decl[0], write=dict(enable=write[0][0], address=write[0][1], data=write[0][2]),
                reads=[dict(data=q, address=a) for q, a in reads])


def _model_fragment(text, cell, width, depth, reads):
    """Strictly parse the concrete model, without trusting its adapter metadata."""
    parsed = modules(text)
    require(set(parsed) == {cell}, 'extra/missing concrete memory definitions')
    header, body = parsed[cell]
    address_width = max(1, (depth - 1).bit_length())
    ports = ['input CP', 'input WE', f'input [{address_width-1}:0] WA', f'input [{width-1}:0] WD']
    for i in range(reads):
        ports += [f'input [{address_width-1}:0] RA{i}', f'output [{width-1}:0] Q{i}']
    require(re.sub(r'\s+', '', header) == re.sub(r'\s+', '', ', '.join(ports)),
            'unsupported concrete memory interface')
    expected = (f'reg [{width-1}:0] contents [0:{depth-1}];\n' +
                '\n'.join(f'assign Q{i} = contents[RA{i}];' for i in range(reads)) +
                '\nalways @(posedge CP) begin\n  if (WE) contents[WA] <= WD;\nend\n')
    require(re.sub(r'\s+', '', body) == re.sub(r'\s+', '', expected),
            'unsupported concrete memory transition/read/hidden state')
    return dict(write=dict(enable='WE', address='WA', data='WD'),
                reads=[dict(data=f'Q{i}', address=f'RA{i}') for i in range(reads)])


def reconstruct(architecture):
    """Bind ALL selected StateIDs to exact fragments and universal shape proofs."""
    architecture = Path(architecture)
    candidate = audit_architecture(architecture)
    normalized = (architecture / 'normalized.sv').read_text()
    original_modules = modules(normalized)
    model_text = (architecture / 'memory-models.v').read_text()
    model_modules = modules(model_text)
    shapes, instances = {}, []
    for entry in candidate['entries']:
        if entry['kind'] != 'memory':
            continue
        cell, width, depth = entry['memory']['cell'], entry['width'], entry['depth']
        reads = len(entry['memory']['reads'])
        model = 'module ' + cell + '(' + model_modules[cell][0] + ');' + model_modules[cell][1] + 'endmodule\n'
        fragment = _fragments(original_modules, entry)
        model_fragment = _model_fragment(model, cell, width, depth, reads)
        # Canonical renaming is a cut at the existing memory ports. The full
        # original enable expression and surrounding logic remain bound above;
        # an unconstrained WE proves every possible value of that expression.
        reference_fragment = dict(write=dict(enable='WE', address='WA', data='WD'),
                                  reads=[dict(data=f'Q{i}', address=f'RA{i}') for i in range(reads)])
        shape = dict(cell=cell, width=width, depth=depth, read_ports=reads,
                     reference_fragment=reference_fragment, model_fragment=model_fragment,
                     concrete_model_sha256=sha(model.encode()))
        require(cell not in shapes or shapes[cell] == shape, 'conflicting projected memory shapes')
        shapes[cell] = shape
        instances.append(dict(state_id=entry['state_id'], original_path=entry['original_path'],
                              architecture_path=entry['architecture_path'], module=entry['module'],
                              width=width, depth=depth, cell=cell, fragment=fragment,
                              module_body_sha256=sha(normalized_module(original_modules, entry['module']).encode())))
    require(set(shapes) == set(model_modules) and instances, 'incomplete memory shape coverage')
    return dict(memory_proof_version=1, artifact_type='production_memory_adapter_obligations',
                original_rtl_sha256=candidate['original_rtl_sha256'],
                normalized_rtl_sha256=candidate['normalized_rtl_sha256'],
                architecture_sha256=candidate['architecture_sha256'],
                models_sha256=candidate['models_sha256'], semantic_manifest_hash=candidate['semantic_manifest_hash'],
                architecture_candidate_sha256=sha(canonical(candidate)),
                memory_bits=sum(e['width'] * e['depth'] for e in instances),
                memory_words=sum(e['depth'] for e in instances), memory_instances=len(instances),
                shapes={c: shapes[c] for c in sorted(shapes)}, instances=instances,
                gate_restore_authorized=False, formal_state_map_complete=False)


def normalized_module(original_modules, name):
    header, body = original_modules[name]
    return header + '\n' + body


def miter(shape):
    width, depth, reads = shape['width'], shape['depth'], shape['read_ports']
    address_width = max(1, (depth - 1).bit_length())
    ports = ['input clock, WE', f'input [{address_width-1}:0] WA, watched',
             f'input [{width-1}:0] WD, old_reference, old_implementation']
    ports += [f'input [{address_width-1}:0] RA{i}' for i in range(reads)]
    ports += [f'input [{width-1}:0] other_reference_Q{i}, other_implementation_Q{i}' for i in range(reads)]
    lines = ['// Universal one-step word projection; no target state is omitted or assumed.',
             'module production_memory_miter(' + ', '.join(ports) + ');',
             f'wire valid_word = watched < {address_width+1}\'d{depth};']
    for prefix, key in (('reference', 'reference_fragment'), ('implementation', 'model_fragment')):
        write = shape[key]['write']
        lines.append(f'wire [{width-1}:0] next_{prefix} = ({write["enable"]} && '
                     f'({write["address"]} == watched)) ? {write["data"]} : old_{prefix};')
        for n, read in enumerate(shape[key]['reads']):
            # Only the selected word supplies the read; outside that word the
            # actual array is unrelated. Do not assert equality there.
            lines.append(f'wire [{width-1}:0] {prefix}_Q{n} = '
                         f'(valid_word && {read["address"]} == watched) ? old_{prefix} : other_{prefix}_Q{n};')
    lines += ['wire relation = old_reference == old_implementation;',
              'word_step: assert property (@(posedge clock) relation |-> next_reference == next_implementation);']
    for i in range(reads):
        lines.append(f'read_{i}: assert property (@(posedge clock) valid_word && relation && RA{i} == watched |-> '
                     f'reference_Q{i} == implementation_Q{i});')
        lines.append(f'read_{i}_last: cover property (@(posedge clock) relation && RA{i} == watched && '
                     f'watched == {address_width}\'d{depth-1});')
    for label, condition in (('write', 'WE && WA == watched'), ('hold_disabled', '!WE && WA == watched'),
                             ('hold_other', 'WE && WA != watched'), ('first', "watched == 0"),
                             ('last', f"watched == {address_width}'d{depth-1}")):
        lines.append(f'{label}: cover property (@(posedge clock) valid_word && relation && ({condition}));')
    for i in range(width):
        for value in (0, 1):
            lines.append(f'bit_{i}_{value}: cover property (@(posedge clock) valid_word && relation && '
                         f'old_implementation[{i}] == 1\'b{value});')
    return '\n'.join(lines + ['endmodule', '']).encode()


def expected_properties(shape):
    names = {'word_step': ('assert', 'proven'), 'word_step:precondition1': ('cover', 'covered')}
    for i in range(shape['read_ports']):
        names.update({f'read_{i}': ('assert', 'proven'), f'read_{i}:precondition1': ('cover', 'covered'),
                      f'read_{i}_last': ('cover', 'covered')})
    names.update({n: ('cover', 'covered') for n in ('write', 'hold_disabled', 'hold_other', 'first', 'last')})
    names.update({f'bit_{i}_{v}': ('cover', 'covered') for i in range(shape['width']) for v in (0, 1)})
    return {'<embedded>::production_memory_miter.' + n: s for n, s in names.items()}


def validate_proof(shape, binding, directory):
    """Rebuild obligations and independently cross-check real raw engine results."""
    directory = Path(directory)
    artifacts = {r: (directory / n).read_bytes() for r, n in
                 (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl'))}
    require(artifacts == dict(binding=canonical(binding), miter=miter(shape), script=SCRIPT.encode()),
            'changed/unbound production memory proof inputs')
    lines = (directory / 'memory-results.tsv').read_text().splitlines()
    require(lines[:1] == ['FORMAT\tproduction-memory-v1'] and lines[-1:] == ['END'], 'incomplete memory proof')
    inputs, results = {}, {}
    for line in lines[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate memory proof input')
            inputs[row[1]] = row[2]
        elif len(row) == 4 and row[0] == 'PROPERTY':
            require(row[1] not in results, 'duplicate memory proof property')
            results[row[1]] = tuple(row[2:])
        else:
            require(False, 'unsupported memory proof row')
    expected = expected_properties(shape)
    require(inputs == {r: sha(artifacts[r]) for r in INPUTS}, 'stale memory proof identity')
    require(results == expected, 'unproven/vacuous/incomplete production memory obligations')
    log = (directory / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and
            'CHECKPOINT_MEMORY_RESET=none' in log and
            'Exiting the analysis session with status 0.' in log and
            re.search(r'assumptions\s*:\s*0\b', log), 'failed/constrained/blackboxed memory proof')
    raw = re.findall(r'^CHECKPOINT_MEMORY_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == expected,
            'raw/machine memory property mismatch')
    raw_inputs = re.findall(r'^CHECKPOINT_MEMORY_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(raw_inputs) == len(INPUTS) and dict(raw_inputs) == inputs, 'raw memory proof identity mismatch')
    for prop, (_, status) in expected.items():
        name = prop.split('::', 1)[1]
        require(re.search(r'The (?:cover )?property "' + re.escape(name) + r'" was ' + status + r' (?:in|at) ', log),
                'missing independent memory engine result')
    return dict(assertions=sum(k == 'assert' for k, _ in expected.values()),
                covers=sum(k == 'cover' for k, _ in expected.values()), proof_status='proven')


def audit(architecture, proof_run):
    proof_run = Path(proof_run)
    binding = reconstruct(architecture)
    require(json.loads((proof_run / 'binding.json').read_text()) == binding, 'changed/incomplete memory binding')
    results = {cell: validate_proof(shape, binding, proof_run / cell) for cell, shape in binding['shapes'].items()}
    return dict(audit='passed', proof_scope='universal original-to-architecture memory word transition/read adapter',
                memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'],
                memory_words=binding['memory_words'], shape_proofs=len(results), shapes=results,
                binding_sha256=sha(canonical(binding)), formal_state_map_complete=False, gate_restore_authorized=False)
