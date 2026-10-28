"""Independent raw-clock/MMIO audit of the live widget staging bank.

This is component waveform evidence, never an FPGA checkpoint receipt.
"""
import hashlib
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_transport_control_state import reconstruct, RTL, ROOT


def audit(path, *, physical=False, corrupt=False):
    path = Path(path)
    top = 'physical_checkpoint_widget_tb' if physical else 'checkpoint_capture_widget_tb'
    dut = top + '.dut.'
    roles = {n: top + '.' + n for n in ('clock', 'reset', 'rvalid', 'rready', 'rdata')}
    roles.update({n: dut + 'snapshot.io_' + n for n in
                  ('access', 'write', 'address', 'data', 'error', 'cutValid', 'cycle')})
    roles.update({n: dut + 'snapshot.' + n for n in ('saved', 'label', 'occupied', 'index')})
    roles.update({n: dut + 'capture_' + n for n in ('ownerPresent', 'ownerFrozen', 'ownerError', 'freeze')})
    if physical:
        roles.update({n: dut + 'capture_physical_' + n for n in ('readEnable', 'cutCycle', 'failed')})
    # These fields are the original eight parent registers, independently of
    # the producer's packing expression and the emitted io_live wire.
    local = [('invalid', 1), ('producedFrames', 64), ('producedSnapshot', 64),
             ('hostDrainedFrames', 64), ('counterOverflow', 1), ('localValid', 1),
             ('localData', 32), ('localError', 1)]
    rows = reconstruct({Path(n).name: (ROOT / n).read_text() for n in RTL}, 3)
    original = []
    for row in rows:
        name = row['relative_path']
        if physical:
            target = dut + 'transport_physicalTransport.' + name
        elif name.startswith('physical.'):
            continue
        else:
            target = dut + 'CheckpointCaptureTransport.' + name.removeprefix('transport.')
        original.append((target, row['width']))
    original += [(dut + name, width) for name, width in local]
    address = [('addr',64),('len',8),('size',3),('burst',2),('lock',1),('cache',4),
               ('prot',3),('qos',4),('region',4),('id',64),('user',1)]
    adapter = [(prefix+'_'+name,width) for prefix, fields in
               [('aw',address),('wd',[('data',32),('last',1),('id',64),('strb',4),('user',1)]),
                ('ar',address)] for name,width in fields]
    adapter += [(name,1) for name in ('haveAW','haveW','haveAR','badW','busy','writing','responseValid','responseError')]
    adapter += [('responseData',32),('responseId',64),('errorReadRemaining',8)]
    original += [(dut+'adapter.'+name,width) for name,width in adapter]
    for i, (name, _) in enumerate(original):
        roles['original' + str(i)] = name
    scopes, codes, values = [], {}, {}
    previous = {}
    expected, label, index, occupied = 0, 0, 0, 0
    captures = words = held_edges = 0
    first = None
    timestamp = 0

    def sample():
        nonlocal previous, expected, label, index, occupied, captures, words, held_edges, first
        now = {n: int(values[c], 2) for n, c in codes.items()
               if re.fullmatch('[01]+', values.get(c, 'x'))}
        if now.get('clock') == 1 and previous.get('clock') == 0:
            p = previous
            if p.get('reset'):
                expected = label = index = occupied = 0
            elif p.get('access') and p.get('write') and not p.get('error'):
                if p['address'] == 0x78 and p['data'] == 1:
                    require(not occupied and p.get('cutValid') == 1, 'uncertified shadow acceptance')
                    require(p.get('ownerPresent') == p.get('ownerFrozen') == 3 and
                            p.get('ownerError') == 0 and p.get('freeze') == 1,
                            'unacknowledged fixture owner at shadow acceptance')
                    source = {name: p.get('original' + str(i)) for i, (name, _) in enumerate(original)}
                    cut = (dut + 'transport_physicalTransport.transport.cut.' if physical else
                           dut + 'CheckpointCaptureTransport.cut.')
                    require(source[cut + 'state'] in (2, 3) and source[cut + 'error'] == 0 and
                            source[cut + 'cut_cycle'] == p['cycle'],
                            'coordinator did not acknowledge the exact shadow target cut')
                    if physical:
                        require(p.get('readEnable') == 1 and p.get('failed') == 0 and
                                p.get('cutCycle') == p['cycle'], 'missing exact physical post-stop cut')
                    expected = 0
                    offset = 0
                    for i, (_, width) in enumerate(original):
                        require('original' + str(i) in p, 'unknown original source at capture')
                        expected |= p['original' + str(i)] << offset
                        offset += width
                    label, index, occupied = p['cycle'], 0, 1
                    captures += 1
                elif p['address'] == 0x78 and p['data'] in (2, 4):
                    occupied = 0
                elif p['address'] == 0x7c:
                    index = p['data']
            require(now.get('occupied') == occupied and now.get('index') == index and
                    now.get('label') == label, 'changed shadow epoch/index/label')
            if occupied:
                held_edges += 1
                if now.get('saved') != expected:
                    require(corrupt, 'shadow differs from complete pre-edge original registers')
                    if first is None:
                        first = dict(timestamp=timestamp, cut=label, expected=expected, actual=now.get('saved'))
            if p.get('access') and not p.get('write') and not p.get('error') and p['address'] in (0x80, 0x84):
                words += 1
        previous = now

    with path.open() as stream:
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == '$scope':
                scopes.append(parts[2])
            elif parts[0] == '$upscope':
                scopes.pop()
            elif parts[0] == '$var':
                target = '.'.join(scopes + [parts[4].lstrip('\\')])
                for role, name in roles.items():
                    if target == name:
                        codes[role] = parts[3]
            elif line.startswith('#'):
                sample()
                timestamp = int(line[1:])
            elif line[0] in 'bB' and len(parts) == 2:
                values[parts[1]] = parts[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
        sample()
    require(set(codes) == set(roles), 'missing full-visibility shadow/source waveform: ' + str(set(roles) - set(codes)))
    if corrupt:
        require(first is not None and first['cut'] == 42 and captures == 1 and words == 1 and
                previous.get('rvalid') == 1 and previous.get('rready') == 0 and index == 0,
                'shadow corruption did not stop on first word before its AXI acknowledgement')
    else:
        require(first is None and captures == (6 if physical else 1) and
                words == (480 if physical else 114) and held_edges > 100,
                'incomplete shadow epochs/words/immutability evidence')
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                captures=captures, word_halves=words, held_raw_edges=held_edges,
                first_divergence=first, component_only=True)
