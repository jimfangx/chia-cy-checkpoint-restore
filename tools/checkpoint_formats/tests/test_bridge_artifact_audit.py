from tools.checkpoint_formats import toolchain as _toolchain
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.tests.audit_bridge_semantic import audit_native_archive
from tools.checkpoint_formats.tests import test_aggregate_packed as fixture_api


class BridgeArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        original_build, old, self.generated, self.layout, original = fixture_api.PackedAggregateTest().fixture(self.out)
        self.executable = self.out / 'AXI4Fuzzer-checkpoint'
        self.executable.write_bytes((self.out / 'simv').read_bytes())
        self.source = self.out / 'actual-native-source.cc'
        self.source.write_text('native implementation')
        self.inputs = dict(compiler=_toolchain.CXX, vcs_home=_toolchain.VCS_HOME,
                           make_profile='fcfs-fased-v1', generated_build=self.layout['generated_build_hash'],
                           sources={str(self.source): hashlib.sha256(self.source.read_bytes()).hexdigest()})
        self.runtime = packed.runtime_manifest(old['profile'], self.generated, self.layout,
                                              old['native_owners'], hashlib.sha256(canonical(self.inputs)).hexdigest())
        self.build = aggregate.build_identity(self.runtime, self.generated, self.layout, self.executable)
        self.metadata = self.out / 'production-build-metadata'
        self.metadata.mkdir()
        self.documents = dict(zip(('native-build-inputs', 'runtime-manifest', 'generated-manifest',
                                   'harness-layout', 'aggregate-build'),
                                  (self.inputs, self.runtime, self.generated, self.layout, self.build)))
        for name, doc in self.documents.items():
            self.write(name, doc)
        # Bind a complete independently assembled image to the exported binary.
        from tools.checkpoint_formats.codec import decode, encode
        cut = decode(original, 'fsckpt', original_build)
        cut['build'] = self.build
        (self.out / 'capture.fsckpt').write_bytes(encode('fsckpt', cut))

    def write(self, name, value):
        (self.metadata / (name + '.json')).write_bytes(canonical(value))

    def test_complete_archive_can_be_audited_without_live_build_directory(self):
        runtime, generated, layout, cut = audit_native_archive(self.out)
        self.assertEqual((runtime, generated, layout), (self.runtime, self.generated, self.layout))
        self.assertEqual(cut['target_cycle'], 9)
        self.assertEqual(len(cut['records']), len(generated['state']) + len(layout['records']) + 3)

    def test_missing_export_and_modified_executable_source_or_image_reject(self):
        for path in [*self.metadata.iterdir(), self.executable, self.source, self.out / 'capture.fsckpt']:
            original = path.read_bytes()
            # Missing metadata reproduces the previous loop audit failure.
            if path.parent == self.metadata or path == self.executable:
                path.unlink()
                with self.assertRaisesRegex(FormatError, 'missing archived'):
                    audit_native_archive(self.out)
                path.write_bytes(original)
            path.write_bytes(original + b' ')
            if path.suffix == '.json':
                # JSON whitespace is immaterial; change a bound field instead.
                doc = copy.deepcopy(self.documents[path.stem])
                if path.stem == 'native-build-inputs': doc['vcs_home'] = 'older-release'
                elif path.stem == 'runtime-manifest': doc['native_build_hash'] = 'c' * 64
                elif path.stem == 'generated-manifest': doc['reference_sha256'] = 'c' * 64
                elif path.stem == 'harness-layout': doc['generated_build_hash'] = 'c' * 64
                else: doc['simulator_build_hash'] = 'c' * 64
                path.write_bytes(canonical(doc))
            with self.assertRaises(FormatError):
                audit_native_archive(self.out)
            path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
