"""Independent Level-2 finite replay with explicitly captured clock events.

No periods, clock ratios, target-cycle increments or state are synthesized from
names. This ordinary RTL backend accepts only settled all-low cuts. It does not
establish a mapping from FAME state, a coherent metasim cut or CPU ownership.
"""
import hashlib

from .codec import bit_value, decode, encode, keys, require
from .multiclock_inventory import access_paths, boundary_ports
from .replay import builds, state_words
from .semantic import decode_semantic, encode_semantic


def ports_with_aliases(manifest, boundary):
    return sorted(boundary_ports(manifest, boundary) +
                  [dict(name=a['name'], direction='output', width=1) for a in boundary['clock_aliases']],
                  key=lambda p: p['name'])


def validate_signals(record, ports):
    for direction in ('input', 'output'):
        values = record[direction + 's']
        require(type(values) is dict and {k: v['width'] for k, v in values.items() if type(v) is dict and 'width' in v} ==
                {p['name']: p['width'] for p in ports if p['direction'] == direction},
                'incomplete, unknown or wrong-width multi-clock boundary')
        for value in values.values():
            keys(value, {'width', 'value'})
            bit_value(value)


def document(kind, build, phase, cycle, records):
    return dict(format_version=2, checkpoint_type=kind, target_cycle=cycle,
                target_clock_phase='before_clock_event', event_phase=phase, build=build, records=records)


def package_capture(manifest, boundary, configuration, rows, start, length, cycle_clock):
    """Validate a complete event-0 capture before selecting an all-low cut.

    Raw rows contain actual pre-event clocks, all boundary samples and every
    semantic word. The upcoming clock vector is explicit, including falls.
    The cycle label is the number of completed rises of the selected clock.
    """
    ports = ports_with_aliases(manifest, boundary)
    require(cycle_clock in manifest['clock_inputs'], 'unknown captured cycle clock')
    require(type(start) is int and type(length) is int and start >= 0 and length > 0 and
            type(rows) is list and start + length <= len(rows), 'capture cut outside finite event stream')
    words = list(state_words(manifest))
    levels = dict.fromkeys(manifest['clock_inputs'], 0)
    counts = dict(levels)
    phases, records = [], []
    for index, row in enumerate(rows):
        keys(row, {'event_index', 'cycle', 'before', 'clock_levels', 'inputs', 'outputs', 'values'})
        require(type(row['event_index']) is int and row['event_index'] == index and
                type(row['cycle']) is int and row['cycle'] == counts[cycle_clock], 'capture event/cycle labels disagree')
        require(type(row['before']) is dict and row['before'] == levels and
                all(type(v) is int for v in row['before'].values()), 'capture clock phase discontinuity')
        validate_signals(row, ports)
        require(type(row['values']) is list and len(row['values']) == len(words), 'incomplete captured semantic state')
        for word, value in zip(words, row['values']):
            bit_value(dict(width=word['width'], value=value))
        for alias in boundary['clock_aliases']:
            require(int(row['outputs'][alias['name']]['value'], 16) == levels[manifest['dut_root'] + '.' + alias['source']],
                    'captured output clock alias disagrees with its actual source')
        phases.append(dict(event_index=index, cycle_clock=cycle_clock, clock_levels=dict(levels), rising_edges=dict(counts)))
        record = {k: row[k] for k in ('event_index', 'cycle', 'clock_levels', 'inputs', 'outputs')}
        next_levels = record['clock_levels']
        require(type(next_levels) is dict and set(next_levels) == set(levels) and next_levels != levels and
                all(type(v) is int and v in (0, 1) for v in next_levels.values()), 'invalid captured clock event')
        for clock in levels:
            counts[clock] += int(levels[clock] == 0 and next_levels[clock] == 1)
        levels = dict(next_levels)
        records.append(record)
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    phase, cycle = phases[start], rows[start]['cycle']
    values = iter(rows[start]['values'])
    ckpt = document('rtlckpt', rtl_build, phase, cycle,
                    [dict(state_id=e['state_id'], width=e['width'], depth=e['depth'],
                          values=[next(values) for _ in range(e['depth'])]) for e in manifest['state']])
    trace = document('trace', trace_build, phase, cycle, records[start:start + length])
    # Both validation paths complete before returning publishable bytes.
    return encode_semantic(ckpt, manifest), encode('trace', trace)


