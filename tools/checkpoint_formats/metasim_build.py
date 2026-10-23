"""Generate the complete compiled inventory for the opt-in FCFS VCS Make build.

No historical captures or test fixtures are build inputs. This profile remains
deliberately restricted; native membership/schema is checked again by every
capture and by all-owner restore preparation before any load or clock edge.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

from .aggregate import prepare_aggregate_loader
from .aggregate_packed import runtime_manifest
from .codec import canonical, require, unique_object
from .durable_restore import prepare_durable_loader
from .generated_restore import generated_build_identity, prepare_generated_loader
from .harness_restore import harness_layout, prepare_harness_loader

ROOT = Path(__file__).resolve().parents[2]
PROFILE = 'fcfs-fased-v1'
TARGET_CYCLE = 'FPGATop.FASEDMemoryTimingModel_0.model.tCycle'
TARGET_PROGRESS = 'FPGATop.sim.target.AXI4Fuzzer_.fuzzer_.fuzzer.num_resps'
# This profile implements one finite 10,000-operation TLFuzzer. Pin its entire
# lowered module, ignoring source locations, rather than inferring retirement
# from traffic, arbitrary changing state, or an unfamiliar response protocol.
TARGET_PROGRESS_MODULE_SHA256 = 'dc94bd5753df7f43ccb2bb192eaca6b0f63c236a39453b1b547e1762f6f3823c'
TARGET_INITIALIZATION = 'FPGATop.sim.target.AXI4Fuzzer_.fuzzer_.model.wipeIndex'
TARGET_INITIALIZATION_MODULE_SHA256 = 'abbd7733daff5e1d4dcfcce050a44d515c06569dde315443815ea53c1f83851d'
WIDGETS = {
    'master_t': 'firesim.widget.master.v1',
    'loadmem_t': 'firesim.widget.loadmem.v1',
    'FASEDMemoryTimingModel': 'firesim.widget.fased.v1',
    'clockmodule_t': 'firesim.widget.clock.v1',
    'reset_pulse_t': 'firesim.widget.reset-pulse.v1',
    'peek_poke_t': 'firesim.widget.peek-poke.v1',
}


def native_inventory(header, constants):
    """Follow entry.cc's three constructor passes, rejecting unfamiliar syntax."""
    constructors = []
    blocks = re.findall(r'#ifdef (GET_\w+_CONSTRUCTOR)\n(.*?)#endif[^\n]*', header, re.S)
    for phase in ('GET_CORE_CONSTRUCTOR', 'GET_MANAGED_STREAM_CONSTRUCTOR', 'GET_BRIDGE_CONSTRUCTOR'):
        for tag, body in blocks:
            if tag != phase:
                continue
            match = re.fullmatch(r'\s*registry\.add_widget\(new (\w+)\(.*?\)\);\s*', body, re.S)
            require(match is not None, 'unsupported generated constructor syntax')
            require(body.count('registry.') == 1 and body.count('new ') == 1,
                    'unsupported nested/extra generated constructor')
            constructors.append(match[1])
    require(len(blocks) == len(constructors) and
            constructors == list(WIDGETS), 'unsupported generated widget membership/order')
    macros = re.findall(r'^`define\s+(\S+)', constants, re.M)
    require([m for m in macros if m.startswith('MEM_HAS_CHANNEL') and m != 'MEM_HAS_CHANNEL-1'] ==
            ['MEM_HAS_CHANNEL0', 'MEM_HAS_CHANNEL1', 'MEM_HAS_CHANNEL2', 'MEM_HAS_CHANNEL3'],
            'profile requires exactly four functional-memory channels')
    require(not any(m.startswith(('QSFP_HAS_CHANNEL', 'CPU_MANAGED_AXI4_PRESENT',
                                  'FPGA_MANAGED_AXI4_PRESENT')) for m in macros),
            'unsupported QSFP/managed-stream topology')
    pairs = [('runtime/mmio', 'firesim.mmio.full.v1')]
    pairs += [(f'runtime/functional-memory/{i}', 'firesim.mm_magic.full.v1') for i in range(4)]
    pairs += [('runtime/host-timing', 'firesim.host-timing.mt19937-64.libstdcxx.v1')]
    pairs += [(f'widget/{i}', WIDGETS[kind]) for i, kind in enumerate(constructors)]
    pairs += [('runtime/simulation', 'firesim.simulation.fcfs.v1'),
              ('runtime/simulation/base', 'firesim.simulation.base.v1'),
              ('runtime/scheduler', 'firesim.scheduler.deadlines.v1'),
              ('runtime/simulation/fased-run-loop', 'firesim.stepped-run-loop.v1'),
              ('runtime/compatibility', 'firesim.runtime.fcfs-config-and-loaded-elf.v1')]
    return [dict(owner=owner, schema=schema) for owner, schema in pairs]


