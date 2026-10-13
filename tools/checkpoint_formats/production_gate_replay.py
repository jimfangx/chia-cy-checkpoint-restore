"""Prepare full production gate replay after a current independent CAD audit.

Arrays remain spans, with one compact value per word. No fixture loader, name
guess, saved PASS summary or partial checkpoint can authorize these deposits.
The immutable composed map keeps its separate, loader-ineligible format.
"""

import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from .codec import canonical, decode, require
from .finite_replay import ports_for
from .formal_state_map import sha
from .gate_replay import validate_design_boundary
from .replay import builds
from .semantic import decode_semantic, manifest_hash


def storage_path(components, storage):
    require(components and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?', c)
                              for c in components), 'unsupported production gate hierarchy')
    require(storage in ('state', 'contents'), 'unsupported production gate storage')
    return '.'.join(['production_gate_tb', 'dut', *components, storage])


def validate_checkpoint(mapping, manifest, checkpoint):
    """Check every conditional predicate before even creating a staging directory."""
    records = {r['state_id']: r for r in checkpoint['records']}
    require(mapping['formal_state_map_complete'] is True and mapping['retiming'] is False and
            mapping['semantic_manifest_hash'] == manifest_hash(manifest), 'unproven production checkpoint map')
    predicates = 0
    for entry in mapping['entries']:
        record = records[entry['state_id']]
        require((record['width'], record['depth']) == (entry['width'], entry['depth']),
                'reshaped production checkpoint state')
        if entry['kind'] == 'register':
            value = int(record['values'][0], 16)
            for bit in entry['bits']:
                if bit['classification'] == 'preserved_predicate':
                    require((value >> bit['bit']) & 1 == bit['value'],
                            'checkpoint violates proven production predicate: ' + entry['original_path'] +
                            f" bit {bit['bit']}")
                    predicates += 1
                else:
                    require(bit['classification'] in ('mapped', 'irrelevant'), 'unproven production bit')
        else:
            require(entry['kind'] == 'memory' and entry['mapping']['classification'] == 'mapped_full_array',
                    'unsupported production checkpoint memory')
    require(predicates == mapping['predicate_bits'], 'incomplete production checkpoint predicates')
    return records


def spans(mapping, records):
    """Only O(storage objects) descriptors; array values reference the decoded image."""
    for entry in mapping['entries']:
        values = records[entry['state_id']]['values']
        if entry['kind'] == 'memory':
            m = entry['mapping']
            require(m['address_transform'] == m['bit_transform'] == 'identity' and
                    m['address_first'] == m['bit_first'] == 0 and
                    m['address_count'] == entry['depth'] and m['bit_count'] == entry['width'],
                    'unsupported production array transformation')
            yield 'M', storage_path(m['instance_components'], m['storage']), entry['width'], entry['depth'], values
        else:
            value = int(values[0], 16)
            for bit in entry['bits']:
                if bit['classification'] != 'mapped':
                    continue
                gate = bit['gate']
                require(gate['bit'] == gate['xor'] == 0, 'unsupported production register transformation')
                yield 'R', storage_path(gate['instance_components'], gate['storage']), 1, 1, [str((value >> bit['bit']) & 1)]


def write_spans(mapping, records, path):
    words, bits, count, seen = 0, 0, 0, set()
    with Path(path).open('w') as stream:
        stream.write('PRODUCTION_GATE_RESTORE_V1\n')
        for kind, name, width, depth, values in spans(mapping, records):
            require(name not in seen, 'duplicate production destination span')
            seen.add(name)
            stream.write(f'{kind} {name} {width} {depth}\n')
            for value in values:
                stream.write(value + '\n')
            words += depth
            bits += width * depth
            count += 1
        require(words == mapping['gate_storage_words'] and bits == mapping['gate_storage_bits'],
                'incomplete production deposits')
        stream.write(f'END {words} {bits}\n')
    return count


