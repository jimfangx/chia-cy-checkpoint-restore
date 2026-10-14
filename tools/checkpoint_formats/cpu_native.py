"""Record an executed exact-recipe CPU native build, without granting restore support.

An up-to-date Make result is insufficient: the selected successful log must
contain the actual pinned VCS invocation. All native translation units, compiler
dependencies, linked libraries and generated artifacts are bound to that run.
"""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from .codec import require
from .cpu_recipe import ROOT, recipe_settings
from .evidence import file_sha

VCS_HOME = '/ecad/tools/synopsys/vcs/Y-2026.03-SP1'


def vcs_invocation(log, binary):
    """Reject no-op, failed, ambiguous, wrong-release or wrong-output builds."""
    require(log.rstrip().endswith('exit=0'), 'native Make did not finish successfully')
    lines = [line for line in log.splitlines() if line.startswith(VCS_HOME + '/bin/vcs ')]
    require(len(lines) == 1, 'exactly one executed native VCS invocation required')
    argv = shlex.split(lines[0])
    require('-full64' in argv and '-Mupdate' in argv and '+define+SYNTHESIS' not in argv,
            'wrong native VCS mode or flags')
    require(argv.count('-o') == 1 and argv[argv.index('-o') + 1] == str(binary),
            'native invocation belongs to another executable')
    return lines[0], argv


def record_build(recipe, build, log, destination):
    require(os.environ.get('VCS_HOME') == VCS_HOME and
            os.environ.get('CC') == '/usr/bin/gcc-13' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env.sh LAST')
    build = Path(build).resolve()
    binary = build / 'FireSim'
    require(binary.is_file(), 'missing native CPU executable')
    command, argv = vcs_invocation(Path(log).read_text(), binary)
    units = sorted({str(Path(token)) for token in argv
                    if token.startswith('/') and Path(token).suffix in ('.cc', '.cpp', '.c')})
    require(len(units) == 58, 'changed CPU native translation unit inventory; audit it explicitly')
    cc = ROOT / 'sims/firesim/sim/midas/src/main/cc'
    paths = [binary, Path(log).resolve(), Path(recipe['recipe_file']),
             ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh',
             ROOT / 'automations/checkpoint_loop/vcs-env.sh',
             cc / 'Makefile', cc / 'rtlsim/Makefrag-vcs',
             ROOT / 'sims/firesim/sim/Makefile',
             cc / '../scala/midas/checkpoint/SimulatorStateInventory.scala',
             ROOT / 'tools/checkpoint_formats/simulator.py',
             ROOT / 'tools/checkpoint_formats/cpu_recipe.py', Path(__file__)]
    paths += list((ROOT / 'sims/firesim/sim/make').glob('*.mk'))
    paths += list(Path(recipe['resolved_makefrag']).glob('*.mk'))
    paths += [build / ('FireSim-generated' + suffix) for suffix in
              ('.sv', '.const.h', '.const.vh', '.defines.vh',
               '.simulator-state.json', '.simulator-reference.fir')]
    # Include static archives (notably FESVR), RTL and VCS itself as well as C++.
    paths += [Path(token) for token in argv if token.startswith('/') and Path(token).is_file()]
    deps = build / 'FireSim-debug.csrc'
    require(deps.is_dir() and list(deps.glob('*.d')), 'missing actual native compiler dependencies')
    for dep in sorted(deps.glob('*.d')):
        paths.append(dep)
        for token in shlex.split(dep.read_text().replace('\\\n', ' ').partition(':')[2]):
            path = Path(token)
            if path.is_absolute():
                require(path.is_file(), 'missing native compiler dependency ' + str(path))
                paths.append(path)
    ldd = subprocess.check_output(['ldd', str(binary)], text=True)
    require('not found' not in ldd, 'missing linked native CPU library')
    libraries = sorted(set(re.findall(r'(?:=> )?(/\S+)\s+\(0x', ldd)))
    paths += [Path(path) for path in libraries]
    paths += sorted(path for path in (build / 'FireSim.daidir').rglob('*') if path.is_file())
    versions = {name: subprocess.check_output([os.environ[name], '--version'], text=True).splitlines()[0]
                for name in ('CC', 'CXX')}
    paths += [Path(os.environ[name]) for name in ('CC', 'CXX', 'VCS_CC')]
    paths = list(dict.fromkeys(path.resolve() for path in paths))
    require(all(path.is_file() for path in paths), 'missing CPU native build input')
    symbols = subprocess.check_output(['nm', '-C', str(binary)], text=True)
    require('uart_t::save_checkpoint() const' in symbols and
            'heartbeat_t::save_checkpoint() const' in symbols, 'missing audited host adapters')
    report = dict(scope='executed exact CPU native build; full CPU restores remain unsupported',
                  native_binary=str(binary), vcs_home=VCS_HOME,
                  compilers={name: os.environ[name] for name in ('CC', 'CXX', 'VCS_CC')},
                  compiler_versions=versions, vcs_build_command=command, translation_units=units,
                  dynamic_libraries=libraries, dependency_root=str(deps), recipe=recipe,
                  sources_sha256={str(path): file_sha(path) for path in paths},
                  uart_adapter_linked=True, heartbeat_adapter_linked=True,
                  checkpoint_profile=None, level1_verified=False, level2_verified=False)
    Path(destination).write_text(json.dumps(report, indent=2) + '\n')
    return report