def audit_target_progress(manifest, fir):
    entries = [e for e in manifest['state'] if e['module'] == 'TLFuzzer' and
               e['hierarchy'].endswith('.num_resps')]
    require(len(entries) == 1, 'unsupported target-progress fuzzer membership')
    entry = entries[0]
    require(entry['hierarchy'] == TARGET_PROGRESS and entry['kind'] == 'register' and
            entry['adapter'] == 'firrtl-register-v1' and entry['width'] == 14 and
            entry['depth'] == 1 and not entry['signed'] and entry['clock_expression'] == 'clock' and
            entry['reset_expression'] == 'UInt<1>("h0")', 'unsupported target-progress register')
    blocks = re.findall(r'^  module TLFuzzer\b.*?(?=^  (?:module|extmodule)\b|\Z)', fir, re.M | re.S)
    require(len(blocks) == 1, 'unsupported target-progress module membership')
    normalized = '\n'.join(re.sub(r'\s*@\[.*', '', line).strip() for line in blocks[0].splitlines())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    require(digest == TARGET_PROGRESS_MODULE_SHA256, 'unsupported target-progress update semantics')
    wipes = [e for e in manifest['state'] if e['module'] == 'TLRAMModel' and e['hierarchy'].endswith('.wipeIndex')]
    require(len(wipes) == 1, 'unsupported target initialization membership')
    wipe = wipes[0]
    require(wipe['hierarchy'] == TARGET_INITIALIZATION and wipe['kind'] == 'register' and
            wipe['adapter'] == 'firrtl-register-v1' and wipe['width'] == 20 and wipe['depth'] == 1 and
            not wipe['signed'] and wipe['clock_expression'] == 'clock' and
            wipe['reset_expression'] == 'UInt<1>("h0")', 'unsupported target initialization register')
    blocks = re.findall(r'^  module TLRAMModel\b.*?(?=^  (?:module|extmodule)\b|\Z)', fir, re.M | re.S)
    require(len(blocks) == 1, 'unsupported target initialization module membership')
    normalized = '\n'.join(re.sub(r'\s*@\[.*', '', line).strip() for line in blocks[0].splitlines())
    wipe_digest = hashlib.sha256(normalized.encode()).hexdigest()
    require(wipe_digest == TARGET_INITIALIZATION_MODULE_SHA256, 'unsupported target initialization semantics')
    return dict(path='emul.'+TARGET_PROGRESS, state_id=entry['state_id'], width=14,
                initialization_path='emul.'+TARGET_INITIALIZATION, initialization_state_id=wipe['state_id'],
                initialization_width=20, initialization_limit=524288,
                initialization_module_sha256=wipe_digest,
                initial_remaining=10000, completed_expression='wipeIndex + 10000 - num_resps',
                semantics='completed_shadow_memory_initialization_and_TileLink_responses_at_settled_cut',
                module_sha256=digest, checkpoint_level=1)


