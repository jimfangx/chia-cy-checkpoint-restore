"""Compile and execute the four-hart CPU workload and actual memory faults.

Spike checks the workload independently; this is not FireSim checkpoint evidence.
Source env.sh before invocation. Diagnostics and executables go under --out.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / 'tools/checkpoint_formats/workloads/rocket_quad'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--exit-protocol', choices=('direct', 'syscall93'), default='direct')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which('riscv64-unknown-elf-gcc')
    spike = shutil.which('spike')
    require(compiler is not None and spike is not None, 'missing RISC-V compiler or Spike')
    commands = []

    def run(argv, name, expected=0):
        log = out / (name + '.log')
        with log.open('w') as stream:
            result = subprocess.run([str(a) for a in argv], cwd=ROOT, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=120)
        commands.append(dict(cwd='.', argv=[str(a) for a in argv],
                             returncode=result.returncode, expected=expected, log=str(log)))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == expected, f'{name}: exit {result.returncode}, expected {expected}; {log}')

    run([compiler, '--version'], 'compiler-version')
    run([spike, '--help'], 'spike-version')
    builds = {}
    source = SOURCES / 'workload.c'
    if args.exit_protocol == 'syscall93':
        # Keep the retained direct-exit source and ELF byte-exact. Only the
        # termination transport changes; every four-hart computation is shared.
        text = source.read_text()
        declaration = 'static volatile uint64_t generation;'
        exit_store = '        tohost = (failed << 1) | 1;'
        require(text.count(declaration) == text.count(exit_store) == 1,
                'workload exit substitution requires an explicit source audit')
        text = text.replace(declaration, declaration + '\n' +
                            'volatile uint64_t exit_request[8] __attribute__((aligned(64)));')
        text = text.replace(exit_store, '''        exit_request[0] = 93;
        exit_request[1] = failed;
        for (uint64_t arg = 2; arg < 8; ++arg) exit_request[arg] = 0;
        __asm__ volatile("fence rw, rw" ::: "memory");
        tohost = (uintptr_t)exit_request;''')
        source = out / 'syscall93-workload.c'
        source.write_text(text)
    for hart in [None, 0, 1, 2, 3]:
        name = 'rocket-quad' if hart is None else f'corrupt-hart-{hart}'
        elf = out / (name + '.riscv')
        flags = [] if hart is None else [f'-DCHECKPOINT_WORKLOAD_CORRUPT_HART={hart}']
        run([compiler, '-march=rv64ima_zicsr', '-mabi=lp64', '-mcmodel=medany', '-O2',
             '-ffreestanding', '-fno-builtin', '-fno-common', '-nostdlib', '-nostartfiles',
             '-Wall', '-Wextra', '-Werror', '-Wl,--build-id=none',
             '-Wl,-T,' + str(SOURCES / 'link.ld'), *flags,
             SOURCES / 'start.S', source, '-o', elf], name + '-build')
        expected = 0 if hart is None else 1 << hart
        run([spike, '-p4', '--isa=rv64ima_zicsr', elf], name + '-spike', expected)
        builds[name] = dict(elf=str(elf), sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
                            corrupt_hart=hart, spike_exit=expected)
    obj = dict(status='passed', evidence_scope='workload_only_not_checkpoint_acceptance',
               harts=4, bytes_per_hart=65536, phases=['early', 'warm', 'memory', 'late'],
               source_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(SOURCES.iterdir()) if p.is_file()},
               compiler=str(Path(compiler).resolve()), spike=str(Path(spike).resolve()),
               builds=builds, commands=str(out / 'commands.json'),
               firesim_execution_verified=False, checkpoint_cuts_verified=False)
    obj['exit_protocol'] = args.exit_protocol
    obj['compiled_source'] = str(source)
    obj['compiled_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    (out / 'summary.json').write_text(json.dumps(obj, indent=2) + '\n')
    print(json.dumps(obj, indent=2))


if __name__ == '__main__':
    main()
