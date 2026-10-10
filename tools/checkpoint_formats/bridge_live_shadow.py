"""Host-only schema-2 lockstep at the actual bridge-extracted DUT clock.

Compile the observer before Level-1 capture; bind its runtime session to the
independent Level-2 image and paired cut after capture. Native image compatibility
therefore never depends on rebuilding an observer after that image was taken.
"""
import hashlib
import json
from pathlib import Path

from .bridge_semantic import bridge_ports
from .codec import canonical, require
from .live_shadow import IMPORTS
from .replay import builds, state_words
from .semantic import decode_semantic, manifest_hash


DPI = [line for line in IMPORTS if 'semantic_fail' not in line] + [
    'import "DPI-C" context function void shadow_fail(input string message);']


def validate_boundary(manifest, boundary, mapping, erased):
    ports = bridge_ports(boundary)
    require(mapping['semantic_manifest_sha256'] == manifest_hash(manifest)
            and mapping['ports'] == ports, 'changed live semantic mapping')
    require(mapping['boundary_input_bindings'] == [
        dict(port=p, target_path=mapping['target_root'] + '.' + p['name'])
        for p in ports if p['direction'] == 'input'], 'incomplete live authoritative inputs')
    require(erased['source_hashes'] == {n: mapping['source_hashes'][n]
            for n in ('reference', 'clean', 'transformed')}
            and erased['erased_output_semantics_verified'] is True
            and not erased['unresolved_inputs'], 'unverified live erased boundary')
    require([e['port'] for e in erased['erased_outputs']] == mapping['missing_transformed_ports']
            and all(e['port']['direction'] == 'output' for e in erased['erased_outputs']),
            'incomplete live erased outputs')
    expressions = {}
    for e in erased['erased_outputs']:
        p = e['port']
        if e['kind'] == 'constant':
            require(type(e['value']) is int and 0 <= e['value'] < 2**p['width']
                    and e['expression'] == f"{p['width']}'h{e['value']:x}", 'changed live output constant')
            expressions[p['name']] = e['expression']
        else:
            require(e['kind'] == 'target_input_alias'
                    and any(b['port']['name'] == e['expression'] and b['port']['width'] == p['width']
                            and b['target_path'] == e['target_path'] for b in mapping['boundary_input_bindings']),
                    'changed live output alias')
            expressions[p['name']] = 'emul.' + e['target_path']
    return ports, expressions


