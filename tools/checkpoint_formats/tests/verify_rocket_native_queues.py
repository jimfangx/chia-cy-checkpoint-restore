"""Exact Rocket ULTRA queue geometry through a shared native capture transport.

This isolated four-queue component is not a CPU image or an FPGA checkpoint.
Native synthesis runs on localhost; every VCS execution runs on EDA.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_shared_queue_access import observation_audit, registered_readout_audit
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
V = 'sims/firesim/sim/midas/src/main/verilog/'
RTL = tuple(V + n for n in ('CheckpointNativeQueueCapture.sv', 'CheckpointNativeCaptureTransport.sv',
    'CheckpointNativeStateCapture.sv', 'CheckpointNativeStateSnapshot.sv', 'CheckpointPhysicalCaptureTransport.sv',
    'CheckpointPhysicalClockCut.sv', 'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv'))
SELF = 'tools/checkpoint_formats/tests/verify_rocket_native_queues.py'
TB = 'tools/checkpoint_formats/tests/rocket_native_queues_tb.sv'
SCALA = 'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/RocketNativeQueueCaptureSpec.scala'
SOURCES = (*RTL, SELF, TB, SCALA, 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/tests/verify_shared_queue_access.py',
    'tools/checkpoint_formats/tests/audit_checkpoint_regions.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    *sorted(str(p.relative_to(ROOT)) for p in (ROOT/'sims/firesim/sim/midas/src/main/scala/midas/checkpoint').glob('*.scala')))
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def audit_generated(g):
    manifest = json.loads((g/'descriptors.json').read_text())
    rows = manifest['state']
    require(len(rows) == 20 and len({r['state_id'] for r in rows}) == 20, 'missing original queue owner')
    require(all(manifest[k] is False for k in ('complete_fpga_capture', 'deployable_capture_image',
        'production_freeze_owners_bound', 'metasim_restore_supported')), 'component admission changed')
    require(not manifest['uncovered_functional_state'], 'queue component omitted original storage')
    require(len(manifest['uncovered_physical_gates'])==1, 'lost original uncovered physical gate')
    inv = inventory_from_firrtl((g/'source.fir').read_text(), 'RocketQueueHost')
    original = {r['state_id']: r for r in inv if r['adapter'] != 'metasim-bufgce-v1'}
    require(len(original) == 20 and {r['state_id'] for r in rows} == original.keys(), 'independent queue inventory mismatch')
    text = (g/'generated.sv').read_text()
    observations = []
    for q in range(4):
        bank = json.loads((g/f'shell-{q}-banks-binding.json').read_text())
        registered_readout_audit(g/f'shell-{q}-banked.fir', bank)
        layout = observation_audit(g/f'shell-{q}-banked.fir', bank)
        require(layout['bits'] == 1664 and len(layout['state']) == 14, 'incomplete native queue vector')
        module = f'checkpoint_shell_region{q}_selected_Queue_56'
        body = re.search(r'(?m)^module '+module+r'\([\s\S]*?^endmodule\b', text)
        require(body is not None, 'missing concrete queue execution')
        registers = dict((n, int(w)+1 if w else 1) for w, n in
            re.findall(r'\breg\s+(?:\[(\d+):0\]\s+)?(\w+)\s*;', body[0]) if not n.startswith('_RAND_'))
        fields = []
        for f in layout['state']:
            name = f['hierarchy'].split('.')[-1]
            emitted = (name+'_pipe_0' if f['adapter'] == 'firrtl-emitter-memory-pipeline-v1' else
                       f'checkpoint_shell_region{q}_'+name if name.startswith('ckpt_') else name)
            require(registers.get(emitted) == f['width'], 'missing emitted native register '+emitted)
            if f['adapter'] == 'firrtl-emitter-memory-pipeline-v1':
                require(len(re.findall(r'\b'+re.escape(emitted)+r' <= '+re.escape(name)+r';', body[0])) == 1,
                        'changed original RAM data pipeline')
            fields.append(dict(f, emitted_register=emitted))
        observations.append(dict(module=module, state=fields))
        for r in rows:
            if r['region'] == q:
                o = original[r['state_id']]
                require(r['logical_state'] == o and r['bank'] == q and r['local_bank'] == 0 and
                    r['depth'] == o['depth']*((o['width']+63)//64), 'crossed or truncated queue descriptor')
        require(len([r for r in rows if r['region'] == q]) == 5, 'incomplete queue region')
    commands = [s for s in (g/'generated.synthesis.xdc').read_text().splitlines() if s and not s.startswith('#')]
    require(commands == [f'set_property RAM_STYLE ULTRA [get_cells -hierarchical -regexp .*q{q}/ram_reg.*]' for q in range(4)],
        'changed original ULTRA memory policy')
    return rows, observations


def capture_manifest(g, rows, observations):
    return dict(version=2, scope='isolated_exact_Rocket_Queue_56_geometry', complete_fpga_capture=False,
        production_source_sha256=(g/'production-source-sha256.txt').read_text().strip(),
        generated_sv_sha256=sha(g/'generated.sv'),
        queue_bank_bindings_sha256=[sha(g/f'shell-{q}-banks-binding.json') for q in range(4)],
        transport_rtl_sha256={n:sha(ROOT/n) for n in RTL},
        original_descriptor_manifest_sha256=sha(g/'descriptors.json'), queue_observations=observations,
        state=rows, native_descriptor=dict(bank=252, slot=0, width=64, depth=104),
        native_bit_order='q0_lsb_then_q1_q2_q3', native_bits=6656,
        initial_selector_policy='retain_unresolved_diagnostic_then_real_frontdoor_reads_before_four_binary_cuts',
        uncovered_original_physical_gates=json.loads((g/'descriptors.json').read_text())['uncovered_physical_gates'],
        remaining_owners=['original unused SYNC gate', 'atomic transport/router self-state and composite restore',
                          'enclosing simulator/memory/bridge/host/pre-FAME owners'],
        router_state=dict(pending=1, invalid=1, owner=2), composite_restore_supported=False)


def wrapper(g, rows, digest):
    host = re.search(r'module RocketQueueHost\((.*?)\n\);', (g/'generated.sv').read_text(), re.S)
    require(host is not None, 'missing actual generated host')
    ports, connections = [], []
    direct = dict(clock='clock', reset='reset')
    suffixes = dict(clock='clock', reset='reset', freeze='functional_hold', bank='queue_bank', slot='queue_slot',
        address='queue_address', req_valid='queue_request_valid[{q}]', req_ready='queue_request_ready[{q}]',
        resp_valid='queue_response_valid[{q}]', resp_ready='queue_response_ready[{q}]',
        resp_data='queue_response_data[{q}*64 +: 64]', resp_error='queue_response_error[{q}]',
        native_state='live_state[{q}*1664 +: 1664]', data='', match='')
    for line in host[1].splitlines():
        if not line.strip(): continue
        m = re.fullmatch(r'\s*(input|output)\s*(\[\d+:\d+\])?\s*(\w+),?', line)
        require(m is not None, 'unsupported generated interface')
        direction, width, name = m.groups()
        access = re.fullmatch(r'checkpoint_shell_region([0-3])_ckpt_(\w+)', name)
        if access:
            require(access[2] in suffixes, 'unknown native queue sideband')
            expr = suffixes[access[2]].format(q=access[1])
        else:
            require(name in direct or name.startswith('lane'), 'unexpected original host pin')
            ports.append(f'    {direction} wire {width or ""} {name}')
            expr = name
        connections.append(f'.{name}({expr})')
    ports += ['    input wire [63:0] target_cycle', '    input wire [3:0] owner_present, owner_error',
        '    input wire mmio_valid, mmio_write, mmio_response_ready, dma_ready',
        '    input wire [7:0] mmio_address', '    input wire [31:0] mmio_wdata',
        '    output wire mmio_ready, mmio_response_valid, mmio_response_error',
        '    output wire [31:0] mmio_rdata', '    output wire dma_valid, dma_last, dma_abort',
        '    output wire [511:0] dma_data', '    output wire functional_hold, native_valid, native_failed, root_clock',
        '    output wire [63:0] native_cut_cycle', '    output wire [6655:0] snapshot_state',
        '    output wire [7287:0] control_state']
    body = '''
    wire [3:0] queue_request_valid,queue_request_ready,queue_response_valid,queue_response_ready,queue_response_error;
    wire [7:0] queue_bank;
    wire [15:0] queue_slot;
    wire [31:0] queue_address;
    wire [255:0] queue_response_data;
    wire [6655:0] live_state;
    wire [31:0] descriptor_entry;
    reg descriptor_valid;
    reg [7:0] descriptor_bank;
    reg [15:0] descriptor_slot,descriptor_width;
    reg [31:0] descriptor_depth;
    always @* begin
        descriptor_valid=1;descriptor_bank=0;descriptor_slot=0;descriptor_width=0;descriptor_depth=0;
        case(descriptor_entry)
'''
    for i, r in enumerate(rows):
        body += f"            {i}:begin descriptor_bank={r['bank']};descriptor_slot={r['slot']};descriptor_width={r['width']};descriptor_depth={r['depth']};end\n"
    body += '            default:descriptor_valid=0;\n        endcase\n    end\n'
    body += '    RocketQueueHost host(\n        '+',\n        '.join(connections)+');\n'
    body += f"    CheckpointNativeQueueCapture #(.GATES(1),.MANIFEST_SHA256(256'h{digest})) capture(\n"
    direct_names = ['clock','reset','target_cycle','owner_present','owner_error','live_state','root_clock',
        'functional_hold','native_valid','native_failed','native_cut_cycle','snapshot_state','control_state',
        'mmio_valid','mmio_write','mmio_address','mmio_wdata','mmio_ready','mmio_response_valid',
        'mmio_response_ready','mmio_rdata','mmio_response_error','descriptor_entry','descriptor_valid','descriptor_bank',
        'descriptor_slot','descriptor_width','descriptor_depth','queue_request_valid','queue_request_ready','queue_bank',
        'queue_slot','queue_address','queue_response_valid','queue_response_ready','queue_response_data','queue_response_error',
        'dma_valid','dma_ready','dma_data','dma_last','dma_abort']
    cs = [f'.{n}({n})' for n in direct_names]
    cs += [".ce(1'b1)", '.owner_frozen({4{functional_hold}})', '.gate_clock()', '.clock_mask()', '.freeze()', '.captured_ce()', '.route_pending()']
    body += '        '+',\n        '.join(cs)+');\nendmodule\n'
    return 'module RocketNativeQueueTop(\n'+',\n'.join(ports)+'\n);\n'+body


def oracle(g, rows, observations):
    digest=hashlib.sha256(canonical(capture_manifest(g,rows,observations))).hexdigest()
    lines = [f"localparam [255:0] EXPECTED_CAPTURE_MANIFEST = 256'h{digest};",
        'task sample_original_native;', 'begin']
    for q, obs in enumerate(observations):
        for f in obs['state']:
            lines.append(f"expected_native[{q*1664+f['offset']} +: {f['width']}] = dut.host.q{q}.{f['emitted_register']};")
    lines += ['end','endtask','task expected_original_word(input integer ordinal,input integer address,output reg [63:0] value);','begin','value=0;case(ordinal)']
    for i, r in enumerate(rows):
        q = r['region']; suffix = r['hierarchy'].split('.')[-1]
        if suffix == 'ram': value = f"memory[{q}][address/8] >> (64*(address%8))"
        elif suffix == 'enq_ptr_value': value = f'wp[{q}]'
        elif suffix == 'deq_ptr_value': value = f'rp[{q}]'
        elif suffix == 'maybe_full': value = f'fullflag[{q}]'
        elif suffix == 'ram_io_deq_bits_MPORT_addr': value = f'ra[{q}]'
        else: raise ValueError('unknown original queue state '+suffix)
        lines.append(f'{i}:value={value};')
    lines += ['default:check(0,"unexpected functional ordinal");','endcase','end','endtask',
        'function automatic [103:0] expected_selector(input integer sequence_number);',
        'begin', "case (1'b1)"]
    offset=0
    for i,r in enumerate(rows):
        lines.append(f"(sequence_number < {offset+r['depth']}):expected_selector={{32'd{i},32'(sequence_number-{offset}),16'd{r['width']},8'd{r['bank']},16'd{r['slot']}}};")
        offset+=r['depth']
    lines += [f"(sequence_number < {offset+104}):expected_selector={{32'd20,32'(sequence_number-{offset}),16'd64,8'd252,16'd0}};",
        "default:expected_selector='1;",'endcase','end','endfunction']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['vivado','vcs'],required=True);p.add_argument('--generated',type=Path)
    p.add_argument('--native',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require(a.out.resolve().is_relative_to(RUNS),'evidence outside runs')
    a.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=a.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    doc=dict(status='running',backend='f2' if a.mode=='vivado' else 'eda',scope='exact Rocket four-queue capture component only',
        physical_fpga_capture=False,full_image=False,production_ownership=False,composite_restore_supported=False,
        observed_utc=datetime.now(timezone.utc).isoformat(),sources=sources,commands=[])
    def save(): (out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n')
    def run(argv,name,expected=0):
        argv=list(map(str,argv));log=out/(name+'.log')
        with log.open('w') as f:r=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        if Path(argv[0]).name=='simv':
            case=next((x.split('=',1)[1] for x in argv if x.startswith('+case=')),'healthy')
            wave=out/('rocket-native-queues-'+case+'.vcd')
            require(wave.is_file() and wave.stat().st_size>0,'missing full debug waveform')
            original_sha=sha(wave)
            compressed=wave.with_suffix('.vcd.gz')
            require(shutil.which('pigz') is not None,'native EDA pigz required for lossless full-wave compression')
            compression=['pigz','-p','4','-1','-c',str(wave)]
            with compressed.open('wb') as stream:subprocess.run(compression,stdout=stream,check=True)
            subprocess.run(['pigz','-p','4','-t',str(compressed)],check=True)
            # Keep the original bytes on EDA, excluded from bulk return syncing;
            # return every byte in the lossless compressed artifact instead.
            retained=RUNS/'migration-source'/out.parent.parent.name/out.name/wave.name
            retained.parent.mkdir(parents=True,exist_ok=True)
            wave.rename(retained)
            doc.setdefault('waveforms',[]).append(dict(original_remote_path=str(wave),retained_remote_path=str(retained),
                original_sha256=original_sha,compressed_path=str(compressed),compressed_sha256=sha(compressed)))
            doc['commands'].append(dict(argv=compression,purpose='lossless full-visibility waveform compression',returncode=0))
        doc['commands'].append(dict(argv=argv,cwd=str(out),returncode=r.returncode,log=str(log),sha256=sha(log)));save()
        require(r.returncode==expected,'inspect underlying log '+str(log));return log.read_text()
    save();print(out,flush=True)
    if a.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native manager Vivado required')
        shutil.copytree(a.generated,out/'generated')
        for n in RTL:shutil.copyfile(ROOT/n,out/Path(n).name)
        shutil.copyfile(ROOT/TB,out/'bench.sv')
        shutil.copyfile(ROOT/'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',out/'exit.cc')
        for n in ['BUFGCE.v','glbl.v']:
            src=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'/('unisims/'+n if n=='BUFGCE.v' else n)
            shutil.copyfile(src,out/n)
        rows,obs=audit_generated(out/'generated')
        manifest=capture_manifest(out/'generated',rows,obs);digest=hashlib.sha256(canonical(manifest)).hexdigest()
        (out/'capture-manifest.json').write_bytes(canonical(manifest))
        (out/'wrapper.sv').write_text(wrapper(out/'generated',rows,digest))
        (out/'oracle.svh').write_text(oracle(out/'generated',rows,obs))
        tcl='''set_param general.maxThreads 4
read_verilog -sv generated/generated.sv
'''+''.join('read_verilog -sv '+Path(n).name+'\n' for n in RTL)+'''read_verilog -sv wrapper.sv
read_xdc generated/generated.synthesis.xdc
synth_design -top RocketNativeQueueTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
foreach q {0 1 2 3} {
    set count 0
    foreach cell [get_cells -hier -filter {REF_NAME =~ URAM*}] {
        if {[string match "host/q$q/*" [get_property NAME $cell]]} {incr count}
    }
    if {$count != 16} {error "exact ULTRA queue $q did not map to sixteen URAMs: $count"}
    foreach cell [get_cells -hier -filter {REF_NAME =~ RAM*}] {
        if {[string match "host/q$q/*" [get_property NAME $cell]]} {error "ULTRA queue fell back to $cell"}
    }
    puts "ROCKET_QUEUE_ULTRA q=$q primitives=$count"
}
report_utilization -file utilization.rpt
report_timing_summary -delay_type min_max -file timing.rpt
write_checkpoint -force rocket-native-queues.dcp
puts "ROCKET_NATIVE_QUEUE_SYNTH_PASS"
'''
        (out/'synth.tcl').write_text(tcl)
        doc['inputs']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='summary.json'};save()
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'native')
        require('ROCKET_NATIVE_QUEUE_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:|Infeasible attribute',text),'native synthesis failure')
        timing=(out/'timing.rpt').read_text()
        require('There are 0 combinational loops' in timing and 'There are 0 combinational latch loops' in timing,'structural permission loop')
        doc.update(ultra_primitives=64,original_stored_bits=12583072,native_bits=6656,entries=20)
    else:
        require(str(ROOT).startswith('/scratch/') and toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'),'fresh EDA SP2 required')
        receipt=a.native/'summary.json';native=json.loads(receipt.read_text())
        require(native['status']=='pass' and native['sources']==sources,'stale native receipt')
        for group in ['inputs','artifacts']:
            for n,h in native[group].items():require(sha(a.native/n)==h,'changed native artifact '+n)
        for n in native['inputs']:
            dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/n,dest)
        rows,obs=audit_generated(out/'generated')
        manifest=capture_manifest(out/'generated',rows,obs);digest=hashlib.sha256(canonical(manifest)).hexdigest()
        require((out/'wrapper.sv').read_text()==wrapper(out/'generated',rows,digest),'changed capture connection')
        require((out/'oracle.svh').read_text()==oracle(out/'generated',rows,obs),'changed independent oracle')
        argv=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
            '+incdir+'+str(out),'-top','rocket_native_queues_tb','-top','glbl','-Mdir='+str(out/'csrc'),'-o',str(out/'simv'),
            out/'generated/generated.sv',*[out/Path(n).name for n in RTL],out/'wrapper.sv',out/'bench.sv',out/'exit.cc',out/'BUFGCE.v',out/'glbl.v']
        run(argv,'compile')
        text=run([out/'simv','-no_save'],'healthy')
        require('ROCKET_NATIVE_QUEUES_PASS cuts=4' in text,'incomplete queue capture')
        for case in ['missing','owner-error','abort']:
            text=run([out/'simv','-no_save','+case='+case],case)
            require('ROCKET_NATIVE_QUEUES_NEGATIVE_PASS '+case in text,'incomplete owner/abort negative')
        doc['native_receipt']=dict(path=str(receipt),sha256=sha(receipt))
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'sources changed during verification')
    doc['artifacts']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.suffix in ['.rpt','.log','.dcp','.vcd','.bin','.gz']}
    doc['status']='pass';save();print(out/'summary.json',flush=True)

if __name__=='__main__':main()
