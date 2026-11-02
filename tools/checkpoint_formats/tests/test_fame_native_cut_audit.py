"""Directed samples exercise the same comparator used by the EDA wave audit."""
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_fame_clock_cut import NativeCutAudit


ROWS = [dict(bank=i // 8, slot=i % 8, hierarchy='Top.model_.' + name)
        for i, name in enumerate([
            'checkpoint_fame_clockA_applied', 'b', 'checkpoint_fame_clockB_applied',
            'checkpoint_fame_completed_steps', 'value_fired_0', 'a',
            'checkpoint_fame_clockB_consumed', 'slow_fired_0', 'checkpoint_fame_overflow',
            'clockA_enabled', 'clockB_enabled', 'checkpoint_fame_clockA_consumed', 'data_fired_0'])]


class Samples:
    def __init__(self):
        self.audit = NativeCutAudit(ROWS)
        self.v = dict(ckpt_bank=0, ckpt_slot=0, ckpt_address=0, ckpt_req_valid=0,
                      ckpt_req_ready=0, ckpt_resp_valid=0, ckpt_resp_ready=0,
                      ckpt_resp_data=0, ckpt_resp_error=0, checkpoint_f2_shadow_request=0,
                      checkpoint_f2_shadow_ready=0, checkpoint_f2_shadow_valid=0,
                      checkpoint_f2_shadow_release=0, checkpoint_f2_shadow_control_state=0,
                      checkpoint_f2_control_state=0, checkpoint_f2_read_enable=0)
        self.v.update({'dut.ckpt_saved_error': 0, 'dut.ckpt_saved_data': 0, 'dut.ckpt_pending': 0})
        self.v.update({name: i + 1 for i, name in enumerate(self.audit.selectors.values())})
        self.audit.sample(None, self.v, False)

    def sample(self, rising=False, **changes):
        after = self.v | changes
        self.audit.sample(self.v, after, rising)
        self.v = after

    def capture(self):
        self.sample(checkpoint_f2_shadow_request=1, checkpoint_f2_shadow_ready=1)
        self.sample(True, checkpoint_f2_shadow_request=0, checkpoint_f2_shadow_ready=0,
                    checkpoint_f2_shadow_valid=1, checkpoint_f2_read_enable=1,
                    checkpoint_f2_shadow_control_state=1 << 147)

    def request(self, key):
        self.sample(ckpt_bank=key[0], ckpt_slot=key[1], ckpt_req_valid=1, ckpt_req_ready=1)
        self.sample(True, ckpt_req_valid=0, ckpt_req_ready=0, ckpt_resp_valid=1,
                    ckpt_resp_data=self.audit.baseline[self.audit.selectors[key]])

    def acknowledge(self):
        self.sample(ckpt_resp_ready=1)
        self.sample(True, ckpt_resp_valid=0, ckpt_resp_ready=0)

    def release(self):
        self.sample(checkpoint_f2_shadow_release=1)
        self.sample(True, checkpoint_f2_shadow_control_state=0,
                    checkpoint_f2_shadow_valid=0, checkpoint_f2_read_enable=0)
        self.sample(checkpoint_f2_shadow_release=0)


class NativeCutAuditTest(unittest.TestCase):
    def test_complete_cuts_require_each_of_thirteen_entries_and_hold_response(self):
        s = Samples()
        for _ in range(2):
            s.capture()
            for key in s.audit.selectors:
                s.request(key)
                for _ in range(4):
                    s.sample(True)
                s.acknowledge()
            s.release()
        s.audit.finish()
        self.assertEqual((s.audit.reads, s.audit.acks, s.audit.cuts, s.audit.completed_cuts), (26, 26, 2, 2))
        self.assertEqual(s.audit.stalls, 5 * 26)

    def test_repeated_selector_cannot_replace_a_missing_selector(self):
        s = Samples(); s.capture()
        key = next(iter(s.audit.selectors))
        s.request(key); s.acknowledge()
        with self.assertRaisesRegex(FormatError, 'repeated native selector'):
            s.request(key)

    def test_missing_selector_rejects_release(self):
        s = Samples(); s.capture()
        for key in list(s.audit.selectors)[:-1]:
            s.request(key); s.acknowledge()
        with self.assertRaisesRegex(FormatError, 'before every selector was acknowledged'):
            s.release()

    def test_missing_acknowledgement_rejects_release(self):
        s = Samples(); s.capture()
        s.request(next(iter(s.audit.selectors)))
        s.sample(checkpoint_f2_shadow_release=1)
        with self.assertRaises(FormatError):
            s.sample(True, checkpoint_f2_shadow_control_state=0, ckpt_resp_valid=0)

    def test_unsolicited_response_and_acknowledgement_reject(self):
        for ready in (0, 1):
            with self.subTest(ready=ready):
                s = Samples(); s.capture()
                with self.assertRaisesRegex(FormatError, 'unsolicited native bank response'):
                    s.sample(ckpt_resp_valid=1, ckpt_resp_ready=ready)

    def test_duplicate_acknowledgement_rejects(self):
        s = Samples(); s.capture()
        s.request(next(iter(s.audit.selectors))); s.acknowledge()
        # Inject a second acknowledgement at the edge, even if its corrupt
        # pre-edge response was not separately supplied to the comparator.
        before = s.v | dict(ckpt_resp_valid=1, ckpt_resp_ready=1)
        with self.assertRaisesRegex(FormatError, 'unsolicited native bank response'):
            s.audit.sample(before, s.v, True)

    def test_overlapping_request_rejects(self):
        s = Samples(); s.capture()
        keys = list(s.audit.selectors)
        s.request(keys[0])
        s.sample(ckpt_req_valid=1, ckpt_req_ready=1, ckpt_bank=keys[1][0], ckpt_slot=keys[1][1])
        with self.assertRaisesRegex(FormatError, 'overlapping native bank requests'):
            s.sample(True)

    def test_every_fired_flag_must_remain_at_the_staging_baseline(self):
        for flag in ('value_fired_0', 'slow_fired_0', 'data_fired_0'):
            with self.subTest(flag=flag):
                s = Samples(); s.capture()
                name = 'dut.model_.' + flag
                with self.assertRaisesRegex(FormatError, 'native original storage changed during cut: ' + name):
                    s.sample(**{name: s.v[name] ^ 1})

    def test_capture_edge_drift_rejects(self):
        s = Samples()
        s.sample(checkpoint_f2_shadow_request=1, checkpoint_f2_shadow_ready=1)
        with self.assertRaisesRegex(FormatError, 'native original storage changed during cut'):
            s.sample(True, checkpoint_f2_shadow_control_state=1 << 147,
                     **{'dut.model_.data_fired_0': 0})

    def test_release_edge_drift_rejects(self):
        s = Samples(); s.capture()
        for key in s.audit.selectors:
            s.request(key); s.acknowledge()
        s.sample(checkpoint_f2_shadow_release=1)
        with self.assertRaisesRegex(FormatError, 'native original storage changed during cut'):
            s.sample(True, checkpoint_f2_shadow_control_state=0,
                     **{'dut.model_.data_fired_0': 0})

    def test_bad_response_rejects_before_acknowledgement(self):
        s = Samples(); s.capture()
        s.request(next(iter(s.audit.selectors)))
        self.assertEqual(s.audit.acks, 0)
        with self.assertRaisesRegex(FormatError, 'native bank response differs before acknowledgement'):
            s.sample(ckpt_resp_data=s.v['ckpt_resp_data'] ^ 1)
        self.assertEqual(s.audit.acks, 0)

    def test_response_cannot_disappear_without_acknowledgement(self):
        s = Samples(); s.capture()
        s.request(next(iter(s.audit.selectors)))
        with self.assertRaisesRegex(FormatError, 'response withdrawn before acknowledgement'):
            s.sample(ckpt_resp_valid=0)

    def test_incomplete_final_cut_rejects(self):
        s = Samples(); s.capture()
        with self.assertRaisesRegex(FormatError, 'native audit ends inside an incomplete cut'):
            s.audit.finish()


if __name__ == '__main__':
    unittest.main()
