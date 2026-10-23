"""Native localhost synthesis of effects, retained Rocket DTLB or data-array banks.

OOC component evidence only. This never builds or deploys a complete Rocket AFI.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, SOURCES, sha
from tools.checkpoint_formats.tests.verify_independent_clock_vcs import SOURCES as INDEPENDENT_SOURCES
from tools.checkpoint_formats.tests.verify_multiple_clocks_vcs import SOURCES as MULTICLOCK_SOURCES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
            'run on native localhost with HDK setup sourced first')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='clocked-vivado-', dir=base))
    for label, source, names in [('generated', args.generated.resolve(), GENERATED),
                                  ('sources', ROOT, (*dict.fromkeys((*SOURCES, *INDEPENDENT_SOURCES, *MULTICLOCK_SOURCES)),
                                    'tools/checkpoint_formats/tests/synth_clocked_effects.py'))]:
        for name in names:
            target = out / label / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
    generated = out / 'generated'
    root = json.loads((generated / 'generated-bank-manifest.json').read_text())['root_module']
    require(root in ('EffectsStorage', 'DTLB', 'DCacheDataArray', 'MultiClockStorage'), 'unexpected synthesis root')
    clocks = ('clock_a', 'clock_b', 'ckpt_clock') if root == 'MultiClockStorage' else ('clock',)
    constraints = '\n'.join(f'create_clock -period 7.142857 [get_ports {clock}]' for clock in clocks)
    script = out / 'synth.tcl'
    script.write_text(f'''set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv {{{generated / 'generated-bank.sv'}}}
synth_design -top {root} -part xcvu47p-fsvh2892-2-e -mode out_of_context
{constraints}
{'' if root == 'MultiClockStorage' else 'if {[llength [get_ports -quiet ckpt_clock]]} { create_clock -period 7.142857 [get_ports ckpt_clock] }'}
opt_design
report_utilization -file {{{out / 'utilization.rpt'}}}
report_timing_summary -file {{{out / 'timing.rpt'}}}
write_checkpoint -force {{{out / (root + '.dcp')}}}
write_verilog -force -mode funcsim {{{out / 'native-functional.v'}}}
puts "CLOCKED_EFFECTS_SYNTH_PASS root={root} scope=component-only"
close_project
''')
    argv = ['vivado', '-mode', 'batch', '-source', str(script), '-log', 'vivado.log', '-journal', 'vivado.jou']
    command = dict(argv=argv, cwd=str(out), log=str(out / 'command.log'))
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (out / 'command.log').open('w') as log:
        result = subprocess.run(argv, cwd=out, stdout=log, stderr=subprocess.STDOUT)
    command['returncode'] = result.returncode
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    require(result.returncode == 0 and f'CLOCKED_EFFECTS_SYNTH_PASS root={root}' in (out / 'command.log').read_text(),
            f'native Vivado failed: {out / "command.log"}')
    with zipfile.ZipFile(out / (root + '.dcp')) as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for token in ('<Part Name="xcvu47p-fsvh2892-2-e"', f'<Top Name="{root}"', '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(token in metadata, 'native DCP identity mismatch: ' + token)
    utilization = (out / 'utilization.rpt').read_text()
    luts = int(re.search(r'\| CLB LUTs\*\s*\|\s*(\d+)\s*\|', utilization)[1])
    registers = int(re.search(r'\| CLB Registers\s*\|\s*(\d+)\s*\|', utilization)[1])
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', backend='f2',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='native localhost component OOC synthesis only', root=root, physical_fpga_capture=False,
        full_rocket_image_build=False, luts=luts, registers=registers, command=command,
        files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
