"""Shared regional-router held-restore component qualification.

Vivado runs on the manager; all VCS runs require the dedicated EDA mirror.
This does not grant endpoint ownership, complete-image or FPGA acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.tests.audit_region_router_restore_wave import audit as audit_wave

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv'
TB = 'tools/checkpoint_formats/tests/region_router_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (RTL, TB, EXIT, 'tools/checkpoint_formats/tests/verify_region_router_restore.py',
           'tools/checkpoint_formats/tests/audit_region_router_restore_wave.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence must remain beneath runs')
    if args.mode == 'vcs':
        require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'VCS belongs exclusively on EDA')
        require(toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'native SP2 required')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'Vivado belongs on current manager')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    doc = dict(status='running', backend='eda' if args.mode == 'vcs' else 'f2',
               source_root=str(ROOT), host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat(),
               scope='shared regional router only; endpoints/global cut and production attachment remain unsupported',
               physical_fpga_capture=False, full_image=False, CPU_migration_verified=False,
               sources={name: sha(ROOT / name) for name in SOURCES}, commands=[])
    summary = out / 'summary.json'

    def save():
        summary.write_text(json.dumps(doc, indent=2) + '\n')

    def run(argv, name, cwd=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(log))
        doc['commands'].append(row)
        save()
        with log.open('x') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(log))
        save()
        require(result.returncode == expected, 'inspect underlying log: ' + str(log))
        return log.read_text()

    save()
    print(out, flush=True)
    try:
        if args.mode == 'vivado':
            shutil.copyfile(ROOT / RTL, out / 'router.sv')
            tcl = '''read_verilog -sv router.sv
synth_design -top CheckpointRegionStateRouter -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -generic {REGIONS=3 BANK_BASE=131328 BANK_COUNT=65793 CE_BASE=8590000128 CE_COUNT=4295032833 RESTORE_SUPPORTED=1}
create_clock -period 7.142857 [get_ports clock]
set regs [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $regs] != 4} {error "router complete owner width changed"}
foreach cell $regs {
  set net [get_nets -segments -of_objects [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]]
  if {[lsearch -exact $net clock] < 0} {error "router owner clock is not raw clock"}
}
report_utilization -file utilization.rpt
write_checkpoint -force router.dcp
puts "REGION_ROUTER_RESTORE_SYNTH_PASS regions=3 complete_owner_bits=4"
'''
            (out / 'synth.tcl').write_text(tcl)
            doc['inputs'] = {n: sha(out / n) for n in ('router.sv', 'synth.tcl')}
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synthesis')
            require('REGION_ROUTER_RESTORE_SYNTH_PASS regions=3 complete_owner_bits=4' in text and
                    not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native owner synthesis failed')
        else:
            doc['cases'] = []
            for regions, enabled in ((1, 1), (2, 1), (3, 1), (255, 1), (3, 0)):
                name = f'regions-{regions}-enabled-{enabled}'
                work = out / name
                work.mkdir()
                binary = work / 'simv'
                compile_text = run([toolchain.VCS, '-full64', '-sverilog', '-Mupdate', '-debug_access+all',
                     '-timescale=1ns/1ps', '-cc', toolchain.CC, '-cpp', toolchain.CXX,
                     '+define+REGIONS=' + str(regions), '+define+RESTORE_ENABLED=' + str(enabled),
                     '-top', 'region_router_restore_tb', '-Mdir=' + str(work / 'csrc'), '-o', binary,
                     ROOT / RTL, ROOT / TB, ROOT / EXIT], name + '-compile', cwd=work)
                require(not re.search(r'Error-\[', compile_text), 'VCS compilation error')
                source = work / 'source'
                source.mkdir()
                image = source / 'router.state'
                source_log = run([binary, '-no_save', '+mode=source', '+image=' + str(image)],
                                 name + '-source', cwd=source)
                require('ROUTER_RESTORE_PASS' in source_log and 'snapshots=5' in source_log,
                        'source did not exercise all actual pipeline states')
                # Check the actual source-process file against an independent ABI oracle.
                values = [int(line, 16) for line in image.read_text().splitlines()]
                require(values == [0, (regions - 1) * 4 + 1, (regions - 1) * 4, 3, 2],
                        'donor file does not retain complete inactive/pending/error states')
                row = dict(regions=regions, restore_enabled=bool(enabled), state_bits=max(1, (regions-1).bit_length())+2,
                           image=str(image), image_sha256=sha(image), source_snapshots=5)
                if enabled:
                    for mode, expected in (('destination', 0), ('corrupt', 1)):
                        dest = work / mode
                        dest.mkdir()
                        argv = [binary, '-no_save', '+mode=destination', '+image=' + str(image)]
                        if mode == 'corrupt':
                            argv.append('+corrupt')
                        text = run(argv, name + '-' + mode, cwd=dest, expected=expected)
                        if mode == 'corrupt':
                            require('ROUTER_FIRST_DIVERGENCE signal=capture_state snapshot=0 expected=0 observed=2 acknowledged_edges=0' in text,
                                    'semantic corruption did not stop before its first acknowledged edge')
                        else:
                            require('ROUTER_RESTORE_PASS' in text and 'snapshots=5' in text and 'acknowledged_edges=5' in text and f'encodings={regions*4}' in text,
                                    'fresh-process held restore incomplete')
                        row[mode] = dict(returncode=expected, waveform=str(dest / 'router-restore.vcd'))
                row['source_wave_audit'] = audit_wave(source / 'router-restore.vcd', regions, enabled, values)
                if enabled:
                    row['destination_wave_audit'] = audit_wave(work / 'destination/router-restore.vcd', regions, enabled, values, destination=True)
                    row['corruption_wave_audit'] = audit_wave(work / 'corrupt/router-restore.vcd', regions, enabled, values, destination=True, corrupt=True)
                    rejected = []
                    for bit in range(row['state_bits']):
                        try:
                            audit_wave(work / 'destination/router-restore.vcd', regions, enabled, values, destination=True, mutate_bit=bit)
                        except ValueError:
                            rejected.append(bit)
                        else:
                            raise RuntimeError('wave checker accepted changed owner bit ' + str(bit))
                    row['rejected_wave_checker_mutation_bits'] = rejected
                doc['cases'].append(row)
                save()
        require(all(sha(ROOT / name) == digest for name, digest in doc['sources'].items()),
                'source changed while qualification ran')
        doc['status'] = 'pass'
    except BaseException as error:
        doc['status'] = 'fail'
        doc['error'] = str(error)
        raise
    finally:
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        doc['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p != summary}
        save()
        print(summary, flush=True)


if __name__ == '__main__':
    main()
