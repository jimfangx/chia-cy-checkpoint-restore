"""Rehashed debug streams must still prove original words and continuation."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_native_queue_graft import compiled_mutation, wave, GRAFT


class NativeQueueGraftWaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'debug.vcd'
        self.rows = [dict(region=q, hierarchy=f'q{q}.ram', bank=q, slot=0, depth=8) for q in range(4)]
        self.obs = [dict(state=[dict(emitted_register='state',offset=0,width=1664)]) for _ in range(4)]

    def fixture(self, fault=None):
        names = ['clock','reset','armed','capture_clock_mask','capture_read_enable',
                 'capture_request_valid','capture_request_ready','capture_bank','capture_slot',
                 'capture_address','capture_response_valid','capture_response_ready',
                 'capture_response_data','capture_response_error','capture_native_state']
        names += [f'lane{q}_io_{n}' for q in range(4) for n in
                  ('enq_valid','enq_ready','enq_bits','deq_valid','deq_ready','deq_bits')]
        names += [f'q{q}.state' for q in range(4)]
        codes = {n:f'v{i}' for i,n in enumerate(names)}
        lines = ['$scope module native_queue_graft_tb $end\n']
        for n in names[:-4]:
            if fault == 'missing-owner' and n == 'lane3_io_enq_bits': continue
            lines.append(f'$var wire 6656 {codes[n]} {n} $end\n')
        lines.append('$scope module dut $end\n')
        for q in range(4):
            lines += [f'$scope module q{q} $end\n',
                      f'$var wire 1664 {codes[f"q{q}.state"]} state $end\n', '$upscope $end\n']
        lines += ['$upscope $end\n','$upscope $end\n','$enddefinitions $end\n']
        time = 0
        def step(**changes):
            nonlocal time
            lines.append(f'#{time}\n')
            time += 1
            for name, value in changes.items(): lines.append(f'b{value:b} {codes[name]}\n')
        values = {n:0 for n in names}
        values.update(reset=1, capture_request_ready=1,
                      capture_native_state=sum((q+1)<<(1664*q) for q in range(4)))
        for q in range(4):
            values[f'q{q}.state'] = q+1
            values[f'lane{q}_io_enq_valid'] = values[f'lane{q}_io_enq_ready'] = 1
        step(**values);step(clock=1);step(clock=0, reset=0)
        for i in range(6143 if fault == 'early-native' else 6144):
            step(clock=0, **{f'lane{q}_io_enq_bits':i+q*100000 for q in range(4)})
            step(clock=1)
        step(clock=0, armed=1, capture_clock_mask=1, capture_read_enable=1,
             **{f'lane{q}_io_enq_valid':0 for q in range(4)})
        if fault in ('native', 'early-native'):
            step(capture_native_state=0)
            self.path.write_text(''.join(lines))
            return
        for q in range(4):
            for address in range(8):
                selector = 0 if fault == 'duplicate-word' and q == 0 and address == 1 else address
                step(clock=0, capture_request_valid=1, capture_bank=q, capture_slot=0,capture_address=selector)
                step(clock=1);step(clock=0, capture_request_valid=0)
                data = q*100000 if address == 0 else 0
                if fault == 'word' and q == address == 0: data ^= 1
                step(capture_response_valid=1,capture_response_data=data)
                for _ in range(3):step(clock=1);step(clock=0)
                step(capture_response_ready=1);step(clock=1)
                step(clock=0,capture_response_ready=0,capture_response_valid=0)
        step(capture_clock_mask=0,capture_read_enable=0,
             **{f'lane{q}_io_deq_{n}':1 for q in range(4) for n in ('valid','ready')})
        for i in range(127 if fault == 'short-continuation' else 128):
            step(clock=0, **{f'lane{q}_io_deq_bits':i+q*100000 for q in range(4)})
            step(clock=1)
        step(clock=0, **{f'lane{q}_io_deq_valid':0 for q in range(4)})
        step(clock=1)
        self.path.write_text(''.join(lines))

    def run_wave(self, **kwargs):
        return wave(self.path, self.rows, self.obs, hashlib.sha256(self.path.read_bytes()).hexdigest(), **kwargs)

    def test_full_history_words_backpressure_and_continuation(self):
        self.fixture()
        result = self.run_wave()
        self.assertEqual(result['original_word_acknowledgements'], 32)
        self.assertEqual(result['response_stalls'], 96)
        self.assertEqual(result['frontdoor_enqueues'], [6144]*4)
        self.assertEqual(result['frontdoor_dequeues'], [128]*4)

    def test_native_corruption_records_first_divergence_without_ack(self):
        self.fixture('native')
        result = self.run_wave(broken=True)
        self.assertEqual(result['first_divergence']['acknowledged_words'],0)
        self.assertGreater(result['first_divergence']['vcd_time'],0)
        with self.assertRaisesRegex(FormatError,'native vector differs'):
            self.run_wave()

    def test_rehashed_bad_words_duplicate_selectors_missing_owners_and_short_execution(self):
        for fault, reason in [('word','bank word differs'),('duplicate-word','out-of-order'),
                              ('missing-owner','unknown waveform'),('short-continuation','incomplete original workload')]:
            with self.subTest(fault=fault):
                self.fixture(fault)
                with self.assertRaisesRegex(FormatError,reason):self.run_wave()

    def test_healthy_stream_cannot_substitute_for_compiled_fault(self):
        self.fixture()
        with self.assertRaisesRegex(FormatError,'missing first divergence'):
            self.run_wave(broken=True)

    def test_compiled_fault_requires_complete_active_frontdoor_workload(self):
        self.fixture('early-native')
        with self.assertRaisesRegex(FormatError,'incomplete active workload'):
            self.run_wave(broken=True)

    def test_digest_is_for_complete_decompressed_bytes(self):
        self.fixture()
        with self.assertRaisesRegex(FormatError,'complete retained bytes'):
            wave(self.path,self.rows,self.obs,'0'*64)

    def test_compiled_lane_fault_must_be_exact_even_after_coherent_rehash(self):
        directory = self.path.parent
        (directory/'generated').mkdir()
        original = 'assign capture_native_state[0 +: 1664] = checkpoint_shell_region0_ckpt_native_state;\n'
        (directory/'generated'/(GRAFT+'.sv')).write_text(original)
        mutation = directory/'compiled-native-swap.sv'
        correct = original.replace('region0_', 'region1_')
        for source, accepted in ((correct,True),(original,False),(correct+'// extra edit\n',False)):
            with self.subTest(source=source):
                mutation.write_text(source)
                digest = hashlib.sha256(mutation.read_bytes()).hexdigest()
                receipt = dict(artifacts={mutation.name:digest},
                               compiled_mutation_source=dict(path=str(mutation),sha256=digest))
                if accepted:self.assertEqual(compiled_mutation(directory,receipt)['sha256'],digest)
                else:
                    with self.assertRaisesRegex(FormatError,'wrong compiled lane mutation'):
                        compiled_mutation(directory,receipt)

    def test_compiled_lane_fault_rejects_unbound_or_changed_source(self):
        directory = self.path.parent
        (directory/'generated').mkdir()
        original = 'assign capture_native_state[0 +: 1664] = checkpoint_shell_region0_ckpt_native_state;\n'
        (directory/'generated'/(GRAFT+'.sv')).write_text(original)
        mutation = directory/'compiled-native-swap.sv'
        mutation.write_text(original.replace('region0_', 'region1_'))
        for artifacts in ({}, {mutation.name:'0'*64}):
            with self.assertRaisesRegex(FormatError,'unbound compiled lane mutation'):
                compiled_mutation(directory,dict(artifacts=artifacts))


if __name__ == '__main__':
    unittest.main()
