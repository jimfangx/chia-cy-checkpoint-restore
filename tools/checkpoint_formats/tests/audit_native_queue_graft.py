"""Independent complete waveform audit for the shell-only shared queue graft.

This component has no target-cycle authority. Report actual VCD time and raw
edges, never relabel them as a CPU target cut or FPGA execution evidence.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_native_queue_graft import ROOT, RUNS, SOURCES, GRAFT, audit, sha


def compiled_mutation(directory, receipt):
    original = (directory/'generated'/(GRAFT+'.sv')).read_text()
    before = 'assign capture_native_state[0 +: 1664] = checkpoint_shell_region0_ckpt_native_state;'
    path = directory/'compiled-native-swap.sv'
    require(original.count(before) == 1, 'ambiguous original lane mutation')
    require(path.is_file() and receipt['artifacts'].get(path.name) == sha(path), 'unbound compiled lane mutation')
    require(path.read_text() == original.replace(before, before.replace('region0_', 'region1_')),
            'wrong compiled lane mutation')
    require(receipt['compiled_mutation_source'] == dict(path=str(path), sha256=sha(path)),
            'compiled lane mutation receipt mismatch')
    return dict(path=str(path), sha256=sha(path))


def wave(path, rows, observations, expected_sha, *, broken=False):
    top = 'native_queue_graft_tb.'
    names = ['clock', 'reset', 'armed', 'capture_clock_mask', 'capture_read_enable',
             'capture_request_valid', 'capture_request_ready', 'capture_bank', 'capture_slot',
             'capture_address', 'capture_response_valid', 'capture_response_ready',
             'capture_response_data', 'capture_response_error', 'capture_native_state']
    for q in range(4):
        names.extend(f'lane{q}_io_{n}' for n in
                     ('enq_valid', 'enq_ready', 'enq_bits', 'deq_valid', 'deq_ready', 'deq_bits'))
    wanted = {top+n: n for n in names}
    fields = []
    for q, observation in enumerate(observations):
        for field in observation['state']:
            name = f'q{q}.'+field['emitted_register']
            fields.append((name, q*1664+field['offset'], field['width']))
            wanted[top+'dut.'+name] = name
    fields.sort(key=lambda f: f[1], reverse=True)
    codes, values, scopes, previous = {}, {}, [], {}
    code_set = set()
    raw_hash = hashlib.sha256()
    memory = [[] for _ in range(4)]
    dequeued = [0]*4
    selectors = iter((r, address) for r in rows for address in range(r['depth']))
    pending = first = None
    native_samples = requests = acks = stalls = edges = 0
    timestamp = 0

    def expand(value, width):
        return value.rjust(width, value[0] if value[0] in 'xz' else '0')

    def integer(d, name):
        require(name in d and re.fullmatch('[01]+', d[name]) is not None,
                'unknown waveform value '+name)
        return int(d[name], 2)

    def sample():
        nonlocal previous, pending, first, native_samples, requests, acks, stalls, edges
        now = {n: values[c] for n, c in codes.items() if c in values}
        if not now:
            return
        if now.get('armed') == '1':
            require(all(n in now for n, _, _ in fields), 'missing original native registers')
            vector = ''.join(expand(now[n], width) for n, _, width in fields)
            if vector != expand(now['capture_native_state'], 6656):
                if first is None:
                    first = dict(signal='all 56 original native register vectors',
                                 vcd_time=timestamp, raw_edges=edges, acknowledged_words=acks)
                require(broken, 'native vector differs from original registers')
            native_samples += 1
        rising = now.get('clock') == '1' and previous.get('clock') == '0'
        if rising:
            edges += 1
        if first is not None:
            require(not (rising and previous.get('capture_response_valid') ==
                         previous.get('capture_response_ready') == '1'), 'divergent word acknowledged')
            previous = now
            return
        if rising and previous.get('reset') == '0':
            for q in range(4):
                prefix = f'lane{q}_io_'
                if previous.get(prefix+'enq_valid') == previous.get(prefix+'enq_ready') == '1':
                    require(len(memory[q]) < 6144, 'unexpected extra frontdoor input')
                    memory[q].append(integer(previous, prefix+'enq_bits'))
                if previous.get(prefix+'deq_valid') == previous.get(prefix+'deq_ready') == '1':
                    i = dequeued[q]
                    require(i < len(memory[q]) and integer(previous, prefix+'deq_bits') == memory[q][i],
                            'continued original queue differs from frontdoor input history')
                    dequeued[q] += 1
            if previous.get('capture_request_valid') == previous.get('capture_request_ready') == '1':
                require(pending is None, 'overlapping bank requests')
                require(previous.get('capture_clock_mask') == previous.get('capture_read_enable') == '1',
                        'bank read without functional freeze')
                item = next(selectors, None)
                require(item is not None, 'extra bank request')
                row, address = item
                require(tuple(integer(previous, n) for n in ('capture_bank','capture_slot','capture_address')) ==
                        (row['bank'], row['slot'], address), 'missing/duplicate/out-of-order bank word')
                name = row['hierarchy'].split('.')[-1]
                if name == 'ram':
                    require(len(memory[row['region']]) == 6144, 'incomplete actual frontdoor memory history')
                    expected = (memory[row['region']][address//8] >> (64*(address%8))) & ((1<<64)-1)
                else:
                    require(name in ('enq_ptr_value','deq_ptr_value','maybe_full','ram_io_deq_bits_MPORT_addr'),
                            'unsupported original register')
                    expected = int(name == 'maybe_full')
                pending = expected
                requests += 1
            if previous.get('capture_response_valid') == '1':
                require(pending is not None, 'unsolicited response')
                require(integer(previous,'capture_response_error') == 0 and
                        integer(previous,'capture_response_data') == pending,
                        'bank word differs from actual frontdoor memory history')
                if previous.get('capture_response_ready') == '1':
                    acks += 1
                    pending = None
                else:
                    stalls += 1
        previous = now

    with (gzip.open(path, 'rb') if path.suffix == '.gz' else path.open('rb')) as stream:
        for raw in stream:
            raw_hash.update(raw)
            kind = raw[:1]
            if kind == b'$':
                parts = raw.decode('ascii').split()
                if parts[0] == '$scope': scopes.append(parts[2])
                elif parts[0] == '$upscope': scopes.pop()
                elif parts[0] == '$var':
                    name = '.'.join(scopes+[parts[4].lstrip('\\')])
                    if name in wanted:
                        codes[wanted[name]] = parts[3]
                        code_set.add(parts[3].encode())
            elif kind == b'#':
                sample()
                timestamp = int(raw[1:])
            elif kind in (b'b', b'B'):
                value, _, code = raw.rstrip().rpartition(b' ')
                if code in code_set: values[code.decode()] = value[1:].decode().lower()
            elif kind in (b'0',b'1',b'x',b'X',b'z',b'Z'):
                code = raw[1:].rstrip()
                if code in code_set: values[code.decode()] = kind.decode().lower()
    sample()
    require(raw_hash.hexdigest() == expected_sha, 'waveform differs from complete retained bytes')
    require(codes.keys() == set(wanted.values()), 'incomplete full visibility waveform owners')
    require(native_samples > 0, 'no original native-vector samples')
    if broken:
        require(first is not None and first['acknowledged_words'] == acks == 0,
                'missing first divergence before acknowledgement')
        require(all(len(lane) == 6144 for lane in memory) and dequeued == [0]*4 and requests == 0,
                'incomplete active workload before compiled divergence')
    else:
        require(first is None and pending is None and next(selectors, None) is None and
                requests == acks == sum(r['depth'] for r in rows), 'incomplete bank coverage')
        require(all(len(lane) == 6144 for lane in memory) and dequeued == [128]*4,
                'incomplete original workload or continuation')
        require(stalls >= 3*acks, 'missing bank backpressure')
    return dict(raw_sha256=raw_hash.hexdigest(), native_vector_samples=native_samples,
                original_word_requests=requests, original_word_acknowledgements=acks,
                response_stalls=stalls, frontdoor_enqueues=list(map(len, memory)),
                frontdoor_dequeues=dequeued, first_divergence=first, raw_edges=edges)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eda', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(str(ROOT).startswith('/scratch/'), 'waveform verification runs on EDA')
    require(args.out.resolve().is_relative_to(RUNS), 'evidence must be under runs')
    args.eda = args.eda.resolve()
    receipt = args.eda/'summary.json'
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda', 'successful EDA graft receipt required')
    require(doc['sources'] == {n:sha(ROOT/n) for n in SOURCES}, 'stale graft sources')
    for group in ('inputs', 'artifacts'):
        for name, digest in doc[group].items():
            require(sha(args.eda/name) == digest, 'changed graft evidence '+name)
    mutation = compiled_mutation(args.eda, doc)
    rows, observations = audit(args.eda/'generated')
    results = dict(healthy=wave(args.eda/'native-queue-graft.vcd.gz', rows, observations,
                              doc['waveform']['original_sha256']),
                   mutation=wave(args.eda/'native-queue-graft-mutation.vcd', rows, observations,
                                 doc['artifacts']['native-queue-graft-mutation.vcd'], broken=True))
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='audit-', dir=args.out.resolve()))
    result = dict(status='pass', backend='eda', physical_fpga_capture=False, target_cycle_authority=False,
                  scope='independent complete original native fields, frontdoor inputs, bank words and continuation',
                  eda_receipt=dict(path=str(receipt),sha256=sha(receipt)), results=results,
                  compiled_mutation_source=mutation, sources={str(Path(__file__).relative_to(ROOT)):sha(__file__)})
    (out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
