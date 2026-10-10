"""Live single-clock, hierarchy-preserving semantic-DUT VCS shadow adapter.

The authoritative gated DUT edge supplies S[C]'s complete settled boundary.
The clean process applies I[C], compares O[C], advances one edge, and ACKs C.
Until that ACK the authoritative edge cannot perform its sequential updates.
No finite trace, clean-output feedback, or simulator-state conversion is used.
This oracle adapter rejects the same state mappings as Level-2 replay; it is
not yet an adapter for the generated FCFS/FASED Level-1 restore profile.
"""
import hashlib
from pathlib import Path

from .codec import canonical, require
from .replay import boundary_ports, builds, prepare_capture, state_words
from .semantic import decode_semantic


IMPORTS = [
    'import "DPI-C" context function void shadow_open(input string path, input int server, '
    'input string identity, input longint unsigned first_cycle, input string shape);',
    'import "DPI-C" context function void shadow_send(input string message);',
    'import "DPI-C" context function string shadow_receive();',
    'import "DPI-C" context function void shadow_close();',
    'import "DPI-C" context function void semantic_fail(input string message);',
]


def prepare_live_shadow(manifest, boundary, configuration, checkpoint_data,
                        clean_text, transformed_text, out):
    """Validate both RTL inventories and the independent Level-2 image first."""
    rtl_build, _ = builds(manifest, boundary, configuration)
    checkpoint = decode_semantic(checkpoint_data, rtl_build, manifest)
    require(checkpoint['target_cycle'] < 2**64 - 1, 'unsupported live target-cycle range')
    ports = boundary_ports(boundary)
    require(any(p['direction'] == 'output' for p in ports), 'shadow requires outputs')
    words = list(state_words(manifest))
    out = Path(out)
    # Reuse the strict complete mapping check, including multiple-instance
    # rejection. This writes only an oracle description, never RTL state.
    prepare_capture(manifest, boundary, clean_text, transformed_text, out / 'mapping')
    start = checkpoint['target_cycle']
    identity = hashlib.sha256(canonical(dict(
        protocol='live-semantic-shadow-v1', configuration=configuration,
        manifest=manifest, boundary=boundary,
        checkpoint_sha256=hashlib.sha256(checkpoint_data).hexdigest(),
        clean_sha256=hashlib.sha256(clean_text.encode()).hexdigest(),
        transformed_sha256=hashlib.sha256(transformed_text.encode()).hexdigest()))).hexdigest()
    shape = ' '.join(str(p['width']) for p in ports)
    records = {r['state_id']: r for r in checkpoint['records']}
    restore = [(word, records[word['state_id']]['values'][word['address']]) for word in words]
    (out / 'restore.txt').write_text(''.join(
        f"live_shadow_tb.dut.{w['path']} {w['width']} {v}\n" for w, v in restore))

    # The module bind observes the actual target clock, not a host-edge count
    # or a FAME token proxy. Sampling precedes this edge's NBA state changes.
    authority = ['`timescale 1ps/1ps',
                 'module live_shadow_authority(input wire clock,',
                 ',\n'.join(f"input wire [{p['width'] - 1}:0] f{i}" for i, p in enumerate(ports)) + ');',
                 *IMPORTS, 'longint unsigned cycle = 0;',
                 'bit enabled = 0, opened = 0;', 'string socket_path, acknowledgment;',
                 'initial enabled = $value$plusargs("shadow-socket=%s", socket_path);',
                 'always @(posedge clock) begin', f'  if (enabled && cycle >= {start}) begin',
                 f'    if (!opened) begin shadow_open(socket_path, 0, "{identity}", {start}, "{shape}"); opened = 1; end',
                 '    if ($isunknown({' + ', '.join(f'f{i}' for i in range(len(ports))) + '}))',
                 '      semantic_fail($sformatf("SHADOW_UNKNOWN_BOUNDARY cycle=%0d", cycle));',
                 '    shadow_send($sformatf("DATA %0d ' + ' '.join('%h' for p in ports) + '", cycle, ' +
                 ', '.join(f'f{i}' for i in range(len(ports))) + '));',
                 '    acknowledgment = shadow_receive();', '  end',
                 '  cycle = cycle + 1;', 'end',
                 'final begin', '  if (enabled) begin',
                 '    if (!opened) semantic_fail("SHADOW_START_UNREACHED");',
                 '    shadow_send($sformatf("END %0d", cycle)); acknowledgment = shadow_receive(); shadow_close();',
                 f'    $display("SHADOW_AUTHORITY_DONE first={start} end=%0d", cycle);',
                 '  end', 'end', 'endmodule',
                 f"bind {boundary['dut_module']} live_shadow_authority live_shadow_observer(.clock(clock), " +
                 ', '.join(f".f{i}({p['name']})" for i, p in enumerate(ports)) + ');']
    (out / 'authority.sv').write_text('\n'.join(authority) + '\n')

    clean = ['`timescale 1ns/1ps', 'module live_shadow_tb;', *IMPORTS,
             'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
             'reg clock = 0;', 'string socket_path, restore_path, packet, kind;',
             f'longint unsigned next_cycle = {start};', 'longint unsigned received_cycle;',
             'integer parsed;', 'integer audit_fd;', 'string audit_path;']
    for i, p in enumerate(ports):
        clean.append(f"{'reg' if p['direction'] == 'input' else 'wire'} [{p['width'] - 1}:0] {p['name']};")
        clean.append(f"reg [{p['width'] - 1}:0] f{i};")
    clean += [boundary['dut_module'] + ' dut(.clock(clock), ' +
              ', '.join(f".{p['name']}({p['name']})" for p in ports) + ');',
              'initial begin',
              '  if (!$value$plusargs("shadow-socket=%s", socket_path)) semantic_fail("Missing shadow socket");',
              '  if (!$value$plusargs("restore=%s", restore_path)) semantic_fail("Missing semantic restore");',
              '  if (!$value$plusargs("shadow-audit=%s", audit_path)) semantic_fail("Missing shadow audit");',
              '  audit_fd = $fopen(audit_path, "w"); if (!audit_fd) semantic_fail("Cannot open shadow audit");',
              f'  #1; if (semantic_restore(restore_path, {len(words)})) semantic_fail("RESTORE_ERROR before first DUT edge");',
              '  #1;']
    for w, value in restore:
        clean.append(f"  if (dut.{w['path']} !== {w['width']}'h{value}) " +
                     f'semantic_fail("RESTORE_MISMATCH cycle={start} signal={w["path"]}");')
    clean += [f'  $display("SHADOW_CLEAN_PRE_EDGE cycle={start} words={len(words)} target_edges=0");',
              f'  shadow_open(socket_path, 1, "{identity}", {start}, "{shape}");',
              '  forever begin', '    packet = shadow_receive();',
              '    parsed = $sscanf(packet, "%s %d", kind, received_cycle);',
              '    if (parsed != 2 || received_cycle != next_cycle) semantic_fail("SHADOW_CYCLE_ERROR");',
              '    if (kind == "END") begin',
              '      shadow_send($sformatf("ACK %0d", next_cycle)); shadow_close();',
              '      $fclose(audit_fd);',
              f'      $display("PASS: live clean RTL shadow first={start} end=%0d samples=%0d outputs_per_cycle={sum(p["direction"] == "output" for p in ports)}", next_cycle, next_cycle - {start});',
              '      $finish;', '    end else begin',
              '      parsed = $sscanf(packet, "%s %d ' + ' '.join('%h' for p in ports) + '", kind, received_cycle, ' +
              ', '.join(f'f{i}' for i in range(len(ports))) + ');',
              f'      if (parsed != {len(ports) + 2} || kind != "DATA") semantic_fail("SHADOW_PACKET_ERROR");']
    for i, p in enumerate(ports):
        if p['direction'] == 'input':
            clean.append(f"      {p['name']} = f{i};")
    clean.append('      #1;')
    # An explicit marker allows the verifier to inject a real state deposit in
    # its optional observer bench, without modifying clean DUT RTL or packets.
    clean.append('      // LIVE_SHADOW_VERIFICATION_INJECTION')
    for i, p in enumerate(ports):
        if p['direction'] == 'output':
            clean.append(f"      if ({p['name']} !== f{i}) " +
                         'semantic_fail($sformatf("FIRST_MISMATCH cycle=%0d signal=' + p['name'] +
                         f' expected=%h actual=%h", next_cycle, f{i}, {p["name"]}));')
    clean += ['      $fdisplay(audit_fd, "%s", packet); $fflush(audit_fd);',
              '      clock = 1; #1; clock = 0; #1;',
              '      shadow_send($sformatf("ACK %0d", next_cycle));',
              '      next_cycle = next_cycle + 1;', '    end', '  end', 'end', 'endmodule']
    (out / 'clean.sv').write_text('\n'.join(clean) + '\n')
    metadata = dict(protocol='live-semantic-shadow-v1', session_identity=identity,
                    first_cycle=start, ports=ports, restored_words=len(words),
                    phase='before_rising_edge', authoritative_clock='actual gated DUT clock',
                    level1_restore_integrated=False)
    (out / 'session.json').write_bytes(canonical(metadata))
    return metadata