def prepare_bridge_authority(manifest, boundary, mapping, erased, out):
    ports, erased_expressions = validate_boundary(manifest, boundary, mapping, erased)
    root = 'emul.' + mapping['target_root']
    expressions = [erased_expressions.get(p['name'], root + '.' + p['name']) for p in ports]
    shape = ' '.join(str(p['width']) for p in ports)
    source = ['`timescale 1ps/1ps', 'module bridge_shadow_authority;', *DPI,
              'bit enabled=0, initialized=0, opened=0;',
              'longint unsigned cycle=0, first_cycle=0, level1_cycle=0, host_edges=0, target_edges=0;',
              'string socket_path, identity, acknowledgment;',
              'always @(posedge emul.clock) host_edges=host_edges+1;',
              'initial begin', '  enabled=$value$plusargs("shadow-socket=%s", socket_path);',
              '  if(enabled) begin',
              '    if(!$test$plusargs("fs-restore=") ||',
              '       !$value$plusargs("shadow-identity=%s", identity) ||',
              '       !$value$plusargs("shadow-first-cycle=%d", first_cycle) ||',
              '       !$value$plusargs("shadow-level1-cycle=%d", level1_cycle) || first_cycle == 64\'hffffffffffffffff)',
              '      shadow_fail("SHADOW_RESTORE_ORIGIN_REQUIRED");',
              '    wait(emul.checkpoint_restore_complete);',
              f'    if(host_edges || target_edges || emul.clock || {root}.clock ||',
              '       emul.FPGATop.FASEDMemoryTimingModel_0.model.tCycle != level1_cycle)',
              '      shadow_fail("SHADOW_RESTORE_ORIGIN_MISMATCH");',
              '    cycle=first_cycle; initialized=1;',
              '    $display("SHADOW_RESTORED_ORIGIN semantic=%0d level1=%0d host_edges=0 target_edges=0", cycle, level1_cycle);',
              '  end', 'end', f'always @(posedge {root}.clock) begin',
              '  if(enabled) begin', '    if(!initialized) shadow_fail("SHADOW_EDGE_BEFORE_RESTORE");',
              f'    if(!opened) begin shadow_open(socket_path, 0, identity, first_cycle, "{shape}"); opened=1; end',
              '    if($isunknown({' + ', '.join(expressions) + '}))',
              '      shadow_fail($sformatf("SHADOW_UNKNOWN_BOUNDARY cycle=%0d", cycle));',
              '    shadow_send($sformatf("DATA %0d ' + ' '.join('%h' for p in ports) + '", cycle, ' +
              ', '.join(expressions) + '));',
              '    acknowledgment=shadow_receive();',
              '    cycle=cycle+1;', '  end', '  target_edges=target_edges+1;', 'end',
              'final begin', '  if(enabled) begin',
              '    if(!opened) shadow_fail("SHADOW_START_UNREACHED");',
              '    shadow_send($sformatf("END %0d", cycle)); acknowledgment=shadow_receive(); shadow_close();',
              '    $display("SHADOW_AUTHORITY_DONE first=%0d end=%0d target_edges=%0d", first_cycle, cycle, target_edges);',
              '  end', 'end', 'endmodule',
              'bind FPGATop bridge_shadow_authority bridge_shadow_observer();']
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'authority.sv').write_text('\n'.join(source) + '\n')


