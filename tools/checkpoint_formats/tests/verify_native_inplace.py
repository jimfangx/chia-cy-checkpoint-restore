"""In-place native bank integration; localhost Vivado and EDA-only VCS.

This bounded integration regression establishes no complete Rocket ownership,
checkpoint-enabled AFI, physical capture or CPU migration acceptance.
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
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_clock_cut_bank import audit as audit_network
from tools.checkpoint_formats.tests.verify_native_clock_cut_bank import SOURCES as NETWORK_SOURCES
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, selectors

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
PREFIX = 'FireSim-generated'
PORT_PREFIX = 'checkpoint_inplace_'
SOURCES = tuple(sorted(set(NETWORK_SOURCES + (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointInPlace.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointInPlaceSpec.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/MultipleFunctionalClocksSpec.scala',
    'tools/checkpoint_formats/tests/verify_native_inplace.py',
    'tools/checkpoint_formats/tests/native_inplace_fixture.sv',
    'tools/checkpoint_formats/tests/native_inplace_tb.sv'))))
TCL = '''set_param general.maxThreads 4
read_verilog -sv generated/instrumented.sv sources/CheckpointPhysicalClockCut.sv sources/native_inplace_fixture.sv
synth_design -top NativeInPlaceFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "duplicate or omitted functional execution/gates"}
foreach name {host/stage/network/checkpoint_physical_root_gate host/stage/network/left_/gate host/stage/network/right_/gate} {
  if {[llength [get_cells $name]] != 1} {error "existing instance path changed $name"}
}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed native clock semantics"}}
set raw [get_nets -of_objects [get_ports clock]]
set raw_registers 0
foreach pattern {host/host_ticks_reg* host/stage/control_ticks_reg* *ckpt_pending_reg *ckpt_saved_data_reg* *ckpt_saved_error_reg} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing ungated state $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "masked ancestor or access register $cell"}
    incr raw_registers
  }
}
if {$raw_registers != 194} {error "incomplete raw ancestor/access register audit $raw_registers"}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "missing unique falling-edge mask"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-inplace.dcp
puts "NATIVE_INPLACE_SYNTH_PASS raw_registers=$raw_registers gates=3"
'''


def normalized(body):
    return '\n'.join(line.strip() for line in body.splitlines() if line.strip())


def audit(generated):
    """Reconstruct all added ports/connections and preserve every original body.

    The selected bank and native clock network are independently reconstructed
    by the existing complete network auditor, then matched to the actual host.
    Coherently rehashed changes are checked structurally, not trusted as hashes.
    """
    generated = Path(generated)
    network = audit_network(generated)
    host_text = (generated / 'host.fir').read_text()
    instrumented = (generated / 'instrumented.fir').read_text()
    host = parse_modules(host_text)
    actual = parse_modules(instrumented)
    selected = parse_modules((generated / (PREFIX + '.native-clock-cut.fir')).read_text())
    reference = parse_modules((generated / (PREFIX + '.native-functional-reference.fir')).read_text())
    require(all(host.get(name) == module for name, module in reference.items()),
            'selected reference differs from the original executing subtree')
    binding = json.loads((generated / 'binding.json').read_text())
    source_doc = json.loads((generated / (PREFIX + '.native-functional-simulator-state.json')).read_text())
    clock_plan = json.loads((generated / (PREFIX + '.native-functional-plan.json')).read_text())
    selected_root = source_doc['root_module']
    raw_ports = selected[selected_root]['ports']
    access = {k: v for k, v in raw_ports.items() if k not in reference[selected_root]['ports'] and k != 'ckpt_clock'}
    target = binding['target']
    parsed = re.fullmatch(r'~(\w+)\|(\w+)((?:/\w+:\w+)+)', target)
    require(parsed and parsed[1] == parsed[2], 'in-place target is not root-relative')
    root = parsed[1]
    path = re.findall(r'/(\w+):(\w+)', parsed[3])
    require(path[-1][1] == selected_root, 'selected root differs from actual path')
    parents = []
    current = root
    for index, (instance, child) in enumerate(path):
        require(host[current]['instances'].get(instance) == child, 'stale original target path')
        parents.append((current, instance, index == len(path) - 1))
        current = child
    source = clock_plan['common_source_clock']
    for name, child, _ in reversed(parents):
        drivers = host[name]['drivers']
        source = drivers.get(child + '.' + source)
        seen = set()
        while source in drivers:
            require(source not in seen, 'raw clock alias cycle')
            seen.add(source)
            source = drivers[source]
        require(host[name]['ports'].get(source) == ('input', 'Clock'), 'raw clock is not a transparent ancestor input')
    expected = dict(binding_version=1, scope='existing_instance_native_banks_only',
        target=target,
        host_sha256=sha(generated / 'host.fir'),
        reference_sha256=sha(generated / (PREFIX + '.native-functional-reference.fir')),
        bank_binding_sha256=sha(generated / (PREFIX + '.native-functional-binding.json')),
        wiring_binding_sha256=sha(generated / (PREFIX + '.native-clock-cut.json')),
        instrumented_sha256=sha(generated / 'instrumented.fir'),
        enclosing_raw_clock=source, selected_raw_clock=clock_plan['common_source_clock'], endpoint_raw_clock='ckpt_clock',
        sideband_ports=[dict(selected=k, enclosing=PORT_PREFIX + k, direction=v[0], type=v[1]) for k, v in access.items()],
        complete_fpga_capture=False, deployable_capture_image=False,
        production_freeze_owners_bound=False, metasim_restore_supported=False)
    require(binding == expected, 'changed in-place binding, ports or ownership claim')
    require(actual.keys() == host.keys() | selected.keys(), 'added/lost enclosing module definitions')
    for name, module in actual.items():
        if name in selected:
            require(normalized(module['body']) == normalized(selected[name]['body']), 'changed selected native network ' + name)
        elif name not in {p[0] for p in parents}:
            require(module == host[name], 'changed unrelated original module ' + name)
    if (generated / 'instrumented.sv').is_file():
        def verilog_modules(text):
            return {m[1]: m[0].strip() for m in re.finditer(r'^module (\w+)\b.*?^endmodule', text, re.M | re.S)}
        emitted = verilog_modules((generated / 'instrumented.sv').read_text())
        network_rtl = verilog_modules((generated / (PREFIX + '.native-clock-cut.sv')).read_text())
        require(all(emitted.get(name) == body for name, body in network_rtl.items()),
                'actual host RTL differs from the separately audited native emission')
    for name, child, immediate in parents:
        original, result = host[name], actual[name]
        ports = dict(original['ports'], **{PORT_PREFIX + k: v for k, v in access.items()})
        require(result['ports'] == ports and result['instances'] == original['instances'], 'duplicate execution or changed parent ports')
        connections = {}
        for key, (direction, _) in access.items():
            pin = child + '.' + (key if immediate else PORT_PREFIX + key)
            exposed = PORT_PREFIX + key
            connections[pin if direction == 'input' else exposed] = exposed if direction == 'input' else pin
        if immediate:
            source = original['drivers'][child + '.' + clock_plan['common_source_clock']]
            while source in original['drivers']:
                source = original['drivers'][source]
            connections[child + '.ckpt_clock'] = source
        require(result['drivers'] == dict(original['drivers'], **connections), 'changed ancestor or sideband connectivity ' + name)
        require(result['consumers'] == original['consumers'] and result['effects'] == original['effects'], 'changed ancestor clocks/effects')
        # Also compare the complete serialized body, so new unparsed statements
        # cannot escape the connectivity/consumer dictionaries above.
        stripped = result['body'].splitlines()
        remove = {f'{lhs} <= {rhs}' for lhs, rhs in connections.items()}
        stripped = [line for line in stripped if not re.match(r'\s*(input|output) ' + PORT_PREFIX, line)
                    and line.strip() not in remove]
        require(normalized('\n'.join(stripped)) == normalized(original['body']), 'changed original ancestor statement ' + name)
    raw_bits = sum(int(width) for name, _, _ in parents for width in
                   re.findall(r'\breg \w+ : UInt<(\d+)>', host[name]['body']))
    return dict(network=network, original_execution_instances=1, raw_ancestor_register_bits=raw_bits,
                routed_sideband_ports=len(access), modules=len(actual))


def corruptions(generated, out):
    rejected = []
    mutations = (
        ('masked-access', 'network.ckpt_clock <= clock', 'network.ckpt_clock <= asClock(checkpoint_inplace_ckpt_freeze)'),
        ('masked-parent', 'reg control_ticks : UInt<64>, clock', 'reg control_ticks : UInt<64>, asClock(checkpoint_inplace_ckpt_freeze)'),
        ('wrong-freeze', 'network.ckpt_freeze <= checkpoint_inplace_ckpt_freeze', 'network.ckpt_freeze <= UInt<1>(0)'),
        ('wrong-reset', 'network.ckpt_reset <= checkpoint_inplace_ckpt_reset', 'network.ckpt_reset <= reset'),
        ('changed-original', 'control_ticks <= mux(reset, UInt<64>("h0"), bits(add(control_ticks, UInt<1>("h1")), 63, 0))',
         'control_ticks <= UInt<64>(0)'),
        ('duplicate-execution', 'inst stage of Stage', 'inst stage of Stage\n    inst duplicate of Stage'),
    )
    for name, before, after in mutations:
        directory = out / name
        shutil.copytree(generated, directory)
        path = directory / 'instrumented.fir'
        text = path.read_text()
        require(before in text, 'ineffective in-place mutation ' + name)
        path.write_text(text.replace(before, after, 1))
        binding = json.loads((directory / 'binding.json').read_text())
        binding['instrumented_sha256'] = sha(path)
        (directory / 'binding.json').write_text(json.dumps(binding))
        try:
            audit(directory)
        except ValueError as error:
            rejected.append(dict(name=name, error=str(error)))
        else:
            raise ValueError('coherent in-place corruption accepted: ' + name)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    for name in ('generated', 'native', 'eda', 'out'):
        parser.add_argument('--' + name, type=Path, required=name == 'out')
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    sources = {name: sha(ROOT / name) for name in SOURCES}
    commands = []

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + '.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            proc = subprocess.run(row['argv'], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = proc.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(proc.returncode == expected, 'inspect underlying log ' + row['log'])
        return Path(row['log']).read_text()

    def validate(path, backend):
        require(path is not None and path.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((path / 'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources and
                doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False,
                'stale or wrong-scope in-place receipt')
        for group in ('inputs', 'artifacts'):
            for name, value in doc[group].items():
                require(sha(path / name) == value, 'changed retained evidence ' + name)
        audit(path / 'generated')
        require((path / 'synth.tcl').read_text() == TCL, 'changed native synthesis scope')
        for name in SOURCES:
            require(sha(path / 'sources' / Path(name).name) == sources[name], 'changed retained source ' + name)
        binding = json.loads((path / 'generated' / (PREFIX + '.native-functional-binding.json')).read_text())
        require((path / 'native-selectors.svh').read_text() == selectors(binding), 'changed independent word oracle')
        return doc

    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        sources=sources, physical_fpga_capture=False, production_rocket_integrated=False,
        scope='existing native instance integration with raw parent execution; no complete CPU ownership or capture admission')
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        shutil.copytree(args.generated, out / 'generated')
        summary['audit'] = audit(out / 'generated')
        summary['rejected_corruptions'] = corruptions(out / 'generated', out / 'corruptions')
        for name in SOURCES:
            dest = out / 'sources' / Path(name).name
            require(not dest.exists(), 'source basename collision')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
        for name, source in (('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')):
            shutil.copyfile(source, out / name)
        binding = json.loads((out / 'generated' / (PREFIX + '.native-functional-binding.json')).read_text())
        (out / 'native-selectors.svh').write_text(selectors(binding))
        (out / 'synth.tcl').write_text(TCL)
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('NATIVE_INPLACE_SYNTH_PASS raw_registers=194 gates=3' in text and
                not re.search(r'ERROR:|CRITICAL WARNING:', text), 'incomplete native synthesis')
        summary['artifacts'] = {name: sha(out / name) for name in
            ('native-inplace.dcp', 'utilization.rpt', 'timing.rpt', 'synth.log', 'commands.json')}
    elif args.mode == 'vcs':
        require(shutil.which('vcs') == toolchain.VCS and toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 required')
        native = validate(args.native, 'f2')
        for name in native['inputs']:
            dest = out / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.native / name, dest)
        summary['inputs'] = native['inputs']
        files = ['generated/instrumented.sv', 'generated/NativeReference.sv',
            'sources/CheckpointPhysicalClockCut.sv', 'sources/native_inplace_fixture.sv',
            'BUFGCE.v', 'glbl.v', 'sources/native_inplace_tb.sv', 'sources/checkpoint_widget_exit.cc']
        common = [toolchain.VCS, '-full64', '-sverilog', '-debug_access+all', '-timescale=1ns/1ps',
            '-Mupdate', '+incdir+' + str(out), '-top', 'native_inplace_tb', '-top', 'glbl']
        run([*common, '-Mdir=csrc', '-o', 'simv', *files], 'compile')
        text = run([out / 'simv', '-no_save'], 'run')
        match = re.search(r'NATIVE_INPLACE_BANK_PASS checks=(\d+) cuts=4 words=128 stalls=(\d+) cycle=(\d+)', text)
        require(match and len(re.findall(r'NATIVE_INPLACE_WORD cut=', text)) == 128, 'incomplete in-place bank execution')
        shutil.move(out / 'native-inplace.vcd', out / 'healthy.vcd')
        for fault, expected in (('corrupt', 1), ('missing-owner', 0), ('ce-drift', 0)):
            text = run([out / 'simv', '-no_save', '+' + fault], fault, expected)
            require(('reason=latched exact bank word/error' if fault == 'corrupt' else
                'NATIVE_INPLACE_REJECTED kind=' + fault) in text, 'negative did not reject at expected boundary')
            shutil.move(out / 'native-inplace.vcd', out / (fault + '.vcd'))
        original = (out / files[0]).read_text()
        changed = original.replace('assign checkpoint_physical_root_gate_CE = ~checkpoint_physical_mask;',
            "assign checkpoint_physical_root_gate_CE = 1'b1;", 1)
        require(changed != original, 'ineffective physical mask mutation')
        (out / 'fault.sv').write_text(changed)
        run([*common, '-Mdir=fault-csrc', '-o', 'fault-simv', 'fault.sv', *files[1:]], 'fault-compile')
        bad = run([out / 'fault-simv', '-no_save'], 'wiring-negative', 1)
        require('reason=physical root clock stopped' in bad, 'physical mask bypass escaped independent oracle')
        shutil.move(out / 'native-inplace.vcd', out / 'wiring-negative.vcd')
        stage = re.search(r'^module Stage\b.*?^endmodule', original, re.M | re.S)
        require(stage and stage[0].count('always @(posedge clock) begin') == 1, 'ambiguous parent control update')
        masked_parent = stage[0].replace('always @(posedge clock) begin',
            'always @(posedge clock) if (!checkpoint_inplace_checkpoint_physical_mask) begin', 1)
        (out / 'parent-fault.sv').write_text(original[:stage.start()] + masked_parent + original[stage.end():])
        run([*common, '-Mdir=parent-fault-csrc', '-o', 'parent-fault-simv', 'parent-fault.sv', *files[1:]], 'parent-fault-compile')
        bad = run([out / 'parent-fault-simv', '-no_save'], 'parent-clock-negative', 1)
        require('reason=both existing ancestor control counters continue on raw clock' in bad and
                'NATIVE_INPLACE_WORD' not in bad, 'masked parent advanced through first cut/readout')
        shutil.move(out / 'native-inplace.vcd', out / 'parent-clock-negative.vcd')
        for name in ('healthy', 'corrupt', 'missing-owner', 'ce-drift', 'wiring-negative', 'parent-clock-negative'):
            wave = out / (name + '.vcd')
            require(wave.stat().st_size > 2000 and re.search(r'#[1-9]\d*', wave.read_text()), 'empty execution waveform')
        summary['checks'], summary['stalls'], summary['last_cycle'] = map(int, match.groups())
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()
            and (p.suffix in ('.log', '.vcd', '.sv') or p.name == 'commands.json') and 'csrc' not in str(p)}
    else:
        native = validate(args.native, 'f2')
        eda = validate(args.eda, 'eda')
        require(native['inputs'] == eda['inputs'], 'native/EDA execution inputs differ')
        summary.update(matched_inputs=len(native['inputs']), checks=eda['checks'], last_cycle=eda['last_cycle'], inputs={}, artifacts={})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
