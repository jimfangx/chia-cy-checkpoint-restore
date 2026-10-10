"""Independent pre-FAME state mapping and paired-cut observation.

No Level-1 image is decoded or converted here. Level-2 values are read from
the actual DUT at the parked cut and again before clocks in a fresh restored
metasim. This establishes state/cut correspondence, not live shadow execution.
The bridge-extracted boundary's clock aliases require schema 2; the existing
schema-1 live adapter continues to reject it explicitly.
"""
import hashlib
import json
from pathlib import Path
import re

from .codec import bit_value, canonical, keys, natural, require, unique_object
from .replay import IDENT, RANGE, boundary_ports, builds, inventory_rtl, modules, state_words
from .semantic import decode_semantic, encode_semantic, manifest_hash, validate_manifest
from .simulator import check_generated_rtl


def bridge_ports(boundary):
    keys(boundary, {'boundary_version', 'dut_module', 'dut_root', 'clock',
                    'sample_phase', 'ports', 'clock_aliases'})
    require(type(boundary['boundary_version']) is int and boundary['boundary_version'] == 2,
            'bridge boundary requires schema 2')
    aliases = boundary['clock_aliases']
    require(type(aliases) is list and aliases, 'missing bridge clock aliases')
    names = []
    for alias in aliases:
        keys(alias, {'name', 'source', 'direction'})
        require(type(alias['name']) is str and re.fullmatch(IDENT, alias['name'])
                and alias['source'] == 'clock' and alias['direction'] == 'output',
                'unsupported bridge clock alias')
        names.append(alias['name'])
    require(len(names) == len(set(names)) and not set(names).intersection(p['name'] for p in boundary['ports']),
            'duplicate/data bridge clock alias')
    ordinary = {k: v for k, v in boundary.items() if k != 'clock_aliases'}
    ordinary['boundary_version'] = 1
    return boundary_ports(ordinary)


def audit_bridge_mapping(manifest, boundary, reference, clean, generated,
                         generated_reference, transformed, bufgce, target_root):
    """Require complete independent inventories; report erased boundary fields.

    State paths must match exactly beneath the explicitly selected emitted
    instance. Missing boundary fields are obligations for a future adapter;
    this function does not guess constants, discard inputs, or authorize replay.
    """
    validate_manifest(manifest)
    ports = bridge_ports(boundary)
    require(boundary['dut_root'] == manifest['dut_root']
            and manifest['clock_domain'] == manifest['dut_root'] + '.clock', 'semantic root/clock mismatch')
    require(hashlib.sha256(reference.encode()).hexdigest() == manifest['reference_sha256'],
            'semantic reference hash mismatch')
    check_generated_rtl(generated, generated_reference, transformed + bufgce, bufgce)
    instances = [i for i in generated['instances'] if i['hierarchy'] == target_root]
    require(len(instances) == 1 and instances[0]['module'] == boundary['dut_module'],
            'missing/ambiguous concrete target instance')
    require(sum(i['module'] == boundary['dut_module'] for i in generated['instances']) == 1,
            'threaded/multiple target instances unsupported')
    expected = {e['hierarchy'][len(manifest['dut_root']) + 1:]:
                (e['width'], e['depth'], e['kind']) for e in manifest['state']}
    selected = {e['hierarchy'][len(target_root) + 1:]: (e['width'], e['depth'], e['kind'])
                for e in generated['state'] if e['hierarchy'].startswith(target_root + '.')}
    require(selected == expected, 'incomplete/extra/reshaped transformed target state')
    clean_mods, transformed_mods = modules(clean), modules(transformed)
    for mods in (clean_mods, transformed_mods):
        require(inventory_rtl(mods, boundary['dut_module']) == expected,
                'incomplete/extra/reshaped emitted semantic state')
    def rtl_ports(mods):
        return {n: dict(name=n, direction=d, width=int(w) + 1 if w else 1)
                for d, w, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})',
                                         mods[boundary['dut_module']][0])}
    clean_ports, actual = rtl_ports(clean_mods), rtl_ports(transformed_mods)
    all_ports = {p['name']: p for p in boundary['ports']}
    all_ports.update({a['name']: dict(name=a['name'], direction='output', width=1)
                      for a in boundary['clock_aliases']})
    require(clean_ports == all_ports, 'incomplete clean boundary/clock alias inventory')
    require(all(name in all_ports and all_ports[name] == p for name, p in actual.items()),
            'extra/reshaped transformed target boundary')
    body = clean_mods[boundary['dut_module']][1]
    for alias in boundary['clock_aliases']:
        require(re.findall(r'\bassign\s+' + re.escape(alias['name']) + r'\s*=\s*([^;]+);', body)
                == ['clock'], 'unverified emitted output clock alias')
    missing = [p for p in ports if p['name'] not in actual]
    entries = [dict(state_id=e['state_id'], path=target_root + e['hierarchy'][len(manifest['dut_root']):],
                    width=e['width'], depth=e['depth'], kind=e['kind']) for e in manifest['state']]
    return dict(mapping_version=1, semantic_manifest_sha256=manifest_hash(manifest),
                generated_manifest_sha256=hashlib.sha256(canonical(generated)).hexdigest(),
                target_root=target_root, entries=entries,
                semantic_entries=len(entries), semantic_words=sum(e['depth'] for e in entries),
                ports=ports, missing_transformed_ports=missing,
                boundary_input_bindings=[dict(port=p, target_path=target_root + '.' + p['name'])
                                         for p in ports if p['direction'] == 'input' and p['name'] in actual],
                source_hashes={k: hashlib.sha256(v.encode()).hexdigest() for k, v in
                               dict(reference=reference, clean=clean, transformed=transformed,
                                    generated_reference=generated_reference, bufgce=bufgce).items()},
                emitted_boundary_ports_complete=not missing, live_boundary_adapter_complete=False)


