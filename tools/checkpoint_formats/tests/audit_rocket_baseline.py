"""Independently audit real four-hart execution from native Rocket VCS output.

Decode retired RV64 stores from the CPU's instruction/register-value log and
check each hart wrote every workload phase, completion and failure field.
This is workload evidence, not a checkpoint/boundary-trace replay audit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from tools.checkpoint_formats.codec import require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runtime, workload = args.runtime.resolve(), args.workload.resolve()
    completion = json.loads((runtime / 'exit.json').read_text())
    require(completion['returncode'] == 0, 'native workload process did not pass')
    image = json.loads((workload / 'summary.json').read_text())
    elf = Path(image['builds']['rocket-quad']['elf'])
    require(hashlib.sha256(elf.read_bytes()).hexdigest() == image['builds']['rocket-quad']['sha256'],
            'workload ELF binding changed')
    nm = shutil.which('riscv64-unknown-elf-nm')
    require(nm is not None, 'missing RISC-V nm')
    symbols_text = subprocess.check_output([nm, '-n', str(elf)], text=True)
    symbols = {name: int(address, 16) for address, _, name in
               re.findall(r'^([0-9a-f]+) ([A-Za-z]) (\S+)$', symbols_text, re.M)}
    require('hart_status' in symbols and 'tohost' in symbols, 'missing workload audit symbols')
    command = json.loads((runtime / 'command.json').read_text())
    require('+memsize=17179869184' in command['argv'][-1] and str(elf) in command['argv'][-1],
            'native baseline must use full recipe memory and the bound workload')
    events = [[] for _ in range(4)]
    retired = [0] * 4
    completion_stores, failure_stores, tohost_stores = {}, {}, []
    request_stores = []
    syscall = image.get('exit_protocol', 'direct') == 'syscall93'
    if syscall:
        require('exit_request' in symbols and symbols['exit_request'] % 64 == 0,
                'missing/alignment of actual syscall request')
    pattern = re.compile(r'^C([0-3]):\s+(\d+) \[1\] pc=\[([0-9a-f]+)\].*?'
                         r'R\[r\s*\d+=([0-9a-f]+)\] R\[r\s*\d+=([0-9a-f]+)\] '
                         r'inst=\[([0-9a-f]+)\]')
    passed = False
    log = runtime / 'native-vcs.log'
    with log.open() as stream:
        for line in stream:
            if '*** PASSED ***' in line:
                passed = True
            match = pattern.match(line)
            if not match:
                continue
            hart, cycle, pc, rs1, rs2, instruction = (int(v, 10 if i < 2 else 16)
                                                    for i, v in enumerate(match.groups()))
            if 0x80000000 <= pc < symbols['tohost']:
                retired[hart] += 1
            # RV64 SD: signed S-immediate, source-register values before commit.
            if instruction & 0x7f != 0x23 or (instruction >> 12) & 7 != 3:
                continue
            immediate = ((instruction >> 25) << 5) | ((instruction >> 7) & 31)
            if immediate & 0x800:
                immediate -= 0x1000
            address = (rs1 + immediate) & ((1 << 64) - 1)
            base = symbols['hart_status'] + hart * 64
            if address == base and rs2 in (1, 2, 3, 4):
                events[hart].append(dict(phase=rs2, cpu_print_cycle=cycle, pc=hex(pc)))
            if address == base + 8 and rs2 == 1:
                completion_stores[hart] = cycle
            if address == base + 24:
                failure_stores[hart] = dict(cpu_print_cycle=cycle, value=rs2)
            if address == symbols['tohost']:
                tohost_stores.append(dict(hart=hart, cpu_print_cycle=cycle, value=rs2))
            if syscall and symbols['exit_request'] <= address < symbols['exit_request'] + 64:
                request_stores.append(dict(hart=hart, cpu_print_cycle=cycle,
                                          word=(address-symbols['exit_request'])//8, value=rs2))
    require(passed, 'native driver did not report workload PASS')
    for hart in range(4):
        require([e['phase'] for e in events[hart]] == [1, 2, 3, 4], f'hart {hart}: missing/repeated phase')
        require(hart in completion_stores and failure_stores.get(hart, {}).get('value') == 0,
                f'hart {hart}: missing completion or real error')
        require(retired[hart] > 0, f'hart {hart}: no workload retirement')
    if syscall:
        require(len(request_stores) == 16 and
                [e['word'] for e in request_stores[:8]] == list(range(8)) and
                all(e['hart'] == 0 and e['value'] == 0 and
                    e['cpu_print_cycle'] < min(events[h][0]['cpu_print_cycle'] for h in range(4))
                    for e in request_stores[:8]), 'incomplete actual request BSS initialization')
        initialization_stores, request_stores = request_stores[:8], request_stores[8:]
        require(len(tohost_stores) == 1 and tohost_stores[0]['hart'] == 0 and
                tohost_stores[0]['value'] == symbols['exit_request'], 'missing syscall pointer publication')
        require([e['word'] for e in request_stores] == list(range(8)) and
                [e['value'] for e in request_stores] == [93, 0, 0, 0, 0, 0, 0, 0] and
                all(e['hart'] == 0 and max(completion_stores.values()) < e['cpu_print_cycle'] < tohost_stores[0]['cpu_print_cycle']
                    for e in request_stores), 'incomplete/out-of-order actual syscall request')
    else:
        require(any(e['hart'] == 0 and e['value'] == 1 for e in tohost_stores), 'missing real HTIF PASS store')
    obj = dict(status='passed', scope='native_workload_only_not_checkpoint_acceptance',
               elf=str(elf), elf_sha256=image['builds']['rocket-quad']['sha256'],
               runtime=str(runtime), full_backing_memory_bytes=17179869184,
               hart_phases=events, completed_harts=completion_stores, failure_stores=failure_stores,
               workload_retirements=retired, tohost_stores=tohost_stores,
               cycle_label_scope='CPU_print_cycles_not_checkpoint_target_cycle_labels',
               checkpoint_cuts_verified=False, level1_verified=False, level2_verified=False)
    if syscall:
        obj.update(exit_protocol='syscall93', exit_request_stores=request_stores,
                   exit_request_initialization_stores=initialization_stores)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(obj, indent=2) + '\n')
    print(json.dumps(obj, indent=2))


if __name__ == '__main__':
    main()
