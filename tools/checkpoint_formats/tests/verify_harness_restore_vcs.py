"""Actual top.sv/generated RTL fresh harness-component continuation.

Host DPI outputs are recorded/replayed. No native/dispatcher restore or whole
.fsckpt restart is implied. Source both environments and vcs-env.sh LAST.
"""
import argparse
import json
import os
from pathlib import Path
import re

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.generated_restore import generated_build_identity, prepare_generated_loader, prepare_generated_restore
from tools.checkpoint_formats.harness_restore import harness_layout, harness_capture, prepare_harness_loader, prepare_harness_restore
from tools.checkpoint_formats.simulator import generated_capture, generated_words
from tools.checkpoint_formats.tests.verify_generated_restore_vcs import ports, pack, unpack_state
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects


def verify_native(layout, out):
    native=out/'native';native.mkdir(exist_ok=True)
    prepare_harness_loader(layout,native)
    values=[f'{(1 << row["width"])-1:0{(row["width"]+3)//4}x}' for row in layout['records']]
    values[-2:]=['0','0']
    staging=native/'ones.load'
    prepare_harness_restore(layout,harness_capture(layout,values,7),staging)
    run([os.environ['CXX'],'-std=c++17','-Wall','-Wextra','-Werror','-Wno-write-strings',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer',f'-I{native}',
         '-I'+os.environ['VCS_HOME']+'/include',ROOT/'tools/checkpoint_formats/tests/harness_restore_native.cc',
         '-o',native/'verify'],native/'build.log')
    result={}
    for mode in ('valid','advanced','readback','clock-during-load'):
        text=run([native/'verify',staging,mode],native/(mode+'.log'))
        result[mode]=int(re.search(r'rejections=(\d+)',text)[1])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    build=args.build.resolve(); simdir=ROOT/'sims/firesim/sim'
    vcs=Path(os.environ['VCS_HOME'])/'bin/vcs'
    require(str(vcs)=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs','source vcs-env.sh LAST')
    generated=build/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    make=['make','DESIGN=InventoryFixture','TARGET_CONFIG=NoConfig','PLATFORM_CONFIG=DefaultF2Config',
          'SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut','SIMULATOR_CHECKPOINT_INVENTORY=FPGATop',f'BUILD_DIR={build}']
    run(make+['verilog'],out/'verilog.log',simdir)
    manifest=json.loads((generated/'FireSim-generated.simulator-state.json').read_text())
    rtl=(generated/'FireSim-generated.sv').read_text()
    top=simdir/'midas/src/main/verilog/top.sv'; bufg=simdir/'midas/src/main/verilog/BUFGCE.v'
    const=generated/'FireSim-generated.const.vh'; defines=generated/'FireSim-generated.defines.vh'
    identity=generated_build_identity(manifest,(generated/'FireSim-generated.simulator-reference.fir').read_text(),rtl,bufg.read_text())
    layout=harness_layout(top.read_text(),const.read_text(),defines.read_text(),identity)
    native_rejections=verify_native(layout,out)
    words=list(generated_words(manifest)); topports=ports(rtl)
    outputs=[p for p in topports if p['direction']=='output']
    banks=layout['records']; bankwidth=sum(r['width'] for r in banks)
    fmt='{"sample":%0d,"state":"%h","banks":['+','.join('"%h"' for _ in banks)+'],"outputs":"%b"}'
    expressions=[pack(words,'emul.')]+[r['owner'] for r in banks]+[pack(outputs,'emul.FPGATop.')]
    reference=out/'reference-probe.sv'
    reference.write_text('\n'.join(['`timescale 1ps/1ps','module harness_reference;',
        'integer fd=0; integer sample=0; string filename;',
        'initial if ($value$plusargs("harness_reference=%s",filename)) begin fd=$fopen(filename,"w"); if (!fd) $fatal(1,"reference open"); end',
        'always @(negedge emul.clock) if (fd) begin #1;',
        '$fdisplay(fd,'+json.dumps(fmt)+',sample,'+','.join(expressions)+'); sample=sample+1; end',
        'final if (fd) $fclose(fd); endmodule','bind FPGATop harness_reference reference();'])+'\n')
    invalidate_stale_driver_objects(generated,out/'rebuilt-driver-objects.json')
    run(make+['vcs',f'VCS={vcs} -full64','VCS_FLAGS=-Mupdate',f'VCS_EXTRA_V={reference}'],out/'reference-build.log',simdir)
    result=run([generated/'InventoryFixture','+vcs+initreg+0','+vcs+initmem+0',f'+harness_reference={out/"reference.jsonl"}'],out/'reference-run.log')
    require('*** PASSED ***' in result,'actual reference metasim failed')
    rows=[json.loads(line) for line in (out/'reference.jsonl').read_text().splitlines()]
    for index,row in enumerate(rows):
        require(row['sample']==index,'reference ordering')
        # Source-derived bank widths are independently checked against the
        # actual VCS $bits below, including all unconnected optional banks.
        require(len(row['banks'])==29,'incomplete reference banks')
    prepare_harness_loader(layout,out)
    prepare_generated_loader(manifest,identity,out,'emul.FPGATop',rtl=rtl)
    (out/'layout.json').write_bytes(canonical(layout))
    (out/'manifest.json').write_bytes(canonical(manifest))
    widths=[r['width'] for r in banks[9:18]]
    fixture='''#include <svdpi.h>
#include <vpi_user.h>
#include <fstream>
#include <string>
#include <cstdlib>
#include <cstdio>
#include <vector>
static std::ifstream output;
extern "C" void simulator_entry() {}
extern "C" svBit simulator_checkpoint_pending() { return 0; }
extern "C" svBit simulator_checkpoint_lowclock() { return 0; }
extern "C" void simulator_checkpoint_settled(unsigned,const svBitVecVal*,svBit*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*) { std::exit(1); }
extern "C" void harness_fixture_open(const char *path) { output.open(path); if (!output) std::exit(1); }
extern "C" void harness_fixture_flip_bank() {
 auto handle=vpi_handle_by_name(const_cast<char *>("emul.ctrl_fwd_sync"),nullptr);
 if (!handle) std::exit(1);
 s_vpi_value value{};value.format=vpiVectorVal;vpi_get_value(handle,&value);
 std::vector<s_vpi_vecval> bits(value.value.vector,value.value.vector+(vpi_get(vpiSize,handle)+31)/32);
 bits[0].aval^=1;value.value.vector=bits.data();vpi_put_value(handle,&value,nullptr,vpiNoDelay);
}
extern "C" void simulator_tick(svBit,svBit *fin,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,svBitVecVal *a,svBitVecVal *b,svBitVecVal *c,svBitVecVal *d,svBitVecVal *e,svBitVecVal *f,svBitVecVal *g,svBitVecVal *h,svBitVecVal *i) {
 svBitVecVal *dest[]={a,b,c,d,e,f,g,h,i};
 const unsigned widths[]={WIDTHS};
 if (!output.is_open()) { for (unsigned k=0;k<9;k++) for (unsigned j=0;j<(widths[k]+31)/32;j++) dest[k][j]=0; *fin=0; return; }
 for (unsigned k=0;k<9;k++) {
  std::string value; if (!(output>>value)) { std::fprintf(stderr,"DPI fixture exhausted\\n"); std::exit(1); }
  for (unsigned j=0;j<(widths[k]+31)/32;j++) dest[k][j]=0;
  for (size_t j=0;j<value.size();j++) { char x=value[value.size()-1-j]; unsigned n=x<='9'?x-'0':x-'a'+10; dest[k][j/8] |= n<<(4*(j%8)); }
 }
 unsigned finish; if (!(output>>finish) || finish>1) std::exit(1); *fin=finish;
}
'''.replace('WIDTHS',','.join(str(w) for w in widths))
    (out/'fixture.cc').write_text(fixture)
    decl=[f'if ($bits({r["owner"]})!={r["width"]}) harness_restore_fail("bank geometry");' for r in banks]
    state_width=sum(w['width'] for w in words); output_width=sum(p['width'] for p in outputs)
    monitor=['`timescale 1ps/1ps','module harness_monitor;',
        'import "DPI-C" context function int harness_restore_initialize();',
        'import "DPI-C" context function int harness_restore(input string filename);',
        'import "DPI-C" context function int harness_restore_verify();',
        'import "DPI-C" context function void harness_restore_fail(input string message);',
        'import "DPI-C" context function int generated_restore(input string filename);',
        'import "DPI-C" context function int generated_restore_verify();',
        'import "DPI-C" context function void harness_fixture_open(input string filename);',
        'import "DPI-C" context function void harness_fixture_flip_bank();',
        f'wire [{state_width-1}:0] state={pack(words,"emul.")};',
        f'wire [{bankwidth-1}:0] banks={pack(banks,"")};',
        f'wire [{output_width-1}:0] outputs={pack(outputs,"emul.FPGATop.")};',
        f'reg [{state_width-1}:0] expected_state, before_state;',
        f'reg [{bankwidth-1}:0] expected_banks, before_banks;',
        f'reg [{output_width-1}:0] expected_outputs;',
        'integer fd=0, count, samples=0, host_edges=0, target_edges=0, negatives=0;',
        'string checkpoint, generated_checkpoint, trace, native_outputs, negative_list, bad, guard;',
        'always @(posedge emul.clock) host_edges=host_edges+1;',
        'always @(posedge emul.FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.O) target_edges=target_edges+1;',
        'task compare; begin',
        ' if ($fscanf(fd,"%h %h %b",expected_state,expected_banks,expected_outputs)!=3) harness_restore_fail("trace row");',
        ' if (state!==expected_state || banks!==expected_banks || outputs!==expected_outputs) begin',
        ' $display("MISMATCH sample=%0d banks=%h expected=%h",samples,banks,expected_banks); harness_restore_fail("continuation mismatch"); end',
        ' samples=samples+1;',
        ' if (samples==count) begin $display("HARNESS_CONTINUATION samples=%0d host_edges=%0d target_edges=%0d",samples,host_edges,target_edges); $finish; end',
        'end endtask',
        'initial begin',*decl,
        ' if ($value$plusargs("guard=%s",guard) && guard=="unsupported") begin if (harness_restore_initialize()!=1 || host_edges || target_edges) harness_restore_fail("unsupported harness accepted"); $display("HARNESS_GUARD unsupported zero edges"); $finish; end',
        ' if ($value$plusargs("guard=%s",guard) && guard=="late-initialize") begin #2; if (harness_restore_initialize()!=1 || host_edges || target_edges) harness_restore_fail("late initialization accepted"); $display("HARNESS_GUARD late-initialize zero edges"); $finish; end',
        ' if (harness_restore("/unarmed")!=1) harness_restore_fail("unarmed load accepted");',
        ' if (harness_restore_initialize()) harness_restore_fail("initialize");',
        ' #2;',
        ' if (guard=="advanced") begin',
        ' if (!$value$plusargs("harness=%s",checkpoint)) harness_restore_fail("guard arguments");',
        ' emul.clock=1; #1; emul.clock=0; #1; before_state=state; before_banks=banks;',
        ' if (harness_restore(checkpoint)!=1) harness_restore_fail("advanced load accepted");',
        ' #1; if (state!==before_state || banks!==before_banks || host_edges!=1) harness_restore_fail("advanced rejection mutation");',
        ' $display("HARNESS_GUARD advanced unchanged after one host edge"); $finish; end',
        ' if (guard=="readback") begin',
        ' if (!$value$plusargs("harness=%s",checkpoint) || harness_restore(checkpoint)) harness_restore_fail("readback guard load");',
        ' #1; harness_fixture_flip_bank(); #1;',
        ' if (harness_restore_verify()!=1) harness_restore_fail("corrupted readback accepted");',
        ' harness_fixture_flip_bank(); #1;',
        ' if (harness_restore_verify()!=1 || harness_restore(checkpoint)!=1 || host_edges || target_edges) harness_restore_fail("poisoned load reused");',
        ' $display("HARNESS_GUARD readback poisoned with zero edges"); $finish; end',
        ' if ($value$plusargs("negative_list=%s",negative_list)) begin',
        ' fd=$fopen(negative_list,"r"); before_state=state; before_banks=banks;',
        ' while ($fscanf(fd,"%s",bad)==1) begin',
        ' if (harness_restore(bad)!=1) harness_restore_fail("invalid accepted");',
        ' #1; if (state!==before_state || banks!==before_banks || host_edges || target_edges) harness_restore_fail("invalid mutated or advanced"); negatives=negatives+1; end',
        ' $display("HARNESS_NEGATIVES count=%0d",negatives); $finish;',
        ' end else begin',
        ' if (!$value$plusargs("harness=%s",checkpoint) || !$value$plusargs("generated=%s",generated_checkpoint) || !$value$plusargs("trace=%s",trace) || !$value$plusargs("native_outputs=%s",native_outputs)) harness_restore_fail("arguments");',
        ' fd=$fopen(trace,"r"); if (!fd || $fscanf(fd,"%d",count)!=1 || count<2) harness_restore_fail("trace header");',
        ' harness_fixture_open(native_outputs);',
        ' if (harness_restore(checkpoint) || generated_restore(generated_checkpoint)) harness_restore_fail("load");',
        ' #1; if (harness_restore_verify() || generated_restore_verify() || host_edges || target_edges) harness_restore_fail("pre-edge verification");',
        ' if (harness_restore(checkpoint)!=1) harness_restore_fail("repeated load accepted");',
        ' compare;',
        ' end end',
        'always @(negedge emul.clock) if (fd && guard=="") begin #1; compare; end',
        'endmodule', 'bind FPGATop harness_monitor monitor();']
    (out/'monitor.sv').write_text('\n'.join(monitor)+'\n')
    wrapper=out/'harness.sv'
    wrapper.write_text(f'`include "{const}"\n`include "{defines}"\n`include "{top}"\n')
    run([vcs,'-full64','-sverilog','-debug_access+all','+vpi','+vcs+initreg+random','+define+VCS','+define+CLOCK_PERIOD=1',
         '-timescale=1ns/1ps','-top','emul','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
         '-CFLAGS',f'-std=c++17 -I{out}',f'-Mdir={out/"csrc"}','-o',out/'simv',wrapper,out/'monitor.sv',
         generated/'FireSim-generated.sv',bufg,out/'fixture.cc',ROOT/'tools/checkpoint_formats/harness_restore.cc',
         ROOT/'tools/checkpoint_formats/generated_restore.cc'],out/'component-build.log')
    offsets={}; offset=0
    for word in reversed(words):
        if '.dut.' in word['owner']: offsets[word['owner'].rsplit('.dut.',1)[-1]]=(offset,word['width'])
        offset+=word['width']
    def observed(row):
        value=int(row['state'],16)
        return {n:(value>>s)&((1<<w)-1) for n,(s,w) in offsets.items()}
    cases=[]
    for label,predicate in [('active',lambda v:v['counter']>=1 and not v['busy']),
                            ('outstanding',lambda v:v['busy']==v['qValid']==1),
                            ('held-response',lambda v:v['responseValid']==1)]:
        cut=next(i for i,row in enumerate(rows) if predicate(observed(row)))
        checkpoint=out/(label+'.harness.load'); gen=out/(label+'.generated.load')
        captured=harness_capture(layout,rows[cut]['banks'],cut)
        prepare_harness_restore(layout,captured,checkpoint)
        (out/(label+'.harness.json')).write_bytes(canonical(captured))
        prepare_generated_restore(manifest,generated_capture(manifest,unpack_state(words,rows[cut]['state']),cut),identity,gen,'emul.FPGATop')
        trace=out/(label+'.trace'); native=out/(label+'.dpi-outputs')
        def bank_vector(row):
            result=0
            for r,value in zip(banks,row['banks']): result=(result<<r['width'])|int(value,16)
            return f'{result:x}'
        trace.write_text(str(len(rows)-cut)+'\n'+'\n'.join(' '.join([r['state'],bank_vector(r),r['outputs']]) for r in rows[cut:])+'\n')
        native.write_text('\n'.join(' '.join([*r['banks'][9:18],r['banks'][-1]]) for r in rows[cut+1:])+'\n')
        result=run([out/'simv','+vcs+initreg+0','+vcs+initmem+0',f'+harness={checkpoint}',f'+generated={gen}',f'+trace={trace}',f'+native_outputs={native}'],out/(label+'.log'))
        require(f'HARNESS_CONTINUATION samples={len(rows)-cut}' in result,'incomplete continuation')
        require('HARNESS_RESTORE: verified 29 words before next edge' in result,'missing bank readback')
        cases.append(dict(label=label,cut=cut,samples=len(rows)-cut,banks=29,generated_words=len(words)))
    good=(out/'outstanding.harness.load').read_text().splitlines()
    variants=[good[:i] for i in range(len(good))]+[good+['extra'],[good[0],*reversed(good[1:])],good+[good[-1]]]
    for col,replacement in [(0,'BAD'),(1,'0'*64),(2,'0'*64),(3,'settled_host_posedge'),(4,'28')]:
        bad=good.copy(); header=bad[0].split();header[col]=replacement;bad[0]=' '.join(header); variants.append(bad)
    for idx in (1,len(good)-1,len(good)-2):
        owner,width,value=good[idx].split()
        for changed in [f'{owner}.absent {width} {value}',f'{owner} {int(width)+1} {value}',f'{owner} {width} x',f'{owner} {width} {value} extra',f'{owner} {width} '+('f'*((int(width)+3)//4))]:
            bad=good.copy();bad[idx]=changed;variants.append(bad)
    invalid=out/'invalid';invalid.mkdir(exist_ok=True); paths=[]
    for i,bad in enumerate(variants):
        path=invalid/f'{i}.load';path.write_text('\n'.join(bad)+'\n');paths.append(str(path))
    negatives=out/'negative-list.txt';negatives.write_text('\n'.join(paths)+'\n')
    result=run([out/'simv','+vcs+initreg+0','+vcs+initmem+0',f'+negative_list={negatives}'],out/'invalid-loads.log')
    require(f'HARNESS_NEGATIVES count={len(variants)}' in result,'incomplete invalid rejection')
    guards=[]
    for mode in ('late-initialize','advanced','readback'):
        text=run([out/'simv','+vcs+initreg+0','+vcs+initmem+0',f'+guard={mode}',
                  f'+harness={out/"outstanding.harness.load"}'],out/(mode+'-guard.log'))
        require('HARNESS_GUARD '+mode in text,'missing VCS lifecycle guard')
        guards.append(mode)
    run([vcs,'-full64','-sverilog','-debug_access+all','+vpi','+vcs+initreg+random','+define+VCS','+define+CLOCK_PERIOD=1',
         '+define+DEBUG','-timescale=1ns/1ps','-top','emul','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
         '-CFLAGS',f'-std=c++17 -I{out}',f'-Mdir={out/"debug-csrc"}','-o',out/'debug-simv',wrapper,out/'monitor.sv',
         generated/'FireSim-generated.sv',bufg,out/'fixture.cc',ROOT/'tools/checkpoint_formats/harness_restore.cc',
         ROOT/'tools/checkpoint_formats/generated_restore.cc'],out/'unsupported-debug-build.log')
    text=run([out/'debug-simv','+vcs+initreg+0','+vcs+initmem+0','+guard=unsupported'],out/'unsupported-guard.log')
    require('unsupported debug/gate-level harness state' in text and 'HARNESS_GUARD unsupported zero edges' in text,
            'unsupported DEBUG state not rejected')
    guards.append('unsupported')
    summary=dict(scope='actual harness/generated RTL; recorded native DPI outputs, no dispatcher/.fsckpt restore',
                 cases=cases,atomic_rejections=len(variants),native_rejections=native_rejections,
                 vcs_lifecycle_guards=guards,harness_bits=bankwidth,reference_samples=len(rows),whole_runtime_restore_verified=False)
    (out/'summary.json').write_bytes(canonical(summary));print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
