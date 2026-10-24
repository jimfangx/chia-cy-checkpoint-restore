"""Generated physical CE bank routing into bank/MMIO/DMA; EDA-only VCS.

This is a component contract, not a checkpoint-enabled Rocket FPGA image.
"""
import argparse
from datetime import datetime, timezone
import hashlib
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
from tools.checkpoint_formats.tests.audit_physical_clock_wiring import audit as audit_wiring
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
VERILOG = 'sims/firesim/sim/midas/src/main/verilog/'
RTL = tuple(VERILOG+n+'.sv' for n in ('CheckpointCaptureCut', 'CheckpointCaptureTransport',
            'CheckpointPhysicalClockCut', 'CheckpointPhysicalCaptureTransport', 'CheckpointPhysicalStateRouter'))
TB = 'tools/checkpoint_formats/tests/physical_state_router_transport_tb.sv'
HEADER = 'tools/checkpoint_formats/tests/physical_state_router_fixture.svh'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'
NETWORK_SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutDependencies.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/PhysicalClockCaptureNetworkSpec.scala',
    'tools/checkpoint_formats/tests/audit_physical_clock_wiring.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_dependencies.py')
ROUTER_TB = 'tools/checkpoint_formats/tests/physical_state_router_tb.sv'
SOURCES = (*RTL, TB, HEADER, ROUTER_TB, EXIT, 'tools/checkpoint_formats/tests/verify_physical_state_router_transport.py',
    'tools/checkpoint_formats/tests/verify_physical_capture_transport.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_state_bank.py',
    'tools/checkpoint_formats/tests/verify_physical_clock_state_bank.py',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockStateBank.scala', *NETWORK_SOURCES)
from tools.checkpoint_formats.tests.audit_physical_clock_state_bank import audit as audit_ce
from tools.checkpoint_formats.tests.verify_physical_clock_state_bank import GENERATED as CE_FILES
NETWORK_FILES = ('reference.fir', 'manifest.json', 'physical-clock-plan.json',
    'physical-clock-wiring.fir', 'physical-clock-wiring.json', 'physical-clock-wiring.sv',
    'physical-clock-wiring-emission.json', 'physical-clock-dependencies.json')
RESET_PHASES = ['freeze', 'response', 'data', 'publish', 'release']
from tools.checkpoint_formats.tests.verify_physical_capture_transport import fixture as original_fixture


def fixture(external):
    require(external, 'generated network required')
    result = original_fixture(True)
    a = result.index('  wire descriptor_valid=')
    b = result.index('  wire bank_request_valid', a)
    result = result[:a] + """  wire descriptor_valid;
  wire [7:0] descriptor_bank;
  wire [15:0] descriptor_slot, descriptor_width;
  wire [31:0] descriptor_depth;
""" + result[b:]
    result = result.replace('  reg bank_response_valid;\n  wire bank_request_ready=!bank_response_valid;\n  reg [63:0] bank_response_data;', """  wire bank_response_valid, bank_request_ready;
  wire [63:0] bank_response_data;
  reg functional_response_valid;
  wire functional_request_ready=!functional_response_valid;
  reg [63:0] functional_response_data;
  wire functional_response_error=0;""")
    result = result.replace('  wire bank_response_error=0;', '  wire bank_response_error;')
    result = result.replace('  CheckpointPhysicalCaptureTransport', '`include "physical_state_router_fixture.svh"\n  CheckpointPhysicalCaptureTransport')
    result = result.replace('.ENTRIES(3)', '.ENTRIES(5)')
    a = result.index('  always @(posedge clock) begin')
    chunk = result[a:]
    for name in ('request_valid','request_ready','response_valid','response_ready','response_data','response_error'):
        chunk = chunk.replace('bank_'+name, 'functional_'+name)
    chunk = chunk.replace('        else functional_response_data<=captured_ce;', '        else functional_response_data<=0;')
    return result[:a] + chunk


def synthesis(external):
    return '''set_param general.maxThreads 4
set ce [open ce-module.txt r]
set module [string trim [read $ce]]
close $ce
set_property include_dirs sources [current_fileset]
set_property verilog_define CE_BANK_MODULE=$module [current_fileset]
read_verilog -sv sources/CheckpointCaptureCut.sv sources/CheckpointCaptureTransport.sv sources/CheckpointPhysicalClockCut.sv sources/CheckpointPhysicalCaptureTransport.sv sources/CheckpointPhysicalStateRouter.sv ce-generated/physical-clock-state-bank.sv generated/physical-clock-wiring.sv fixture.sv
synth_design -top PhysicalTransportSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected four generated native gates"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "wrong native gate semantics"}}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "expected falling-edge common clock mask"}
foreach name {network/checkpoint_physical_root_gate network/left/gate network/middle/gate network/right/gate} {
  if {[llength [get_cells $name]] != 1} {error "lost generated native gate $name"}
}
if {[llength [get_cells -hier -filter {NAME =~ *dut/physical/internal_clock_network*}]] != 0} {error "duplicate native gates"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-transport.dcp
puts "PHYSICAL_TRANSPORT_SYNTH_PASS gates=4 falling_edge_registers=1"
'''


def check_network(directory):
    audit_dependencies(directory/'reference.fir', directory/'manifest.json', directory/'physical-clock-plan.json',
                       directory/'physical-clock-dependencies.json')
    audit_wiring(directory/'reference.fir', directory/'manifest.json', directory/'physical-clock-plan.json',
                 directory/'physical-clock-wiring.fir', directory/'physical-clock-wiring.json',
                 directory/'physical-clock-wiring.sv', directory/'physical-clock-wiring-emission.json')
    dep = json.loads((directory/'physical-clock-dependencies.json').read_text())
    require(dep['root_module'] == 'PhysicalTransportNetwork' and
            dep['external_inputs_require_freeze'] == ['PhysicalTransportNetwork.reset'],
            'fixture must bind its sole external CE input to the shared capture/network/endpoint reset')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()



def audit_frames(raw):
    """Independent arithmetic and per-StateID descriptor/CRC reconstruction."""
    require(len(raw) == 9*64, 'incomplete composed snapshot')
    frames=[int.from_bytes(raw[i:i+64], 'little') for i in range(0,len(raw),64)]
    cycle=field(frames[0],96,64)
    require(cycle <= 1024, 'fixture cycle outside test scope')
    expected=[1,2,3]
    for c in range(cycle):
        for i, enabled in enumerate([not c&1, bool(c&4), bool((c>>1 ^ c)&1)]):
            if enabled:
                expected[i]=((expected[i]*33) ^ (c+i)) & 0xffffffff
    ce=[int(not cycle&1), int(bool(cycle&4)), int(bool((cycle>>1 ^ cycle)&1))]
    values=[cycle,*expected,*ce]
    selectors=[(0,1,0,64,0),*( (1,2,0,32,a) for a in range(3)),*( (2+i,255,i,1,0) for i in range(3))]
    for i,frame in enumerate(frames):
        require(field(frame,0,64)==0x3154504b434d5346 and field(frame,64,16)==1, 'bad frame identity')
        require(field(frame,96,64)==cycle, 'mixed target-cycle labels')
        require(field(frame,80,16)==(1 if i==0 else 3 if i==8 else 2), 'bad frame type/order')
        require(field(frame,160,64)==(0 if i==0 else 7 if i==8 else i-1), 'bad word sequence')
        if i==0:
            require(field(frame,224,32)==5 and field(frame,256,256)==int('0123456789abcdef'*4,16), 'bad manifest header')
        elif i==8:
            require(field(frame,224,32)==crc32c(raw[:-64])^0xffffffff and frame>>256==0, 'bad trailer checksum')
        else:
            ordinal,bank,slot,width,address=selectors[i-1]
            require(field(frame,224,32)==ordinal and field(frame,256,32)==address and
                    field(frame,288,16)==width and field(frame,304,8)==bank and
                    field(frame,312,16)==slot and field(frame,328,8)==0 and frame>>400==0, 'bad bank selector/shape')
            require(field(frame,336,64)==values[i-1], 'independent host state mismatch')
    return cycle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    parser.add_argument('--ce-generated', type=Path)
    parser.add_argument('--generated', type=Path, help='compiler-generated physical transport network')
    parser.add_argument('--native', type=Path)
    parser.add_argument('--eda', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(RUNS), 'evidence must be below runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=base))
    commands = []

    def run(argv, name, cwd=out, expected=0):
        log = out/(name+'.log')
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(log))
        commands.append(row)
        with log.open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'inspect underlying log '+str(log))
        return log.read_text()

    def validate(directory, backend):
        require(directory is not None and directory.resolve().is_relative_to(RUNS), 'receipt must be below runs')
        doc = json.loads((directory/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and
                not doc['physical_fpga_capture'] and not doc['full_rocket_image_build'], 'invalid component scope')
        require(doc['sources'] == {n: sha(ROOT/n) for n in SOURCES}, 'stale source receipt')
        for group in ('inputs', 'artifacts'):
            for name, digest in doc[group].items():
                require(sha(directory/name) == digest, 'changed '+group+' '+name)
        for name in SOURCES:
            require(sha(directory/'sources'/Path(name).name) == doc['sources'][name], 'changed source snapshot')
        external = doc['external_clock_network']
        require(type(external) is bool, 'invalid network mode')
        require((directory/'fixture.sv').read_text() == fixture(external) and
                (directory/'synth.tcl').read_text() == synthesis(external), 'changed synthesis contract')
        if external:
            require(all('generated/'+name in doc['inputs'] for name in NETWORK_FILES), 'missing generated inputs')
            check_network(directory/'generated')
        audit_ce(directory/'ce-generated')
        require((directory/'ce-module.txt').read_text().strip() == doc['endpoint_module'], 'changed CE module')
        return doc

    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='compiler physical CE bank with functional bank/MMIO/DMA component only',
                   physical_fpga_capture=False, full_rocket_image_build=False)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native manager Vivado required')
        (out/'sources').mkdir()
        for name in SOURCES:
            (out/'sources'/Path(name).name).write_bytes((ROOT/name).read_bytes())
        external = args.generated is not None
        summary['external_clock_network'] = external
        if external:
            require(args.generated.resolve().is_relative_to(RUNS), 'generated inputs must be below runs')
            check_network(args.generated)
            (out/'generated').mkdir()
            for name in NETWORK_FILES:
                shutil.copyfile(args.generated/name, out/'generated'/name)
        require(external and args.ce_generated is not None and args.ce_generated.resolve().is_relative_to(RUNS), 'generated CE inputs required')
        audit_ce(args.ce_generated)
        (out/'ce-generated').mkdir()
        for name in CE_FILES:
            shutil.copyfile(args.ce_generated/name, out/'ce-generated'/name)
        ce_doc=json.loads((out/'ce-generated/physical-clock-state-bank.json').read_text())
        require(len(ce_doc['state']) == 3, 'three CE owners required')
        summary['endpoint_module']=ce_doc['endpoint_module']
        (out/'ce-module.txt').write_text(ce_doc['endpoint_module']+'\n')
        (out/'fixture.sv').write_text(fixture(external))
        (out/'synth.tcl').write_text(synthesis(external))
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models'] = {}
        for name, path in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]:
            (out/name).write_bytes(path.read_bytes())
            summary['vendor_models'][name] = dict(original_path=str(path), sha256=sha(path))
        text = run(['vivado','-mode','batch','-source','synth.tcl','-log','vivado.log','-journal','vivado.jou'], 'synth')
        require('PHYSICAL_TRANSPORT_SYNTH_PASS gates=4 falling_edge_registers=1' in text and
                not re.search(r'ERROR:|CRITICAL WARNING:', text), 'synthesis failed')
        summary['sources'] = {n: sha(out/'sources'/Path(n).name) for n in SOURCES}
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in (out/'sources').iterdir()}
        summary['inputs'].update({n: sha(out/n) for n in ('fixture.sv','synth.tcl','BUFGCE.v','glbl.v','ce-module.txt')})
        if external:
            summary['inputs'].update({'generated/'+name: sha(out/'generated'/name) for name in NETWORK_FILES})
        summary['inputs'].update({'ce-generated/'+name: sha(out/'ce-generated'/name) for name in CE_FILES})
        summary['artifacts'] = {n: sha(out/n) for n in ('physical-transport.dcp','utilization.rpt','timing.rpt','synth.log','vivado.log','vivado.jou','commands.json')}
    elif args.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA VCS SP2 required')
        native = validate(args.native, 'f2')
        summary['external_clock_network'] = native['external_clock_network']
        summary['endpoint_module'] = native['endpoint_module']
        for name, digest in native['inputs'].items():
            path=out/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((args.native/name).read_bytes())
            require(sha(path) == digest, 'copy mismatch')
        standalone=out/'router'; standalone.mkdir()
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
             '-top','physical_state_router_tb','-Mdir='+str(standalone/'csrc'),'-o',standalone/'simv',
             out/'sources/CheckpointPhysicalStateRouter.sv',out/'sources/physical_state_router_tb.sv',
             out/'sources/checkpoint_generated_network_exit.cc'], 'router-compile', standalone)
        text=run([standalone/'simv','-no_save'], 'router-healthy', standalone)
        match=re.search(r'PHYSICAL_ROUTER_PASS checks=(\d+) transactions=6',text)
        require(match is not None, 'incomplete standalone routing checks')
        summary['router_checks']=int(match[1])
        work=out/'router-corrupt'; work.mkdir()
        text=run([standalone/'simv','-no_save','+corrupt'], 'router-corrupt', work, expected=1)
        require('accepted destination pinned under selector changes acknowledged_edges=0' in text, 'routing oracle failed to stop')
        mutant=out/'router-mutant'; mutant.mkdir()
        source=(out/'sources/CheckpointPhysicalStateRouter.sv').read_text()
        require(source.count('selected_ce <= route_ce;')==1, 'ambiguous routing mutation site')
        (mutant/'router.sv').write_text(source.replace('selected_ce <= route_ce;', 'selected_ce <= !route_ce;'))
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
             '-top','physical_state_router_tb','-Mdir='+str(mutant/'csrc'),'-o',mutant/'simv',
             mutant/'router.sv',out/'sources/physical_state_router_tb.sv',out/'sources/checkpoint_generated_network_exit.cc'],
             'router-mutant-compile', mutant)
        text=run([mutant/'simv','-no_save'], 'router-mutant', mutant, expected=1)
        require('accepted destination pinned under selector changes acknowledged_edges=0' in text, 'mutant route failed to stop')
        healthy=out/'healthy'; healthy.mkdir()
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
             *(['+define+GENERATED_TRANSPORT_NETWORK', str(out/'generated/physical-clock-wiring.sv')] if native['external_clock_network'] else []),
             '+incdir+'+str(out/'sources'), '+define+CE_BANK_MODULE='+native['endpoint_module'], str(out/'ce-generated/physical-clock-state-bank.sv'),
             '-top','physical_state_router_transport_tb','-top','glbl','-Mdir='+str(healthy/'csrc'),'-o',healthy/'simv',
             out/'BUFGCE.v',out/'glbl.v',*(out/'sources'/Path(n).name for n in (*RTL,TB,EXIT))], 'compile', healthy)
        text=run([healthy/'simv','-no_save','+frames='+str(healthy/'frames.hex')], 'healthy', healthy)
        match=re.search(r'PHYSICAL_TRANSPORT_PASS checks=(\d+) cuts=5 requests=36 dma_stalls=(\d+) bank_delays=(\d+) aborts=1 cycles=(\d+)', text)
        require(match is not None, 'incomplete healthy run')
        summary.update(checks=int(match[1]), cuts=5, requests=36, dma_stalls=int(match[2]), bank_delays=int(match[3]), aborts=1, cycles=int(match[4]))
        raw_frames=[int(row,16).to_bytes(64,'little') for row in (healthy/'frames.hex').read_text().splitlines()]
        groups=[]; partial=[]
        for frame in raw_frames:
            if field(int.from_bytes(frame,'little'),80,16)==1:
                if partial:
                    require(len(partial)==1, 'aborted transfer did not stop before data')
                partial=[]
            partial.append(frame)
            if field(int.from_bytes(frame,'little'),80,16)==3:
                groups.append(b''.join(partial)); partial=[]
        require(len(groups)==5 and not partial and len(raw_frames)==46, 'missing complete captures or aborted header')
        summary['host_audited_cuts']=[audit_frames(raw) for raw in groups]
        summary['host_integrity_rejections']=[]
        original=groups[1]
        mutations={'truncated':original[:-1], 'bit_flip':bytes([original[0]^1])+original[1:],
                   'wrong_order':original[:64]+original[128:192]+original[64:128]+original[192:]}
        # A semantically wrong state with a corrected transport CRC must fail.
        changed=bytearray(original); changed[64+42]^=1
        changed[-64+28:-64+32]=(crc32c(changed[:-64])^0xffffffff).to_bytes(4,'little')
        mutations['semantic_with_valid_crc']=bytes(changed)
        for name,offset in (('physical_ce_with_valid_crc',5*64+42), ('physical_slot_with_valid_crc',6*64+39)):
            changed=bytearray(original); changed[offset]^=1
            changed[-64+28:-64+32]=(crc32c(changed[:-64])^0xffffffff).to_bytes(4,'little')
            mutations[name]=bytes(changed)
        mutations['missing_physical_owner']=original[:7*64]+original[8*64:]

        for name,raw in mutations.items():
            try:
                audit_frames(raw)
            except (ValueError, RuntimeError):
                summary['host_integrity_rejections'].append(name)
            else:
                raise RuntimeError('accepted corrupt snapshot '+name)
        summary['negative_tests']=[]
        for fault in ('missing','ce','cycle','owner','lost'):
            work=out/fault; work.mkdir()
            text=run([healthy/'simv','-no_save','+fault='+fault], fault, work)
            require(re.search('PHYSICAL_TRANSPORT_REJECT fault='+fault+r' target_cycle=\d+ acknowledged_edges=0',text) is not None and 'PHYSICAL_TRANSPORT_PASS' not in text, 'negative failed '+fault)
            summary['negative_tests'].append(fault)
        work=out/'corrupt'; work.mkdir()
        text=run([healthy/'simv','-no_save','+corrupt'], 'corrupt', work, expected=1)
        require('reason=banked logical CE state' in text and 'PHYSICAL_TRANSPORT_PASS' not in text, 'corrupt readback did not stop')
        summary['negative_tests'].append('banked logical CE state')
        summary['reset_recovery_tests'] = []
        for phase in RESET_PHASES:
            work = out/('reset-'+phase); work.mkdir()
            text = run([healthy/'simv', '-no_save', '+reset_at='+phase], 'reset-'+phase, work)
            require(re.search('PHYSICAL_TRANSPORT_RESET_PASS phase='+phase+r' recovered_cuts=1 cycles=64 checks=\d+', text),
                    'reset invalidation/recovery failed '+phase)
            summary['reset_recovery_tests'].append(phase)
        summary['sources']=native['sources']; summary['inputs']=native['inputs']
        summary['native_receipt']=str(args.native/'summary.json')
        summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.vcd','.hex')}
    else:
        native=validate(args.native,'f2'); eda=validate(args.eda,'eda')
        summary['external_clock_network'] = native['external_clock_network']
        summary['endpoint_module'] = native['endpoint_module']
        require(native['external_clock_network']==eda['external_clock_network'], 'different clock network modes')
        require(eda['reset_recovery_tests']==RESET_PHASES, 'incomplete reset interruption/recovery scope')
        require(len(list(args.eda.rglob('*.vcd')))==15, 'missing complete debug waveforms')
        require(native['inputs']==eda['inputs'] and native['sources']==eda['sources'], 'different native and EDA inputs')
        require(eda['cuts']==5 and eda['requests']==36 and eda['cycles']>=320 and len(eda['negative_tests'])==6, 'incomplete EDA scope')
        summary.update(native_receipt=str(args.native/'summary.json'),eda_receipt=str(args.eda/'summary.json'),matched_inputs=len(native['inputs']),matched_sources=len(native['sources']))
        summary['sources']={n:sha(ROOT/n) for n in SOURCES}
        summary['inputs']={}; summary['artifacts']={}
    require(summary['sources']=={n:sha(ROOT/n) for n in SOURCES}, 'source changed during execution')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
