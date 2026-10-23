"""Native metasim capture and fresh ordinary RTL replay of memory port state.

This is compiler/component evidence, not a CPU acceptance test. Source env.sh,
sims/firesim/env.sh and vcs-env.sh LAST before invoking this module.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

from tools.checkpoint_formats.codec import FormatError, encode, require
from tools.checkpoint_formats.replay import package_capture, prepare_capture, prepare_replay, read_json
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, verify_case


DESIGN = 'MemoryPipelineFixture'
CONFIGURATION = DESIGN + '-NoConfig-DefaultF2Config'
PIPELINES = {
    'old_io_readerOld_MPORT_data': (9, 'io_readerOld'),
    'fresh_io_readerNew_MPORT_addr': (3, 'io_readerNew'),
    'rwOld_io_readwriterOld_MPORT_rdata': (9, 'io_readwriterOld'),
    'rwUndefined_io_readwriterUndefined_MPORT_rdata': (9, 'io_readwriterUndefined'),
}


def audit_capture(fields, rows):
    """Independent word-by-word recurrence, including held and collision state."""
    values = [{f['path']: int(v, 16) for f, v in zip(fields, row['values'])} for row in rows]
    require(len(values) == 37, 'changed directed workload edge count')
    memories = ('old', 'fresh', 'rwOld', 'rwUndefined')
    stored = {f'{name}[{i}]': 0 for name in memories for i in range(8)}
    stored.update({name: 0 for name in PIPELINES})
    stored['count'] = 0
    for c, value in enumerate(values):
        require(rows[c]['cycle'] == c, 'lost original target edge label')
        require(all(value[k] == v for k, v in stored.items()), f'complete memory/pipeline state differs at C={c}')
        expected = {
            'io_readerOld': stored['old_io_readerOld_MPORT_data'],
            'io_readerNew': stored[f"fresh[{stored['fresh_io_readerNew_MPORT_addr']}]"],
            'io_readwriterOld': stored['rwOld_io_readwriterOld_MPORT_rdata'],
            'io_readwriterUndefined': stored['rwUndefined_io_readwriterUndefined_MPORT_rdata'],
            'io_count': stored['count'],
        }
        require(all(value[k] == v for k, v in expected.items()), f'memory output differs at C={c}')
        address = value['io_address']
        if value['io_enable']:
            stored['old_io_readerOld_MPORT_data'] = stored[f'old[{address}]']
            stored['fresh_io_readerNew_MPORT_addr'] = address
            stored['rwOld_io_readwriterOld_MPORT_rdata'] = stored[f'rwOld[{address}]']
            stored['rwUndefined_io_readwriterUndefined_MPORT_rdata'] = stored[f'rwUndefined[{address}]']
            if value['io_write']:
                for name in memories:
                    stored[f'{name}[{address}]'] = value['io_data']
        stored['count'] = 0 if value['reset'] else (stored['count'] + 1) % 512
    require(all(v['reset'] == (c < 5) for c, v in enumerate(values)), 'reset workload changed')
    require(values[21]['io_enable'] == 0 and values[21]['io_address'] == 2,
            'missing disabled-read cut')
    require(values[24]['io_enable'] == values[24]['io_write'] == 1 and values[24]['io_data'] == 0x1a2,
            'missing active collision cut')
    require(values[28]['io_readerOld'] == values[28]['io_readwriterOld'] == 0x1a2
            and values[28]['io_readerNew'] == 0x155 and values[28]['io_enable'] == 0,
            'saved data/address distinction not exercised')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    require(str(vcs) == _toolchain.VCS, 'source vcs-env.sh LAST')
    make = ['make', f'DESIGN={DESIGN}', 'TARGET_CONFIG=NoConfig', 'PLATFORM_CONFIG=DefaultF2Config',
            f'SEMANTIC_CHECKPOINT_ROOT={DESIGN}.dut', f'BUILD_DIR={build}']
    sim_dir = ROOT / 'sims/firesim/sim'
    run(make + ['verilog'], out / 'verilog.log', sim_dir)
    generated = build / ('f2/f2-midasexamples-' + CONFIGURATION)
    base = generated / 'FireSim-generated'
    manifest = read_json(str(base) + '.semantic-state.json')
    boundary = read_json(str(base) + '.semantic-boundary.json')
    clean = Path(str(base) + '.semantic-clean.sv')
    expected = {name: (9, 8, 'memory') for name in ('old', 'fresh', 'rwOld', 'rwUndefined')}
    expected.update({name: (width, 1, 'register') for name, (width, _) in PIPELINES.items()})
    expected['count'] = (9, 1, 'register')
    require({e['hierarchy'].removeprefix(manifest['dut_root'] + '.'):
             (e['width'], e['depth'], e['kind']) for e in manifest['state']} == expected,
            'incomplete/changed memory or pipeline ownership')
    fields = prepare_capture(manifest, boundary, clean.read_text(), Path(str(base) + '.sv').read_text(), out)
    run(make + ['vcs', f'VCS={vcs} -full64', 'VCS_FLAGS=-Mupdate', 'VCS_FORCE_REBUILD=1',
                f'VCS_EXTRA_V={out / "capture.sv"}'], out / 'metasim-build.log', sim_dir)
    binary = generated / DESIGN
    result = run([binary, '+vcs+initreg+0', '+vcs+initmem+0',
                  f'+semantic_capture={out / "capture.jsonl"}'], out / 'metasim-run.log')
    require('*** PASSED ***' in result, 'self-checking metasim workload did not pass')
    rows = [json.loads(line) for line in (out / 'capture.jsonl').read_text().splitlines()]
    audit_capture(fields, rows)
    cases = []
    for c in (0, 5, 13, 21, 24, 26, 28, 30):
        case = out / f'cut-{c}'
        package_capture(manifest, boundary, CONFIGURATION, out / 'capture.jsonl', c, len(rows) - c, case)
        result = verify_case(vcs, clean, manifest, boundary, case, configuration=CONFIGURATION, monitor_edges=True)
        require('RESTORE: deposited 37 semantic words before first DUT edge' in result,
                'incomplete zero-edge restore')
        require(result.count('ACKNOWLEDGED_TARGET_EDGE') == len(rows) - c, 'replay edge acknowledgement mismatch')
        cases.append(dict(cycle=c, samples=len(rows) - c, zero_edge_words=37, outputs=5))
    original = out / 'cut-21'
    ckpt, trace = ((original / ('capture.' + suffix)).read_bytes() for suffix in ('rtlckpt', 'trace'))
    doc, _ = package_capture(manifest, boundary, CONFIGURATION, out / 'capture.jsonl', 21, len(rows) - 21, original)
    invalid = dict(truncated=ckpt[:-5], corrupt_checksum=ckpt[:-1] + bytes([ckpt[-1] ^ 1]))
    for name in ('incompatible_build', 'missing_pipeline', 'unknown_owner'):
        altered = copy.deepcopy(doc)
        if name == 'incompatible_build':
            altered['build']['rtl_build_hash'] = '0' * 64
        elif name == 'missing_pipeline':
            identity = next(e['state_id'] for e in manifest['state'] if e['hierarchy'].endswith('.old_io_readerOld_MPORT_data'))
            altered['records'] = [r for r in altered['records'] if r['state_id'] != identity]
        else:
            altered['records'][0]['state_id'] = '0' * 64
            altered['records'].sort(key=lambda r: r['state_id'])
        invalid[name] = encode('rtlckpt', altered)
    rejections = []
    for name, data in invalid.items():
        case = out / ('invalid-' + name)
        case.mkdir(exist_ok=True)
        (case / 'capture.rtlckpt').write_bytes(data)
        (case / 'capture.trace').write_bytes(trace)
        try:
            prepare_replay(manifest, boundary, CONFIGURATION, data, trace, case)
        except FormatError as error:
            rejections.append(dict(case=name, rejection=str(error)))
        else:
            raise AssertionError('accepted invalid memory image: ' + name)
        require(not (case / 'restore.txt').exists() and not (case / 'replay.sv').exists(), 'partial invalid restore publication')
    faults = []
    for state, (width, signal) in PIPELINES.items():
        case = out / ('fault-' + state)
        case.mkdir(exist_ok=True)
        (case / 'capture.rtlckpt').write_bytes(ckpt)
        (case / 'capture.trace').write_bytes(trace)
        result = verify_case(vcs, clean, manifest, boundary, case, expected=None, configuration=CONFIGURATION,
                             post_restore_checks=f"  dut.{state} = dut.{state} ^ {width}'h1;\n"
                                                 f'  $display("INJECTED_STATE {state} after complete readback");',
                             monitor_edges=True)
        require('RESTORE: deposited 37 semantic words before first DUT edge' in result
                and f'FIRST_MISMATCH cycle=21 signal={signal}' in result
                and result.count('FIRST_MISMATCH') == 1 and 'ACKNOWLEDGED_TARGET_EDGE' not in result,
                'actual pipeline corruption did not fail at its first boundary')
        faults.append(dict(state=state, cycle=21, signal=signal, acknowledged_edges=0))
    restore = (original / 'restore.txt').read_text()
    loader_cases = dict(missing_handle=restore.replace('.count ', '.absent '),
                        wrong_width=restore.replace('.count 9 ', '.count 8 '),
                        malformed=restore + 'truncated-row\n',
                        incomplete='\n'.join(restore.splitlines()[:-1]) + '\n')
    for name, text in loader_cases.items():
        path = out / (name + '.restore.txt')
        path.write_text(text)
        result = run([original / 'simv', f'+restore={path}', f'+waveform={out / (name + ".vcd")}'],
                     out / (name + '.log'), expected=None)
        require('RESTORE_ERROR' in result and 'RESTORE: deposited' not in result
                and 'ACKNOWLEDGED_TARGET_EDGE' not in result, 'invalid loader partially restored/advanced')
    sources = [clean, Path(str(base) + '.semantic-state.json'), Path(str(base) + '.semantic-boundary.json'),
               Path(str(base) + '.semantic-reference.fir'), Path(str(base) + '.sv'), binary,
               out / 'capture.jsonl', ROOT / 'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SemanticStateInventory.scala',
               ROOT / 'sims/firesim/sim/src/main/scala/midasexamples/MemoryPipelineFixture.scala',
               ROOT / 'sims/firesim/sim/src/main/cc/midasexamples/TestMemoryPipelineFixture.cc', Path(__file__)]
    summary = dict(status='passed', fixture_only=True, CPU_level1_verified=False, CPU_level2_verified=False,
                   design=DESIGN, semantic_entries=9, words=37, captured_edges=len(rows),
                   cases=cases, image_rejections=rejections, loader_rejections=list(loader_cases),
                   actual_state_faults=faults,
                   inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
