"""Independent checks of concrete widget payloads against generated constructors.

Registry identities follow entry.cc's core/stream/bridge passes, not the header's
text order. This audit checker is deliberately limited to the six supported
widget classes; it never infers checkpoint support for an unfamiliar driver.
"""
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_fased_checkpoint_vcs import configuration, NAMES, text, words


def check_fased_widget(schema, payload, block):
    """Bind the production default-argument, unprofiled cut to its constructor."""
    maps = re.findall(r'std::vector<std::pair<std::string, uint32_t>>\{(.*?)\n\s*\}', block, re.S)
    require(len(maps) == 2, 'changed FASED address-map emission')
    read, write = [dict((name, int(addr)) for name, addr in
        re.findall(r'R"ESC\((.*?)\)ESC",\s*(\d+)', mapping)) for mapping in maps]
    tail = re.search(r'\n\s*(\d+),\s*\n\s*args\s*,\s*R"ESC\(.*?\)ESC"\s*,\s*(\d+)L << (\d+)', block)
    require(tail is not None, 'changed FASED model/memory configuration')
    model, base, shift = map(int, tail.groups())
    histograms = NAMES if 'hostReadLatencyHist_enable' in write else ()
    ranges = ('read', 'write') if 'readRanges_enable' in write else ()
    config = configuration(read, write, model, base << shift, False, {}, histograms, ranges)
    exclusion = ('Hist_dataL','Hist_dataH','Hist_addr','Hist_enable','hostMemOffsetLow',
                 'hostMemOffsetHigh','Ranges_dataL','Ranges_dataH','Ranges_addr','Ranges_enable','numRanges')
    header = ''.join(name+',' for name in sorted(read) if name not in write and
                     not any(part in name for part in exclusion))+'\n'
    # The production fixture has no software instrumentation baselines. Fail
    # closed if its generated configuration adds them until independently
    # cross-checked against hardware, rather than assuming zero values.
    require(not histograms and not ranges, 'unhandled production FASED baseline fixture')
    require(schema == 'firesim.widget.fased.v1' and payload == config + words(1) + text(header),
            'FASED configuration/lifecycle/profiling history differs from generated construction')


FIELDS = {
    'master_t': ('master', 1, ('INIT_DONE', 'PRESENCE_READ', 'PRESENCE_WRITE')),
    'clockmodule_t': ('clock', 2, ('hCycle_0', 'hCycle_1', 'hCycle_latch', 'tCycle_0', 'tCycle_1', 'tCycle_latch')),
    'loadmem_t': ('loadmem', 3, ('W_ADDRESS_H', 'W_ADDRESS_L', 'W_LENGTH', 'ZERO_OUT_DRAM', 'W_DATA',
                              'ZERO_FINISHED', 'R_ADDRESS_H', 'R_ADDRESS_L', 'R_DATA')),
    'reset_pulse_t': ('reset-pulse', 4, ('pulseLength', 'doneInit')),
    'peek_poke_t': ('peek-poke', 5, ('STEP', 'DONE', 'PRECISE_PEEKABLE')),
}


def constructor_inventory(header):
    rows = []
    for category in ('CORE', 'MANAGED_STREAM', 'BRIDGE'):
        for block in re.findall(rf'#ifdef GET_{category}_CONSTRUCTOR\n(.*?)#endif', header, re.S):
            kind = re.search(r'registry.add_widget\(new (\w+)\(', block)
            require(kind is not None, 'unrecognized constructor')
            rows.append((kind[1], block))
    require(rows, 'empty generated registry')
    return rows


def check_widget_inventory(owners, header):
    def words(*values):
        return struct.pack('<' + 'Q' * len(values), *values)
    supported, unsupported = [], []
    for index, (kind, block) in enumerate(constructor_inventory(header)):
        identity = f'widget/{index}'
        require(identity in owners, f'missing actual widget owner {identity}')
        schema, payload = owners[identity]
        if kind == 'FASEDMemoryTimingModel':
            check_fased_widget(schema, payload, block)
            supported.append(identity)
            continue
        if kind not in FIELDS:
            require(not schema and not payload, f'unaudited driver {kind} declared supported')
            unsupported.append(identity)
            continue
        name, tag, fields = FIELDS[kind]
        values = []
        for field in fields:
            value = re.search(rf'\.{field}\s*=\s*(\d+)\s*,', block)
            require(value is not None, f'missing generated field {field}')
            values.append(int(value[1]))
        if kind == 'loadmem_t':
            geom = re.search(r'\.mem = AXI4Config\{(\d+), (\d+), (\d+)\}', header)
            chunk = re.search(r'conf_target.mem\s*,\s*(\d+)', block)
            require(geom is not None and chunk is not None, 'missing memory geometry')
            values.extend(map(int, geom.groups())); values.append(int(chunk[1]))
        if kind == 'reset_pulse_t':
            reset = re.search(r'args\s*,\s*(\d+)\s*,\s*(\d+)', block)
            require(reset is not None, 'missing reset configuration')
            maximum, default = map(int, reset.groups())
            values.extend((maximum, default, default))  # verifier uses default runtime args
        expected = words(0x3154504B43474457, 1, tag, len(values), *values)
        if kind == 'peek_poke_t':
            maps = re.findall(r'std::map<std::string, peek_poke_t::Port, std::less<>>\{(.*?)\}\s*(?:,|\)\))', block, re.S)
            require(len(maps) == 2, 'changed peek/poke map emission')
            for port_map in maps:
                ports = re.findall(r'R"ESC\((.*?)\)ESC", peek_poke_t::Port\{\.address = (\d+)ULL,\.chunks = (\d+)\}', port_map)
                expected += words(len(ports))
                for port, addr, chunks in sorted(ports):
                    expected += words(len(port.encode())) + port.encode() + words(int(addr), int(chunks))
            # Result flags depend on actual sampling; config is immutable.
            require(len(payload) == len(expected) + 8, 'incomplete peek/poke flags')
            flags, = struct.unpack_from('<Q', payload, len(expected))
            require(flags <= 3, 'invalid production peek/poke flags')
        else:
            flags = 0
        require(schema == f'firesim.widget.{name}.v1' and payload == expected + words(flags),
                f'{identity}/{kind}: actual config or flags differ from generated construction')
        supported.append(identity)
    require({k for k in owners if k.startswith('widget/')} == set(supported + unsupported),
            'extra widget identity')
    return set(supported), set(unsupported)
