"""Independent finite Level-2 replay in ordinary VCS (no FireSim runtime).

Both boundary schemas use pre-rising-edge S[C], I[C], O[C]. Clock aliases
are checked against the emitted RTL and never treated as trace data. The
validated trace is a data file, so SV compilation size is independent of L.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .bridge_semantic import bridge_ports
from .codec import bit_value, canonical, decode, encode, require
from .replay import IDENT, RANGE, boundary_ports, builds, inventory_rtl, modules, state_words
from .semantic import decode_semantic


def ports_for(boundary):
    return bridge_ports(boundary) if boundary.get('boundary_version') == 2 else boundary_ports(boundary)


def check_clean(manifest, boundary, rtl):
    ports = ports_for(boundary)
    require(boundary['dut_root'] == manifest['dut_root'] and
            manifest['clock_domain'] == manifest['dut_root'] + '.clock', 'unsupported replay root/clock')
    mods = modules(rtl)
    visited, active = set(), set()
    def check_emitter(module):
        require(module in mods and module not in active, 'unsupported recursive/missing replay module')
        if module in visited:
            return
        active.add(module)
        body = mods[module][1]
        # The inventory is for the FIRRTL emitter's reg/wire grammar. Refuse
        # additional procedural state that this parser cannot enumerate.
        require(not re.search(r'^\s*(?:logic|bit|int|longint|shortint|byte|time|real|realtime|event|struct|union|typedef)\b',
                              body, re.M), 'unsupported replay variable declaration')
        integers = re.findall(r'\binteger\s+([^;]+);', body)
        require(all(v.strip() == 'initvar' for v in integers), 'unsupported replay integer state')
        require(not re.search(r'\balways_(?:ff|comb|latch)\b', body), 'unsupported replay procedural syntax')
        require(all(event.strip() == 'posedge clock' for event in re.findall(r'\balways\s*@\s*\((.*?)\)', body)),
                'unsupported replay sequential clock or procedural block')
        for child, _ in re.findall(rf'^[ \t]*({IDENT})[ \t]+({IDENT})[ \t]*\(', body, re.M):
            # Repeated instances share a definition; inventory_rtl separately
            # enumerates the full instance-qualified state of each one.
            check_emitter(child)
        active.remove(module)
        visited.add(module)
    check_emitter(boundary['dut_module'])
    expected = {e['hierarchy'][len(manifest['dut_root']) + 1:]:
                (e['width'], e['depth'], e['kind']) for e in manifest['state']}
    require(inventory_rtl(mods, boundary['dut_module']) == expected,
            'unsupported/lost/extra/reshaped replay state')
    header, body = mods[boundary['dut_module']]
    actual = sorted([dict(name=n, direction=d, width=int(w) + 1 if w else 1)
                     for d, w, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', header)],
                    key=lambda p: p['name'])
    aliases = boundary.get('clock_aliases', [])
    expected_ports = boundary['ports'] + [dict(name=a['name'], direction='output', width=1) for a in aliases]
    require(actual == sorted(expected_ports, key=lambda p: p['name']), 'incomplete/reshaped replay boundary')
    for alias in aliases:
        require(re.findall(r'\bassign\s+' + re.escape(alias['name']) + r'\s*=\s*([^;]+);', body)
                == ['clock'], 'unsupported replay clock alias')
    return ports


def package_boundary_trace(manifest, boundary, configuration, image, raw, out):
    """Package complete DATA rows recorded at actual target edges.

    The producer may be metasim or FPGA transport. No Level-1 image, paired
    cut sidecar, FASED model, or live connection is needed by this consumer.
    The raw file must contain the whole selected finite interval, without END.
    """
    ports = ports_for(boundary)
    require(boundary['dut_root'] == manifest['dut_root'] and
            manifest['clock_domain'] == manifest['dut_root'] + '.clock', 'unsupported finite capture root/clock')
    build, trace_build = builds(manifest, boundary, configuration)
    checkpoint = decode_semantic(image, build, manifest)
    start = checkpoint['target_cycle']
    records = []
    with Path(raw).open() as stream:
        for line in stream:
            fields = line.split()
            require(len(fields) == len(ports) + 2 and fields[0] == 'DATA'
                    and re.fullmatch(r'[0-9]+', fields[1]) is not None
                    and int(fields[1]) == start + len(records), 'missing/duplicated/malformed finite target edge')
            record = dict(cycle=start + len(records), inputs={}, outputs={})
            for p, value in zip(ports, fields[2:]):
                field = dict(width=p['width'], value=value)
                bit_value(field)
                record[p['direction'] + 's'][p['name']] = field
            records.append(record)
    require(records, 'empty finite trace')
    require(0 <= start < start + len(records) < 2**64, 'unsupported finite target-cycle range')
    trace = dict(format_version=1, checkpoint_type='trace', target_cycle=start,
                 target_clock_phase='before_rising_edge', build=trace_build, records=records)
    data = encode('trace', trace)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'capture.rtlckpt').write_bytes(image)
    (out / 'capture.trace').write_bytes(data)
    metadata = dict(first_cycle=start, end_cycle=start + len(records), samples=len(records),
                    checkpoint_sha256=hashlib.sha256(image).hexdigest(), trace_sha256=hashlib.sha256(data).hexdigest(),
                    raw_sha256=hashlib.sha256(Path(raw).read_bytes()).hexdigest(),
                    boundary_sha256=hashlib.sha256(canonical(boundary)).hexdigest())
    (out / 'capture.json').write_bytes(canonical(metadata))
    return metadata


def prepare_finite_replay(manifest, boundary, configuration, image, trace_data, rtl, out):
    build, trace_build = builds(manifest, boundary, configuration)
    checkpoint = decode_semantic(image, build, manifest)
    trace = decode(trace_data, 'trace', trace_build)
    ports = check_clean(manifest, boundary, rtl)
    start = checkpoint['target_cycle']
    require(start == trace['target_cycle'] and trace['records'], 'checkpoint/trace cycle mismatch or empty trace')
    end = start + len(trace['records'])
    require(0 <= start < end < 2**64, 'unsupported finite target-cycle range')
    for record in trace['records']:
        for direction in ('input', 'output'):
            require({n: v['width'] for n, v in record[direction + 's'].items()} ==
                    {p['name']: p['width'] for p in ports if p['direction'] == direction},
                    'incomplete, unknown, or wrong-width finite boundary')
    words = sum(e['depth'] for e in manifest['state'])
    require(0 < words < 2**32, 'unsupported finite restore word count')
    # All container, mapping and shape checks precede any output publication.
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    records = {r['state_id']: r for r in checkpoint['records']}
    with (out / 'restore.txt').open('w') as stream:
        for w in state_words(manifest):
            stream.write(f"finite_replay_tb.dut.{w['path']} {w['width']} {records[w['state_id']]['values'][w['address']]}\n")
    with (out / 'trace.txt').open('w') as stream:
        for r in trace['records']:
            stream.write('DATA ' + str(r['cycle']) + ' ' + ' '.join(
                r[p['direction'] + 's'][p['name']]['value'] for p in ports) + '\n')
    source = ['`timescale 1ns/1ps', 'module finite_replay_tb;',
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned words);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              'reg clock=0;', f'longint unsigned next_cycle={start}, received_cycle, target_edges=0;',
              'string restore_path, trace_path, waveform, audit_path, packet, kind, extra;',
              'integer trace_fd, audit_fd, parsed, got;',
              'always @(posedge clock) target_edges=target_edges+1;',
              'task replay_fail(input string message);', '  $vcdplusflush; semantic_fail(message);', 'endtask']
    for i, p in enumerate(ports):
        source += [f"{'reg' if p['direction'] == 'input' else 'wire'} [{p['width']-1}:0] {p['name']}" +
                   ('=0;' if p['direction'] == 'input' else ';'), f"reg [{p['width']-1}:0] f{i};"]
    source += [boundary['dut_module'] + ' dut(.clock(clock), ' +
               ', '.join(f".{p['name']}({p['name']})" for p in ports) + ');',
               'initial begin',
               '  if(!$value$plusargs("restore=%s", restore_path) || !$value$plusargs("trace=%s", trace_path) ||',
               '     !$value$plusargs("waveform=%s", waveform) || !$value$plusargs("audit=%s", audit_path))',
               '    semantic_fail("FINITE_REPLAY_ARGUMENTS");',
               '  trace_fd=$fopen(trace_path, "r"); audit_fd=$fopen(audit_path, "w");',
               '  if(!trace_fd || !audit_fd) semantic_fail("FINITE_REPLAY_FILES");',
               '  $vcdplusfile(waveform); $vcdpluson(0, finite_replay_tb);']
    # $vcdpluson alone omits unpacked RAM contents. Enumerate every complete
    # semantic memory, with no address or hierarchy filtering.
    memories = []
    for e in manifest['state']:
        if e['kind'] == 'memory':
            path = 'dut.' + e['hierarchy'][len(manifest['dut_root']) + 1:]
            memories.append(dict(path=path, width=e['width'], depth=e['depth']))
            source.append(f'  $vcdplusmemon({path});')
    source += ['  #1;', f'  if(semantic_restore(restore_path, {words})) replay_fail("FINITE_RESTORE_ERROR");',
               '  #1;', f'  if(semantic_verify(restore_path, {words})) replay_fail("FINITE_READBACK_ERROR");',
               '  if(clock || target_edges) replay_fail("FINITE_LOAD_ADVANCED_EDGE");',
               f'  $display("FINITE_PRE_EDGE cycle={start} words={words} target_edges=0");',
               f'  while(next_cycle < {end}) begin',
               '    got=$fgets(packet, trace_fd); if(!got) replay_fail("FINITE_SHORT_TRACE");',
               '    parsed=$sscanf(packet, "%s %d ' + ' '.join('%h' for p in ports) + ' %s", kind, received_cycle, ' +
               ', '.join(f'f{i}' for i in range(len(ports))) + ', extra);',
               f'    if(parsed != {len(ports)+2} || kind != "DATA" || received_cycle !== next_cycle)',
               '      replay_fail("FINITE_PACKET_OR_CYCLE_ERROR");',
               '    if($isunknown({' + ', '.join(f'f{i}' for i in range(len(ports))) + '}))',
               '      replay_fail("FINITE_UNKNOWN_TRACE");']
    source += [f"    {p['name']}=f{i};" for i, p in enumerate(ports) if p['direction'] == 'input']
    source += ['    #1;']
    for i, p in enumerate(ports):
        if p['direction'] == 'output':
            source.append(f"    if({p['name']} !== f{i}) " +
                'replay_fail($sformatf("FIRST_MISMATCH cycle=%0d signal=' + p['name'] +
                f' expected=%h actual=%h target_edges=%0d", next_cycle, f{i}, {p["name"]}, target_edges));')
    source += ['    $fwrite(audit_fd, "%s", packet); $fflush(audit_fd);',
               '    clock=1; #1; clock=0; #1; next_cycle=next_cycle+1;', '  end',
               '  if($fgets(packet, trace_fd)) replay_fail("FINITE_EXTRA_TRACE");',
               f'  if(target_edges != {end-start}) replay_fail("FINITE_EDGE_COUNT_ERROR");',
               '  $fclose(trace_fd); $fclose(audit_fd); $vcdplusflush; $vcdplusclose;',
               f'  $display("PASS: standalone finite replay first={start} end={end} target_edges=%0d outputs_per_cycle={sum(p["direction"] == "output" for p in ports)}", target_edges);',
               '  $finish;', 'end', 'endmodule']
    (out / 'replay.sv').write_text('\n'.join(source) + '\n')
    (out / 'clean.sv').write_text(rtl)
    metadata = dict(first_cycle=start, end_cycle=end, samples=end-start, restored_words=words, ports=ports,
                    output_comparisons=(end-start)*sum(p['direction'] == 'output' for p in ports),
                    checkpoint_sha256=hashlib.sha256(image).hexdigest(), trace_sha256=hashlib.sha256(trace_data).hexdigest(),
                    replay_rtl_sha256=hashlib.sha256(rtl.encode()).hexdigest(), waveform='VPD',
                    waveform_scope='all hierarchy signals and all complete semantic memories', memories=memories)
    (out / 'replay.json').write_bytes(canonical(metadata))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('package', 'replay'))
    for name in ('manifest', 'boundary', 'checkpoint', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--configuration', required=True)
    for name in ('raw', 'trace', 'clean'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    manifest, boundary = [json.loads(p.read_text()) for p in (args.manifest, args.boundary)]
    if args.action == 'package':
        require(args.raw is not None, '--raw required for package')
        result = package_boundary_trace(manifest, boundary, args.configuration, args.checkpoint.read_bytes(), args.raw, args.out)
    else:
        require(args.trace is not None and args.clean is not None, '--trace and --clean required for replay')
        result = prepare_finite_replay(manifest, boundary, args.configuration, args.checkpoint.read_bytes(),
                                      args.trace.read_bytes(), args.clean.read_text(), args.out)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
