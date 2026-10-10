"""Full production-entry FCFS/FASED aggregate VCS restart.

Uses the generated registry and actual driver, MMIO, native memories, harness
and dispatcher. The default capability is restricted; --public-restore links
the concrete native durable restore consumer. Public capture remains disabled. Source env.sh,
FireSim env.sh and vcs-env.sh LAST. No FPGA validation is claimed.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import shutil
import tempfile

from tools.checkpoint_formats import aggregate_packed as packed
from tools.checkpoint_formats.aggregate import build_identity, prepare_aggregate_loader
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.durable_restore import prepare_durable_loader
from tools.checkpoint_formats.generated_restore import generated_build_identity, prepare_generated_loader
from tools.checkpoint_formats.harness_restore import harness_layout, harness_capture, prepare_harness_loader
from tools.checkpoint_formats.simulator import prepare_settled_generated_probe
from tools.checkpoint_formats.tests.verify_driver_boundary_vcs import read_diagnostic
from tools.checkpoint_formats.tests.verify_generated_restore_vcs import verify_native
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def prepare_output(path, normal_make):
    out = path.resolve(); out.mkdir(parents=True, exist_ok=True)
    if normal_make and ((out/'simv').exists() or (out/'simv').is_symlink()):
        # Keep the executable, companion libraries, checkpoints and old source
        # bindings together. A repeated verification runs every check afresh.
        out = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
        print('NORMAL_MAKE_VERIFICATION_OUTPUT '+str(out), flush=True)
    return out


def compare_target_trace(expected, observed, fields, cut, sample):
    """Report the first target-cycle/port difference, including inactive ports."""
    for index in range(max(len(expected), len(observed))):
        e = expected[index] if index < len(expected) else None
        a = observed[index] if index < len(observed) else None
        if e == a:
            continue
        cycle = (e or a).split()[0]
        signal, ev, av = 'trace_length', len(expected), len(observed)
        if e is not None and a is not None:
            ec, ef, eb = e.split(); ac, af, ab = a.split()
            if ec != ac: signal, ev, av = 'FASED.model.tCycle', ec, ac
            elif ef != af: signal, ev, av = 'FASED.targetFire', ef, af
            else:
                ev, av = int(eb, 16), int(ab, 16)
                offset = 0
                signal = 'trace_format'
                for shape, name in reversed(fields):
                    width = 1 if not shape else int(shape[1:-1].split(':')[0])-int(shape[1:-1].split(':')[1])+1
                    mask = (1 << width)-1
                    if ((ev ^ av) >> offset) & mask:
                        signal, ev, av = name, (ev >> offset)&mask, (av >> offset)&mask
                        break
                    offset += width
        require(False, f'FIRST_MISMATCH cut={cut} host_sample={sample+index+1} target_cycle={cycle} '
                       f'signal={signal} expected={ev} actual={av}')


def verify_rejections(common, out, owner_rows, manifest):
    # Native payload and late complete generated/harness preparation failures
    # must leave ALL owners unmodified, with no loads/deposits or rising edge.
    first = out/'default/cut-3'
    good = (first/'aggregate.load').read_text().splitlines(keepends=True)
    failures = []
    for index, row in enumerate(owner_rows, 1):
        altered = good.copy(); fields = altered[index].split()
        fields[3] = str(int(fields[3])-1); fields[4] = fields[4][:-2]
        altered[index] = ' '.join(fields)+'\n'
        failures.append(('native-'+row['owner'].replace('/','-'), altered))
    altered = good.copy(); fields=altered[1].split(); fields[2]='unsupported'; altered[1]=' '.join(fields)+'\n'
    failures.append(('native-schema',altered))
    altered = good.copy(); altered[1],altered[2]=altered[2],altered[1]
    failures.append(('native-order',altered))
    gi = 1+len(owner_rows)
    hi = gi+2+len(manifest['state'])
    for label, index, section_start, section_end in [
            ('late-generated-shape', hi-1, gi+1, hi),
            ('late-harness-shape', len(good)-1, hi+1, len(good))]:
        altered=good.copy();fields=altered[index].split();fields[1]=str(int(fields[1])+1)
        altered[index]=' '.join(fields)+'\n'
        altered[section_start-1]=good[section_start-1].split()[0]+' '+str(sum(len(s) for s in altered[section_start:section_end]))+'\n'
        failures.append((label,altered))
    failures.append(('trailing-section', [*good,'extra\n']))
    altered=good.copy(); header=altered[0].split(); header[2]=str(int(header[2])+1)
    altered[0]=' '.join(header)+'\n'; failures.append(('target-cycle',altered))
    negative_results=[]
    for label, lines in failures:
        case=out/'negative'/label;case.mkdir(parents=True,exist_ok=True)
        (case/'aggregate.load').write_text(''.join(lines))
        text=run([*common,f'+test-aggregate={case/"aggregate.load"}',f'+test-negative={label}'],case/'run.log',case)
        require('native_loads=0 deposits=0' in text and 'PRODUCTION_NEGATIVE zero_edges=1' in text,
                'production rejection mutated an owner or advanced clocks')
        negative_results.append(label)
    unsupported=out/'unsupported';unsupported.mkdir(exist_ok=True)
    text=run([*common,f'+test-aggregate={first/"aggregate.load"}','+profile-interval=250000'],
             unsupported/'run.log',unsupported,expected=1)
    require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'unsupported' in text and
            'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
            'unaudited production callback did not fail closed')
    # Real fresh processes with changed configuration or an extra loaded ELF
    # must reject during all-owner prevalidation before ANY native/VPI state loads.
    runtime_rejections=[]
    for label, change in [('memory',['+memsize=4194368']), ('horizon',['+max-cycles=1000001']),
                          ('host-delay',['+fuzz-host-timing=2']), ('seed',['+fuzz-seed=1'])]:
        case=out/'runtime-negative'/label;case.mkdir(parents=True,exist_ok=True)
        replacement={arg.split('=')[0] for arg in change}
        configured=[arg for arg in common if str(arg).split('=')[0] not in replacement]+change
        text=run([*configured,f'+test-aggregate={first/"aggregate.load"}',f'+test-negative={label}'],
                 case/'run.log',case)
        expected_error = {'memory':'incompatible AXI/backing-memory geometry',
                          'horizon':'incompatible scheduler configuration',
                          'host-delay':'incompatible timing configuration',
                          'seed':'incompatible timing configuration'}[label]
        require(expected_error in text and
                'native_loads=0 deposits=0' in text and 'PRODUCTION_NEGATIVE zero_edges=1' in text,
                'changed runtime configuration did not reject atomically')
        runtime_rejections.append(label)
    preload=out/'preload.cc';preload.write_text('extern "C" int checkpoint_extra_library() { return 33; }\n')
    run([os.environ['CXX'],'-shared','-fPIC',preload,'-o',out/'preload.so'],out/'preload-build.log')
    case=out/'runtime-negative/loaded-library';case.mkdir(parents=True,exist_ok=True)
    text=run([*common,f'+test-aggregate={first/"aggregate.load"}',f'+test-extra-library={out/"preload.so"}',
              '+test-negative=loaded-library'],case/'run.log',case)
    require('configuration/loaded ELF changed after entry' in text and 'native_loads=0 deposits=0' in text
            and 'PRODUCTION_NEGATIVE zero_edges=1' in text,'changed loaded library did not reject atomically')
    runtime_rejections.append('loaded-library')
    case=out/'runtime-negative/preload-hook';case.mkdir(parents=True,exist_ok=True)
    text=run(['env',f'LD_PRELOAD={out/"preload.so"}',*common,f'+test-aggregate={first/"aggregate.load"}'],
             case/'run.log',case,expected=1)
    require('unsupported LD_PRELOAD/LD_AUDIT library hooks' in text and
            'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text, 'unaudited preload hook accepted')
    runtime_rejections.append('preload-hook')
    # Sanitize both staging encodings, with wide registers and memory padding.
    native_rejections = verify_native(out)
    native_out = out/'native'
    old = (native_out/'wide.load').read_text().splitlines()
    lines = [old[0].replace('FSGRTL1','FSGRTL2')]
    from tools.checkpoint_formats.tests.test_simulator import fixture
    index = 1
    for entry in fixture()['state']:
        bits = ''.join(line.split()[2] for line in old[index:index+entry['depth']])
        lines.append(f'generated_tb.{entry["hierarchy"]} {entry["width"]} {entry["depth"]} {bits}')
        index += entry['depth']
    (native_out/'wide-packed.load').write_text('\n'.join(lines)+'\n')
    run([native_out/'verify',native_out/'wide-packed.load'], native_out/'packed.log')
    return dict(malformed_processes=negative_results, unsupported_callback_rejected=True,
                runtime_compatibility_rejections=runtime_rejections,
                fixture_word_sanitizer_rejections=native_rejections)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--public-restore', action='store_true',
                        help='Link the concrete native durable restore capability and use +fs-restore')
    parser.add_argument('--live-capture', action='store_true',
                        help='Collect/publish the complete live cut natively; verify every byte against Python')
    parser.add_argument('--public-capture', action='store_true',
                        help='Use public operation scheduling and the ordinary opt-in harness capture callback')
    parser.add_argument('--normal-make', action='store_true',
                        help='Build the public capability and production restore coordinator through ordinary Make')
    parser.add_argument('--resume-after-continuations', action='store_true',
                        help='Recheck this run\'s completed continuations and rerun every rejection/sanitizer scope')
    args = parser.parse_args()
    if args.normal_make:
        args.public_capture = True
    if args.public_capture:
        args.public_restore = args.live_capture = True
    require(not args.live_capture or args.public_restore, 'live capture requires the durable capability')
    require(not (args.public_restore and args.resume_after_continuations),
            'public restoration must run its full verification, without restricted resumption')
    out = prepare_output(args.out, args.normal_make)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'preserve VCS compiler setup')
    if args.resume_after_continuations:
        manifest=json.loads((out/'generated-manifest.json').read_text())
        runtime=json.loads((out/'runtime-manifest.json').read_text())
        layout=json.loads((out/'harness-layout.json').read_text())
        build=json.loads((out/'aggregate-build.json').read_text())
        inputs=json.loads((out/'native-build-inputs.json').read_text())
        require(hashlib.sha256(canonical(inputs)).hexdigest()==runtime['native_build_hash'] and
                all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value
                    for name,value in inputs['sources'].items()),'changed native implementation in resumed run')
        require(build_identity(runtime,manifest,layout,out/'simv')==build,'changed executable in resumed run')
        results=json.loads((out/'partial-results.json').read_text())
        require({(r['timing'],r['cut']) for r in results}=={('default',3),('default',11),
                ('default',699275),('default',699276),('randomized',101)} and len(results)==5,
                'resumption requires all five completed fresh continuations')
        fields=json.loads((out/'target-port-layout.json').read_text())
        for r in results:
            case=out/r['timing']/f'cut-{r["cut"]}'
            text=(case/'restore.log').read_text()
            require(text.endswith('exit=0\n') and '*** PASSED ***' in text
                    and f'Target Cycles Emulated: {r["target_completion"]}\n' in text
                    and 'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text
                    and 'PRODUCTION_BOOTSTRAP zero_edges=1' in text,'incomplete continuation evidence')
            packed.decode_aggregate((case/'capture.fsckpt').read_bytes(),build,runtime,manifest,layout)
            reference=(out/r['timing']/'reference/ports.trace').read_text().splitlines(keepends=True)
            require((case/'capture.trace').read_text().splitlines(keepends=True)==reference,'changed capture evidence')
            compare_target_trace(reference[r['host_sample']:],(case/'restore.trace').read_text().splitlines(keepends=True),
                                 fields,r['cut'],r['host_sample'])
        common=[out/'simv','-no_save','+vcs+initreg+0','+vcs+initmem+0','+memsize=4194304','+max-cycles=1000000']
        rejections=verify_rejections(common,out,runtime['native_owners'],manifest)
        summary=dict(cases=results,**rejections,test_entry_production_continuation_verified=True,
                     real_production_entry_verified=True,
                     production_plusargs_enabled=False,physical_fpga_validated=False)
        (out/'summary.json').write_bytes(canonical(summary))
        print('PASS: rechecked all five fresh continuations and reran every rejection/sanitizer scope',flush=True)
        return
    generated = args.build.resolve()/'f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config'
    cc = ROOT/'sims/firesim/sim/midas/src/main/cc'
    verilog = ROOT/'sims/firesim/sim/midas/src/main/verilog'
    tests = Path(__file__).resolve().parent
    manifest = json.loads((generated/'FireSim-generated.simulator-state.json').read_text())
    rtl = (generated/'FireSim-generated.sv').read_text()
    identity = generated_build_identity(manifest, (generated/'FireSim-generated.simulator-reference.fir').read_text(),
                                        rtl, (verilog/'BUFGCE.v').read_text())
    layout = harness_layout((verilog/'top.sv').read_text(), (generated/'FireSim-generated.const.vh').read_text(),
                            (generated/'FireSim-generated.defines.vh').read_text(), identity)
    prepare_generated_loader(manifest, identity, out, 'emul.FPGATop', rtl=rtl)
    prepare_harness_loader(layout, out)
    prepare_settled_generated_probe(manifest, out, lowclock=True)
    # Concrete owner enumeration is pinned to this generated production profile.
    # It is checked against the real registry and diagnostic at every cut.
    old = ROOT/'automations/checkpoint_loop/runs/m4-iteration28/lowclock-final/default/cut-699275/software.diag'
    _, inventory = read_diagnostic(old)
    owner_rows = [dict(owner=name, schema=schema) for name, (schema, _) in inventory.items()
                  if schema and name != 'diagnostic/harness-banks']
    compatibility = dict(owner='runtime/compatibility', schema='firesim.runtime.fcfs-config-and-loaded-elf.v1')
    owner_rows.append(compatibility)
    capability = ROOT/'tools/checkpoint_formats/durable_restore_entry.cc' if args.public_restore else tests/'production_aggregate_checkpoint.cc'
    sources = [cc/'entry.cc', capability, cc/'simif_emul_all.cc', *sorted((cc/'core').glob('*.cc')),
               *[cc/p for p in ('emul/simif_emul.cc', 'emul/dpi.cc', 'emul/mm.cc', 'emul/mmio.cc',
                               'emul/qsfp.cc', 'emul/host_timing.cc', 'bridges/master.cc', 'bridges/clock.cc',
                               'bridges/loadmem.cc', 'bridges/peek_poke.cc', 'bridges/reset_pulse.cc',
                               'bridges/fased_memory_timing_model.cc')],
               ROOT/'sims/firesim/sim/src/main/cc/fasedtests/fasedtests_top.cc',
               ROOT/'tools/checkpoint_formats/aggregate_restore.cc',
               ROOT/'tools/checkpoint_formats/runtime_identity.cc',
               ROOT/'tools/checkpoint_formats/generated_restore.cc',
               ROOT/'tools/checkpoint_formats/harness_restore.cc']
    if args.public_restore:
        sources += [ROOT/'tools/checkpoint_formats/durable_restore.cc',
                    ROOT/'tools/checkpoint_formats/durable_publish.cc',
                    ROOT/'tools/checkpoint_formats/durable_history.cc',
                    ROOT/'tools/checkpoint_formats/progress_watchdog.cc',
                    ROOT/'tools/checkpoint_formats/durable_capture.cc']
    dependencies = sorted({*sources, *cc.rglob('*.h'), *cc.rglob('*.cc'),
                           ROOT/'tools/checkpoint_formats/aggregate_restore.h',
                           ROOT/'tools/checkpoint_formats/runtime_identity.h', generated/'FireSim-generated.const.h'})
    if args.public_restore:
        dependencies += [ROOT/'tools/checkpoint_formats/durable_restore.h',
                         ROOT/'tools/checkpoint_formats/durable_history.h',
                         ROOT/'tools/checkpoint_formats/progress_watchdog.h',
                         ROOT/'tools/checkpoint_formats/durable_capture.h',
                         ROOT/'tools/checkpoint_formats/durable_restore.py',Path('/usr/include/boost/json/src.hpp')]
    native_inputs = dict(
        sources={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},
        compiler='/usr/bin/g++-13', vcs_home=os.environ['VCS_HOME'],
        cflags='-std=c++20 -DVCS -DFS_CHECKPOINT_ENTRY',
        translation_units=[str(p.relative_to(ROOT)) for p in sources],
        generated_build=identity)
    native_hash = hashlib.sha256(canonical(native_inputs)).hexdigest()
    (out/'native-build-inputs.json').write_bytes(canonical(native_inputs))
    runtime = packed.runtime_manifest('fcfs-fased-production-entry-v3', manifest, layout, owner_rows, native_hash,
                                     'FPGATop.FASEDMemoryTimingModel_0.model.tCycle')
    prepare_aggregate_loader(runtime, out)
    if args.public_restore: prepare_durable_loader(runtime,manifest,layout,out)
    for name, value in [('generated-manifest', manifest), ('harness-layout', layout), ('runtime-manifest', runtime)]:
        (out/(name+'.json')).write_bytes(canonical(value))
    prefix = 'emul.FPGATop.FASEDMemoryTimingModel_0.'
    header = re.search(r'module FASEDMemoryTimingModel\((.*?)\n\);', rtl, re.S)
    fields = re.findall(r'(?:input|output)\s*(\[[^]]+\])?\s*(hPort_\w+)(?=\s*(?:,|//|$))', header[1], re.M)
    require(len(fields) == 40, 'changed FASED target ports')
    paths = [prefix+name for _, name in fields]
    (out/'target-port-layout.json').write_bytes(canonical(fields))
    monitor = [
        '`timescale 1ps/1ps', 'module production_aggregate_monitor();',
        'import "DPI-C" context function int harness_restore_initialize();',
        'import "DPI-C" context function int harness_restore_verify();',
        'import "DPI-C" context function int generated_restore_verify();',
        'import "DPI-C" context function int production_aggregate_load();',
        'import "DPI-C" context function void production_runtime_identity_verify();',
        'import "DPI-C" context function void harness_restore_fail(input string message);',
        'integer fd=0, status=0, refreshes=0; longint unsigned edges=0, target_edges=0;',
        'bit restoring=0; string filename, bundle;',
        'always @(posedge emul.clock) begin', 'edges=edges+1;',
        f'if(fd) $fdisplay(fd,"%0d %b %h",{prefix}model.tCycle,{prefix}targetFire,{{'+','.join(paths)+'});',
        'end',
        # Independent gate edge accounting, without forcing its enable.
        *['always @(posedge emul.'+e['hierarchy']+') target_edges=target_edges+1;'
          for e in manifest['state'] if e['adapter']=='metasim-bufgce-v1'],
        # Full capture validates runtime identity when a target deadline is
        # due. Poll-only callbacks must not hash the executable or emit a log
        # row on every completed operation; this observer is optional.
        'always @(emul.checkpoint_settled_event) if(!$test$plusargs("test-live-periodic=") && !$test$plusargs("fs-checkpoint-directory=") && !$test$plusargs("fs-checkpoint-host-timeout-ms=") && !$test$plusargs("fs-checkpoint-cycle-timeout-ms=")) begin production_runtime_identity_verify(); $display("PRODUCTION_CUT host_edges=%0d target_edges=%0d",edges,target_edges); end',
        'always @(emul.checkpoint_input_refresh) if(restoring && !emul.checkpoint_restore_complete) begin',
        'if(edges || target_edges || emul.clock || refreshes) harness_restore_fail("bootstrap refresh phase");',
        'refreshes=refreshes+1; end',
        'initial begin',
        'restoring=$value$plusargs("'+('fs-restore' if args.public_restore else 'test-aggregate')+'=%s",bundle);',
        'if($value$plusargs("target_port_trace=%s",filename)) begin fd=$fopen(filename,"w"); if(!fd) harness_restore_fail("trace open"); end',
        'if(restoring) begin', 'if(harness_restore_initialize()) harness_restore_fail("initialize");',
        '#2002;',
        'if(edges || target_edges || emul.clock || !emul.checkpoint_restore_waiting) harness_restore_fail("reservation edge");',
        'status=production_aggregate_load();',
        'if(status==2) begin if(edges || target_edges) harness_restore_fail("negative edge"); $display("PRODUCTION_NEGATIVE zero_edges=1"); $finish; end',
        'else begin',
        'if(status) begin if(edges || target_edges) harness_restore_fail("failed restore advanced time"); $display("PRODUCTION_REJECTION zero_edges=1"); harness_restore_fail("aggregate loading"); end',
        '#1; if(harness_restore_verify() || generated_restore_verify() || edges || target_edges) harness_restore_fail("pre-edge readback");',
        '$display("PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0");',
        'emul.checkpoint_resume_restored();',
        'if(edges || target_edges || emul.clock || refreshes!=1) harness_restore_fail("bootstrap advanced time");',
        '$display("PRODUCTION_BOOTSTRAP zero_edges=1");',
        'end end end', 'final begin production_runtime_identity_verify(); if(fd) $fclose(fd); end', 'endmodule',
        'bind FPGATop production_aggregate_monitor aggregate_monitor();']
    if args.live_capture and not args.public_capture:
        monitor[1:1] = [
            'module durable_live_capture_observer();',
            'import "DPI-C" context function int production_durable_live_capture(input longint unsigned host_sample);',
            'import "DPI-C" context function void harness_restore_fail(input string message);',
            'longint unsigned edges=0; string destination;',
            'always @(posedge emul.clock) edges=edges+1;',
            'always @(emul.checkpoint_settled_event) if($value$plusargs("test-live-capture=%s",destination)) begin',
            'if(production_durable_live_capture(edges)) harness_restore_fail("live capture");',
            'end', 'endmodule', 'bind FPGATop durable_live_capture_observer live_capture_observer();']
    (out/'monitor.sv').write_text('\n'.join(monitor)+'\n')
    (out/'harness.sv').write_text(''.join(f'`include "{p}"\n' for p in (
        generated/'FireSim-generated.const.vh', generated/'FireSim-generated.defines.vh', verilog/'top.sv')))
    if args.normal_make:
        # The monitor only observes. Make generates, compiles and runs the real
        # coordinator; no test loader may perform the production restore.
        begin = monitor.index('if(restoring) begin')
        end = monitor.index('end end end', begin)
        monitor[begin:end+1] = ['end']
        (out/'monitor.sv').write_text('\n'.join(monitor)+'\n')
        command = ['make', 'TARGET_PROJECT=fasedtests', 'DESIGN=AXI4Fuzzer', 'TARGET_CONFIG=FCFSConfig',
                   'PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config', f'BUILD_DIR={args.build.resolve()}',
                   'FS_CHECKPOINT_PROFILE=fcfs-fased-v1', 'VCS_FLAGS=-Mupdate',
                   f'VCS={Path(os.environ["VCS_HOME"])/"bin/vcs"} -full64',
                   f'VCS_EXTRA_V={out/"monitor.sv"} {out/"settled-generated-probe.sv"}', 'vcs']
        run(command, out/'build.log', ROOT/'sims/firesim/sim')
        executable = generated/'checkpoint-vcs/AXI4Fuzzer-checkpoint'
        require(executable.is_file(), 'Make did not produce the checkpoint executable')
        shutil.copy2(executable, out/executable.name)
        (out/'simv').symlink_to(executable.name)
        shutil.copytree(Path(str(executable)+'.daidir'), out/(executable.name+'.daidir'))
        (out/'simv.daidir').symlink_to(executable.name+'.daidir', target_is_directory=True)
        for library in executable.parent.glob('*.so'):
            shutil.copy2(library, out/library.name)
        compiled = generated/'checkpoint-native'
        for name in ('native-build-inputs', 'runtime-manifest', 'generated-manifest', 'harness-layout'):
            (out/(name+'.json')).write_bytes((compiled/(name+'.json')).read_bytes())
        (out/'checkpoint-coordinator.sv').write_bytes((compiled/'checkpoint-coordinator.sv').read_bytes())
        native_inputs = json.loads((out/'native-build-inputs.json').read_text())
        runtime = json.loads((out/'runtime-manifest.json').read_text())
        require(runtime['native_owners'] == owner_rows and
                json.loads((out/'generated-manifest.json').read_text()) == manifest and
                json.loads((out/'harness-layout.json').read_text()) == layout,
                'Make inventory differs from independent production oracle')
    else:
        run([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-debug_access+all', '+vpi',
         *(['+define+FS_CHECKPOINT_DURABLE'] if args.public_capture else []),
         '+vcs+initreg+random', '+define+VCS', '+define+CLOCK_PERIOD=1', '-timescale=1ps/1ps', '-top', 'emul',
         '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS', f'-std=c++20 -DVCS -DFS_CHECKPOINT_ENTRY -I{cc} -I{out} -I{generated}',
         '-LDFLAGS', '-Wl,--no-as-needed -pthread -lgmp -lcrypto -ldl', f'-Mdir={out/"csrc"}', '-o', out/'simv',
         out/'harness.sv', out/'monitor.sv', out/'settled-generated-probe.sv',
             generated/'FireSim-generated.sv', verilog/'BUFGCE.v', *sources], out/'build.log')
    build = build_identity(runtime, manifest, layout, out/'simv')
    (out/'aggregate-build.json').write_bytes(canonical(build))
    # Preserve linked library provenance with the executable binding.
    run(['ldd', out/'simv'], out/'linked-libraries.log')
    common = [out/'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0', '+memsize=4194304', '+max-cycles=1000000']
    results = []
    for label, timing, cuts in [('default', [], (3, 11, 699275, 699276)),
                              ('randomized', ['+fuzz-host-timing=7', '+fuzz-seed=18446744073709551615'], (101,))]:
        ref = out/label/'reference'; ref.mkdir(parents=True, exist_ok=True)
        text = run([*common, *timing, f'+target_port_trace={ref/"ports.trace"}'], ref/'run.log', ref)
        require('*** PASSED ***' in text, 'production reference failed')
        cycles = int(re.search(r'Target Cycles Emulated: (\d+)', text)[1])
        reference = (ref/'ports.trace').read_text().splitlines(keepends=True)
        def verify_cut(cut):
            case = out/label/f'cut-{cut}'; case.mkdir(parents=True, exist_ok=True)
            diagnostic = case/'software.diag'; diagnostic.unlink(missing_ok=True)
            log = run([*common, *timing, f'+fs-driver-cut={cut}', '+fs-driver-settled', '+fs-driver-lowclock',
                       *([f'+fs-checkpoint={case/"capture.fsckpt"}', f'+fs-checkpoint-operation={cut}']
                         if args.public_capture else [f'+test-live-capture={case/"capture.fsckpt"}'] if args.live_capture else []),
                       f'+test-runtime-identity={case/"runtime-identity.bin"}',
                       f'+fs-driver-diagnostic={diagnostic}', f'+settled_generated_capture={case/"generated.jsonl"}',
                       f'+target_port_trace={case/"capture.trace"}'], case/'capture.log', case)
            require('*** PASSED ***' in log and (case/'capture.trace').read_bytes()==(ref/'ports.trace').read_bytes(),
                    'capture changed production target output/transaction timing')
            operation, native = read_diagnostic(diagnostic)
            native[compatibility['owner']] = (compatibility['schema'], (case/'runtime-identity.bin').read_bytes())
            require(operation==cut, 'wrong operation cut')
            require([dict(owner=name, schema=schema) for name,(schema,_) in native.items()
                     if schema and name!='diagnostic/harness-banks']==owner_rows, 'changed production owner inventory')
            sample, entries = packed.read_generated_cut(manifest, case/'generated.jsonl')
            magic, bits = struct.unpack_from('<QQ', native['diagnostic/harness-banks'][1])
            require(magic==0x3153424F534E5248, 'wrong packed harness diagnostic')
            packed_banks = int.from_bytes(native['diagnostic/harness-banks'][1][16:], 'little')
            bank_bits = sum(r['width'] for r in layout['records'][:-2])
            require(bits==bank_bits+67 and packed_banks>>bank_bits==0, 'high clock/reset/finish harness cut')
            values = []; offset = bank_bits
            for row in layout['records'][:-2]:
                offset -= row['width']; v = (packed_banks>>offset)&((1<<row['width'])-1)
                values.append(f'{v:0{(row["width"]+3)//4}x}')
            h = harness_capture(layout, [*values, '0', '0'], sample)
            scalar = {e['owner']:e['value'] for e in entries}
            target_cycle = int(scalar['generated-entry/'+prefix[5:]+'model.tCycle'],16)
            require(sample==int(re.search(r'PRODUCTION_CUT host_edges=(\d+)',log)[1]), 'cut host sample disagrees with independent edge count')
            payloads = {r['owner']:native[r['owner']][1] for r in owner_rows}
            container = packed.encode_aggregate(build, runtime, manifest, layout, sample, entries, h, payloads, target_cycle)
            if args.live_capture:
                require('FS_DURABLE_LIVE_CAPTURE_PUBLISHED' in log and
                        (case/'capture.fsckpt').read_bytes()==container,
                        'live snapshot differs from the independent complete Python oracle')
            else:
                packed.publish_aggregate(container, build, runtime, manifest, layout, case/'capture.fsckpt')
            # Fresh loading consumes the reopened durable artifact, rather than
            # the capture process's original in-memory container.
            packed.prepare_aggregate_restore((case/'capture.fsckpt').read_bytes(), build, runtime,
                                             manifest, layout, case/'aggregate.load')
            request = f'+fs-restore={case/"capture.fsckpt"}' if args.public_restore else f'+test-aggregate={case/"aggregate.load"}'
            restored = run([*common, *timing, request,
                            f'+test-loaded-native={case/"loaded-native.txt"}',
                            f'+target_port_trace={case/"restore.trace"}'], case/'restore.log', case)
            require('PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in restored
                    and 'PRODUCTION_BOOTSTRAP zero_edges=1' in restored and '*** PASSED ***' in restored,
                    'fresh production continuation failed')
            require(f'Target Cycles Emulated: {cycles}\n' in restored, 'changed target completion cycle')
            loaded = dict(line.split() for line in (case/'loaded-native.txt').read_text().splitlines())
            require(loaded == {name:b.hex() for name,b in payloads.items()}, 'incomplete native pre-edge readback evidence')
            observed = (case/'restore.trace').read_text().splitlines(keepends=True)
            expected = reference[sample:]
            compare_target_trace(expected, observed, fields, cut, sample)
            memories = [struct.unpack_from('<13Q', payloads[f'runtime/functional-memory/{i}']) for i in range(4)]
            if cut==699275:
                require(any(r[8] for r in memories), 'missing in-flight native write')
                require(int(scalar['generated-entry/'+prefix[5:]+'model.SatUpDownCounter_1.value'],16)>0,
                        'missing outstanding FASED write')
            result = dict(timing=label, cut=cut, target_cycle=target_cycle, host_sample=sample, target_completion=cycles,
                          native_owners=len(owner_rows), generated_entries=len(entries), generated_words=sum(e['depth'] for e in manifest['state']),
                          continuation_rows=len(observed), container_bytes=len(container), zero_edges_before_load_and_bootstrap=True)
            result['native_live_capture_verified'] = args.live_capture
            return result
        # Shared executable is immutable; simulator processes and artifacts are distinct.
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for future in concurrent.futures.as_completed([pool.submit(verify_cut, cut) for cut in cuts]):
                result = future.result(); results.append(result)
                results.sort(key=lambda r:(r['timing'],r['cut']))
                (out/'partial-results.json').write_bytes(canonical(results))
                print('PASS:', result, flush=True)
    if args.public_restore:
        from tools.checkpoint_formats.tests.verify_public_durable_restore import verify_rejections as public_rejections
        rejections=public_rejections(common,out,build,runtime,manifest,layout)
    else: rejections=verify_rejections(common, out, owner_rows, manifest)
    summary = dict(cases=results, **rejections, normal_make_build=args.normal_make,
                   test_entry_production_continuation_verified=True, real_production_entry_verified=True,
                   production_plusargs_enabled=False,
                   public_durable_restore_enabled=args.public_restore,
                   native_live_capture_verified=args.live_capture,
                   public_durable_capture_enabled=args.public_capture,
                   physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    print('PASS: fresh production entry aggregate continuation with '+('public durable restore' if args.public_restore else 'a test capability'), flush=True)


if __name__=='__main__': main()
