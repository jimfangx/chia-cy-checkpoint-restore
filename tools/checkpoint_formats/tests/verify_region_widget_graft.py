"""Native synthesis and EDA-only VCS for sibling regions on the real widget.

This is a bounded transport component. Opaque transport, enclosing and host state
remain unsupported; neither a deployable image nor hardware capture is claimed.
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
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.tests.verify_widget_graft import (
    ROOT, RUNS, TESTS, RTL, sha, source_files, header_parameters)
from tools.checkpoint_formats.tests.verify_native_checkpoint_top import STUB
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_widget_graft import instances
from tools.checkpoint_formats.tests.audit_widget_annotations import HEADER


def sources():
    return tuple(sorted(set(source_files()) | {
        'tools/checkpoint_formats/tests/region_widget_tb.sv',
        'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegionWidgetGraftSpec.scala'}))


def rows(directory):
    result = json.loads((directory/'manifest.json').read_text())['state']
    require(len(result) == 14 and sum(r['depth'] for r in result) == 68 and
            {r['region'] for r in result} == {0, 1}, 'wrong sibling fixture geometry')
    return result


def verilog(directory):
    return ['generated/connected.sv'] + [
        'generated/'+p.name for p in sorted(directory.glob('graft*.sv'))] + [
        'sources/'+n for n in RTL] + ['target-clock-sink.sv']


def headers(directory):
    text = (directory/'connected.sv').read_text()
    top = re.search(r'module ReservationShell\((.*?)\);', text, re.S)
    require(top, 'actual enclosing shell missing')
    ports = re.findall(r'(input|output)\s*(\[\d+:\d+\])?\s*(\w+)',
                       re.sub(r'//[^\n]*', '', top[1]))
    require(len(ports) > 30 and len({p[2] for p in ports}) == len(ports), 'invalid root interface')
    port_text = '\n'.join(f'{"reg" if d=="input" else "wire"} {w} {n}{"=0" if d=="input" else ""};'
                          for d, w, n in ports)
    port_text += '\nReservationShell dut('+','.join(f'.{n}({n})' for _, _, n in ports)+');\n'
    params = header_parameters(directory)
    lines = [f'localparam [63:0] {k.upper()}={v};' for k, v in params.items()]
    lines += ["localparam [255:0] EXPECTED_MANIFEST=256'h"+'f'*64+';',
              'localparam integer ENTRIES=14, WORDS=68, FRAMES=70;']
    for suffix, width in [('reservedCycle', '[63:0]'), ('reservedPresent', '[1:0]'),
                          ('reservedFrozen', '[1:0]'), ('reservedError', '[1:0]'), ('reservedFreeze', '')]:
        found = [n for _, w, n in ports if w == width and (n == suffix or n.endswith('_'+suffix))]
        require(len(found) == 1, 'ambiguous actual owner port '+suffix)
        lines.append(f'`define {suffix.upper()} {found[0]}')
    peer = json.loads((directory/'peer-routing.json').read_text())
    transport = 'dut.'+'.'.join(peer['transport'].split('.')[1:])
    for name, pin in [('MASK', 'clock_mask'), ('READ_ENABLE', 'physical_read_enable'), ('CAPTURED_CE', 'captured_ce')]:
        lines.append(f'`define {name} {transport}.{pin}')
    lines += ['`define CYCLE dut.top.sim.network.cycle', '`define PEERCYCLE dut.top.peer.cycle']
    functions = {n: [] for n in ('bank', 'slot', 'width', 'depth', 'offset', 'kind', 'region')}
    offset = 0
    for i, row in enumerate(rows(directory)):
        hierarchy = row['hierarchy']
        if row['bank'] == 255: kind = 5
        elif hierarchy.endswith('.cycles'): kind = 0
        elif hierarchy.endswith('.ram_r_data'): kind = 1
        elif hierarchy.endswith('.ram'): kind = 2
        elif re.search(r'\.left_?\.value$', hierarchy): kind = 3
        elif re.search(r'\.right_?\.value$', hierarchy): kind = 4
        else: raise ValueError('unknown oracle storage '+hierarchy)
        for name, value in dict(bank=row['bank'], slot=row['slot'], width=row['width'],
                                depth=row['depth'], offset=offset, kind=kind, region=row['region']).items():
            functions[name].append(f'{i}: entry_{name}={value};')
        offset += row['depth']
    for name, values in functions.items():
        lines.append(f'function automatic integer entry_{name}(input integer e); case(e)\n' +
                     '\n'.join(values)+f'\ndefault: entry_{name}=-1; endcase endfunction')
    return port_text, '\n'.join(lines)+'\n'


def constraints(directory):
    """Reconstruct all final host/native snippets against original FIRRTL paths."""
    modules = parse_modules((directory/'connected.fir').read_text())
    live = instances(modules, 'ReservationShell')
    annotations = json.loads((directory/'connected-annotations.json').read_text())
    emitted = {'Synthesis': [], 'Implementation': []}
    counts = {'Synthesis': 0, 'Implementation': 0}
    for a in annotations:
        if a['class'] not in ('midas.InternalXDCAnnotation', 'midas.targetutils.xdc.XDCAnnotation'): continue
        args = a['argumentList']
        destination = a['destinationFile']['class'].split('$')[-2]
        require(destination in emitted, 'unknown XDC destination')
        roots = [re.fullmatch(r'~\w+\|(\w+).*', v)[1] for v in args]
        require(not roots or len(set(roots)) == 1, 'uncorrelated XDC roots')
        owner = roots[0] if roots else 'ReservationShell'
        paths = [p for p, m in live if m == owner]
        require(paths, 'unreachable final XDC owner')
        for path in paths:
            prefix = '' if path == 'ReservationShell' else path.split('.', 1)[1].replace('.', '/')+'/'
            references = []
            for target in args:
                base, ref = target.split('>')
                hops = re.findall(r'/(\w+):\w+', base)
                references.append(prefix+'/'.join(hops+ref.split('.')))
            pieces = a['formatString'].split('{}')
            require(len(pieces) == len(references)+1, 'unsupported XDC formatting')
            emitted[destination].append(''.join(piece+(references[i] if i < len(references) else '')
                                                 for i, piece in enumerate(pieces)))
            counts[destination] += 1
    for destination, body in emitted.items():
        name = 'connected.'+destination.lower()+'.xdc'
        require((directory/name).read_text() == '\n'.join([HEADER]+body), 'native final XDC omitted/changed host/native constraints')
    receipt = json.loads((directory/'connected-xdc-emission.json').read_text())
    require(receipt['status'] == 'pass' and receipt['backend'] == 'f2' and
            all(sha(directory/n) == h for n, h in receipt['inputs'].items()) and
            all(sha(directory/n) == h for n, h in receipt['outputs'].items()), 'stale native connected XDC emission')
    return counts


def component_constraints(directory):
    """Defer only the four literal board-pad placements outside this OOC root."""
    text = (directory/'connected.implementation.xdc').read_text()
    annotations = json.loads((directory/'connected-annotations.json').read_text())
    deferred = []
    expected = [('AW19', 'default_300mhz_clk1_clk_n'), ('AW20', 'default_300mhz_clk1_clk_p'),
                ('E32', 'default_300mhz_clk2_clk_n'), ('F32', 'default_300mhz_clk2_clk_p')]
    for a in annotations:
        if a['class'] not in ('midas.InternalXDCAnnotation', 'midas.targetutils.xdc.XDCAnnotation') or a['argumentList']: continue
        require(a['destinationFile']['class'].endswith('$Implementation$'), 'unknown literal synthesis constraint')
        placements = []
        for line in a['formatString'].splitlines():
            if not line.strip(): continue
            match = re.fullmatch(r'set_property\s+-dict\s+\{PACKAGE_PIN\s+(\w+)\s+IOSTANDARD\s+LVDS\}\s+\[get_ports\s+(\w+)\];?', line.strip())
            require(match, 'unknown literal implementation constraint cannot be deferred')
            placements.append(match.groups())
        require(placements == expected and text.count(a['formatString']) == 1, 'changed board-pad placement contract')
        text = text.replace(a['formatString'], '', 1)
        import hashlib
        deferred.append(dict(format_sha256=hashlib.sha256(a['formatString'].encode()).hexdigest(),
                             placements=placements, reason='board pads are outside ReservationShell OOC'))
    require(len(deferred) == 1, 'one explicit board-placement deferral required')
    return text, deferred


def synth_tcl(directory):
    constraints(directory)
    peer = json.loads((directory/'peer-routing.json').read_text())
    transport = '/'.join(peer['transport'].split('.')[1:])
    require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', n) for n in transport.split('/')), 'literal checked transport hierarchy required')
    synthesis = list(directory.glob('connected.synthesis.xdc'))
    implementation = list(directory.glob('connected.implementation.xdc'))
    require(len(synthesis) == len(implementation) == 1, 'one complete pair of generated constraints required')
    return 'set_param general.maxThreads 4\nread_verilog -sv '+' '.join(verilog(directory))+f'''
read_xdc generated/{synthesis[0].name}
synth_design -top ReservationShell -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source component.implementation.xdc
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {{REF_NAME == BUFGCE}}]
if {{[llength $gates] != 6}} {{error "expected all original gates and both native root masks"}}
foreach region {{top/sim/network top/peer}} {{
  foreach leaf {{checkpoint_physical_root_gate left_/gate right_/gate}} {{
    if {{[llength [get_cells $region/$leaf]] != 1}} {{error "original region clock path changed"}}
  }}
}}
foreach gate $gates {{if {{[get_property CE_TYPE $gate] ne "SYNC"}} {{error "changed native gate contract"}}}}
if {{[llength [get_cells -hier -filter {{REF_NAME == FDRE && IS_C_INVERTED == 1}}]] != 1}} {{error "missing unique low-phase mask"}}
set raw [get_nets -of_objects [get_ports clock]]
set checked 0
foreach pattern {{*CPUManagedStreamEngine*/* *ctrlInterconnect*/* *checkpoint_region_readout_adapter/router/* *checkpoint_region_readout_adapter/region*/ce_endpoint/* {transport}/*}} {{
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {{[llength $cells] == 0}} {{error "missing raw control/readout owner $pattern"}}
  foreach cell $cells {{
    if {{[get_property IS_C_INVERTED $cell] eq "1"}} {{continue}}
    set clocks [get_nets -segments -of_objects [get_pins -of_objects $cell -filter {{REF_PIN_NAME == C}}]]
    if {{[lsearch -exact $clocks $raw] < 0}} {{error "masked MMIO/DMA/readout control $cell"}}
    incr checked
  }}
}}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force region-widget.dcp
puts "REGION_WIDGET_SYNTH_PASS raw_registers=$checked gates=6"
'''


def audit_frames(directory, work):
    state = rows(directory)
    order = [(i, address) for i, row in enumerate(state) for address in range(row['depth'])]
    audits = []
    for path in sorted(work.glob('capture-*.hex')):
        data = [int(line, 16).to_bytes(64, 'little') for line in path.read_text().splitlines()]
        require(len(data) == 70, 'truncated sibling capture stream')
        frames = [int.from_bytes(b, 'little') for b in data]
        cut = field(frames[0], 96, 64)
        require(12 <= cut < 10000, 'capture outside active fixture range')
        for index, frame in enumerate(frames):
            require(field(frame, 0, 64) == 0x3154504b434d5346 and field(frame, 64, 16) == 1 and
                    field(frame, 96, 64) == cut, 'frame identity/common cut changed')
            require(field(frame, 80, 16) == (1 if index == 0 else 3 if index == 69 else 2), 'frame order')
            if index == 0:
                require(field(frame, 224, 32) == 14 and field(frame, 256, 256) == 2**256-1, 'sentinel/count changed')
            elif index == 69:
                require(field(frame, 160, 64) == 68 and field(frame, 224, 32) == crc32c(b''.join(data[:-1])) ^ 0xffffffff,
                        'CRC/completeness mismatch')
            else:
                ordinal, at = field(frame, 224, 32), field(frame, 256, 32)
                require((ordinal, at) == order[index-1] and field(frame, 160, 64) == index-1, 'selector/word order')
                row = state[ordinal]
                require((field(frame, 288, 16), field(frame, 304, 8), field(frame, 312, 16)) ==
                        (row['width'], row['bank'], row['slot']), 'state selector/geometry changed')
                hierarchy = row['hierarchy']
                if row['bank'] == 255: value = 1
                else:
                    chunks = (row['logical_state']['width']+63)//64
                    if hierarchy.endswith('.ram'):
                        value = max(c for c in range(cut) if c % 8 == at//chunks)
                    elif hierarchy.endswith('.ram_r_data'): value = cut-9
                    else:
                        require(hierarchy.endswith('.cycles') or re.search(r'\.(?:left|right)_?\.value$', hierarchy),
                                'unknown independent oracle state')
                        value = cut
                    if row['region'] == 1 and hierarchy.endswith(('.ram', '.ram_r_data')): value ^= 0x1234
                    value = (value >> (64*(at % chunks))) & (2**64-1)
                require(field(frame, 336, 64) == value, 'independent sibling DMA payload differs')
        audits.append(dict(file=path.name, target_cut=cut, words=68, crc32c=field(frames[-1], 224, 32)))
    require(len(audits) == 4, 'four active captures required')
    return audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    parser.add_argument('--generated', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from tools.checkpoint_formats.tests.audit_region_widget_graft import audit, corruptions
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    pins = {n: sha(ROOT/n) for n in sources()}
    commands = []
    summary = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda', sources=pins,
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), source_root=str(ROOT),
                   scope='real widget/disjoint sibling readout component only; production cut/owners remain incomplete',
                   physical_fpga_capture=False, deployable_capture_image=False, metasim_restore_supported=False)
    def run(argv, name, expected=0, cwd=out):
        log = out/(name+'.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log)); commands.append(row)
        with log.open('w') as stream:
            stream.write('argv='+json.dumps(row['argv'])+'\n'); stream.flush()
            row['returncode'] = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(row['returncode'] == expected, 'inspect underlying '+str(log))
        return log.read_text()
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out, flush=True)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost Vivado required')
        require(args.generated is not None and args.native is None, 'explicit generated input required')
        shutil.copytree(args.generated, out/'generated')
        summary['audit'] = audit(out/'generated')
        summary['rejected_corruptions'] = corruptions(out/'generated', out/'corruptions')
        for name in pins:
            target = out/'sources'/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, target)
        for name in RTL: shutil.copyfile(ROOT/'sims/firesim/sim/midas/src/main/verilog'/name, out/'sources'/name)
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name, path in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]: shutil.copyfile(path, out/name)
        (out/'target-clock-sink.sv').write_text(STUB)
        port_text, binding_text = headers(out/'generated')
        (out/'top_ports.svh').write_text(port_text); (out/'top_bindings.svh').write_text(binding_text)
        (out/'synth.tcl').write_text(synth_tcl(out/'generated'))
        summary['complete_final_constraints'] = constraints(out/'generated')
        component, deferred = component_constraints(out/'generated')
        (out/'component.implementation.xdc').write_text(component)
        summary['ooc_deferred_shell_constraints'] = deferred
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                             if p.is_file() and 'corruptions' not in p.relative_to(out).parts and p.name != 'summary.json'}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('REGION_WIDGET_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native sibling synthesis failed')
        summary['artifacts'] = {n: sha(out/n) for n in ('region-widget.dcp', 'utilization.rpt', 'timing.rpt', 'synth.log', 'commands.json')}
    else:
        require(str(ROOT).startswith('/scratch/') and shutil.which('vcs') == toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 only')
        require(args.native is not None and args.generated is None, 'explicit native input required')
        native = json.loads((args.native/'summary.json').read_text())
        require(native['status'] == 'pass' and native['backend'] == 'f2' and native['sources'] == pins, 'stale native source pins')
        for group in ('inputs', 'artifacts'):
            for name, digest in native[group].items(): require(sha(args.native/name) == digest, 'changed native evidence '+name)
        for name in native['inputs']:
            target = out/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.native/name, target)
        summary.update(inputs=native['inputs'], audit=audit(out/'generated'), native_receipt_sha256=sha(args.native/'summary.json'),
                       complete_final_constraints=constraints(out/'generated'))
        component, deferred = component_constraints(out/'generated')
        require((out/'component.implementation.xdc').read_text() == component and
                native['ooc_deferred_shell_constraints'] == json.loads(json.dumps(deferred)), 'changed explicit OOC board-placement deferral')
        summary['ooc_deferred_shell_constraints'] = deferred
        files = verilog(out/'generated') + ['BUFGCE.v', 'glbl.v', 'sources/'+TESTS+'region_widget_tb.sv',
                                          'sources/'+TESTS+'checkpoint_generated_network_exit.cc']
        common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                  '+incdir+'+str(out), '-top', 'region_widget_tb', '-top', 'glbl']
        run([*common, '-Mdir=csrc', '-o', 'simv', *files], 'compile')
        for case in ('healthy', 'missing-owner'):
            work = out/case; work.mkdir()
            text = run([out/'simv', '-no_save']+([] if case == 'healthy' else ['+'+case]), case, cwd=work)
            if case == 'healthy':
                match = re.search(r'REGION_WIDGET_PASS checks=(\d+) cuts=4 words=272 stalls=(\d+)', text)
                require(match and int(match[1]) > 100 and int(match[2]) > 20, 'incomplete four-cut sibling execution')
                summary['execution'] = dict(checks=int(match[1]), cuts=4, words=272, stalls=int(match[2]))
                summary['frame_audits'] = audit_frames(out/'generated', work)
            else: require('REGION_WIDGET_REJECT missing_owner=1 reset_recovered=1' in text, 'missing-owner/reset escaped')
            require((work/'region-widget.vcd').stat().st_size > 2000, 'missing full debug wave')
        adapter = [n for n in files if n.endswith('.native-region-graft-1.sv')]
        require(len(adapter) == 1, 'one second-region endpoint required')
        good = (out/adapter[0]).read_text()
        before = 'assign functional_response_data = checkpoint_inplace_region1_ckpt_resp_data;'
        after = "assign functional_response_data = checkpoint_inplace_region1_ckpt_resp_data ^ 64'd1;"
        require(good.count(before) == 1, 'ambiguous second-region defect location')
        (out/'corrupt-adapter.sv').write_text(good.replace(before, after))
        run([*common, '-Mdir=corrupt-csrc', '-o', 'corrupt-simv', *['corrupt-adapter.sv' if n == adapter[0] else n for n in files]], 'corrupt-compile')
        work = out/'corrupt'; work.mkdir()
        text = run([out/'corrupt-simv', '-no_save'], 'corrupt', expected=1, cwd=work)
        require('reason=independent captured bank payload' in text, 'real region defect escaped')
        match = re.search(r'REGION_WIDGET_PAYLOAD_MISMATCH cut=(\d+) word=(\d+) entry=(\d+) address=0 .*payload_byte=42', text)
        state = rows(out/'generated'); first = next(i for i, r in enumerate(state) if r['region'] == 1 and r['bank'] != 255)
        word = sum(r['depth'] for r in state[:first])
        require(match and (int(match[2]), int(match[3])) == (word, first), 'defect did not stop at first second-region word')
        summary['compiled_defect'] = dict(target_cut=int(match[1]), word=word, entry=first, payload_byte=42)
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
                                (p.suffix in ('.vcd', '.hex', '.log') or p == out/'corrupt-adapter.sv')}
        summary['artifacts']['commands.json'] = sha(out/'commands.json')
    require(pins == {n: sha(ROOT/n) for n in pins}, 'source epoch changed')
    summary['status'] = 'pass'; (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__': main()