def bench(top, ports, start, end, words, bits):
    source = ['`timescale 1ns/1ps', 'module production_gate_tb;', 'reg clock=0;',
              'import "DPI-C" context function int production_gate_restore(input string path, input int unsigned words, input longint unsigned bits);',
              'import "DPI-C" context function int production_gate_verify(input string path, input int unsigned words, input longint unsigned bits);',
              'import "DPI-C" context function int production_gate_flip(input string path, input int unsigned bit_index);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              f'longint unsigned next_cycle={start}, received_cycle, target_edges=0;',
              'longint unsigned fault_cycle;', 'integer fault_bit;',
              'string restore_path, trace_path, audit_path, packet, kind, extra, fault_path, reject_path;',
              'integer trace_fd, audit_fd, parsed, got;', 'bit has_fault=0, has_reject=0;',
              'always @(posedge clock) target_edges=target_edges+1;']
    for i, p in enumerate(ports):
        source += [f"{'reg' if p['direction'] == 'input' else 'wire'} [{p['width']-1}:0] {p['name']}" +
                   ('=0;' if p['direction'] == 'input' else ';'), f"reg [{p['width']-1}:0] f{i};"]
    source += [top + ' dut(.clock(clock), ' + ', '.join(f".{p['name']}({p['name']})" for p in ports) + ');',
               'initial begin',
               '  if(!$value$plusargs("restore=%s",restore_path) || !$value$plusargs("trace=%s",trace_path) ||',
               '     !$value$plusargs("audit=%s",audit_path)) semantic_fail("PRODUCTION_GATE_ARGUMENTS");',
               '  has_fault=$value$plusargs("fault_path=%s",fault_path);',
               '  has_reject=$value$plusargs("reject=%s",reject_path);',
               '  if(has_fault && has_reject) semantic_fail("PRODUCTION_GATE_CONFLICTING_TESTS");',
               '  if(has_fault && (!$value$plusargs("fault_cycle=%d",fault_cycle) ||',
               f'     !$value$plusargs("fault_bit=%d",fault_bit) || fault_cycle < {start} || fault_cycle >= {end} || fault_bit < 0))',
               '    semantic_fail("PRODUCTION_GATE_FAULT_ARGUMENTS");',
               '  trace_fd=$fopen(trace_path,"r"); audit_fd=$fopen(audit_path,"w");',
               '  if(!trace_fd || !audit_fd) semantic_fail("PRODUCTION_GATE_FILES");',
               '  #1;', f'  if(production_gate_restore(restore_path,{words},{bits})) semantic_fail("PRODUCTION_GATE_RESTORE_FAILED");',
               '  #1;', f'  if(production_gate_verify(restore_path,{words},{bits})) semantic_fail("PRODUCTION_GATE_READBACK_FAILED");',
               '  if(clock || target_edges) semantic_fail("PRODUCTION_GATE_LOAD_ADVANCED_EDGE");',
               f'  $display("PRODUCTION_GATE_ZERO_EDGE cycle={start} words={words} bits={bits} edges=0");',
               '  if(has_reject) begin',
               f'    if(!production_gate_restore(reject_path,{words},{bits})) semantic_fail("PRODUCTION_GATE_INVALID_RESTORE_ACCEPTED");',
               '    #1;', f'    if(production_gate_verify(restore_path,{words},{bits})) semantic_fail("PRODUCTION_GATE_REJECTION_CHANGED_STATE");',
               '    if(clock || target_edges) semantic_fail("PRODUCTION_GATE_REJECTION_ADVANCED_EDGE");',
               f'    $display("PRODUCTION_GATE_ATOMIC_REJECTION words={words} bits={bits} edges=0");',
               '    $finish;', '  end',
               f'  while(next_cycle < {end}) begin',
               '    got=$fgets(packet,trace_fd); if(!got) semantic_fail("PRODUCTION_GATE_SHORT_TRACE");',
               '    parsed=$sscanf(packet,"%s %d ' + ' '.join('%h' for _ in ports) + ' %s",kind,received_cycle,' +
               ','.join(f'f{i}' for i in range(len(ports))) + ',extra);',
               f'    if(parsed != {len(ports)+2} || kind != "DATA" || received_cycle !== next_cycle)',
               '      semantic_fail("PRODUCTION_GATE_PACKET_OR_CYCLE");',
               '    if($isunknown({' + ','.join(f'f{i}' for i in range(len(ports))) + '})) semantic_fail("PRODUCTION_GATE_UNKNOWN_TRACE");']
    source += [f"    {p['name']}=f{i};" for i, p in enumerate(ports) if p['direction'] == 'input']
    source += ['    if(has_fault && next_cycle==fault_cycle) begin',
               '      if(production_gate_flip(fault_path,fault_bit)) semantic_fail("PRODUCTION_GATE_FAULT_FAILED");',
               '      $display("PRODUCTION_GATE_CORRUPTION cycle=%0d path=%s bit=%0d edges=%0d",next_cycle,fault_path,fault_bit,target_edges);',
               '    end', '    #1;']
    for i, p in enumerate(ports):
        if p['direction'] == 'output':
            source += [f"    if({p['name']} !== f{i}) semantic_fail($sformatf(" +
                       f'"FIRST_MISMATCH cycle=%0d signal={p["name"]} expected=%h actual=%h target_edges=%0d",' +
                       f'next_cycle,f{i},{p["name"]},target_edges));']
    # Record observed outputs, rather than copying the oracle packet.
    source += ['    $fwrite(audit_fd,"DATA %0d ' + ' '.join('%h' for _ in ports) + '\\n",next_cycle,' +
               ','.join(p['name'] for p in ports) + '); $fflush(audit_fd);',
               '    clock=1; #1; clock=0; #1; next_cycle=next_cycle+1;', '  end',
               '  if($fgets(packet,trace_fd)) semantic_fail("PRODUCTION_GATE_EXTRA_TRACE");',
               f'  if(target_edges != {end-start}) semantic_fail("PRODUCTION_GATE_EDGE_COUNT");',
               '  $fclose(trace_fd); $fclose(audit_fd);',
               f'  $display("PRODUCTION_GATE_END first={start} end={end} edges=%0d outputs_per_cycle={sum(p["direction"] == "output" for p in ports)}",target_edges);',
               '  $finish;', 'end', 'endmodule']
    return '\n'.join(source) + '\n'


