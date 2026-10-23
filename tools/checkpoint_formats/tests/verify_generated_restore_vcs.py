"""Generated FPGATop component loading and fresh VCS continuation.

Replay actual captured HOST inputs to the complete generated RTL. Host native
owners/harness/driver continuations are outside this component test; this is
not a fresh whole FireSim .fsckpt restart. Source vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re

from tools.checkpoint_formats.codec import bit_value, canonical, require
from tools.checkpoint_formats.generated_restore import (generated_build_identity,
    prepare_generated_loader, prepare_generated_restore)
from tools.checkpoint_formats.simulator import generated_capture, generated_words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects
from tools.checkpoint_formats.tests.test_simulator import fixture


def ports(rtl):
    header = re.search(r'module FPGATop\((.*?)\n\);', rtl, re.S)
    require(header is not None, 'missing generated top')
    syntax = re.sub(r'//[^\n]*', '', header[1])
    result = []
    for declaration in syntax.split(','):
        match = re.fullmatch(r'\s*(input|output)\s*(?:\[(\d+):0\]\s*)?(\w+)\s*', declaration)
        require(match is not None, 'unsupported generated port syntax')
        direction, high, name = match.groups()
        result.append(dict(direction=direction, width=int(high)+1 if high else 1, name=name))
    require(sum(p['name'] == 'clock' for p in result) == 1, 'missing host clock')
    return result


def pack(rows, prefix):
    return '{' + ','.join(prefix + r.get('owner', r.get('name')) for r in rows) + '}'


def prepare_reference(words, layout, path):
    # Each capture is one picosecond after a falling edge, after all NBA and
    # BUFGCE updates. All clock provider outputs must consequently be low.
    inputs = [p for p in layout if p['direction'] == 'input' and p['name'] != 'clock']
    outputs = [p for p in layout if p['direction'] == 'output']
    fmt = '{"sample":%0d,"state":"%h","inputs":[' + ','.join('"%b"' for _ in inputs) + '],"outputs":"%b"}'
    expressions = [pack(words, 'emul.')] + ['emul.FPGATop.'+p['name'] for p in inputs] + [pack(outputs, 'emul.FPGATop.')]
    path.write_text('\n'.join([
        '`timescale 1ps/1ps', 'module generated_restore_reference();',
        'integer fd=0; integer sample=0; string filename;',
        'initial if ($value$plusargs("generated_restore_reference=%s",filename)) begin',
        '  fd=$fopen(filename,"w"); if (!fd) $fatal(1,"reference open"); end',
        'always @(negedge emul.clock) if (fd) begin', '  #1;',
        f'  $fdisplay(fd,{json.dumps(fmt)},sample,' + ','.join(expressions) + ');',
        '  sample=sample+1;', 'end', 'final if (fd) $fclose(fd);', 'endmodule',
        'bind FPGATop generated_restore_reference restore_reference();'])+'\n')


def prepare_tb(words, layout, out):
    inputs = [p for p in layout if p['direction'] == 'input' and p['name'] != 'clock']
    decl = [f"{'reg' if p['direction']=='input' else 'wire'} [{p['width']-1}:0] {p['name']}" +
            ('=0;' if p['direction']=='input' else ';') for p in layout]
    state_width = sum(w['width'] for w in words)
    output_ports = [p for p in layout if p['direction'] == 'output']
    output_width = sum(p['width'] for p in output_ports)
    source = ['`timescale 1ps/1ps', 'module generated_tb;',
        'import "DPI-C" context function int generated_restore(input string filename);',
        'import "DPI-C" context function int generated_restore_verify();',
        'import "DPI-C" context function void generated_restore_fail(input string message);',
        *decl, 'FPGATop FPGATop(' + ','.join('.'+p['name']+'('+p['name']+')' for p in layout) + ');',
        f'wire [{state_width-1}:0] all_state = {pack(words,"generated_tb.")};',
        f'wire [{output_width-1}:0] all_outputs = {pack(output_ports,"generated_tb.")};',
        f'reg [{state_width-1}:0] before_state, expected_state;',
        f'reg [{output_width-1}:0] expected_outputs;',
        'integer fd, status, expected_rows, rows=0, host_edges=0, target_edges=0, negatives=0;',
        'string restore_file, trace_file, negative_list, negative_file;',
        'always @(posedge clock) host_edges=host_edges+1;',
        'always @(posedge FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.O) target_edges=target_edges+1;',
        'initial begin', '  #2;',
        '  if ($value$plusargs("negative_list=%s", negative_list)) begin',
        '    fd=$fopen(negative_list,"r"); if (!fd) generated_restore_fail("negative list open");',
        '    before_state=all_state;',
        '    while ($fscanf(fd,"%s",negative_file)==1) begin',
        '      if (generated_restore(negative_file)!=1) generated_restore_fail("invalid load accepted");',
        '      #1;',
        '      if (all_state !== before_state || host_edges || target_edges) generated_restore_fail("invalid load mutated state or clock");',
        '      negatives=negatives+1;', '    end',
        '    $display("GENERATED_RESTORE_NEGATIVES: %0d rejected atomically",negatives); $finish;',
        '  end else begin',
        '    if (!$value$plusargs("restore=%s",restore_file) || !$value$plusargs("trace=%s",trace_file)) generated_restore_fail("missing arguments");',
        '    fd=$fopen(trace_file,"r"); if (!fd) generated_restore_fail("trace open");',
        '    if ($fscanf(fd,"%d",expected_rows)!=1 || expected_rows<=0) generated_restore_fail("trace count");',
        '    while (rows<expected_rows) begin',
        '      status=$fscanf(fd,"' + ' '.join('%b' for _ in inputs) + ' %h %b",' +
             ','.join(p['name'] for p in inputs) + ',expected_state,expected_outputs);',
        f'      if (status!={len(inputs)+2}) generated_restore_fail("trace row malformed");',
        '      #1;',
        '      if (rows==0) begin',
        '        if (generated_restore(restore_file)) generated_restore_fail("load rejected");',
        '        #1;', '        if (generated_restore_verify()) generated_restore_fail("readback");',
        '        if (host_edges || target_edges) generated_restore_fail("edge during load");',
        '      end',
        '      if (all_state !== expected_state || all_outputs !== expected_outputs) begin',
        '        $display("MISMATCH row=%0d state=%h expected=%h outputs=%h expected_outputs=%h",rows,all_state,expected_state,all_outputs,expected_outputs);',
        '        generated_restore_fail("continuation mismatch"); end',
        '      rows=rows+1;',
        '      if (rows<expected_rows) begin #4; clock=1; #5; clock=0; #1; end',
        '    end',
        '    $display("GENERATED_RESTORE_CONTINUATION: rows=%0d host_edges=%0d target_edges=%0d",rows,host_edges,target_edges);',
        '    $finish;', '  end', 'end', 'endmodule']
    (out/'generated-tb.sv').write_text('\n'.join(source)+'\n')
    return inputs, output_ports


def unpack_state(words, value):
    integer = int(value, 16)
    result = []
    for word in reversed(words):
        result.append(f"{integer & ((1 << word['width']) - 1):0{(word['width']+3)//4}x}")
        integer >>= word['width']
    require(integer == 0, 'nonzero packed state padding')
    return list(reversed(result))


def verify_native(out):
    native = out/'native'; native.mkdir(exist_ok=True)
    native_manifest=fixture()
    native_words=list(generated_words(native_manifest))
    native_capture=generated_capture(native_manifest,
        [f"{(1 << w['width'])-1:0{(w['width']+3)//4}x}" for w in native_words],0)
    prepare_generated_loader(native_manifest,'a'*64,native,'generated_tb.Top')
    prepare_generated_restore(native_manifest,native_capture,'a'*64,native/'wide.load','generated_tb.Top')
    run([os.environ['CXX'],'-std=c++17','-Wall','-Wextra','-Werror',
         '-Wno-write-strings','-fsanitize=address,undefined','-fno-omit-frame-pointer',
         '-I'+str(native),'-I'+os.environ['VCS_HOME']+'/include',
         ROOT/'tools/checkpoint_formats/tests/generated_restore_native.cc','-o',native/'verify'],native/'build.log')
    native_log=run([native/'verify',native/'wide.load'],native/'run.log')
    return int(re.search(r'rejections=(\d+)',native_log)[1])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out, build=args.out.resolve(),args.build.resolve()
    out.mkdir(parents=True,exist_ok=True)
    vcs=Path(os.environ['VCS_HOME'])/'bin/vcs'
    require(str(vcs)==_toolchain.VCS,'source vcs-env.sh LAST')
    native_rejections=verify_native(out)
    make=['make','DESIGN=InventoryFixture','TARGET_CONFIG=NoConfig','PLATFORM_CONFIG=DefaultF2Config',
          'SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut','SIMULATOR_CHECKPOINT_INVENTORY=FPGATop',f'BUILD_DIR={build}']
    simdir=ROOT/'sims/firesim/sim'
    run(make+['verilog'],out/'verilog.log',simdir)
    generated=build/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    manifest=json.loads((generated/'FireSim-generated.simulator-state.json').read_text())
    rtl=(generated/'FireSim-generated.sv').read_text()
    reference=(generated/'FireSim-generated.simulator-reference.fir').read_text()
    bufg=simdir/'midas/src/main/verilog/BUFGCE.v'
    build_hash=generated_build_identity(manifest,reference,rtl,bufg.read_text())
    words=list(generated_words(manifest)); layout=ports(rtl)
    (out/'manifest.json').write_bytes(canonical(manifest))
    (out/'port-layout.json').write_bytes(canonical(layout))
    prepare_reference(words,layout,out/'reference-probe.sv')
    invalidate_stale_driver_objects(generated,out/'rebuilt-driver-objects.json')
    run(make+['vcs',f'VCS={vcs} -full64','VCS_FLAGS=-Mupdate',f'VCS_EXTRA_V={out/"reference-probe.sv"}'],
        out/'reference-build.log',simdir)
    text=run([generated/'InventoryFixture','+vcs+initreg+0','+vcs+initmem+0',
              f'+generated_restore_reference={out/"reference.jsonl"}'],out/'reference-run.log')
    require('*** PASSED ***' in text,'reference metasim failed')
    rows=[json.loads(line) for line in (out/'reference.jsonl').read_text().splitlines()]
    state_width=sum(w['width'] for w in words)
    input_ports=[p for p in layout if p['direction']=='input' and p['name']!='clock']
    output_width=sum(p['width'] for p in layout if p['direction']=='output')
    for i,row in enumerate(rows):
        require(row['sample']==i,'reference sample order')
        # Validating the packed known-state vector checks every bit of every
        # manifested word once, without repeating manifest hashes per edge.
        bit_value(dict(width=state_width,value=row['state']))
        require(len(row['inputs'])==len(input_ports),'reference input membership')
        for port,value in zip(input_ports,row['inputs']):
            require(len(value)==port['width'] and re.fullmatch('[01xz]+',value),'reference input bits')
        require(len(row['outputs'])==output_width and re.fullmatch('[01xz]+',row['outputs']),'reference output bits')
    prepare_generated_loader(manifest,build_hash,out,rtl=rtl)
    inputs, outputs=prepare_tb(words,layout,out)
    run([vcs,'-full64','-sverilog','-debug_access+all','+vpi',
         '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-top','generated_tb',
         '-CFLAGS',f'-std=c++17 -I{out}',f'-Mdir={out/"csrc"}','-o',out/'simv',
         out/'generated-tb.sv',generated/'FireSim-generated.sv',bufg,
         ROOT/'tools/checkpoint_formats/generated_restore.cc'],out/'component-build.log')
    offsets={};offset=0
    for word in reversed(words):
        if '.dut.' in word['owner']:
            offsets[word['owner'].rsplit('.dut.',1)[-1]]=(offset,word['width'])
        offset+=word['width']
    def observed(row):
        value=int(row['state'],16)
        return {name:(value >> shift) & ((1 << width)-1) for name,(shift,width) in offsets.items()}
    predicates=[('active',lambda v:v['counter']>=1 and v['busy']==0),
                ('outstanding',lambda v:v['busy']==v['qValid']==1),
                ('held-response',lambda v:v['responseValid']==1)]
    cases=[]
    for label,predicate in predicates:
        cut=next(i for i,row in enumerate(rows) if predicate(observed(row)))
        capture=generated_capture(manifest,unpack_state(words,rows[cut]['state']),cut)
        staging=out/(label+'.load')
        prepare_generated_restore(manifest,capture,build_hash,staging)
        (out/(label+'.capture.json')).write_bytes(canonical(capture))
        trace=out/(label+'.trace')
        trace.write_text(str(len(rows)-cut)+'\n'+'\n'.join(' '.join([*row['inputs'],row['state'],row['outputs']])
            for row in rows[cut:])+'\n')
        result=run([out/'simv','+vcs+initreg+0','+vcs+initmem+0',f'+restore={staging}',f'+trace={trace}'],out/(label+'.log'))
        require(f'verified {len(words)} words before next edge' in result,'missing full pre-edge verification')
        require(f'rows={len(rows)-cut}' in result,'incomplete component continuation')
        cases.append(dict(label=label,cut=cut,samples=len(rows)-cut,words=len(words)))
    # Every missing row prefix and malformed membership/bits/header must reject
    # before any deposit, including corruption of the final manifested word.
    good=(out/'outstanding.load').read_text().splitlines()
    invalid=out/'invalid'; invalid.mkdir(exist_ok=True)
    variants=[good[:i] for i in range(len(good))]
    variants += [good+['extra'], good+[good[-1]], [good[0],*reversed(good[1:])]]
    for index in (1,len(good)-1):
        path,width,value=good[index].split()
        for altered in (f'{path} {int(width)+1} {value}',f'{path}.absent {width} {value}',
                        f'{path} {width} x',f'{path} {width} {value} extra'):
            bad=good.copy();bad[index]=altered;variants.append(bad)
    for column,replacement in ((0,'BAD'),(1,'0'*64),(2,'0'*64),(3,'settled_host_posedge_parked_driver'),(4,'1')):
        bad=good.copy();header=bad[0].split();header[column]=replacement;bad[0]=' '.join(header);variants.append(bad)
    clock_index=next(i for i,line in enumerate(good) if '.RationalClockBridge_clocks_0_buffer.O ' in line)
    bad=good.copy();bad[clock_index]=bad[clock_index][:-1]+'1';variants.append(bad)
    invalid_paths=[]
    for i,bad in enumerate(variants):
        path=invalid/f'{i}.load';path.write_text('\n'.join(bad)+'\n');invalid_paths.append(str(path))
    negative_list=out/'negative-list.txt';negative_list.write_text('\n'.join(invalid_paths)+'\n')
    result=run([out/'simv','+vcs+initreg+0','+vcs+initmem+0',f'+negative_list={negative_list}'],out/'invalid-loads.log')
    require(f'{len(variants)} rejected atomically' in result,'missing atomic rejection checks')
    summary=dict(scope='complete generated RTL component; host/harness replayed, no whole FireSim restart',
        manifest_entries=len(manifest['state']),words=len(words),bits=sum(w['width'] for w in words),
        reference_host_samples=len(rows),cases=cases,atomic_rejections=len(variants),
        native_sanitized_rejections=native_rejections,wide_native_bits=257,
        build_hash=build_hash,physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
