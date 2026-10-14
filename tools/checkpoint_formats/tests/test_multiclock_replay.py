import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, decode, encode
from tools.checkpoint_formats.multiclock_replay import document, package_capture, prepare_replay
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic, encode_semantic
from tools.checkpoint_formats.tests.test_semantic_multiclock import inventory


def example():
    manifest, old = inventory()
    clock, slow = manifest['clock_inputs']
    boundary = dict(boundary_version=3, dut_module='Dut', dut_root=manifest['dut_root'],
                    sample_phase='before_clock_event', clock_inputs=manifest['clock_inputs'],
                    clock_aliases=manifest['clock_aliases'],
                    ports=[dict(name='data', direction='input', width=9), dict(name='out', direction='output', width=9)])
    phase = dict(event_index=8, cycle_clock=clock, clock_levels={clock: 0, slow: 0}, rising_edges={clock: 2, slow: 3})
    rtl_build, trace_build = builds(manifest, boundary, 'test')
    ckpt = document('rtlckpt', rtl_build, phase, 2, old['records'])
    records = []
    for index, (cycle, levels, alias) in enumerate([(2, {clock: 0, slow: 1}, '0'),
                                                  (2, {clock: 1, slow: 1}, '1'),
                                                  (3, {clock: 0, slow: 0}, '1')]):
        records.append(dict(event_index=8 + index, cycle=cycle, clock_levels=levels,
                            inputs={'data': dict(width=9, value='007')},
                            outputs={'out': dict(width=9, value='003'), 'forwarded': dict(width=1, value=alias)}))
    trace = document('trace', trace_build, phase, 2, records)
    return manifest, boundary, ckpt, trace


