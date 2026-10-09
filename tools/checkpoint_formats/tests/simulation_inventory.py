"""Independently bind default production simulation_t configuration/phase."""
import struct
from tools.checkpoint_formats.codec import require


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
