"""Production parked-driver/settled-harness diagnostics, without full restore.

Read every generated RAM word and every audited software owner at a single
settled rising or falling edge. Compare the complete target token/AXI port sequence and
FASED target timing with uninterrupted execution. Source vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.widget_inventory import check_widget_inventory
from tools.checkpoint_formats.tests.simulation_inventory import check_simulation_base, check_fcfs_driver
from tools.checkpoint_formats.simulator import (prepare_generated_stream_probe,
    prepare_settled_generated_probe, validate_generated_stream)
from tools.checkpoint_formats.tests.verify_driver_boundary_vcs import read_diagnostic, words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects


def digest(path):
    with path.open('rb') as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest()


def prepare_trace(rtl, out, lowclock=False):
    # Inventory every real target-facing FASED port, including data, strobes,
    # IDs, held responses and FAME token handshakes. Reject changed geometry.
    header = re.search(r'module FASEDMemoryTimingModel\((.*?)\n\);', rtl, re.S)
    require(header is not None, 'missing actual FASED ports')
    fields = re.findall(r'(?:input|output)\s*(\[[^]]+\])?\s*(hPort_\w+)(?=\s*(?:,|//|$))', header[1], re.M)
    require(len(fields) == 40, f'changed target token/AXI layout: {len(fields)}')
    prefix = 'emul.FPGATop.FASEDMemoryTimingModel_0.'
    paths = [prefix + name for _, name in fields]
    (out / 'target-port-layout.json').write_text(json.dumps(fields, indent=2) + '\n')
    source = ['`timescale 1ps/1ps', 'module settled_boundary_trace();',
        'integer fd = 0; integer guard = 0; integer refreshes = 0; string filename;',
        'longint unsigned host_edges = 0; longint unsigned parked_edge = 0;',
        'initial if ($value$plusargs("target_port_trace=%s", filename)) begin',
        '  fd = $fopen(filename,"w"); if (!fd) $fatal(1,"trace open failed"); end',
        'always @(posedge emul.clock) begin',
        '  host_edges = host_edges + 1;',
        f'  if ({int(lowclock)} && guard && refreshes != 1) $fatal(1,"rising edge before input refresh");',
        '  if (fd)',
        f'  $fdisplay(fd,"%0d %b %h", {prefix}model.tCycle, {prefix}targetFire, {{'+', '.join(paths)+'});',
        'end', 'always @(emul.checkpoint_settled_event) begin',
        f'  if (emul.clock != {0 if lowclock else 1} || emul.fin || ($time % 1000 != {1 if lowclock else 501})) $fatal(1,"unsettled clock phase");',
        '  if (!simulator_checkpoint_pending()) $fatal(1,"driver not parked");',
        '  parked_edge = host_edges;',
        '  guard = guard + 1; $display("SETTLED_BOUNDARY: guard=%0d time=%0t", guard, $time);',
        'end',
        'always @(emul.checkpoint_output_refresh) if (guard) begin',
        '  if (host_edges != parked_edge) $fatal(1,"host edge during parked continuation");',
        'end',
        'always @(emul.checkpoint_input_refresh) begin',
        f'  if (!{int(lowclock)} || emul.clock || host_edges != parked_edge || !guard || refreshes) $fatal(1,"invalid input refresh");',
        '  refreshes = refreshes + 1; $display("LOWCLOCK_RESUME: same_host_edge=%0d",host_edges);',
        'end', 'final if (fd) $fclose(fd);', 'endmodule',
        'bind FPGATop settled_boundary_trace boundary_trace();']
    return '\n'.join(source) + '\n'


def verify_terminal(binary, out, lowclock=False):
    """A completed dispatcher must park/capture before timeout finalization."""
    out.mkdir(parents=True, exist_ok=True)
    diagnostic = out / 'terminal.diag'
    diagnostic.unlink(missing_ok=True)
    log = run([binary, '+vcs+initreg+0', '+vcs+initmem+0', '+memsize=4194304',
               '+max-cycles=0', '+fs-driver-cut=1', '+fs-driver-settled',
               *(['+fs-driver-lowclock'] if lowclock else []),
               f'+fs-driver-diagnostic={diagnostic}'], out / 'run.log', out, expected=1)
    require('*** FAILED *** simulation timed out' in log and 'FS_DRIVER_BOUNDARY_ERROR:' not in log,
            'completed dispatcher did not resume through finalization')
    cut, owners = read_diagnostic(diagnostic)
    require(cut == 1 and 'diagnostic/harness-banks' in owners, 'terminal boundary capture missing')
    simulation_base = check_simulation_base(owners)
    require(simulation_base['run_done'], 'terminal base did not retain completed step')
    result = dict(cut=cut, finalized_timeout=True, simulation_base=simulation_base, diagnostic=str(diagnostic))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: terminal dispatcher settled capture precedes normal timeout finalization')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--lowclock', action='store_true', help='park across the natural falling edge')
    args = parser.parse_args()
    out, build = args.out.resolve(), args.build.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    require(str(vcs) == _toolchain.VCS, 'source vcs-env.sh last')
    generated = build / 'f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config'
    manifest = json.loads((generated / 'FireSim-generated.simulator-state.json').read_text())
    rtl = (generated / 'FireSim-generated.sv').read_text()
    prefix = 'FPGATop.FASEDMemoryTimingModel_0'
    stages = [{prefix + '.model.SatUpDownCounter.value': 1, prefix + '.SatUpDownCounter.value': 1},
              {prefix + '.model.SatUpDownCounter_1.value': 1, prefix + '.SatUpDownCounter_1.value': 1},
              {prefix + '.model.SatUpDownCounter.value': 1, prefix + '.model.SatUpDownCounter_1.value': 1}]
    prepare_generated_stream_probe(manifest, out, stages)
    prepare_settled_generated_probe(manifest, out, lowclock=args.lowclock)
    probe = out / 'combined-probe.sv'
    probe.write_text((out / 'generated-probe.sv').read_text() +
                     (out / 'settled-generated-probe.sv').read_text() + prepare_trace(rtl, out, args.lowclock))
    invalidate_stale_driver_objects(generated, out / 'rebuilt-driver-objects.json')
    make = ['make', 'vcs', 'TARGET_PROJECT=fasedtests', 'DESIGN=AXI4Fuzzer', 'TARGET_CONFIG=FCFSConfig',
            'PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config', 'SIMULATOR_CHECKPOINT_INVENTORY=FPGATop',
            f'BUILD_DIR={build}', f'VCS={vcs} -full64', 'VCS_FLAGS=-Mupdate', f'VCS_EXTRA_V={probe}']
    run(make, out / 'vcs-build.log', ROOT / 'sims/firesim/sim')
    binary = generated / 'AXI4Fuzzer'
    common = ['+vcs+initreg+0', '+vcs+initmem+0', '+memsize=4194304', '+max-cycles=1000000']
    phase_options = ['+fs-driver-lowclock'] if args.lowclock else []
    cases = []
    for label, timing, cuts in [('default', [], (3, 11, 699275, 699276)),
                               ('randomized', ['+fuzz-host-timing=7', '+fuzz-seed=18446744073709551615'], (101,))]:
        reference = out / label / 'reference'
        reference.mkdir(parents=True, exist_ok=True)
        baseline_trace = reference / 'ports.trace'
        baseline_rtl = reference / 'generated.jsonl'
        log = run([binary, *common, *timing, f'+target_port_trace={baseline_trace}',
                   f'+generated_capture={baseline_rtl}'], reference / 'run.log', reference)
        cycles = re.search(r'Target Cycles Emulated: (\d+)', log)
        require('*** PASSED ***' in log and cycles is not None, 'uninterrupted fuzzer failed')
        target_cycles = int(cycles[1])
        require(target_cycles == 774628 if label == 'default' else 774000 < target_cycles < 1000000,
                'unexpected uninterrupted target completion')
        expected_trace, expected_rtl = digest(baseline_trace), digest(baseline_rtl)
        require('SETTLED_BOUNDARY:' not in log, 'unexpected reference handoff')
        def verify_cut(cut):
            case = out / label / f'cut-{cut}'
            case.mkdir(parents=True, exist_ok=True)
            diagnostic, trace = case / 'software.diag', case / 'ports.trace'
            rtl_capture, parked = case / 'generated.jsonl', case / 'settled.generated.jsonl'
            diagnostic.unlink(missing_ok=True)
            log = run([binary, *common, *timing, f'+fs-driver-cut={cut}', '+fs-driver-settled',
                *phase_options,
                f'+fs-driver-diagnostic={diagnostic}', f'+target_port_trace={trace}',
                f'+generated_capture={rtl_capture}', f'+settled_generated_capture={parked}'], case / 'run.log', case)
            require('*** PASSED ***' in log and f'Target Cycles Emulated: {target_cycles}\n' in log,
                    'settled handoff changed completion')
            require(log.count('SETTLED_BOUNDARY:') == 1, 'missing/repeated settled handoff')
            require(log.count('LOWCLOCK_RESUME:') == int(args.lowclock), 'missing/repeated lowclock input refresh')
            require(digest(trace) == expected_trace, 'target token/AXI cycle trace changed')
            require(digest(rtl_capture) == expected_rtl, 'full outstanding generated-state observations changed')
            actual_cut, owners = read_diagnostic(diagnostic)
            simulation_base = check_simulation_base(owners)
            require(actual_cut == cut, 'operation cut changed')
            require(words(owners['runtime/host-timing'][1])[5] == 0, 'suspended delay captured')
            harness_schema, harness = owners['diagnostic/harness-banks']
            magic, bits = struct.unpack_from('<QQ', harness)
            require(harness_schema == 'firesim.diagnostic.harness-banks.v1' and magic == 0x3153424F534E5248,
                    'missing harness observation')
            require(len(harness) == 16 + 4 * ((bits + 31) // 32), 'incomplete harness banks')
            packed = int.from_bytes(harness[16:], 'little')
            flags = (packed >> (bits - 67)) & 7
            require(flags in ((0, 2) if args.lowclock else (4, 6)), 'clock/fin not at settled capture phase')
            require(packed >> bits == 0, 'noncanonical harness padding')
            sample, = validate_generated_stream(manifest, parked, 1,
                'settled_host_negedge_parked_driver' if args.lowclock else 'settled_host_posedge_parked_driver')
            if args.lowclock:
                require(all(sample['scalars'][entry['hierarchy']] == 0
                    for entry in manifest['state'] if entry['adapter'] == 'metasim-bufgce-v1'),
                    'generated clock output did not settle low')
            memories = []
            for i in range(4):
                payload = owners[f'runtime/functional-memory/{i}'][1]
                header = struct.unpack_from('<13Q', payload)
                require(header[5] == 4194304, 'incomplete functional memory')
                offset = 104 + header[5] + header[4] // 8
                b, = struct.unpack_from('<Q', payload, offset)
                r, = struct.unpack_from('<Q', payload, offset + 8 + b * 8)
                memories.append(dict(cycle=header[7], inflight_write=bool(header[8]), queued_b=b, queued_r=r))
            if cut == 699275:
                require(any(m['inflight_write'] or m['queued_b'] or m['queued_r'] for m in memories),
                        'late cut lost outstanding native memory traffic')
                require(sample['scalars'][prefix + '.model.SatUpDownCounter_1.value'] > 0,
                        'late settled cut lost outstanding target write')
            audited_widgets, unsupported_widgets = check_widget_inventory(owners, (generated / 'FireSim-generated.const.h').read_text())
            require(len(audited_widgets) == 6 and not unsupported_widgets, 'incomplete concrete widget inventory')
            concrete_driver = check_fcfs_driver(owners, (generated / 'FireSim-generated.const.h').read_text())
            require(all(not owners[key][0] for key in ('runtime/harness','runtime/execution-context',
                    'generated/rtl')), 'unaudited owner declared restorable')
            return dict(timing=label, cut=cut, target_cycles=target_cycles, target_port_sha256=expected_trace,
                generated_sha256=expected_rtl, settled_generated_sha256=digest(parked),
                generated_words=sample['words'], host_sample=sample['host_sample'], harness_bits=bits,
                simulation_base=simulation_base, concrete_driver=concrete_driver, memories=memories, audited_widgets=sorted(audited_widgets), unsupported_widgets=sorted(unsupported_widgets), diagnostic=str(diagnostic), settled_generated=str(parked))
        # Unique processes/output trees; the shared executable remains fixed.
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for future in concurrent.futures.as_completed([pool.submit(verify_cut, cut) for cut in cuts]):
                cases.append(future.result())
                cases.sort(key=lambda c: (c['timing'], c['cut']))
                (out / 'partial-results.json').write_text(json.dumps(cases, indent=2) + '\n')
    negatives = []
    for label, options, message in [
        ('profile', ['+profile-interval=250000', '+fs-driver-cut=3'], 'unsupported anonymous/unaudited callback'),
        ('unreached', ['+max-cycles=0', '+fs-driver-cut=2'], 'requested operation cut was never reached'),
        ('duplicate', ['+fs-driver-cut=3', '+fs-driver-settled'], 'invalid/duplicate settled modifier'),
        ('destination', ['+fs-driver-cut=3'], 'diagnostic destination already exists')]:
        diagnostic = out / (label + '.diag')
        diagnostic.unlink(missing_ok=True)
        if label == 'destination':
            diagnostic.write_bytes(b'preserve existing artifact')
        log = run([binary, *common, *options, '+fs-driver-settled',
                   *phase_options,
                   f'+fs-driver-diagnostic={diagnostic}'], out / (label + '.log'), out, expected=1)
        require(message in log and not Path(str(diagnostic) + '.tmp').exists(), 'failure not closed')
        require(diagnostic.read_bytes() == b'preserve existing artifact' if label == 'destination'
                else not diagnostic.exists(), 'failure published/overwrote a diagnostic')
        negatives.append(label)
    if args.lowclock:
        for label, options, message in [
            ('low-without-settled', ['+fs-driver-lowclock'], 'lowclock modifier requires a settled diagnostic request'),
            ('low-duplicate', ['+fs-driver-settled', '+fs-driver-lowclock', '+fs-driver-lowclock'], 'invalid/duplicate lowclock modifier'),
            ('low-malformed', ['+fs-driver-settled', '+fs-driver-lowclock=1'], 'invalid/duplicate lowclock modifier')]:
            diagnostic = out / (label + '.diag')
            diagnostic.unlink(missing_ok=True)
            log = run([binary, *common, '+fs-driver-cut=3', *options,
                       f'+fs-driver-diagnostic={diagnostic}'], out / (label + '.log'), out, expected=1)
            require(message in log and not diagnostic.exists()
                    and not Path(str(diagnostic) + '.tmp').exists(), 'lowclock configuration failed open')
            negatives.append(label)
    terminal = verify_terminal(binary, out / 'terminal', args.lowclock)
    summary = dict(terminal=terminal, scope='coherent generated/software/harness diagnostic at parked driver; no whole runtime restore',
                   cases=cases, negative_requests=negatives, whole_runtime_restore_verified=False,
                   physical_fpga_validated=False)
    summary['sample_phase'] = 'settled_host_negedge_parked_driver' if args.lowclock else 'settled_host_posedge_parked_driver'
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