class MultiClockReplayTests(unittest.TestCase):
    def test_explicit_phase_complete_state_and_staggered_events_roundtrip(self):
        manifest, _, ckpt, trace = example()
        self.assertEqual(decode_semantic(encode_semantic(ckpt, manifest), ckpt['build'], manifest), ckpt)
        self.assertEqual(decode(encode('trace', trace), 'trace', trace['build']), trace)
        self.assertEqual([r['cycle'] for r in trace['records']], [2, 2, 3])

    def test_missing_clocks_wrong_counts_high_cuts_and_version_substitution_reject(self):
        manifest, _, ckpt, _ = example()
        clock = manifest['clock_inputs'][0]
        mutations = [lambda d: d['event_phase']['clock_levels'].pop(clock),
                     lambda d: d['event_phase']['rising_edges'].pop(clock),
                     lambda d: d['event_phase']['clock_levels'].update({clock: 1}),
                     lambda d: d['event_phase']['clock_levels'].update({clock: False}),
                     lambda d: d['event_phase']['rising_edges'].update({clock: 9}),
                     lambda d: d['event_phase']['rising_edges'].update({clock: True}),
                     lambda d: d['event_phase'].update(event_index=True),
                     lambda d: d['event_phase'].update(cycle_clock='unknown'),
                     lambda d: d.update(target_cycle=3), lambda d: d.update(target_clock_phase='before_rising_edge'),
                     lambda d: d['build'].update(rtl_build_hash='d' * 64),
                     lambda d: d['records'].pop()]
        for mutate in mutations:
            bad = copy.deepcopy(ckpt); mutate(bad)
            with self.subTest(bad=bad), self.assertRaises(FormatError):
                encode_semantic(bad, manifest)
        bad = copy.deepcopy(ckpt)
        bad['event_phase']['clock_levels']['Other.clock'] = 0
        bad['event_phase']['rising_edges']['Other.clock'] = 0
        with self.assertRaisesRegex(FormatError, 'unknown semantic event-phase'):
            encode_semantic(bad, manifest)
        bad = copy.deepcopy(ckpt); bad['checkpoint_type'] = 'fsckpt'
        with self.assertRaisesRegex(FormatError, 'unsupported version'):
            encode('fsckpt', bad)

    def test_skipped_reordered_unchanged_and_incomplete_clock_events_reject(self):
        _, _, _, trace = example()
        mutations = [lambda d: d['records'][0].update(event_index=9),
                     lambda d: d['records'].reverse(), lambda d: d['records'][1].update(cycle=3),
                     lambda d: d['records'][0].update(clock_levels=dict(d['event_phase']['clock_levels'])),
                     lambda d: d['records'][0]['clock_levels'].pop(next(iter(d['event_phase']['clock_levels']))),
                     lambda d: d['records'][0]['clock_levels'].update(unknown=1),
                     lambda d: d['records'][0].update(event_index=True),
                     lambda d: d['records'][0]['outputs']['out'].update(value='00x')]
        for mutate in mutations:
            bad = copy.deepcopy(trace); mutate(bad)
            with self.subTest(bad=bad), self.assertRaises(FormatError):
                encode('trace', bad)

    def test_capture_requires_complete_actual_state_and_clock_phase(self):
        manifest, boundary, ckpt, _ = example()
        clocks = manifest['clock_inputs']
        rows = []
        levels = dict.fromkeys(clocks, 0)
        for event in range(4):
            next_levels = dict.fromkeys(clocks, 1 - event % 2)
            rows.append(dict(event_index=event, cycle=(event + 1) // 2, before=dict(levels), clock_levels=next_levels,
                             inputs={'data': dict(width=9, value='007')},
                             outputs={'out': dict(width=9, value='003'),
                                      'forwarded': dict(width=1, value=str(levels[clocks[1]]))}, values=['101'] * 10))
            levels = next_levels
        data, trace = package_capture(manifest, boundary, 'test', rows, 2, 2, clocks[0])
        self.assertEqual(decode_semantic(data, ckpt['build'], manifest)['target_cycle'], 1)
        for mutate in [lambda r: r[2]['values'].pop(), lambda r: r[1]['before'].update({clocks[0]: 0}),
                       lambda r: r[1].update(cycle=0), lambda r: r[0]['outputs'].pop('out'),
                       lambda r: r[1]['outputs']['forwarded'].update(value='0'),
                       lambda r: r[0]['inputs'].update(unknown=dict(width=1, value='0'))]:
            bad = copy.deepcopy(rows); mutate(bad)
            with self.assertRaises(FormatError):
                package_capture(manifest, boundary, 'test', bad, 2, 2, clocks[0])
        with self.assertRaisesRegex(FormatError, 'all clocks low'):
            package_capture(manifest, boundary, 'test', rows, 1, 2, clocks[0])

    def test_both_complete_artifacts_validate_before_loader_publication(self):
        manifest, boundary, ckpt, trace = example()
        clean = '// mapping validation fixture'
        access = dict(access_version=1, scope='clean-rtl-inventory-only',
                      state_manifest_sha256=ckpt['build']['state_manifest_hash'],
                      clean_rtl_sha256=hashlib.sha256(clean.encode()).hexdigest(), dut_module='Dut',
                      state=[dict(state_id=e['state_id'], rtl_path=e['hierarchy'][len(manifest['dut_root']) + 1:])
                             for e in manifest['state']])
        data = encode_semantic(ckpt, manifest)
        mutations = [lambda t: t['records'][0]['outputs'].pop('out'),
                     lambda t: t['records'][0]['inputs'].update(unknown=dict(width=1, value='0')),
                     lambda t: t['records'][0]['outputs']['forwarded'].update(value='1'),
                     lambda t: t['event_phase']['rising_edges'].update({manifest['clock_inputs'][1]: 2})]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'reject'
            for mutate in mutations:
                bad = copy.deepcopy(trace); mutate(bad)
                with self.assertRaises(FormatError):
                    prepare_replay(manifest, boundary, 'test', clean, access, data, encode('trace', bad), directory)
                self.assertFalse(directory.exists())
            result = prepare_replay(manifest, boundary, 'test', clean, access, data, encode('trace', trace), directory)
            self.assertEqual(result['words'], 10)
            self.assertEqual(result['samples'], 3)
            self.assertEqual(len((directory / 'restore.txt').read_text().splitlines()), 10)


if __name__ == '__main__':
    unittest.main()
