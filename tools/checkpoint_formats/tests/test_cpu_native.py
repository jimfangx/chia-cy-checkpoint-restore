"""Build-log rejection and actual two-layer Make dependency behavior.

The Make test uses a mock compiler, not a claimed native VCS execution. The
full recipe controls separately rebuild and run licensed VCS.
"""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.cpu_native import VCS_HOME, vcs_invocation
from tools.checkpoint_formats.cpu_recipe import ROOT


class CPUNativeTest(unittest.TestCase):
    def test_build_log_rejects_noop_failed_ambiguous_and_incompatible_invocations(self):
        binary = Path('/tmp/native build/FireSim')
        command = shlex.join([VCS_HOME + '/bin/vcs', '-full64', '-Mupdate', '-o', str(binary)])
        log = command + '\nexit=0\n'
        self.assertEqual(vcs_invocation(log, binary)[0], command)
        bad = ['Nothing to be done\nexit=0\n', log.replace('exit=0', 'exit=1'),
               command + '\n' + log, log.replace('-full64 ', ''),
               log.replace('-Mupdate ', ''), log.replace(' -o ', ' +define+SYNTHESIS -o '),
               log.replace(VCS_HOME, '/ecad/tools/synopsys/vcs/older'),
               log.replace(str(binary), str(binary) + '-different')]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(FormatError):
                vcs_invocation(text, binary)

    def test_force_rebuild_crosses_both_real_make_layers_without_changing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            inner = out / 'inner'
            (inner / 'rtlsim').mkdir(parents=True)
            (inner / 'rtlsim/Makefrag-checkpoint').write_text('# no checkpoint profile in this mock\n')
            generated = out / 'generated'
            generated.mkdir()
            rtl, driver = out / 'rtl.sv', out / 'driver.cc'
            rtl.write_text('module emul; endmodule\n')
            driver.write_text('// unchanged driver\n')
            calls = out / 'calls'
            fake = out / 'mock-compiler'
            fake.write_text('#!/bin/sh\n'
                            'while [ "$#" -gt 0 ]; do\n'
                            ' if [ "$1" = "-o" ]; then shift; binary="$1"; fi\n'
                            ' shift\n'
                            'done\n'
                            'printf "invoked\\n" >> ' + shlex.quote(str(calls)) + '\n'
                            'printf "mock\\n" > "$binary"\n')
            fake.chmod(0o755)
            (inner / 'Makefile').write_text(
                'OUT_DIR := $(GEN_DIR)\n'
                'emul_v := $(DESIGN_V)\n'
                'emul_cc := $(DRIVER)\n'
                'include ' + str(ROOT / 'sims/firesim/sim/midas/src/main/cc/rtlsim/Makefrag-vcs') + '\n'
                '.PHONY: vcs\nvcs: $(OUT_DIR)/$(DRIVER_NAME)\n')
            (out / 'Makefile').write_text(
                'DESIGN := FireSim\n'
                'GENERATED_DIR := ' + str(generated) + '\n'
                'simif_dir := ' + str(inner) + '\n'
                'simulator_verilog := ' + str(rtl) + '\n'
                'DRIVER_CC := ' + str(driver) + '\n'
                'include ' + str(ROOT / 'sims/firesim/sim/make/vcs.mk') + '\n')
            stamps = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (rtl, driver)}

            def make(force):
                argv = ['make', '-C', str(out), 'VCS=' + str(fake), 'vcs']
                if force is not None:
                    argv.append('VCS_FORCE_REBUILD=' + str(force))
                subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            make(None)
            make(None)
            make(0)
            self.assertEqual(calls.read_text().splitlines(), ['invoked'])
            make(1)
            make(1)
            self.assertEqual(calls.read_text().splitlines(), ['invoked'] * 3)
            make(None)
            self.assertEqual(calls.read_text().splitlines(), ['invoked'] * 3)
            self.assertEqual(stamps, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                                      for path in (rtl, driver)})


if __name__ == '__main__':
    unittest.main()
