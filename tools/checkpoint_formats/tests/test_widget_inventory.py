import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.verify_widget_checkpoint_vcs import oracle
from tools.checkpoint_formats.tests.widget_inventory import check_widget_inventory, constructor_inventory
from tools.checkpoint_formats.tests.verify_fased_checkpoint_vcs import configuration, text, words
from tools.checkpoint_formats.tests.verify_stream_checkpoint_vcs import configuration as stream_configuration


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
    def stream_fixture(self):
        owners, header = fixture()
        vectors = []
        for direction, names in enumerate((('push0','push1'),('pull0','pull1'))):
            values=[]
            for i, name in enumerate(names):
                q=direction*2+i
                values.append(f'CPUManagedStreams::StreamParameters(std::string(R"ESC({name})ESC"), '
                              f'{(q+1)*4096}ULL, {256+q*4}ULL, {(3,5)[i]}, {8*(i+1)})')
            vectors.append('std::vector<CPUManagedStreams::StreamParameters>{'+','.join(values)+'}')
        header += '#ifdef GET_MANAGED_STREAM_CONSTRUCTOR\nregistry.add_widget(new CPUManagedStreamWidget(\n'
        header += 'simif,0,args,'+','.join(vectors)+'));\n#endif\n.cpu_managed = AXI4Config{4,40,64}\n'
        owners = {f'widget/{int(key.split("/")[1]) + (int(key.split("/")[1])>=2)}': value
                  for key,value in owners.items()}
        owners['widget/2'] = ('firesim.widget.cpu-managed-stream.v1', stream_configuration(8)+words(1))
        return owners, header

    def test_stream_configuration_direction_order_and_lifecycle(self):
        owners, header = self.stream_fixture()
        self.assertEqual(check_widget_inventory(owners,header),
                         ({f'widget/{i}' for i in range(6)}, {'widget/6'}))
        schema, payload = owners['widget/2']
        owners['widget/2'] = (schema, payload[:-8]+words(0))
        check_widget_inventory(owners,header)

    def test_stream_mismatch_and_unknown_peer_engine_fail_closed(self):
        owners, header = self.stream_fixture()
        for changed in (header.replace('4096ULL','4097ULL'),
                        header.replace('256ULL','257ULL'),
                        header.replace('ESC(push0)ESC','ESC(renamed)ESC'),
                        header.replace('3, 8','4, 8'),
                        header.replace('5, 16','5, 32'),
                        header.replace('AXI4Config{4,40,64}','AXI4Config{4,40,128}'),
                        header.replace('simif,0,args','simif,1,args'),
                        header.replace('CPUManagedStreamWidget','FPGAManagedStreamWidget'),
                        header.replace('4096ULL','not_a_literal')):
            with self.assertRaises(FormatError): check_widget_inventory(owners,changed)
        schema, payload = owners['widget/2']
        for bad in (b'',payload[:-1],payload+b'\0',payload[:-8]+words(2)):
            current=owners.copy(); current['widget/2']=(schema,bad)
            with self.assertRaises(FormatError): check_widget_inventory(current,header)

    def fased_fixture(self):
        owners, header = fixture()
        block = '''#ifdef GET_BRIDGE_CONSTRUCTOR
registry.add_widget(new FASEDMemoryTimingModel(
  simif,
  AddressMap{
    std::vector<std::pair<std::string, uint32_t>>{
      { R"ESC(latency)ESC", 8 },
      { R"ESC(cycles)ESC", 12 },
    },
    std::vector<std::pair<std::string, uint32_t>>{
      { R"ESC(latency)ESC", 8 },
    }
  },
  0,
  args,
  R"ESC(stats.csv)ESC",
  1L << 10
));
#endif
'''
        header = header.replace('#ifdef GET_BRIDGE_CONSTRUCTOR\nregistry.add_widget(new unknown_t(',
                                block+'#ifdef GET_BRIDGE_CONSTRUCTOR\nregistry.add_widget(new unknown_t(')
        owners['widget/6'] = owners.pop('widget/5')
        config = configuration({'latency':8,'cycles':12}, {'latency':8}, 0, 1024, False, {}, (), ())
        owners['widget/5'] = ('firesim.widget.fased.v1', config+words(1)+text('cycles,\n'))
        return owners, header

    def test_fased_configuration_lifecycle_and_history(self):
        owners, header = self.fased_fixture()
        self.assertEqual(check_widget_inventory(owners, header),
                         ({f'widget/{i}' for i in range(6)}, {'widget/6'}))

    def test_changed_fased_configuration_or_history_reject(self):
        owners, header = self.fased_fixture()
        for changed in (header.replace('1L << 10', '1L << 11'),
                        header.replace('ESC(cycles)ESC', 'ESC(renamed)ESC'),
                        header.replace('ESC(latency)ESC", 8', 'ESC(latency)ESC", 9')):
            with self.assertRaises(FormatError):
                check_widget_inventory(owners, changed)
        for payload in (b'', owners['widget/5'][1][:-1], owners['widget/5'][1]+b'\0'):
            current = owners.copy(); current['widget/5'] = ('firesim.widget.fased.v1', payload)
            with self.assertRaises(FormatError):
                check_widget_inventory(current, header)

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
