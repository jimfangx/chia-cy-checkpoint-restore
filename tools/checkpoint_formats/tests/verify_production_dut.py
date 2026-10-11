"""Real production synthesis and complete metasim-sample architecture parity.

This preparatory check does NOT export a proven map or authorize gate deposits.
Source both repository environments and vcs-env.sh LAST before invocation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.finite_replay import prepare_finite_replay
from tools.checkpoint_formats.production_dut import audit_architecture, prepare
from .verify_formal_state_map import GENUS, ROOT


CONFIGURATION = 'AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config'


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify(inputs, out):
    inputs, out = Path(inputs).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    commands = []

    def launch(argv, directory, name, env=None):
        log = directory / (name + '.log')
        stream = log.open('w')
        process = subprocess.Popen([str(a) for a in argv], cwd=directory, env=env, stdout=stream, stderr=subprocess.STDOUT)
        command = dict(cwd=str(directory.relative_to(ROOT)), argv=[str(a) for a in argv], log=str(log), pid=process.pid)
        commands.append(command)
        (run / 'commands.json').write_bytes(canonical(commands))
        return process, stream, command

    def finish(job):
        process, stream, command = job
        try:
            command['exit_code'] = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            process.kill()
            command['exit_code'] = process.wait()
            raise
        finally:
            stream.close()
            (run / 'commands.json').write_bytes(canonical(commands))
        require(command['exit_code'] == 0, 'tool failed: ' + command['log'])
        return Path(command['log']).read_text()

    manifest = json.loads((inputs / 'FireSim-generated.semantic-state.json').read_text())
    boundary = json.loads((inputs / 'FireSim-generated.semantic-boundary.json').read_text())
    rtl = (inputs / 'FireSim-generated.semantic-clean.sv').read_text()
    architecture = run / 'architecture'
    candidate = prepare(manifest, boundary, rtl, architecture)
    require(candidate['state_entries'] == 1543 and candidate['state_bits'] == 102993417 and
            candidate['memory_instances'] == 201 and candidate['restored_words'] == 13503308,
            'unexpected production DUT inventory')
    require(candidate == audit_architecture(architecture), 'architecture audit mismatch')
    synthesis = run / 'synthesis'
    synthesis.mkdir()
    tool_env = dict(os.environ)
    tool_env.pop('LD_LIBRARY_PATH', None)
    tool_env.update(CHECKPOINT_RTL=str(architecture / 'original.sv'),
                    CHECKPOINT_ARCHITECTURE=str(architecture / 'architecture.sv'),
                    CHECKPOINT_MEMORY_MODELS=str(architecture / 'memory-models.v'),
                    CHECKPOINT_MEMORY_STUBS=str(architecture / 'memory-stubs.v'),
                    CHECKPOINT_ARCHITECTURE_CANDIDATE=str(architecture / 'architecture-candidate.json'),
                    CHECKPOINT_LIBRARY=str(ROOT / 'tools/checkpoint_formats/tests/fixtures/formal/cells.lib'),
                    CHECKPOINT_TOP=boundary['dut_module'], CHECKPOINT_MEMORY_INSTANCES=str(candidate['memory_instances']))
    synth_job = launch([GENUS, '-no_gui', '-batch', '-files', ROOT / 'tools/checkpoint_formats/production_synth.tcl'],
                       synthesis, 'synth', tool_env)
    try:
        original = run / 'ordinary-rtl'
        metadata = prepare_finite_replay(manifest, boundary, CONFIGURATION,
                                        (inputs / 'capture.rtlckpt').read_bytes(), (inputs / 'capture.trace').read_bytes(),
                                        rtl, original)
        require(metadata['samples'] == 250185 and metadata['output_comparisons'] == 8506290,
                'incomplete production captured trace')
        adapted = run / 'memory-architecture-rtl'
        adapted.mkdir()
        replacements = {e['original_path']: e['architecture_path'] for e in candidate['entries']}
        bench = (original / 'replay.sv').read_text()
        for entry in candidate['entries']:
            if entry['kind'] == 'memory':
                before = '$vcdplusmemon(dut.' + entry['original_path'] + ');'
                after = '$vcdplusmemon(dut.' + entry['architecture_path'] + ');'
                require(bench.count(before) == 1, 'incomplete architecture waveform memory scope')
                bench = bench.replace(before, after)
        (adapted / 'replay.sv').write_text(bench)
        (adapted / 'clean.sv').write_text((architecture / 'architecture.sv').read_text() +
                                          (architecture / 'memory-models.v').read_text())
        prefix = 'finite_replay_tb.dut.'
        words = 0
        with (original / 'restore.txt').open() as source, (adapted / 'restore.txt').open('w') as target:
            for line in source:
                path, width, value = line.split()
                require(path.startswith(prefix), 'unexpected ordinary restore root')
                relative = path[len(prefix):]
                suffix = re.search(r'\[\d+\]$', relative)
                base = relative[:suffix.start()] if suffix else relative
                require(base in replacements, 'unmapped architecture restore state')
                target.write(prefix + replacements[base] + (suffix[0] if suffix else '') + ' ' + width + ' ' + value + '\n')
                words += 1
        require(words == candidate['restored_words'], 'incomplete architecture restore words')
        log = finish(synth_job)
        synth_job = None
        require('CHECKPOINT_SYNTHESIS_ONLY_UNPROVEN_STATE_MAP' in log and
                'CHECKPOINT_SYNTH_OUTPUT\t' + file_sha(synthesis / 'netlist.v') in log and
                '\tfalse' in log, 'incomplete production synthesis evidence')
        require(len(re.findall(r'^CHECKPOINT_PRESERVED_MEMORY\t', log, re.M)) == 201,
                'incomplete synthesis memory preservation')
        # All VCS children inherit the required LAST-sourced tool environment.
        require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
                os.environ.get('CC') == '/usr/bin/gcc-13' and os.environ.get('CXX') == '/usr/bin/g++-13',
                'source vcs-env.sh LAST before production VCS')
        vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
        for directory in (original, adapted):
            finish(launch([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi',
                           '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS', '-std=c++17',
                           '-timescale=1ns/1ps', '-top', 'finite_replay_tb', '-Mdir=' + str(directory / 'csrc'),
                           '-o', directory / 'simv', directory / 'clean.sv', directory / 'replay.sv',
                           ROOT / 'tools/checkpoint_formats/semantic_restore.cc'], directory, 'build'))
            log = finish(launch([directory / 'simv', '-no_save', '+restore=' + str(directory / 'restore.txt'),
                                 '+trace=' + str(original / 'trace.txt'), '+waveform=' + str(directory / 'replay.vpd'),
                                 '+audit=' + str(directory / 'matched.txt')], directory, 'replay'))
            require('FINITE_PRE_EDGE cycle=524453 words=13503308 target_edges=0' in log and
                    'PASS: standalone finite replay first=524453 end=774638 target_edges=250185 outputs_per_cycle=34' in log,
                    'incomplete production pre-edge readback/replay evidence')
            require(file_sha(directory / 'matched.txt') == file_sha(original / 'trace.txt'), 'production sampled boundary mismatch')
        require(candidate == audit_architecture(architecture), 'architecture inputs changed during verification')
        summary = dict(milestone='M10-production-dut-formal-map', status='in_progress', configuration=CONFIGURATION,
                       run=str(run), production_synthesis=True, retiming=False, memory_instances=201,
                       memory_model_definitions=candidate['memory_model_definitions'], state_entries=1543,
                       state_bits=102993417, restored_words=13503308, fresh_VCS_processes=2,
                       target_edges=metadata['samples'], first_cycle=metadata['first_cycle'], end_cycle=metadata['end_cycle'],
                       output_comparisons_per_process=metadata['output_comparisons'], zero_edge_readback=True,
                       full_original_and_memory_architecture_RTL_replay=True, formal_state_map_complete=False,
                       gate_replay=False, physical_FPGA_validated=False,
                       next='Hierarchy-aware complete gate inventory and original-to-architecture/netlist state proofs; candidates remain unproven',
                       inputs={str(p): file_sha(p) for p in sorted(inputs.iterdir()) if p.is_file()},
                       netlist_sha256=file_sha(synthesis / 'netlist.v'))
        (run / 'summary.json').write_bytes(canonical(summary))
        (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
        return summary
    finally:
        if synth_job is not None:
            process, stream, command = synth_job
            if process.poll() is None:
                process.terminate()
                process.wait()
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.inputs, args.out), indent=2))


if __name__ == '__main__':
    main()