def prepare(mapping_path, checkpoint_path, trace_path, configuration, out):
    # Import the independent auditor, never trust its retained summary alone.
    from .tests.audit_production_state_map import audit_components, audit_map
    mapping_path, checkpoint_path, trace_path, out = [Path(p).resolve() for p in
        (mapping_path, checkpoint_path, trace_path, out)]
    require(not out.exists(), 'production replay destination already exists')
    mapping = json.loads(mapping_path.read_text())
    require(mapping.get('artifact_type') == 'complete_production_semantic_gate_state_map', 'unsupported production map format')
    context = audit_components(mapping['proof_components']['original'], mapping['proof_components']['memory'])
    audit = audit_map(context, mapping_path)
    manifest = context['manifest']
    architecture = Path(context['original']['architecture'])
    boundary = json.loads((architecture / 'boundary.json').read_text())
    require(sha(canonical(boundary)) == mapping['boundary_manifest_sha256'], 'unbound production boundary')
    require(boundary['dut_root'] == manifest['dut_root'] and boundary['dut_module'] == mapping['top'] and
            manifest['clock_domain'] == manifest['dut_root'] + '.clock', 'unsupported production replay clock/root')
    build, trace_build = builds(manifest, boundary, configuration)
    checkpoint_bytes, trace_bytes = checkpoint_path.read_bytes(), trace_path.read_bytes()
    checkpoint = decode_semantic(checkpoint_bytes, build, manifest)
    records = validate_checkpoint(mapping, manifest, checkpoint)
    trace = decode(trace_bytes, 'trace', trace_build)
    ports = ports_for(boundary)
    start, end = checkpoint['target_cycle'], checkpoint['target_cycle'] + len(trace['records'])
    require(trace['target_cycle'] == start and start < end < 2**64, 'production checkpoint/trace cycle mismatch')
    for record in trace['records']:
        for direction in ('input', 'output'):
            require({n: v['width'] for n, v in record[direction+'s'].items()} ==
                    {p['name']: p['width'] for p in ports if p['direction'] == direction}, 'incomplete production trace boundary')
    evidence = Path(context['memory']['synthesis_evidence'])
    sources = {name: evidence / filename for name, filename in (('netlist', 'netlist-design.v'), ('models', 'models.v'))}
    netlist = sources['netlist'].read_text()
    top = re.findall(r'\bmodule\s+' + re.escape(mapping['top']) + r'\s*\(.*?\bendmodule\b', netlist, re.S)
    require(len(top) == 1, 'missing/duplicate production gate top')
    expected_ports = boundary['ports'] + [dict(name=a['name'], direction='output', width=1) for a in boundary.get('clock_aliases', [])]
    validate_design_boundary(top[0], mapping['top'], expected_ports)
    for path in sources.values():
        require(mapping['dependency_artifacts'][str(path)] == sha(path.read_bytes()), 'unbound production simulation design')
    out.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=out.name+'-pending-', dir=out.parent))
    count = write_spans(mapping, records, staged / 'restore.spans')
    with (staged / 'trace.txt').open('w') as stream:
        for record in trace['records']:
            stream.write('DATA ' + str(record['cycle']) + ' ' + ' '.join(record[p['direction']+'s'][p['name']]['value'] for p in ports) + '\n')
    (staged / 'tb.sv').write_text(bench(mapping['top'], ports, start, end, mapping['gate_storage_words'], mapping['gate_storage_bits']))
    root = Path(__file__).resolve().parents[2]
    dependencies = dict(mapping['dependency_artifacts'])
    dependencies.update({str(mapping_path): sha(mapping_path.read_bytes()), str(checkpoint_path): sha(checkpoint_bytes),
                         str(trace_path): sha(trace_bytes)})
    for filename in ('production_gate_replay.py', 'production_gate_restore.cc', 'tests/audit_production_state_map.py'):
        p = root / 'tools/checkpoint_formats' / filename
        dependencies[str(p)] = sha(p.read_bytes())
    request = dict(production_gate_request_version=1, map=str(mapping_path), checkpoint=str(checkpoint_path), trace=str(trace_path),
                   configuration=configuration, first_cycle=start, end_cycle=end, samples=end-start, ports=ports,
                   output_comparisons=(end-start)*sum(p['direction'] == 'output' for p in ports),
                   gate_storage_words=mapping['gate_storage_words'], gate_storage_bits=mapping['gate_storage_bits'],
                   storage_spans=count, predicate_bits=mapping['predicate_bits'], independent_map_audit=audit,
                   sources={k: str(v) for k, v in sources.items()}, dependency_artifacts=dependencies,
                   generated_artifacts={n: sha((staged/n).read_bytes()) for n in ('restore.spans', 'trace.txt', 'tb.sv')},
                   gate_restore_authorized=True, gate_replay_verified=False,
                   scope='complete production functional gate replay; no power or FPGA result')
    (staged / 'request.json').write_bytes(canonical(request))
    os.rename(staged, out)
    return request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('map', 'checkpoint', 'trace', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--configuration', required=True)
    args = parser.parse_args()
    result = prepare(args.map, args.checkpoint, args.trace, args.configuration, args.out)
    print(json.dumps(dict(out=str(args.out.resolve()), first_cycle=result['first_cycle'], samples=result['samples'],
                          gate_storage_words=result['gate_storage_words'], storage_spans=result['storage_spans'],
                          gate_restore_authorized=True, gate_replay_verified=False)))


if __name__ == '__main__':
    main()