def prepare_bridge_clean(manifest, boundary, mapping, erased, configuration, image, cut, level1_sha256, out):
    ports, _ = validate_boundary(manifest, boundary, mapping, erased)
    build, _ = builds(manifest, boundary, configuration)
    checkpoint = decode_semantic(image, build, manifest)
    start = checkpoint['target_cycle']
    require(type(start) is int and 0 <= start < 2**64 - 1, 'unsupported live target-cycle range')
    require(cut['semantic_cycle'] == start and cut['checkpoint_sha256'] == hashlib.sha256(image).hexdigest()
            and cut['mapping_sha256'] == hashlib.sha256(canonical(mapping)).hexdigest()
            and type(cut['level1_fased_cycle']) is int and 0 <= cut['level1_fased_cycle'] < 2**64,
            'live paired cycle origin mismatch')
    require(len(level1_sha256) == 64 and set(level1_sha256) <= set('0123456789abcdef'),
            'invalid live Level-1 binding')
    identity = hashlib.sha256(canonical(dict(protocol='bridge-live-shadow-v1',
        configuration=configuration, manifest=manifest, boundary=boundary, mapping=mapping,
        erased_outputs=erased, level2_sha256=hashlib.sha256(image).hexdigest(),
        level1_sha256=level1_sha256, cut=cut))).hexdigest()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    records = {r['state_id']: r for r in checkpoint['records']}
    with (out / 'restore.txt').open('w') as stream:
        for w in state_words(manifest):
            stream.write(f"bridge_shadow_tb.dut.{w['path']} {w['width']} {records[w['state_id']]['values'][w['address']]}\n")
    words = sum(e['depth'] for e in manifest['state'])
    shape = ' '.join(str(p['width']) for p in ports)
    source = ['`timescale 1ns/1ps', 'module bridge_shadow_tb;', *DPI,
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned words);',
              'reg clock=0;', f'longint unsigned next_cycle={start}, received_cycle, target_edges=0;',
              'string socket_path, audit_path, packet, kind;', 'integer audit_fd, parsed;',
              'always @(posedge clock) target_edges=target_edges+1;']
    for i, p in enumerate(ports):
        source += [f"{'reg' if p['direction'] == 'input' else 'wire'} [{p['width']-1}:0] {p['name']}" +
                   ('=0;' if p['direction'] == 'input' else ';'), f"reg [{p['width']-1}:0] f{i};"]
    source += [boundary['dut_module'] + ' dut(.clock(clock), ' +
               ', '.join(f".{p['name']}({p['name']})" for p in ports) + ');',
               'initial begin',
               '  if(!$value$plusargs("shadow-socket=%s", socket_path) ||',
               '     !$value$plusargs("shadow-audit=%s", audit_path)) shadow_fail("SHADOW_ARGUMENTS");',
               '  audit_fd=$fopen(audit_path, "w"); if(!audit_fd) shadow_fail("SHADOW_AUDIT_OUTPUT");',
               '  #1;',
               f'  if(semantic_restore({json.dumps(str(out / "restore.txt"))}, {words})) shadow_fail("SHADOW_LOAD_ERROR");',
               '  #1;',
               f'  if(semantic_verify({json.dumps(str(out / "restore.txt"))}, {words})) shadow_fail("SHADOW_READBACK_ERROR");',
               '  if(clock || target_edges) shadow_fail("SHADOW_LOAD_ADVANCED_EDGE");',
               f'  $display("SHADOW_CLEAN_PRE_EDGE cycle={start} words={words} target_edges=0");',
               f'  shadow_open(socket_path, 1, "{identity}", {start}, "{shape}");',
               '  forever begin', '    packet=shadow_receive();',
               '    parsed=$sscanf(packet, "%s %d", kind, received_cycle);',
               '    if(parsed != 2 || received_cycle != next_cycle) shadow_fail("SHADOW_CYCLE_ERROR");',
               '    if(kind == "END") begin',
               f'      if(target_edges != next_cycle-{start}) shadow_fail("SHADOW_EDGE_COUNT_ERROR");',
               '      shadow_send($sformatf("ACK %0d", next_cycle)); shadow_close(); $fclose(audit_fd);',
               f'      $display("PASS: restored live clean RTL shadow first={start} end=%0d target_edges=%0d", next_cycle, target_edges);',
               '      $finish;', '    end else begin',
               '      parsed=$sscanf(packet, "%s %d ' + ' '.join('%h' for p in ports) + '", kind, received_cycle, ' +
               ', '.join(f'f{i}' for i in range(len(ports))) + ');',
               f'      if(parsed != {len(ports)+2} || kind != "DATA") shadow_fail("SHADOW_PACKET_ERROR");']
    source += [f"      {p['name']}=f{i};" for i, p in enumerate(ports) if p['direction'] == 'input']
    source += ['      #1;', '      // BRIDGE_LIVE_VERIFICATION_INJECTION']
    for i, p in enumerate(ports):
        if p['direction'] == 'output':
            source.append(f"      if({p['name']} !== f{i}) " +
                'shadow_fail($sformatf("FIRST_MISMATCH cycle=%0d signal=' + p['name'] +
                f' expected=%h actual=%h target_edges=%0d", next_cycle, f{i}, {p["name"]}, target_edges));')
    source += ['      $fdisplay(audit_fd, "%s", packet); $fflush(audit_fd);',
               '      clock=1; #1; clock=0; #1;',
               '      shadow_send($sformatf("ACK %0d", next_cycle)); next_cycle=next_cycle+1;',
               '    end', '  end', 'end', 'endmodule']
    (out / 'clean.sv').write_text('\n'.join(source) + '\n')
    metadata = dict(session_identity=identity, first_cycle=start, level1_cycle=cut['level1_fased_cycle'],
                    restored_words=words, ports=ports, phase='before_rising_edge',
                    clock='actual gated DUT clock', level1_sha256=level1_sha256,
                    level2_sha256=hashlib.sha256(image).hexdigest(),
                    authority_sha256=hashlib.sha256((out / 'authority.sv').read_bytes()).hexdigest())
    (out / 'session.json').write_bytes(canonical(metadata))
    return metadata
