"""Native source closures must survive the real flat snapshot file layout."""
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.tests import verify_native_descriptors as descriptors
from tools.checkpoint_formats.tests import verify_native_checkpoint_widget as widget
from tools.checkpoint_formats.tests import verify_native_checkpoint_top as top


class NativeSourceClosureTests(unittest.TestCase):
    def test_descriptor_widget_and_top_preserve_complete_unique_flat_snapshots(self):
        endpoint = 'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala'
        self.assertTrue(set(descriptors.SOURCES).issubset(widget.NETWORK_SOURCES))
        self.assertTrue(set(widget.NETWORK_SOURCES).issubset(widget.SOURCES))
        self.assertTrue(set(widget.SOURCES).issubset(top.SOURCES))
        self.assertTrue(set(top.INPLACE_SOURCES).issubset(top.SOURCES))
        for producer in (descriptors, widget, top):
            with self.subTest(producer=producer.__name__), tempfile.TemporaryDirectory() as temporary:
                sources = producer.SOURCES
                self.assertEqual(len(sources), len(set(sources)), 'duplicate source path')
                self.assertEqual(sources.count(endpoint), 1, 'endpoint helper must appear exactly once')
                self.assertEqual(len(sources), len({Path(name).name for name in sources}),
                                 'different source paths collide in the native flat layout')
                directory = Path(temporary)
                # Match the exclusive destination ownership required by the native
                # widget runner. Keep every original byte, including inherited files.
                for name in sources:
                    source = producer.ROOT / name
                    with (directory / source.name).open('xb') as snapshot:
                        snapshot.write(source.read_bytes())
                self.assertEqual({p.name for p in directory.iterdir()}, {Path(n).name for n in sources})
                for name in sources:
                    self.assertEqual((directory / Path(name).name).read_bytes(), (producer.ROOT / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
