"""Independently bind default production simulation_t configuration/phase."""
import struct
import re
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.widget_inventory import constructor_inventory


def check_fcfs_driver(owners, header, expectations=()):
    """Bind production FCFS traversal/maps and ordered effective expectations."""
    def words(*values):
        return struct.pack('<' + 'Q' * len(values), *values)
    def text(value):
        data = value.encode()
        return words(len(data)) + data
    rows = constructor_inventory(header)
    def identity(i):
        return text(f'widget/{i}') + text(owners[f'widget/{i}'][0])
    peek = [i for i, (kind, _) in enumerate(rows) if kind == 'peek_poke_t']
    require(len(peek) == 1, 'missing FCFS peek/poke construction')
    # entry.cc classifies these as bridges. Fail if new constructor kinds need
    # independent classification, instead of silently omitting their order.
    bridge_kinds = {'FASEDMemoryTimingModel', 'reset_pulse_t'}
    require(all(kind in bridge_kinds | {'master_t', 'loadmem_t', 'clockmodule_t', 'peek_poke_t'}
                for kind, _ in rows), 'unaudited FCFS traversal constructor')
    bridges = [i for i, (kind, _) in enumerate(rows) if kind in bridge_kinds]
    models = [i for i, (kind, _) in enumerate(rows) if kind == 'FASEDMemoryTimingModel']
    config = words(0x3154504B43474457, 1, 9, 2, 0, 0, len(expectations))
    for key, value in expectations:
        config += text(key) + words(value)
    config += identity(peek[0])
    config += words(len(bridges)) + b''.join(identity(i) for i in bridges)
    config += words(len(models))
    for i in models:
        config += identity(i)
        maps = re.findall(r'std::vector<std::pair<std::string, uint32_t>>\{(.*?)\n\s*\}', rows[i][1], re.S)
        require(len(maps) == 2, 'changed FCFS model map emission')
        for mapping in maps:
            fields = sorted((name, int(addr)) for name, addr in
                            re.findall(r'R"ESC\((.*?)\)ESC",\s*(\d+)', mapping))
            config += words(len(fields))
            for name, address in fields:
                config += text(name) + words(address)
    schema, payload = owners['runtime/simulation']
    require(schema == 'firesim.simulation.fcfs.v1' and payload == config + words(1),
            'FCFS configuration/lifecycle differs from independent construction')
    require(owners['runtime/scheduler'][0] == 'firesim.scheduler.deadlines.v1',
            'concrete driver adapter displaced scheduler ownership')
    return dict(models=len(models), bridges=len(bridges), expectation_count=len(expectations))


def check_simulation_base(owners):
    def words(*values):
        return struct.pack('<' + 'Q' * len(values), *values)
    def text(value):
        data = value.encode()
        return words(len(data)) + data
    schema, payload = owners['runtime/simulation/base']
    require(schema == 'firesim.simulation.base.v1', 'missing base simulation owner')
    # Current production FCFS cuts use the default effective base arguments.
    config = words(0x3154504B43474457, 1, 8, 5, 0, 0, 0, 0, 1) + text('') + text('')
    widgets = [(key, value[0]) for key, value in owners.items() if key.startswith('widget/')]
    require([key for key, _ in widgets] == [f'widget/{i}' for i in range(len(widgets))],
            'base widget configuration order changed')
    config += words(len(widgets))
    for key, kind in widgets:
        config += text(key) + text(kind)
    require(len(payload) == len(config) + 32 and payload[:len(config)] == config,
            'base configuration differs from independent registry inventory')
    phase, done, start_time, start_hcycle = struct.unpack_from('<4Q', payload, len(config))
    require(phase == 1 and done in (0, 1) and start_time > 0, 'invalid running base lifecycle')
    if 'runtime/simulation/fased-run-loop' in owners:
        loop = struct.unpack('<6Q', owners['runtime/simulation/fased-run-loop'][1])
        require(done == (loop[3] == 6), 'base completion differs from independently owned driver loop')
    return dict(run_done=bool(done), start_time=start_time, start_hcycle=start_hcycle)