def coordinator(manifest):
    """Reserve, validate, load, read back and bootstrap before the first edge."""
    gates = [e['hierarchy'] for e in manifest['state'] if e['adapter'] == 'metasim-bufgce-v1']
    source = [
        '`timescale 1ps/1ps', 'module durable_checkpoint_coordinator();',
        'import "DPI-C" context function int harness_restore_initialize();',
        'import "DPI-C" context function int harness_restore_verify();',
        'import "DPI-C" context function int generated_restore_verify();',
        'import "DPI-C" context function int production_aggregate_load();',
        'import "DPI-C" context function void production_runtime_identity_verify();',
        'import "DPI-C" context function void harness_restore_fail(input string message);',
        'longint unsigned edges=0, target_edges=0; integer refreshes=0; bit restoring=0; string bundle;',
        'always @(posedge emul.clock) edges=edges+1;',
        *[f'always @(posedge emul.{gate}) target_edges=target_edges+1;' for gate in gates],
        # A due full capture revalidates identity through its native owner.
        # Poll-only callbacks must not hash every ELF on every operation.
        'always @(emul.checkpoint_settled_event) if(!$test$plusargs("test-live-periodic=") && !$test$plusargs("fs-checkpoint-directory=") && !$test$plusargs("fs-checkpoint-host-timeout-ms=") && !$test$plusargs("fs-checkpoint-cycle-timeout-ms=") && !$test$plusargs("fs-checkpoint-target-timeout-cycles=")) production_runtime_identity_verify();',
        'always @(emul.checkpoint_input_refresh) if(restoring && !emul.checkpoint_restore_complete) begin',
        'if(edges || target_edges || emul.clock || refreshes) harness_restore_fail("bootstrap refresh phase");',
        'refreshes=refreshes+1; end',
        'initial begin',
        'restoring=$value$plusargs("fs-restore=%s",bundle);',
        'if(restoring) begin',
        'if(harness_restore_initialize()) harness_restore_fail("initialize");',
        'wait(emul.checkpoint_entry_done);',
        '// Let audited emitter initialization settle with every clock reserved.',
        '#2002;',
        'if(edges || target_edges || emul.clock || !emul.checkpoint_restore_waiting)',
        'harness_restore_fail("reservation edge");',
        'if(production_aggregate_load()) begin',
        'if(edges || target_edges) harness_restore_fail("failed restore advanced time");',
        '$display("PRODUCTION_REJECTION zero_edges=1"); harness_restore_fail("aggregate loading"); end',
        '#1;',
        'if(harness_restore_verify() || generated_restore_verify() || edges || target_edges)',
        'harness_restore_fail("pre-edge readback");',
        '$display("PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0");',
        'emul.checkpoint_resume_restored();',
        'if(edges || target_edges || emul.clock || refreshes!=1) harness_restore_fail("bootstrap advanced time");',
        '$display("PRODUCTION_BOOTSTRAP zero_edges=1");',
        'end end',
        'final production_runtime_identity_verify();', 'endmodule',
        'bind FPGATop durable_checkpoint_coordinator checkpoint_coordinator();',
    ]
    return '\n'.join(source)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sources', type=Path, nargs='+', required=True)
    parser.add_argument('--driver-name', required=True)
    parser.add_argument('--driver', type=Path, nargs='+', required=True)
    parser.add_argument('--extra-verilog', type=Path, nargs='*', default=[])
    parser.add_argument('--cflags', required=True)
    parser.add_argument('--ldflags', required=True)
    parser.add_argument('--vcs-flags', default='')
    args = parser.parse_args()
    require(args.profile == PROFILE, 'unsupported checkpoint Make profile')
    require(args.driver_name == 'AXI4Fuzzer-checkpoint', 'checkpoint build requires a separate binary name')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX and os.environ.get('CC') == _toolchain.CC,
            'source vcs-env.sh LAST; preserve its VCS and compiler setup')
    require(args.vcs_flags.strip() in ('', '-Mupdate'), 'unsupported checkpoint VCS flags')
    require(not re.search(r'\b(?:DEBUG|FSDB|GATE_LEVEL_SIM)\b', args.cflags),
            'unsupported checkpoint compile mode')
    driver = ROOT/'sims/firesim/sim/src/main/cc/fasedtests/fasedtests_top.cc'
    require([p.resolve() for p in args.driver] == [driver], 'unsupported checkpoint driver')
    generated, out = args.generated.resolve(), args.out.resolve()
    base = generated/'FireSim-generated'
    manifest = json.loads(base.with_suffix('.simulator-state.json').read_text(), object_pairs_hook=unique_object)
    rtl = base.with_suffix('.sv').read_text()
    verilog = ROOT/'sims/firesim/sim/midas/src/main/verilog'
    identity = generated_build_identity(manifest, base.with_suffix('.simulator-reference.fir').read_text(),
                                        rtl, (verilog/'BUFGCE.v').read_text())
    layout = harness_layout((verilog/'top.sv').read_text(), base.with_suffix('.const.vh').read_text(),
                            base.with_suffix('.defines.vh').read_text(), identity)
    owners = native_inventory(base.with_suffix('.const.h').read_text(),
                              base.with_suffix('.const.vh').read_text()+base.with_suffix('.defines.vh').read_text())
    cc = ROOT/'sims/firesim/sim/midas/src/main/cc'
    sources = [p.resolve() for p in args.sources]
    require(len(set(sources)) == len(sources) and cc/'entry.cc' in sources and driver in sources and
            ROOT/'tools/checkpoint_formats/durable_restore_entry.cc' in sources,
            'incomplete/duplicate checkpoint translation units')
    dependencies = {*sources, *cc.rglob('*.h'), *cc.rglob('*.cc'),
                    *Path(__file__).parent.glob('*.py'), *Path(__file__).parent.glob('*.h'),
                    *Path(__file__).parent.glob('*.cc'), *args.extra_verilog,
                    *[base.with_suffix(suffix) for suffix in ('.const.h', '.const.vh', '.defines.vh')],
                    ROOT/'sims/firesim/sim/Makefile', * (ROOT/'sims/firesim/sim/make').glob('*.mk'),
                    cc/'Makefile', cc/'rtlsim/Makefrag-checkpoint', cc/'rtlsim/Makefrag-vcs',
                    Path('/usr/include/boost/json/src.hpp')}
    def name(path):
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    inputs = dict(sources={name(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dependencies)},
                  compiler=os.environ['CXX'], vcs_home=os.environ['VCS_HOME'],
                  cflags=args.cflags, ldflags=args.ldflags, vcs_flags=args.vcs_flags,
                  translation_units=[name(p) for p in sources], generated_build=identity,
                  make_profile=PROFILE)
    runtime = runtime_manifest('fcfs-fased-production-entry-v3', manifest, layout, owners,
                               hashlib.sha256(canonical(inputs)).hexdigest(), TARGET_CYCLE)
    progress = audit_target_progress(manifest, base.with_suffix('.simulator-reference.fir').read_text())
    # All input, RTL coverage, profile and owner checks precede output access.
    out.mkdir(parents=True, exist_ok=True)
    prepare_generated_loader(manifest, identity, out, 'emul.FPGATop', rtl=rtl)
    prepare_harness_loader(layout, out)
    prepare_aggregate_loader(runtime, out)
    with (out/'aggregate-restore-table.h').open('a') as table:
        table.write('\n#define AGGREGATE_TARGET_PROGRESS_PATH '+json.dumps(progress['path'])+'\n')
        table.write('#define AGGREGATE_TARGET_INITIALIZATION_PATH '+json.dumps(progress['initialization_path'])+'\n')
    prepare_durable_loader(runtime, manifest, layout, out)
    for name, value in (('generated-manifest', manifest), ('harness-layout', layout),
                        ('runtime-manifest', runtime), ('native-build-inputs', inputs)):
        (out/(name+'.json')).write_bytes(canonical(value))
    (out/'checkpoint-coordinator.sv').write_text(coordinator(manifest))
    (out/'target-progress-inventory.json').write_bytes(canonical(progress))
    # VCS's cached external-C Makefile can miss included table/header changes.
    # Remove only checkpoint objects with a newer recorded dependency. The
    # ordinary simulator's cache and all saved executables remain untouched.
    removed = []
    for dependency_file in (generated/(args.driver_name+'-debug.csrc')).glob('*.d'):
        obj = dependency_file.with_suffix('.o')
        if not obj.is_file():
            continue
        dependencies = shlex.split(dependency_file.read_text().replace('\\\n', ' ').partition(':')[2])
        newer = [str(p) for token in dependencies if (p := Path(token)).is_file() and
                 p.stat().st_mtime_ns > obj.stat().st_mtime_ns]
        if newer:
            obj.unlink()
            removed.append(dict(object=str(obj), newer_dependencies=newer))
    (out/'rebuilt-driver-objects.json').write_bytes(canonical(removed))
    print(f'CHECKPOINT_BUILD_INVENTORY profile={PROFILE} generated_entries={len(manifest["state"])} '
          f'generated_words={sum(e["depth"] for e in manifest["state"])} '
          f'harness_records={len(layout["records"])} native_owners={len(owners)}')


if __name__ == '__main__':
    main()