def audit_erased_boundary_outputs(boundary, reference, clean, transformed, mapping):
    """Resolve erased constants/input aliases from both semantic definitions.

    This supplies comparator expressions for erased outputs only. An erased
    input is still an obligation: no value is invented from its name or from
    the clean simulator, and this audit alone never enables live execution.
    """
    ports = bridge_ports(boundary)
    for name, source in dict(reference=reference, clean=clean, transformed=transformed).items():
        require(hashlib.sha256(source.encode()).hexdigest() == mapping['source_hashes'][name],
                'changed erased-boundary source: ' + name)
    clean_header, body = modules(clean)[boundary['dut_module']]
    actual_header = modules(transformed)[boundary['dut_module']][0]
    def declarations(header):
        return {n: dict(name=n, direction=d, width=int(w) + 1 if w else 1)
                for d, w, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', header)}
    actual, original = declarations(actual_header), declarations(clean_header)
    missing = [p for p in ports if p['name'] not in actual]
    require(missing == mapping['missing_transformed_ports'], 'changed erased-boundary membership')
    # Use only the selected LowForm module, never an identically named port in
    # another module. Unsupported FIRRTL/SV drivers reject instead of guessing.
    definitions = re.findall(r'^  module ' + re.escape(boundary['dut_module']) +
                             r' :\n(.*?)(?=^  (?:module|extmodule) |\Z)', reference, re.M | re.S)
    require(len(definitions) == 1, 'missing/ambiguous erased-boundary reference module')
    firrtl = re.sub(r'\s+@\[[^\n]*', '', definitions[0])
    outputs, unresolved = [], []
    for p in missing:
        if p['direction'] == 'input':
            unresolved.append(p)
            continue
        assignments = re.findall(r'\bassign\s+' + re.escape(p['name']) + r'\s*=\s*([^;]+);', body)
        drivers = re.findall(r'^    ' + re.escape(p['name']) + r' <= ([^\n]+)', firrtl, re.M)
        require(len(assignments) == len(drivers) == 1, 'unsupported erased output driver: ' + p['name'])
        expression, driver = assignments[0].strip(), drivers[0].strip()
        constant = re.fullmatch(r"(\d+)'h([0-9a-f]+)", expression)
        if constant:
            width, value = int(constant[1]), int(constant[2], 16)
            reference_constant = re.fullmatch(r'UInt<(\d+)>\("h([0-9a-f]+)"\)', driver)
            require(width == p['width'] and value < 2**width and reference_constant is not None
                    and (int(reference_constant[1]), int(reference_constant[2], 16)) == (width, value),
                    'unverified erased output constant: ' + p['name'])
            outputs.append(dict(port=p, kind='constant', expression=expression, value=value))
        else:
            require(expression == driver and expression in actual
                    and original[expression] == actual[expression]
                    and actual[expression]['direction'] == 'input' and actual[expression]['width'] == p['width'],
                    'unsupported erased output alias: ' + p['name'])
            outputs.append(dict(port=p, kind='target_input_alias', expression=expression,
                                target_path=mapping['target_root'] + '.' + expression))
    return dict(audit_version=1, source_hashes={n: mapping['source_hashes'][n]
                for n in ('reference', 'clean', 'transformed')}, erased_outputs=outputs,
                unresolved_inputs=unresolved, live_boundary_adapter_complete=False,
                erased_output_semantics_verified=True)


def _records(manifest, prefix):
    source = []
    for e in manifest['state']:
        path = prefix + e['hierarchy'][len(manifest['dut_root']) + 1:]
        header = canonical(dict(state_id=e['state_id'], width=e['width'], depth=e['depth'])).decode()[:-1]
        source.append('    $fwrite(fd, ' + json.dumps(header + ',"values":[') + ');')
        if e['kind'] == 'memory':
            source += [f"    for(address=0; address<{e['depth']}; address=address+1) begin",
                       '      if(address) $fwrite(fd, ",");',
                       f'      $fwrite(fd, "\\\"%h\\\"", {path}[address]);', '    end']
        else:
            source.append(f'    $fwrite(fd, "\\\"%h\\\"", {path});')
        source.append('    $fdisplay(fd, "]}");')
    return source


def prepare_paired_probe(manifest, mapping, out):
    """Read-only host VCS observer, separate from either checkpoint owner.

    The production harness parks its worker before this event and yields a
    delta for observers before collecting Level 1. Restore observation waits
    for the existing zero-edge bootstrap and checks both clocks/edge counters.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(canonical(mapping)).hexdigest()
    header = dict(snapshot_version=1, snapshot_type='independent_semantic_cut',
                  semantic_manifest_sha256=manifest_hash(manifest), mapping_sha256=digest)
    prefix = canonical(header).decode()[:-1] + ',"target_cycle":%0d,"observed_target_edges":%0d}'
    root = 'emul.' + mapping['target_root']
    cycle_path = 'emul.FPGATop.FASEDMemoryTimingModel_0.model.tCycle'
    bindings = mapping['boundary_input_bindings']
    input_observation = canonical(dict(boundary_input_version=1, mapping_sha256=digest)).decode()[:-1]
    input_observation += ',"target_cycle":%0d,"observed_target_edges":%0d,"ports":['
    input_observation += ','.join(canonical(dict(name=b['port']['name'], width=b['port']['width'])).decode()[:-1]
                                 + ',"value":"%h"}' for b in bindings) + ']}'
    source = ['`timescale 1ps/1ps', 'module paired_semantic_probe();',
              'import "DPI-C" context function void harness_restore_fail(input string message);',
              'integer fd=0, address; bit captured=0, restoring=0;',
              'longint unsigned host_edges=0, target_edges=0;',
              'always @(posedge emul.clock) host_edges=host_edges+1;',
              f'always @(posedge {root}.clock) target_edges=target_edges+1;',
              'task snapshot;', 'begin',
              '  if(captured || emul.clock || ' + root + '.clock) harness_restore_fail("semantic snapshot phase");',
              '  if(restoring && (host_edges || target_edges)) harness_restore_fail("semantic restore observation advanced edges");',
              '  fd=$fopen(restoring ? ' + json.dumps(str(out / 'restored.jsonl')) + ' : ' +
              json.dumps(str(out / 'captured.jsonl')) + ', "w");',
              '  if(!fd) harness_restore_fail("semantic snapshot output");',
              '  $fdisplay(fd, ' + json.dumps(prefix) + f', {cycle_path}, target_edges);',
              *_records(manifest, root + '.'),
              '  $fflush(fd); $fclose(fd);',
              '  fd=$fopen(restoring ? ' + json.dumps(str(out / 'boundary-restored.json')) + ' : ' +
              json.dumps(str(out / 'boundary-captured.json')) + ', "w");',
              '  if(!fd) harness_restore_fail("semantic boundary observation output");',
              '  $fdisplay(fd, ' + json.dumps(input_observation) + f', {cycle_path}, target_edges' +
              ''.join(', emul.' + b['target_path'] for b in bindings) + ');',
              '  $fflush(fd); $fclose(fd); captured=1;',
              f'  $display("PAIRED_SEMANTIC_SNAPSHOT cycle=%0d entries={len(manifest["state"])} words={mapping["semantic_words"]} host_edges=%0d target_edges=%0d restoring=%0d", {cycle_path}, host_edges, target_edges, restoring);',
              'end endtask',
              'initial begin', '  restoring=$test$plusargs("fs-restore=");',
              '  if(restoring) begin wait(emul.checkpoint_restore_complete); snapshot(); end', 'end',
              'always @(emul.checkpoint_settled_event) if(!restoring && !captured) snapshot();',
              'endmodule', 'bind FPGATop paired_semantic_probe semantic_paired_observer();']
    (out / 'paired-probe.sv').write_text('\n'.join(source) + '\n')
    (out / 'mapping.json').write_bytes(canonical(mapping))


def read_boundary_inputs(path, mapping, target_cycle, target_edges):
    """Validate every directly bound authoritative input at a parked cut."""
    observation = json.loads(Path(path).read_text(), object_pairs_hook=unique_object)
    keys(observation, {'boundary_input_version', 'mapping_sha256', 'target_cycle', 'observed_target_edges', 'ports'})
    require(type(observation['boundary_input_version']) is int and observation['boundary_input_version'] == 1
            and observation['mapping_sha256'] == hashlib.sha256(canonical(mapping)).hexdigest(),
            'incompatible authoritative input observation')
    for field, expected in [('target_cycle', target_cycle), ('observed_target_edges', target_edges)]:
        natural(observation[field])
        require(observation[field] == expected, 'authoritative input observation cycle mismatch')
    records = observation['ports']
    bindings = mapping['boundary_input_bindings']
    require(type(records) is list and len(records) == len(bindings), 'incomplete authoritative input observation')
    for record, binding in zip(records, bindings):
        keys(record, {'name', 'width', 'value'})
        require(record['name'] == binding['port']['name'] and type(record['width']) is int
                and record['width'] == binding['port']['width'], 'changed authoritative input membership/shape')
        bit_value(dict(width=record['width'], value=record['value']))
    return records


def read_snapshot(path, manifest, mapping):
    with Path(path).open() as stream:
        def row():
            line = stream.readline()
            require(bool(line), 'incomplete semantic snapshot')
            return json.loads(line, object_pairs_hook=unique_object)
        header = row()
        keys(header, {'snapshot_version', 'snapshot_type', 'semantic_manifest_sha256', 'mapping_sha256',
                      'target_cycle', 'observed_target_edges'})
        require(type(header['snapshot_version']) is int and header['snapshot_version'] == 1
                and header['snapshot_type'] == 'independent_semantic_cut'
                and header['semantic_manifest_sha256'] == manifest_hash(manifest)
                and header['mapping_sha256'] == hashlib.sha256(canonical(mapping)).hexdigest(),
                'incompatible semantic snapshot')
        natural(header['target_cycle']); natural(header['observed_target_edges'])
        require(header['target_cycle'] < 2**64 and header['observed_target_edges'] < 2**64,
                'unsupported semantic cycle range')
        records = []
        for e in manifest['state']:
            r = row()
            keys(r, {'state_id', 'width', 'depth', 'values'})
            require((r['state_id'], r['width'], r['depth']) == (e['state_id'], e['width'], e['depth'])
                    and type(r['width']) is int and type(r['depth']) is int
                    and type(r['values']) is list and len(r['values']) == e['depth'],
                    'missing/reordered/reshaped semantic snapshot entry')
            for value in r['values']:
                bit_value(dict(width=e['width'], value=value))
            records.append(r)
        require(not stream.read(), 'extra semantic snapshot entries')
    return header, records


def package_snapshot(path, manifest, boundary, mapping, configuration, destination):
    header, records = read_snapshot(path, manifest, mapping)
    build, _ = builds(manifest, boundary, configuration)
    # The Level-1 FASED counter can restart during target reset. Its label is
    # not the semantic oracle's count of actual DUT edges (including reset).
    # S[C] is after exactly C observed edges and before edge C. Never infer
    # its origin from a software operation index or the FASED counter.
    doc = dict(format_version=1, checkpoint_type='rtlckpt', build=build,
               target_clock_phase='before_rising_edge', target_cycle=header['observed_target_edges'], records=records)
    data = encode_semantic(doc, manifest)
    Path(destination).write_bytes(data)
    Path(str(destination) + '.cut.json').write_bytes(canonical(dict(
        level1_fased_cycle=header['target_cycle'], semantic_cycle=header['observed_target_edges'],
        semantic_cycle_domain='actual_DUT_rising_edges_since_process_initialization_including_target_reset',
        phase='before_next_gated_DUT_rising_edge', mapping_sha256=header['mapping_sha256'],
        checkpoint_sha256=hashlib.sha256(data).hexdigest(), live_cycle_alignment_verified=False)))
    return header


def prepare_clean_readback(image, manifest, boundary, mapping, configuration, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    build, _ = builds(manifest, boundary, configuration)
    doc = decode_semantic(image, build, manifest)
    records = {r['state_id']: r for r in doc['records']}
    with (out / 'restore.txt').open('w') as stream:
        for w in state_words(manifest):
            stream.write(f"bridge_clean_tb.dut.{w['path']} {w['width']} {records[w['state_id']]['values'][w['address']]}\n")
    ports = bridge_ports(boundary)
    header = dict(snapshot_version=1, snapshot_type='independent_semantic_cut',
                  semantic_manifest_sha256=manifest_hash(manifest),
                  mapping_sha256=hashlib.sha256(canonical(mapping)).hexdigest(),
                  target_cycle=doc['target_cycle'], observed_target_edges=0)
    source = ['`timescale 1ns/1ps', 'module bridge_clean_tb;',
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              'reg clock=0; integer fd, address; longint unsigned target_edges=0;',
              'always @(posedge clock) target_edges=target_edges+1;',
              *[f"{'reg' if p['direction'] == 'input' else 'wire'} [{p['width']-1}:0] {p['name']}" +
                ('=0;' if p['direction'] == 'input' else ';') for p in ports],
              boundary['dut_module'] + ' dut(.clock(clock), ' +
              ', '.join(f".{p['name']}({p['name']})" for p in ports) + ');',
              'initial begin', '  #1;',
              f'  if(semantic_restore({json.dumps(str(out / "restore.txt"))}, {mapping["semantic_words"]})) semantic_fail("BRIDGE_CLEAN_LOAD_ERROR");',
              '  #1;', '  // BRIDGE_READBACK_VERIFICATION_INJECTION',
              '  if(target_edges || clock) semantic_fail("BRIDGE_CLEAN_LOAD_ADVANCED_CLOCK");',
              '  fd=$fopen(' + json.dumps(str(out / 'readback.jsonl')) + ', "w");',
              '  if(!fd) semantic_fail("BRIDGE_CLEAN_READBACK_OUTPUT");',
              '  $fdisplay(fd, "%s", ' + json.dumps(canonical(header).decode()) + ');',
              *_records(manifest, 'dut.'),
              '  $fflush(fd); $fclose(fd);',
              f'  $display("BRIDGE_CLEAN_READBACK cycle={doc["target_cycle"]} words={mapping["semantic_words"]} target_edges=%0d", target_edges);',
              '  $finish;', 'end', 'endmodule']
    (out / 'clean.sv').write_text('\n'.join(source) + '\n')
    return doc['target_cycle']
