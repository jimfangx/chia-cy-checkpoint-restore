from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from tools.checkpoint_formats.tests.native_parallel import checked_map

class NativeParallelTests(unittest.TestCase):
    def test_complete_ordered_results(self):
        def action(n):
            time.sleep((3-n)*0.001)
            return n*n
        self.assertEqual(checked_map(action,range(4)),[0,1,4,9])

    def test_failed_sibling_does_not_skip_real_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            def action(n):
                path=Path(directory)/str(n)
                subprocess.run([sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.argv[2])',str(path),str(n)],check=True)
                if n in (0,3):raise RuntimeError('failure '+str(n))
                return n
            with self.assertRaisesRegex(RuntimeError,'failure 0'):checked_map(action,range(8))
            self.assertEqual({p.name for p in Path(directory).iterdir()},{str(n) for n in range(8)})

    def test_empty_batch(self):
        self.assertEqual(checked_map(lambda x:x,[]),[])

    def test_generator_exception_waits_for_submitted_processes(self):
        # Executor shutdown joins all submitted jobs even if constructing the
        # remaining batch fails; their retained outputs cannot disappear.
        with tempfile.TemporaryDirectory() as directory:
            def items():
                yield 0
                raise ValueError('batch input')
            def action(n):
                time.sleep(.01);(Path(directory)/str(n)).write_text('finished')
            with self.assertRaisesRegex(ValueError,'batch input'):checked_map(action,items())
            self.assertEqual((Path(directory)/'0').read_text(),'finished')
