"""Native bank/clock attachment through actual FPGATop AXI/MMIO/CPU DMA.

Fixture evidence only. No production Rocket ownership, AFI or FPGA capture.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_native_checkpoint_widget import (
    SOURCES as WIDGET_SOURCES, TCL as WIDGET_TCL, PREFIX, audit, audit_frames, manifest_header)
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, selectors
from tools.checkpoint_formats.tests.audit_native_inplace_access import audit as audit_inplace
from tools.checkpoint_formats.tests.verify_native_inplace_access import SOURCES as INPLACE_SOURCES, TCL as INPLACE_TCL

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
SOURCES = tuple(sorted(set(WIDGET_SOURCES + INPLACE_SOURCES + (
    'sims/firesim/sim/midas/src/main/scala/midas/core/FPGATop.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/core/CheckpointCaptureTop.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/core/NativeCheckpointCapture.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/core/CheckpointCaptureTopSpec.scala',
    'tools/checkpoint_formats/tests/native_checkpoint_top_tb.sv',
    'tools/checkpoint_formats/tests/native_inplace_top_tb.sv',
    'tools/checkpoint_formats/tests/verify_native_checkpoint_top.py',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'))))
RTL = ('FPGATop.v', 'NativeStorageCheckpointStateAccess.sv', 'CheckpointCaptureTransport.sv',
       'CheckpointCaptureCut.sv', 'CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv')
STUB = ('module TargetBox(input hostClock,input hostReset,input clock_valid,input clock_bits,'
        'output clock_ready); assign clock_ready=1\'b1; endmodule\n')
TCL = ('set_param general.maxThreads 4\nread_verilog -sv ' +
       ' '.join('generated/' + n for n in RTL) + ' target-clock-sink.sv\n'
       'synth_design -top FPGATop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none\n'
       'create_clock -name raw_clock -period 7.142857 [get_ports clock]\n' +
       WIDGET_TCL[WIDGET_TCL.index('current_instance access'):]
       .replace('current_instance access', 'current_instance nativeCapture')
       .replace('access/network', 'nativeCapture/network').replace('native-widget.dcp', 'native-top.dcp') +
       '''set raw_control_registers 0
foreach pattern {CheckpointCaptureWidget_*/* CPUManagedStreamEngine_*/* ctrlInterconnect/*} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing control/stream registers $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "masked control/DMA register $cell"}
    incr raw_control_registers
  }
}
puts "NATIVE_TOP_RAW_CONTROL_PASS registers=$raw_control_registers"
''' +
       'puts "NATIVE_TOP_SYNTH_PASS raw_transport_and_cpu_dma=1"\n')


def audit_attachment(generated, in_place=False):
    access = generated / 'access' if in_place else generated
    result = audit_inplace(access) if in_place else audit(generated)
    module = 'NativeHostCheckpointStateAccess' if in_place else 'NativeStorageCheckpointStateAccess'
    inline = (generated / (module + '.sv')).read_text()
    if in_place:
        expected = (access / 'instrumented.sv').read_text() + '\n' + '\n'.join(
            (access / (PREFIX + suffix)).read_text() for suffix in
            ('.native-inplace-access.sv', '.native-inplace-access-router.sv', '.native-inplace-access-ce.sv'))
        # Both annotation placements are actual Scala emissions from the same
        # source. Check complete XDC bytes after their concrete host rebase.
        for kind in ('synthesis', 'implementation'):
            suffix = '.native-state-access.' + kind + '.xdc'
            require((generated / 'attachment' / (PREFIX + suffix)).read_text() ==
                    (access / (PREFIX + suffix)).read_text().replace('host/', 'nativeCapture/'),
                    'changed in-place original constraints ' + kind)
        bound = json.loads((generated / 'attachment' / (PREFIX + '.native-state-access-constraints.json')).read_text())
        original = json.loads((access / (PREFIX + '.native-state-access-constraints.json')).read_text())
        expected_bound = dict(original)
        for key in ('original_pre_link_path', 'original_post_link_path', 'rebased_pre_link_path', 'rebased_post_link_path'):
            if key in expected_bound and isinstance(expected_bound[key], str):
                expected_bound[key] = expected_bound[key].replace('host', 'nativeCapture')
        expected_bound['inputs'] = {key: sha(generated / 'attachment' / (PREFIX + key)) for key in original['inputs']}
        require(bound == expected_bound, 'changed in-place constraint placement binding')
    else:
        expected = (generated / (PREFIX + '.native-clock-cut.sv')).read_text() + '\n' + \
            (generated / (PREFIX + '.native-descriptors-physical-bank.sv')).read_text() + '\n' + \
            '\n'.join((generated / (PREFIX + s)).read_text() for s in
                      ('.native-state-access.sv', '.native-state-access-router.sv'))
    require(inline == expected, 'inline native network differs from independently audited emission')
    rtl = (generated / 'FPGATop.v').read_text()
    match = re.search(re.escape(module) + r' nativeCapture\s*\((.*?)\);', rtl, re.S)
    require(match, 'native attachment absent from actual FPGATop')
    pins = dict(re.findall(r'\.(\w+)\((\w+)\)', match[1]))
    # Follow FPGATop wire aliases independently; never trust a callback's claim.
    aliases = dict(re.findall(r'assign\s+(\w+)\s*=\s*(\w+)\s*;', rtl[rtl.index('module FPGATop('):]))
    def follow(name):
        seen = set()
        while name in aliases:
            require(name not in seen, 'attachment alias cycle')
            seen.add(name)
            name = aliases[name]
        return name
    require(follow(pins['clock']) == 'clock', 'native endpoint lost raw FPGATop clock')
    for name in ('reset', 'enable', 'address', 'data', 'write', 'cycle', 'left_count', 'right_count', 'read_data') + (('host_ticks_out', 'control_ticks_out') if in_place else ()):
        require(follow(pins[name]) == follow('native_' + name), 'changed original functional port ' + name)
    widget = re.search(r'CheckpointCaptureWidget\s+\w+\s*\((.*?)\);', rtl[rtl.index('module FPGATop('):], re.S)
    require(widget, 'registered checkpoint widget missing')
    wpins = dict(re.findall(r'\.(\w+)\((\w+)\)', widget[1]))
    require(follow(wpins['clock']) == 'clock' and follow(wpins['reset']) == 'reset', 'widget raw clock/reset changed')
    connections = {
        'capture_reset': 'capture_controllerReset', 'capture_clock_mask': 'capture_physical_clockMask',
        'capture_read_enable': 'capture_physical_readEnable', 'capture_captured_ce': 'capture_physical_capturedCE',
        'capture_logical_ce': 'capture_physical_logicalCE', 'capture_descriptor_entry': 'capture_descriptorEntry',
        'capture_request_valid': 'capture_bankRequestValid', 'capture_request_ready': 'capture_bankRequestReady',
        'capture_bank': 'capture_bank', 'capture_slot': 'capture_slot', 'capture_address': 'capture_address',
        'capture_response_valid': 'capture_bankResponseValid', 'capture_response_ready': 'capture_bankResponseReady',
        'capture_response_data': 'capture_bankResponseData', 'capture_response_error': 'capture_bankResponseError'}
    for net, widget_port in connections.items():
        require(follow(pins[net]) == follow(wpins[widget_port]), 'changed native/widget attachment ' + net)
    header = (generated / 'top_constants.h').read_text()
    prefix, base = re.search(r'#define (CHECKPOINTCAPTUREWIDGET_\d+)_BASE (\d+)ULL', header).groups()
    descriptor_binding = '.native-inplace-access-descriptor-binding.json' if in_place else '.native-descriptors-binding.json'
    require(f'{prefix}_DESCRIPTOR_BINDING_SHA256 "{sha(access / (PREFIX + descriptor_binding))}"' in header,
            'top driver binding mismatch')
    streams = re.findall(r'CPUManagedStreams::StreamParameters\(\s*std::string\(R"ESC\((.*?)\)ESC"\),\s*(\d+)ULL,\s*(\d+)ULL,\s*(\d+),\s*(\d+)', header)
    require(len(streams) == 2 and streams[1][0] == prefix + '_to_cpu_stream' and streams[1][3:] == ('2', '64') and
            f'{prefix}_TO_HOST_STREAM_IDX 1U' in header, 'checkpoint not appended to actual CPU stream engine')
    return dict(audit=result, capture_base=int(base), dma_address=int(streams[1][1]), stream_count=int(streams[1][2]))


def corruptions(generated, out, in_place=False):
    rejected = []
    pins = (('clock', 'native_mask'), ('capture_reset', 'native_reset'),
                             ('capture_clock_mask', 'native_read_enable'),
                             ('capture_response_ready', 'native_mask'), ('reset', 'reset'))
    if in_place:
        pins += (('host_ticks_out', 'native_cycle'), ('control_ticks_out', 'native_cycle'))
    for pin, replacement in pins:
        directory = out / pin; shutil.copytree(generated, directory)
        path = directory / 'FPGATop.v'; rtl = path.read_text()
        module = 'NativeHostCheckpointStateAccess' if in_place else 'NativeStorageCheckpointStateAccess'
        match = re.search(re.escape(module) + r' nativeCapture\s*\((.*?)\);', rtl, re.S)
        changed = re.sub(r'\.' + pin + r'\(\w+\)', '.' + pin + '(' + replacement + ')', match[0])
        require(changed != match[0], 'ineffective native top corruption ' + pin)
        path.write_text(rtl[:match.start()] + changed + rtl[match.end():])
        try:
            audit_attachment(directory, in_place)
        except ValueError as error:
            rejected.append(dict(name=pin, error=str(error)))
        else:
            raise AssertionError('accepted changed native top connection ' + pin)
    if in_place:
        for name in ('inline-extra-driver', 'global-descriptor-driver', 'coherent-xdc'):
            directory = out / name
            shutil.copytree(generated, directory)
            if name == 'inline-extra-driver':
                path = directory / 'NativeHostCheckpointStateAccess.sv'
                path.write_text(path.read_text() + '\nassign invented = 1;\n')
            elif name == 'global-descriptor-driver':
                path = directory / 'top_constants.h'
                path.write_text(re.sub(r'(DESCRIPTOR_BINDING_SHA256 ")[0-9a-f]{64}', r'\g<1>' + '0'*64, path.read_text()))
            else:
                suffix = '.native-state-access.implementation.xdc'
                path = directory / 'attachment' / (PREFIX + suffix)
                path.write_text(path.read_text().replace('left_/gate', 'right_/gate', 1))
                binding = directory / 'attachment' / (PREFIX + '.native-state-access-constraints.json')
                doc = json.loads(binding.read_text()); doc['inputs'][suffix] = sha(path)
                binding.write_text(json.dumps(doc))
            try:
                audit_attachment(directory, in_place)
            except ValueError as error:
                rejected.append(dict(name=name, error=str(error)))
            else:
                raise AssertionError('accepted in-place attachment mutation ' + name)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in-place', action='store_true')
    parser.add_argument('--in-place-source', type=Path)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    for name in ('generated', 'native', 'eda', 'out'):
        parser.add_argument('--' + name, type=Path, required=name == 'out')
    args = parser.parse_args()
    rtl_files = tuple('NativeHostCheckpointStateAccess.sv' if n == 'NativeStorageCheckpointStateAccess.sv' and args.in_place else n for n in RTL)
    testbench = 'native_inplace_top_tb.sv' if args.in_place else 'native_checkpoint_top_tb.sv'
    tcl = TCL
    if args.in_place:
        core = INPLACE_TCL[INPLACE_TCL.index('set gates [get_cells'):]
        core = core.replace('host/network/', 'nativeCapture/network/').replace('native-inplace-access.dcp', 'native-top.dcp')
        controls = TCL[TCL.index('set raw_control_registers 0'):]
        tcl = ('set_param general.maxThreads 4\nread_verilog -sv ' +
               ' '.join('generated/' + n for n in rtl_files) + ' target-clock-sink.sv\n' +
               'read_xdc generated/attachment/FireSim-generated.native-state-access.synthesis.xdc\n' +
               'synth_design -top FPGATop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none\n' +
               'source generated/attachment/FireSim-generated.native-state-access.implementation.xdc\n' +
               'create_clock -name raw_clock -period 7.142857 [get_ports clock]\n' + core + controls)
    attachment = lambda path: audit_attachment(path, args.in_place)
    access_dir = lambda path: path / 'access' if args.in_place else path
    descriptor_suffix = '.native-inplace-access-descriptors.json' if args.in_place else '.native-descriptors.json'
    frame_audit = lambda path, lines: audit_frames(access_dir(path), lines, descriptor_suffix)

    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    commands = []
    def run(argv, name, cwd=out, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(out / (name + '.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            process = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = process.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(process.returncode == expected, 'inspect underlying log ' + row['log'])
        return Path(row['log']).read_text()
    def validate(path, backend):
        require(path is not None and path.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((path / 'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources and
                doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False and doc.get('in_place_component', False) == args.in_place,
                'stale/wrong-scope native top receipt')
        for group in ('inputs', 'artifacts'):
            for name, value in doc[group].items():
                require((path / name).stat().st_size > 0 and sha(path / name) == value, 'changed native top evidence ' + name)
        require((path / 'synth.tcl').read_text() == tcl, 'changed native synthesis recipe')
        require(attachment(path / 'generated') == doc['attachment'], 'changed native top attachment')
        return doc
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2', sources=sources,
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
                   scope='native clock/bank fixture attached through actual FPGATop MMIO/CPU DMA; production ownership pending',
                   physical_fpga_capture=False, production_rocket_integrated=False, in_place_component=args.in_place)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost Vivado required')
        require(args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        shutil.copytree(args.generated, out / 'generated')
        if args.in_place:
            require(args.in_place_source and args.in_place_source.resolve().is_relative_to(RUNS), 'in-place source below runs required')
            shutil.copytree(args.in_place_source, out / 'generated/access')
        summary['attachment'] = attachment(out / 'generated')
        summary['rejected_corruptions'] = corruptions(out / 'generated', out / 'corruptions', args.in_place)
        for name in SOURCES:
            dest = out / 'sources' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (out / 'target-clock-sink.sv').write_text(STUB)
        (out / 'synth.tcl').write_text(tcl)
        vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
        summary['vendor_models'] = {}
        for name, source in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
            shutil.copyfile(source, out / name)
            summary['vendor_models'][name] = dict(original_path=str(source), sha256=sha(source))
        bank = json.loads((access_dir(out / 'generated') / (PREFIX + '.native-functional-binding.json')).read_text())
        (out / 'native-selectors.svh').write_text(selectors(bank))
        (out / 'native-widget-manifest.svh').write_text(manifest_header(access_dir(out / 'generated'), descriptor_suffix))
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and 'corruptions' not in p.relative_to(out).parts}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('NATIVE_TOP_SYNTH_PASS raw_transport_and_cpu_dma=1' in text and
                ('NATIVE_INPLACE_ACCESS_SYNTH_PASS' in text if args.in_place else 'NATIVE_CONSTRAINTS_PASS queries=6 scope=nativeCapture/network' in text) and
                not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native top synthesis failed')
        summary['artifacts'] = {n: sha(out / n) for n in ('native-top.dcp', 'utilization.rpt', 'timing.rpt', 'synth.log', 'commands.json')}
    elif args.mode == 'vcs':
        require(shutil.which('vcs') == toolchain.VCS and toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 VCS required')
        native = validate(args.native, 'f2')
        for name in native['inputs']:
            dest = out / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.native / name, dest)
        summary.update(attachment=attachment(out / 'generated'), inputs=native['inputs'], vendor_models=native['vendor_models'])
        rtl = (out / 'generated/FPGATop.v').read_text()
        top = re.search(r'module FPGATop\((.*?)\);', rtl, re.S).group(1)
        ports = re.findall(r'(input|output)\s*(\[\d+:\d+\])?\s*(\w+)', re.sub(r'//[^\n]*', '', top))
        declarations = [f'{"reg" if d == "input" else "wire"} {width} {name}{"=0" if d == "input" else ""};' for d, width, name in ports]
        declarations.append('FPGATop dut(' + ','.join(f'.{n}({n})' for _, _, n in ports) + ');')
        (out / 'top_ports.svh').write_text('\n'.join(declarations) + '\n')
        binding = summary['attachment']
        (out / 'top_bindings.svh').write_text(f'localparam [31:0] CAPTURE_BASE={binding["capture_base"]},STREAM_COUNT={binding["stream_count"]};\n'
                                              f'localparam [63:0] CAPTURE_DMA={binding["dma_address"]};\n')
        files = [out / 'generated' / n for n in rtl_files] + [out / n for n in ('BUFGCE.v', 'glbl.v', 'target-clock-sink.sv')] + [
            out / 'sources/tools/checkpoint_formats/tests' / n for n in (testbench, 'checkpoint_generated_network_exit.cc')]
        common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                  '+incdir+' + str(out), '-top', 'native_checkpoint_top_tb', '-top', 'glbl']
        run([*common, '-Mdir=csrc', '-o', 'simv', *files], 'compile')
        healthy = out / 'healthy'; healthy.mkdir()
        text = run([out / 'simv', '-no_save'], 'healthy', healthy)
        match = re.search(r'NATIVE_TOP_PASS checks=(\d+) cuts=5 words=170 stalls=(\d+) recovered_cycle=(\d+)', text)
        require(match and int(match[2]) > 100 and int(match[3]) >= 200, 'incomplete native top execution')
        summary.update(checks=int(match[1]), cuts=5, words=170, dma_stalls=int(match[2]), recovered_cycle=int(match[3]),
                       frame_audits=[frame_audit(out / 'generated', (healthy / f'capture-{i}.hex').read_text().splitlines()) for i in range(5)])
        for fault in ('missing', 'cycle'):
            work = out / fault; work.mkdir()
            text = run([out / 'simv', '-no_save', '+fault=' + fault], fault, work)
            require('NATIVE_TOP_REJECT fault=' + fault in text and 'acknowledged_edges=0' in text, 'failed native cut escaped')
        work = out / 'corrupt'; work.mkdir()
        text = run([out / 'simv', '-no_save', '+corrupt'], 'corrupt', work, expected=1)
        require('frame=1 frozen=1 reason=independent native bank and CE payload' in text, 'corruption escaped first word')
        original = files[1].read_text()
        site = '.captured_ce(capture_captured_ce)'
        require(original.count(site) == 1, 'ambiguous CE wiring mutation')
        mutation = out / 'mutated-native.sv'; mutation.write_text(original.replace(site, '.captured_ce(~capture_captured_ce)'))
        run([*common, '-Mdir=fault-csrc', '-o', 'fault-simv', files[0], mutation, *files[2:]], 'mutated-compile')
        work = out / 'mutated'; work.mkdir()
        text = run([out / 'fault-simv', '-no_save'], 'mutated', work, expected=1)
        require('reason=independent native bank and CE payload' in text, 'misconnected CE escaped payload oracle')
        summary['negative_tests'] = ['missing', 'cycle', 'corrupt', 'mutated']
        for name in ['healthy', *summary['negative_tests']]:
            wave = out / name / 'native-top.vcd'
            require(wave.stat().st_size > 2000 and re.search(r'#[1-9]\d*', wave.read_text()), 'missing debug wave')
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log', '.vcd', '.hex', '.svh')}
    else:
        native = validate(args.native, 'f2'); eda = validate(args.eda, 'eda')
        require(native['inputs'] == eda['inputs'] and native['attachment'] == eda['attachment'] and
                eda['negative_tests'] == ['missing', 'cycle', 'corrupt', 'mutated'] and eda['cuts'] == 5 and eda['words'] == 170,
                'incomplete native/EDA matching')
        require(eda['frame_audits'] == [frame_audit(args.eda / 'generated', (args.eda / 'healthy' / f'capture-{i}.hex').read_text().splitlines())
                                      for i in range(5)], 'changed independent complete-word audits')
        summary.update(matched_inputs=len(native['inputs']), matched_sources=len(sources), checks=eda['checks'], inputs={}, artifacts={})
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, 'source changed during verification')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
