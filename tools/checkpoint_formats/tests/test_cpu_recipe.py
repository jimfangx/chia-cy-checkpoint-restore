from tools.checkpoint_formats import toolchain as _toolchain
import tempfile
from pathlib import Path
import shlex
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.cpu_recipe import (
    FIELDS, RECIPES, RECIPE_FILE, ROOT, native_build_command, recipe_settings,
)


class CPURecipeTest(unittest.TestCase):
    def test_exact_settings_and_makefrag_resolution(self):
        for name in RECIPES.values():
            settings = recipe_settings(name)
            self.assertEqual(set(settings['settings']), set(FIELDS))
            self.assertEqual(settings['settings']['PLATFORM'], 'f2')
            self.assertEqual(settings['settings']['TARGET_PROJECT'], 'firesim')
            self.assertEqual(settings['settings']['DESIGN'], 'FireSim')
            self.assertEqual(settings['resolved_makefrag'],
                             str(ROOT / 'generators/firechip/chip/src/main/makefrag/firesim'))
            self.assertFalse(settings['checkpoint_support_verified'])
            command = native_build_command(settings, ROOT / 'automations/checkpoint_loop/runs/test/build', 'vcs')
            shell = command['argv'][2]
            self.assertIn('vcs-env.sh && make', shell)
            argv = shlex.split(shell.partition(' && make ')[2])
            for field in FIELDS:
                value = settings['resolved_makefrag'] if field == 'TARGET_PROJECT_MAKEFRAG' else settings['settings'][field]
                self.assertIn(field + '=' + value, argv)
            self.assertIn('VCS=' + _toolchain.VCS + ' -full64', argv)
            self.assertIn('VCS_FORCE_REBUILD=1', argv)
            self.assertNotIn('FS_CHECKPOINT_PROFILE=fcfs-fased-v1', argv)

    def test_changed_settings_are_read_from_current_recipe_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'recipes.yaml'
            source = RECIPE_FILE.read_text()
            path.write_text(source.replace('WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config', 'ChangedConfiguration'))
            name = RECIPES['Rocket']
            modified = recipe_settings(name, path)
            self.assertEqual(modified['settings']['PLATFORM_CONFIG'], 'ChangedConfiguration')
            self.assertNotEqual(modified['recipe_file_sha256'], recipe_settings(name)['recipe_file_sha256'])

    def test_explicit_lifecycle_provider_preserves_recipe_and_rejects_missing_source(self):
        settings = recipe_settings(RECIPES['Rocket'])
        build = ROOT / 'automations/checkpoint_loop/runs/test/build'
        source = ROOT / 'toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc'
        command = native_build_command(settings, build, 'vcs', htif_source=source)
        argv = shlex.split(command['argv'][2].partition(' && make ')[2])
        self.assertIn('CHECKPOINT_HTIF_SOURCE=' + str(source), argv)
        self.assertEqual(settings, recipe_settings(RECIPES['Rocket']))
        self.assertFalse(any('CHECKPOINT_HTIF_SOURCE=' in token for token in
                             shlex.split(native_build_command(settings, build, 'vcs')['argv'][2])))
        with self.assertRaises(FormatError):
            native_build_command(settings, build, 'vcs', htif_source=source.with_name('missing.cc'))

    def test_unknown_recipe_incomplete_settings_and_non_metasim_goals_reject(self):
        with self.assertRaises(FormatError):
            recipe_settings('standalone_shuttle')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'recipes.yaml'
            path.write_text(RECIPES['Rocket'] + ': {PLATFORM: f2}\n')
            with self.assertRaises(FormatError):
                recipe_settings(RECIPES['Rocket'], path)
        settings = recipe_settings(RECIPES['Rocket'])
        for goal in ('replace-rtl', 'f2', 'vcs-debug', 'verilator'):
            with self.assertRaises(FormatError):
                native_build_command(settings, ROOT / 'automations/checkpoint_loop/runs/test/build', goal)
        with self.assertRaises(FormatError):
            native_build_command(settings, Path('/tmp/cpu-build'), 'vcs')


if __name__ == '__main__':
    unittest.main()
