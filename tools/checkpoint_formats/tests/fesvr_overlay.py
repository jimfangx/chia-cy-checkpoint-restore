"""Use the production build-local loader overlay in native host regressions."""
import os
from pathlib import Path

from tools.checkpoint_formats.cpu_recipe import ROOT

DIRECTORY = ROOT / 'generators/firechip/bridgestubs/src/main/cc/fesvr'
BUILDER = DIRECTORY / 'build_checkpoint_fesvr.py'
LOADER = DIRECTORY / 'owned_elfloader.cc'
INSTALLED = ROOT / '.conda-env/riscv-tools'


def overlay_inputs():
    return [Path(__file__), BUILDER, LOADER]


def build_overlay(out, execute, *, named_log=False):
    library = out / 'libfesvr-checkpoint.a'
    execute(['python3', BUILDER, '--library', INSTALLED / 'lib/libfesvr.a',
             '--include', INSTALLED / 'include', '--out', library, '--cxx', os.environ['CXX']],
            'fesvr-overlay-build' if named_log else out / 'fesvr-overlay-build.log')
    return library