def prepare_replay(manifest, boundary, configuration, clean, access, ckpt_data, trace_data, out):
    """Validate both artifacts completely before publishing any loader input."""
    ports = ports_with_aliases(manifest, boundary)
    paths = access_paths(manifest, boundary, clean, access)
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    ckpt = decode_semantic(ckpt_data, rtl_build, manifest)
    trace = decode(trace_data, 'trace', trace_build)
    require(trace['format_version'] == 2 and trace['event_phase'] == ckpt['event_phase'] and
            trace['target_cycle'] == ckpt['target_cycle'] and trace['records'], 'checkpoint/trace event-phase mismatch')
    for record in trace['records']:
        validate_signals(record, ports)
    levels = dict(trace['event_phase']['clock_levels'])
    for record in trace['records']:
        for alias in boundary['clock_aliases']:
            require(int(record['outputs'][alias['name']]['value'], 16) == levels[manifest['dut_root'] + '.' + alias['source']],
                    'trace output clock alias disagrees with its source')
        levels = record['clock_levels']
    clocks = manifest['clock_inputs']
    names = [c[len(manifest['dut_root']) + 1:] for c in clocks]
    records = {r['state_id']: r for r in ckpt['records']}
    restore = []
    for e in manifest['state']:
        for address in range(e['depth']):
            path = paths[e['state_id']] + (f'[{address}]' if e['kind'] == 'memory' else '')
            restore.append(f"event_replay_tb.dut.{path} {e['width']} {records[e['state_id']]['values'][address]}")
    source = ['`timescale 1ns/1ps', 'module event_replay_tb;',
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              'integer edges = 0; integer acknowledged = 0; integer sampled_event = -1;']
    for name in names:
        source += [f'reg {name} = 0;', f'always @(posedge {name}) edges = edges + 1;']
    for port in ports:
        source += [f"{'reg' if port['direction'] == 'input' else 'wire'} [{port['width'] - 1}:0] {port['name']}" +
                   (' = 0;' if port['direction'] == 'input' else ';')]
    pins = names + [p['name'] for p in ports]
    source += [boundary['dut_module'] + ' dut(' + ', '.join(f'.{n}({n})' for n in pins) + ');',
               'initial begin', '  #1;',
               f'  if (semantic_restore("{out / "restore.txt"}", {len(restore)})) semantic_fail("RESTORE_FAILED");',
               '  #1;',
               f'  if (semantic_verify("{out / "restore.txt"}", {len(restore)})) semantic_fail("READBACK_FAILED");',
               '  if (edges || ' + ' || '.join(names) + ') semantic_fail("EDGE_BEFORE_COMPLETE_READBACK");',
               f'  $display("ZERO_EDGE_READBACK words={len(restore)} edges=%0d", edges);',
               '  // POST_READBACK_FAULT_INSERTION']
    for record in trace['records']:
        event, cycle = record['event_index'], record['cycle']
        for name, value in record['inputs'].items():
            source += [f"  {name} = {value['width']}'h{value['value']};"]
        source += ['  #1;']
        for name, value in sorted(record['outputs'].items()):
            source += [f"  if ({name} !== {value['width']}'h{value['value']}) begin",
                       f'    $display("DIVERGENCE event={event} cycle={cycle} signal={name} expected={value["value"]} actual=%h acknowledged=%0d", {name}, acknowledged);',
                       '    semantic_fail("EVENT_REPLAY_MISMATCH"); end']
        source += [f'  $display("MATCH event={event} cycle={cycle} outputs={len(record["outputs"])}");',
                   f'  sampled_event = {event}; #1;',
                   '  {' + ', '.join(names) + '} = ' + str(len(names)) + "'b" +
                   ''.join(str(record['clock_levels'][c]) for c in clocks) + ';',
                   '  #1; acknowledged = acknowledged + 1;']
    source += [f'  $display("PASS: event replay samples={len(trace["records"])} words={len(restore)} acknowledged=%0d", acknowledged);',
               '  $finish;', 'end', 'endmodule']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'restore.txt').write_text('\n'.join(restore) + '\n')
    (out / 'replay.sv').write_text('\n'.join(source) + '\n')
    return dict(samples=len(trace['records']), words=len(restore), first_event=trace['event_phase']['event_index'],
                first_target_cycle=trace['target_cycle'], clock_inputs=list(clocks),
                checkpoint_sha256=hashlib.sha256(ckpt_data).hexdigest(), trace_sha256=hashlib.sha256(trace_data).hexdigest())
