"""Opt-in NASTI restoration: localhost OOC and independent fresh-process EDA continuation.

Fixture images include the explicitly modeled response owner. They are neither
.fsckpt nor FPGA-origin images, and grant no production ownership exemption.
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
from tools.checkpoint_formats.tests.audit_nasti_restore_wave import audit as audit_wave

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
GEOMETRIES = ((8, 1), (32, 4), (32, 12), (64, 64))
TB = 'tools/checkpoint_formats/tests/checkpoint_nasti_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (TB, EXIT, 'tools/checkpoint_formats/tests/audit_nasti_restore_wave.py', 'tools/checkpoint_formats/tests/verify_nasti_restore.py',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointNastiState.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureNastiStateSpec.scala')
TCL = '''set_param general.maxThreads 4
read_verilog adapter.v
synth_design -top CheckpointNastiAdapter -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME =~ BUFG*}]] != 0} {error "unexpected clock gating"}
set raw [get_nets -of_objects [get_ports clock]]
set flops [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $flops] < 100} {error "missing original state"}
foreach cell $flops {
  set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != 0 ||
      [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "changed original clock $cell"}
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force adapter.dcp
puts "NASTI_RESTORE_SYNTH_PASS flops=[llength $flops] raw_clock=1"
'''


SOURCES = (*SOURCES, 'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    parser.add_argument('--generated', type=Path)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    commands = []
    summary = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), hostname=socket.gethostname(),
        original_root=str(ROOT), sources=sources, physical_fpga_capture=False,
        production_restore_enabled=False, complete_state_ownership=False,
        scope='opt-in adapter plus explicit fixture backend owner; fresh component processes only')

    def run(argv, name, cwd, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(cwd / (name + '.log')))
        commands.append(row)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with Path(row['log']).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == expected, 'inspect underlying log ' + row['log'])
        return Path(row['log']).read_text()

    for name in SOURCES:
        dest = out / 'sources' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    results = []
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                'native manager Vivado required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS),
                'generated source below runs required')
        for addr, ident in GEOMETRIES:
            work = out / f'{addr}-{ident}'
            work.mkdir()
            rtl = args.generated / f'adapter-state/{addr}-{ident}-restore/CheckpointNastiAdapter.v'
            shutil.copyfile(rtl, work / 'adapter.v')
            require('io_restore_hold' in rtl.read_text(), 'missing opt-in restore controls')
            (work / 'synth.tcl').write_text(TCL)
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth', work)
            match = re.search(r'NASTI_RESTORE_SYNTH_PASS flops=(\d+) raw_clock=1', text)
            require(match and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native synthesis failed')
            results.append(dict(addr=addr, ident=ident, flops=int(match[1])))
        summary.update(tool_version=run(['vivado', '-version'], 'version', out), results=results)
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                             if p.is_file() and (p.suffix == '.v' or p.name == 'synth.tcl')}
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                                if p.is_file() and p.suffix in ('.dcp', '.rpt', '.log')}
    else:
        require(shutil.which('vcs') == toolchain.VCS and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
                'EDA native SP2 required; source vcs-env.sh last')
        require(args.native is not None and args.native.resolve().is_relative_to(RUNS), 'native receipt required')
        native = json.loads((args.native / 'summary.json').read_text())
        require(native['status'] == 'pass' and native['backend'] == 'f2' and native['sources'] == sources and
                native['physical_fpga_capture'] is False and native['production_restore_enabled'] is False,
                'stale or wrong-scope native receipt')
        for group in ('inputs', 'artifacts'):
            for name, digest in native[group].items():
                require(sha(args.native / name) == digest, 'changed native evidence ' + name)
        for name, digest in sources.items():
            require(sha(args.native / 'sources' / name) == digest, 'changed native source ' + name)
        for addr, ident in GEOMETRIES:
            work = out / f'{addr}-{ident}'
            work.mkdir()
            require((args.native / f'{addr}-{ident}/synth.tcl').read_text() == TCL, 'changed synthesis recipe')
            rtl = work / 'adapter.v'
            shutil.copyfile(args.native / f'{addr}-{ident}/adapter.v', rtl)
            common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                '-debug_access+all', f'+define+NASTI_ADDR_BITS={addr}', f'+define+NASTI_ID_BITS={ident}',
                '-top', 'checkpoint_nasti_restore_tb']
            run([*common, '-Mdir=csrc', '-o', 'simv', rtl, ROOT / TB, ROOT / EXIT], 'compile', work)
            for cut in range(6):
                donor = work / f'cut-{cut}-donor'; donor.mkdir()
                dest = work / f'cut-{cut}-restored'; dest.mkdir()
                image = donor / 'state.txt'
                coverage = {}
                for directory, options, restored in (
                    (donor, ['+SAVE=' + str(image)], 0), (dest, ['+IMAGE=' + str(image)], 1)):
                    text = run([work / 'simv', '-no_save', f'+CUT={cut}',
                        '+TRACE=' + str(directory / 'trace.txt'), *options], 'run', directory)
                    match = re.search(rf'NASTI_RESTORE_PASS addr={addr} id={ident} cut={cut} restored={restored} '
                        r'cycles=3000 trials=(\d+) rejected=(\d+) held=5 checks=(\d+)', text)
                    require(match and int(match[3]) > 3000, 'incomplete fresh component execution')
                    if not restored:
                        require(int(match[1]) == 64 and int(match[2]) == 2 * (64 - addr) + 4 * (64 - ident) + 1,
                                'incomplete padding/roundtrip/no-hold rejection sweep')
                    cov = re.search(r'NASTI_CONTINUATION_COVERAGE reads=(\d+) writes=(\d+) responses=(\d+) good_reads=(\d+) good_writes=(\d+) stalls=(\d+)', text)
                    require(cov and all(int(x)>=8 for x in cov.groups()) and int(cov[3])>=16,
                            'missing active continuation transaction coverage')
                    coverage['restored' if restored else 'donor'] = list(map(int,cov.groups()))
                    wave = directory / 'adapter-restore.vcd' 
                    require(wave.stat().st_size > 2000 and re.search(r'#[1-9]\d*', wave.read_text()), 'missing debug wave')
                require(coverage['donor'] == coverage['restored'], 'continuation owner coverage differs')
                reference = (donor / 'trace.txt').read_text().splitlines()
                actual = (dest / 'trace.txt').read_text().splitlines()
                require(len(reference) == len(actual) == 3000, 'incomplete continuation trace')
                for cycle, (expected, observed) in enumerate(zip(reference, actual)):
                    require(expected == observed, f'first component continuation divergence addr={addr} id={ident} cut={cut} cycle={cycle}')
                wave_audits = {name: audit_wave(directory / 'adapter-restore.vcd', addr, ident)
                    for name, directory in [('donor', donor), ('restored', dest)]}
                require(wave_audits['restored']['loaded_edges'] == 1 and
                        wave_audits['restored']['enabled_edges'] == 3000, 'incomplete fresh held load/continuation waveform')
                results.append(dict(addr=addr, ident=ident, cut=cut, compared_cycles=3000, wave_audits=wave_audits, coverage=coverage,
                    image_sha256=sha(image), trace_sha256=sha(donor / 'trace.txt')))
            # The independent image oracle must stop without releasing either interface.
            image = work / 'cut-2-donor/state.txt'
            bad = work / 'semantic'; bad.mkdir()
            text = run([work / 'simv', '-no_save', '+CUT=2', '+IMAGE=' + str(image),
                '+TRACE=' + str(bad / 'trace.txt'), '+CORRUPT=semantic'], 'run', bad, expected=1)
            require('NASTI_RESTORE_DIVERGENCE saved-image semantic readback before release' in text and
                not (bad / 'trace.txt').exists(), 'semantic corruption advanced the restored interface')
            semantic_wave = audit_wave(bad / 'adapter-restore.vcd', addr, ident)
            require(semantic_wave['enabled_edges'] == 0, 'semantic corruption acknowledged an edge')
            for name, content, reason in (
                ('truncated', image.read_text().split()[0] + '\n', 'truncated component image'),
                ('trailing', image.read_text() + 'unexpected', 'trailing component image bytes')):
                bad = work / name; bad.mkdir(); (bad / 'state.txt').write_text(content)
                text = run([work / 'simv', '-no_save', '+CUT=2', '+IMAGE=' + str(bad / 'state.txt'),
                    '+TRACE=' + str(bad / 'trace.txt')], 'run', bad, expected=1)
                require('NASTI_RESTORE_DIVERGENCE ' + reason in text and not (bad / 'trace.txt').exists(),
                        'malformed fixture image escaped')
            # Compile a broken original-register restore mux, not a bad test oracle.
            broken = work / 'broken.v'
            original = rtl.read_text()
            site = re.compile(r'(responseData <= )(data_\d+)(;[^\n]*CheckpointNastiState.scala)')
            require(len(site.findall(original)) == 1, 'ambiguous original restore mux mutation')
            broken.write_text(site.sub(r"\1(\2 ^ 32'h1)\3", original))
            run([*common, '-Mdir=broken-csrc', '-o', 'broken-simv', broken, ROOT / TB, ROOT / EXIT], 'broken-compile', work)
            bad = work / 'broken'; bad.mkdir()
            text = run([work / 'broken-simv', '-no_save', '+CUT=2', '+IMAGE=' + str(image),
                '+TRACE=' + str(bad / 'trace.txt')], 'run', bad, expected=1)
            require('NASTI_RESTORE_DIVERGENCE complete original-register readback before release' in text and
                not (bad / 'trace.txt').exists(), 'compiled restore defect escaped independent original-state readback')
            broken_wave = audit_wave(bad / 'adapter-restore.vcd', addr, ident, broken=True)
            require(broken_wave['first_divergence']['canonical_bit'] == 426 and
                    broken_wave['enabled_edges'] == 0, 'wrong first compiled-defect divergence')
        summary.update(tool=toolchain.VCS, native_receipt=str(args.native / 'summary.json'),
            native_receipt_sha256=sha(args.native / 'summary.json'), results=results,
            compared_cycles=sum(r['compared_cycles'] for r in results), negative_processes=16,
            inputs=native['inputs'], artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                if p.is_file() and p.suffix in ('.log', '.vcd', '.txt', '.v')})
    require(all(sha(ROOT / n) == h for n, h in sources.items()), 'source changed during execution')
    summary['status'] = 'pass'
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
