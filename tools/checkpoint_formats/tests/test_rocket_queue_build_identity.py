"""A queue's state shape alone cannot identify its synthesized readout protocol."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.checkpoint_formats.codec import canonical
from tools.checkpoint_formats.tests import verify_rocket_native_queues as queue


class RocketQueueBuildIdentityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.generated = self.base / 'generated'
        self.generated.mkdir()
        (self.generated / 'production-source-sha256.txt').write_text('1' * 64 + '\n')
        (self.generated / 'descriptors.json').write_bytes(canonical(dict(uncovered_physical_gates=[])))
        (self.generated / 'generated.sv').write_text('module same_state_shape; endmodule\n')
        for q in range(4):
            (self.generated / f'shell-{q}-banks-binding.json').write_bytes(canonical(dict(
                synchronous_memory_readout=dict(adapter_version=3, response_latency_edges=4))))

    def digest(self):
        return hashlib.sha256(canonical(queue.capture_manifest(self.generated, [], []))).hexdigest()

    def test_identical_inputs_retain_identity(self):
        self.assertEqual(self.digest(), self.digest())

    def test_readout_protocol_changes_identity_with_identical_state_shape(self):
        original = self.digest()
        path = self.generated / 'shell-2-banks-binding.json'
        path.write_bytes(canonical(dict(synchronous_memory_readout=dict(
            adapter_version=2, response_latency_edges=3))))
        self.assertNotEqual(original, self.digest())

    def test_emitted_equation_changes_identity_with_identical_descriptors(self):
        original = self.digest()
        path = self.generated / 'generated.sv'
        path.write_text(path.read_text().replace('same_state_shape', 'changed_equation'))
        self.assertNotEqual(original, self.digest())

    def test_transport_change_changes_identity(self):
        original = self.digest()
        sources = self.base / 'source'
        for name in queue.RTL:
            path = sources / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((queue.ROOT / name).read_bytes())
        with patch.object(queue, 'ROOT', sources):
            self.assertEqual(original, self.digest())
            path = sources / queue.RTL[0]
            path.write_bytes(path.read_bytes() + b'\n// changed transport build\n')
            self.assertNotEqual(original, self.digest())


if __name__ == '__main__':
    unittest.main()
