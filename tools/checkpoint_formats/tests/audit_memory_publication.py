"""Independent byte, queue, strobed-write and AXI-boundary oracle for memory."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha


def pack(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


class Memory:
    def __init__(self, bank):
        self.bank = bank
        self.data = bytearray((i * 13 + bank * 17 + 3) & 255 for i in range(4096))
        self.cycle = self.addr = self.ident = self.count = self.size = 0
        self.inflight = False
        self.reads = []
        self.writes = []

    def tick(self, step):
        if step == 1:
            self.reads = [(7 + self.bank, int(i == 2), bytes(self.data[64 + i * 8:72 + i * 8])) for i in range(3)]
            self.addr, self.ident, self.count, self.size, self.inflight = 64, 11 + self.bank, 3, 8, True
        if 2 <= step <= 4:
            incoming = struct.pack('<II', 0x12345678 + self.bank, 0xabcdef00 + step)
            strobe = (0x55, 0xaa, 0xff)[step - 2]
            for i in range(8):
                if strobe & (1 << i):
                    self.data[self.addr + i] = incoming[i]
            self.addr += 8
            self.count -= 1
            if not self.count:
                self.inflight = False
                self.writes.append(self.ident)
        if step in (2, 3, 5):
            self.reads.pop(0)
        if step == 5:
            self.writes.pop(0)
        self.cycle += 1

    def payload(self):
        result = pack(0x3154504b434d4d46, 1, 16, 34, 64, 4096, 64, self.cycle,
                      self.inflight, self.addr, self.ident, self.size, self.count)
        result += self.data + bytes(8) + pack(len(self.writes), *self.writes, len(self.reads))
        for ident, last, data in self.reads:
            result += pack(ident, last) + data
        return result

    def observation(self, step):
        ident, last, data = self.reads[0] if self.reads else (0, 0, bytes(8))
        return ' '.join(map(str, [step, self.bank, int(bool(self.writes)), self.writes[0] if self.writes else 0,
                                 int(bool(self.reads)), ident, last, *data]))


def expected(banks, cut):
    memories = [Memory(b) for b in range(banks)]
    step = (0, 1, 2, 4)[cut]
    for n in range(1, step + 1):
        for m in memories:
            m.tick(n)
    image = [m.payload() for m in memories]
    trace = [m.observation(step) for m in memories]
    for n in range(step + 1, 7):
        for m in memories:
            m.tick(n)
        trace += [m.observation(n) for m in memories]
    return image, [m.payload() for m in memories], '\n'.join(trace) + '\n'


def audit(path):
    path = Path(path).resolve()
    out = path.parent
    report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and
            not report['level2_verified'], 'memory scope')
    require(report['fixture_memory_bytes_per_bank'] == 4096 and report['exact_recipe_memory_channels'] == 1 and
            report['additional_bank_group'] == 4, 'memory geometry scope')
    require(json.loads((out / 'source-inputs.json').read_text()) == report['source_inputs'], 'memory source bindings')
    for binding in report['source_inputs']:
        require(file_sha(binding['snapshot']) == binding['sha256'], 'memory source snapshot')
    require({str(f) for f in out.rglob('*') if f.is_file() and f != path} ==
            set(report['artifact_sha256']), 'memory artifact membership')
    for f, digest in report['artifact_sha256'].items():
        require(file_sha(f) == digest, 'memory changed artifact')
    require(json.loads((out / 'commands.json').read_text()) == report['commands'], 'memory command bindings')
    modes = ('reference', 'restore', 'negative', 'fatal-unsealed', 'fatal-thread', 'fatal-destination',
             'fatal-recycled', 'fatal-consumed', 'fatal-stale', 'fatal-legacy')
    wanted = {(b, n, m, c) for b in ('native', 'vcs-dpi') for n in (1, 4) for m in modes for c in range(4)}
    require(len(report['commands']) == 162 and len(report['cases']) == len(wanted) and
            {(c['backend'], c['banks'], c['mode'], c['cut']) for c in report['cases']} == wanted,
            'memory complete matrix')
    comparisons = rejects = preparation = sealing = fatals = samples = 0
    for case in report['cases']:
        log = Path(case['log']).read_text()
        lines = log.splitlines()
        fatal = case['mode'].startswith('fatal-')
        require(lines[0] == 'cwd=' + str(out) and json.loads(lines[1][5:]) == case['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1] == ('exit=86' if fatal else 'exit=0'),
                'memory fresh process receipt')
        require('source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in
                case['argv'][2], 'memory VCS environment')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected',
                                         'MEMORY_FAIL')), 'memory sanitizer failure')
        dest = Path(case['destination'])
        if fatal:
            require(f'MEMORY_FATAL mode={case["mode"]} unchanged=1 target_edges=0' in log and
                    'MEMORY_PASS' not in log and 'MEMORY_VCS_ZERO_EDGES' not in log and not dest.exists(),
                    'memory fatal contract before partial publication/return')
            fatals += 1
            continue
        if case['backend'] == 'vcs-dpi':
            require('MEMORY_VCS_ZERO_EDGES time=0 edges=0' in log, 'memory zero edges')
        banks, cut = case['banks'], case['cut']
        image, final, trace = expected(banks, cut)
        if case['mode'] == 'negative':
            match = re.search(r'MEMORY_NEGATIVE rejected=(\d+) preparation_failures=(\d+) sealing_failures=(\d+) '
                              r'publication_allocations=0 partial_publication=0 cancellation_unchanged=1 target_edges=0', log)
            require(match and int(match[1]) == 13 * banks + 13 and int(match[2]) > 0 and int(match[3]) > 0,
                    'memory complete atomic rejections')
            rejects += int(match[1])
            preparation += int(match[2])
            sealing += int(match[3])
            for i, payload in enumerate(image):
                require((dest / f'published.{i}').read_bytes() == payload, 'memory complete negative payload')
                comparisons += 1
            continue
        require(f'MEMORY_PASS banks={banks} cut={cut} stable_aliases=1 target_edges=0' in log, 'memory continuation')
        prefix = 'cut' if case['mode'] == 'reference' else 'readback'
        for i in range(banks):
            require((dest / f'{prefix}.{i}').read_bytes() == image[i] and
                    (dest / f'final.{i}').read_bytes() == final[i], 'memory independent complete owner oracle')
            comparisons += 2
        require((dest / 'trace').read_text() == trace, 'memory every AXI boundary and cycle label')
        samples += len(trace.splitlines())
        if case['mode'] == 'restore':
            ref = Path(case['reference'])
            require((dest / 'trace').read_bytes() == (ref / 'trace').read_bytes(), 'memory fresh continuation timing')
            for i in range(banks):
                require((dest / f'readback.{i}').read_bytes() == (ref / f'cut.{i}').read_bytes() and
                        (dest / f'final.{i}').read_bytes() == (ref / f'final.{i}').read_bytes(), 'memory fresh readback')
    return dict(status='passed', fresh_component_restores=16, complete_owner_comparisons=comparisons,
                sampled_axi_boundaries=samples, invalid_rejections=rejects,
                preparation_allocation_failures=preparation, sealing_allocation_failures=sealing,
                fatal_contract_rejections=fatals, publication_allocations=0, partial_publication=0,
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    print(json.dumps(audit(parser.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
