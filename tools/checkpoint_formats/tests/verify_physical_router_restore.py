"""Qualify complete physical-router observation/held restore; never CPU acceptance."""
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
from tools.checkpoint_formats.tests.audit_physical_router_restore_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv'
TB = 'tools/checkpoint_formats/tests/physical_router_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (RTL, TB, EXIT, 'tools/checkpoint_formats/tests/verify_physical_router_restore.py',
           'tools/checkpoint_formats/tests/audit_physical_router_restore_wave.py')


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
    require(args.out.resolve().is_relative_to(RUNS), 'all evidence belongs beneath runs')
    if args.mode == 'vcs':
        require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'VCS belongs on native EDA SP2')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'Vivado belongs on current manager')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=args.out.resolve()))
    doc = dict(status='running', backend='eda' if args.mode == 'vcs' else 'f2', source_root=str(ROOT),
               host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat(),
               scope='physical router only; endpoint/global cut/production attachment ownership remains pending',
               physical_fpga_capture=False, full_image=False, CPU_migration_verified=False,
               sources={name: sha(ROOT / name) for name in SOURCES}, commands=[], cases=[])
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
            for enabled in (0, 1):
                tcl = f'''read_verilog -sv router.sv
synth_design -top CheckpointPhysicalStateRouter -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -generic {{ENTRIES=2 GATES=3 RESTORE_SUPPORTED={enabled}}}
create_clock -period 7.142857 [get_ports clock]
set regs [get_cells -hier -filter {{REF_NAME =~ FD*}}]
if {{[llength $regs] != 2}} {{error "physical router complete owner width changed"}}
foreach cell $regs {{
  set net [get_nets -segments -of_objects [get_pins -of_objects $cell -filter {{REF_PIN_NAME == C}}]]
  if {{[lsearch -exact $net clock] < 0}} {{error "physical router state left original raw clock"}}
}}
report_utilization -file utilization-{enabled}.rpt
write_checkpoint -force router-{enabled}.dcp
puts "PHYSICAL_ROUTER_RESTORE_SYNTH_PASS enabled={enabled} original_owner_bits=2"
'''
                script = f'synth-{enabled}.tcl'
                (out / script).write_text(tcl)
                text = run(['vivado', '-mode', 'batch', '-source', script], f'synthesis-{enabled}')
                require(f'PHYSICAL_ROUTER_RESTORE_SYNTH_PASS enabled={enabled} original_owner_bits=2' in text
                        and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native original-owner synthesis failed')
        else:
            for entries, gates, enabled in ((1, 1, 1), (2, 3, 1), (65534, 1, 1), (2, 3, 0),
                                             (0, 3, 1), (1, 0, 1), (1, 65536, 1)):
                geometry = entries > 0 and gates > 0 and gates <= 65536 and entries <= 65535-gates
                name = f'entries-{entries}-gates-{gates}-enabled-{enabled}'
                work = out / name
                work.mkdir()
                binary = work / 'simv'
                text = run([toolchain.VCS, '-full64', '-sverilog', '-Mupdate', '-debug_access+all',
                            '-timescale=1ns/1ps', '-cc', toolchain.CC, '-cpp', toolchain.CXX,
                            f'+define+ENTRIES={entries}', f'+define+GATES={gates}', f'+define+RESTORE_ENABLED={enabled}',
                            '-top', 'physical_router_restore_tb', '-Mdir=' + str(work / 'csrc'), '-o', binary,
                            ROOT / RTL, ROOT / TB, ROOT / EXIT], name + '-compile', cwd=work)
                require(not re.search(r'Error-\[', text), 'VCS compilation error')
                row = dict(entries=entries, gates=gates, restore_enabled=bool(enabled), state_bits=2, geometry=geometry)
                modes = ('source', 'destination', 'corrupt-0', 'corrupt-1') if enabled and geometry else ('source',) if geometry else ('invalid',)
                image = work / 'source/router.state'
                for mode in modes:
                    dest = work / mode
                    dest.mkdir()
                    expected = 1 if mode.startswith('corrupt-') else 0
                    argv = [binary, '-no_save', '+mode=' + ('destination' if expected else mode), '+image=' + str(image)]
                    if expected:
                        argv.append('+corrupt_bit=' + mode[-1])
                    text = run(argv, name + '-' + mode, cwd=dest, expected=expected)
                    if mode == 'source':
                        values = [int(line, 16) for line in image.read_text().splitlines()]
                        require(values == [0, 1, 0, 3, 2], 'actual donor complete ABI mismatch')
                        row.update(image=str(image), image_sha256=sha(image), source_snapshots=len(values))
                    if expected:
                        require(f'PHYSICAL_FIRST_DIVERGENCE signal=capture_state snapshot=0 expected=0 observed={1 << int(mode[-1])} acknowledged_edges=0' in text,
                                'semantic corruption must stop at first readback with no edge acknowledgement')
                    else:
                        require('PHYSICAL_RESTORE_PASS' in text, 'missing healthy process completion')
                        if mode == 'destination':
                            require('snapshots=5 encodings=4 acknowledged_edges=5' in text, 'incomplete independent restore sweep')
                    row[mode] = dict(returncode=expected, waveform=str(dest / 'physical-restore.vcd'),
                        wave_audit=audit(dest / 'physical-restore.vcd', enabled, values if geometry else [],
                                         destination=mode != 'source' and geometry, corrupt=bool(expected), geometry=geometry))
                if enabled and geometry:
                    rejected = []
                    for bit in range(2):
                        try:
                            audit(work / 'destination/physical-restore.vcd', enabled, values, destination=True, mutate_bit=bit)
                        except ValueError:
                            rejected.append(bit)
                        else:
                            raise RuntimeError('wave checker admitted corrupted original owner bit ' + str(bit))
                    row['rejected_wave_checker_mutation_bits'] = rejected
                doc['cases'].append(row)
                save()
        require(all(sha(ROOT / name) == digest for name, digest in doc['sources'].items()), 'source changed during qualification')
        doc['status'] = 'pass'
    except BaseException as error:
        doc.update(status='fail', error=str(error))
        raise
    finally:
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        doc['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p != summary}
        save()
        print(summary, flush=True)


if __name__ == '__main__':
    main()
