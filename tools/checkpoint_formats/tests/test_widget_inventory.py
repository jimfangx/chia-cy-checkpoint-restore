import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.verify_widget_checkpoint_vcs import oracle
from tools.checkpoint_formats.tests.widget_inventory import check_widget_inventory, constructor_inventory


def fixture():
    def block(category, kind, fields, tail=''):
        return f'#ifdef GET_{category}_CONSTRUCTOR\nregistry.add_widget(new {kind}(simif,\nConfig{{' + ','.join(
            f'.{key} = {value},' for key, value in fields) + f'}},0,args{tail}));\n#endif\n'
    # Deliberately interleave textual categories; actual entry.cc makes core
    # owners first, so textual header order cannot be used as owner identity.
    header = block('CORE', 'master_t', [('INIT_DONE',0),('PRESENCE_READ',4),('PRESENCE_WRITE',8)])
    header += block('BRIDGE', 'clockmodule_t', list(zip(('hCycle_0','hCycle_1','hCycle_latch','tCycle_0','tCycle_1','tCycle_latch'),(16,20,24,28,32,36))))
    header += block('BRIDGE', 'reset_pulse_t', [('pulseLength',112),('doneInit',116)], ',20,7')
    maps = ',std::map<std::string, peek_poke_t::Port, std::less<>>{std::make_pair(R"ESC(in)ESC", peek_poke_t::Port{.address = 144ULL,.chunks = 3})}'
    maps += ',std::map<std::string, peek_poke_t::Port, std::less<>>{std::make_pair(R"ESC(out)ESC", peek_poke_t::Port{.address = 160ULL,.chunks = 3})}'
    header += block('BRIDGE', 'peek_poke_t', [('STEP',128),('DONE',132),('PRECISE_PEEKABLE',136)], maps)
    header += block('CORE', 'loadmem_t', list(zip(('W_ADDRESS_H','W_ADDRESS_L','W_LENGTH','ZERO_OUT_DRAM','W_DATA','ZERO_FINISHED','R_ADDRESS_H','R_ADDRESS_L','R_DATA'),range(64,100,4))), ',conf_target.mem,3')
    header += block('BRIDGE', 'unknown_t', [])
    header += '.mem = AXI4Config{4, 40, 96}\n'
    # Component fixture uses reset length 7 with a default of 5. Here default
    # is 7, and the independent generated-constructor verifier checks that.
    _, snapshots = oracle()
    payloads = snapshots[0]
    reset = bytearray(payloads[3]); reset[56:64] = (7).to_bytes(8,'little')
    owners = {f'widget/{i}': (f'firesim.widget.{name}.v1', payload) for i, name, payload in (
        (0,'master',payloads[0]), (1,'loadmem',payloads[2]), (2,'clock',payloads[1]),
        (3,'reset-pulse',bytes(reset)), (4,'peek-poke',payloads[4]))}
    owners['widget/5'] = ('',b'')
    return owners, header


class WidgetInventoryTest(unittest.TestCase):
    def test_generated_pass_order_and_complete_configuration(self):
        owners, header = fixture()
        self.assertEqual([row[0] for row in constructor_inventory(header)],
                         ['master_t','loadmem_t','clockmodule_t','reset_pulse_t','peek_poke_t','unknown_t'])
        self.assertEqual(check_widget_inventory(owners, header),
                         ({f'widget/{i}' for i in range(5)}, {'widget/5'}))

    def test_missing_extra_unsupported_and_changed_configuration_reject(self):
        owners, header = fixture()
        for change in (
            lambda o: o.pop('widget/4'),
            lambda o: o.update({'widget/6': ('',b'')}),
            lambda o: o.update({'widget/5': ('invented.v1',b'')}),
            lambda o: o.update({'widget/5': ('',b'omit')}),
            lambda o: o.update({'widget/0': o['widget/1']}),
            lambda o: o.update({'widget/2': ('firesim.widget.clock.v1',b'')}),
            lambda o: o.update({'widget/4': (o['widget/4'][0],o['widget/4'][1][:-1]+b'\x80')}),
        ):
            current = owners.copy(); change(current)
            with self.assertRaises(FormatError):
                check_widget_inventory(current, header)
        for changed in (header.replace('.DONE = 132,','.DONE = 133,'),
                        header.replace('AXI4Config{4, 40, 96}','AXI4Config{4, 40, 64}'),
                        header.replace('ESC(out)ESC','ESC(renamed)ESC')):
            with self.assertRaises(FormatError):
                check_widget_inventory(owners, changed)
