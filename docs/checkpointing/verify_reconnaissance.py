#!/usr/bin/env python3
"""Validate M0 source evidence; deliberately does not claim RTL/replay testing."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
doc = root / 'docs/checkpointing/reconnaissance.md'
text = doc.read_text()
assert len(text) > 10000, 'Missing or incomplete reconnaissance artifact'
links = re.findall(r'\]\((\.\./\.\./[^)]+)\)', text)
assert len(links) > 75
for link in links:
    assert (doc.parent / link).exists(), f'Missing source: {link}'
s = root / 'sims/firesim/sim/midas/src/main/scala/midas'
compiler = (s / 'stage/GoldenGateCompilerPhase.scala').read_text()
assert compiler.index('val loweredTarget') < compiler.index('.execute(loweredTarget)')
passes = (s / 'passes/MidasTransforms.scala').read_text()
ordered = ['new firrtl.transforms.DeadCodeElimination', 'new BridgeExtraction',
           'fame.WrapTop', 'new fame.ExtractModel', 'new fame.FAMETransform',
           'fame.MultiThreadFAME5Models', 'new fame.EmitAndWrapRAMModels',
           'new SimulationMapping']
positions = [passes.index(x) for x in ordered]
assert positions == sorted(positions), 'Documented pass ordering changed'
assert 'TODO: Renames!' in (s / 'passes/fame/MultiThreadFAME5Models.scala').read_text()
assert 'require(readWritePorts.isEmpty)' in (s / 'passes/fame/EmitAndWrapRAMModels.scala').read_text()
assert 'class BridgeExtraction' in (s / 'passes/ExtractBridges.scala').read_text()
cc = root / 'sims/firesim/sim/midas/src/main/cc'
interface = (cc / 'core/bridge_driver.h').read_text()
assert 'virtual void tick()' in interface
assert 'save_state' not in interface and 'load_state' not in interface
for anchor in ['rresp', 'bresp', 'std::vector<char> data']:
    assert anchor in (cc / 'emul/mm.h').read_text()
for path in [
    '/ecad/tools/synopsys/vcs/W-2024.09-1/bin/vcs',
    '/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg',
    '/ecad/tools/synopsys/fm/P-2019.03-SP2/bin/fm_shell',
    '/ecad/tools/cadence/CONFRML/CONFRML212/bin/lec',
    '/ecad/tools/synopsys/syn/T-2022.03-SP5/bin/dc_shell',
    '/ecad/tools/cadence/GENUS/GENUS211/bin/genus',
    '/ecad/tools/cadence/JLS/JLS211/bin/joules',
    '/ecad/tools/cadence/SSV/SSV171/bin/voltus',
    '/ecad/tools/synopsys/pts/P-2019.03-SP2/bin/pt_shell',
]:
    assert Path(path).is_file(), f'Missing installed entry: {path}'
print(f'PASS: {len(links)} source links, insertion/order anchors, unsupported mappings, driver boundary, memory owners and 9 installed tool entries')
print('Scope: source reconnaissance only; no compile, simulation, checkpoint replay, formal proof or license test')
