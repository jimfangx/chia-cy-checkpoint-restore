"""Audit the complete real DUT synthesis inventory; state relations unproven."""

import argparse
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.hierarchical_state import architecture_cell_adapter, bind_concrete_models, hierarchical_inventory
from tools.checkpoint_formats.production_dut import audit_architecture
from .verify_formal_state_map import ROOT
from .verify_production_dut import file_sha


def audit(run, out):
    run = Path(run).resolve()
    architecture, synthesis = run / 'architecture', run / 'synthesis'
    candidate = audit_architecture(architecture)
    commands = json.loads((run / 'commands.json').read_text())
    synth_commands = [c for c in commands if c['argv'][0].endswith('/genus')]
    require(len(synth_commands) == 1 and synth_commands[0]['exit_code'] == 0, 'incomplete real Genus command')
    log = (synthesis / 'synth.log').read_text()
    expected_paths = dict(rtl=architecture / 'original.sv', architecture=architecture / 'architecture.sv',
                          memory_stubs=architecture / 'memory-stubs.v', memory_models=architecture / 'memory-models.v',
                          candidate=architecture / 'architecture-candidate.json',
                          library=ROOT / 'tools/checkpoint_formats/tests/fixtures/formal/cells.lib',
                          synthesis_script=ROOT / 'tools/checkpoint_formats/production_synth.tcl')
    observed = re.findall(r'^CHECKPOINT_SYNTH_INPUT\t(\S+)\t([0-9a-f]{64})$', log, re.M)
    require(len(observed) == len(expected_paths) and dict(observed) == {k: file_sha(p) for k, p in expected_paths.items()},
            'changed/incomplete real synthesis input identities')
    require(re.findall(r'^CHECKPOINT_SYNTH_OUTPUT\t([0-9a-f]{64})$', log, re.M) == [file_sha(synthesis / 'netlist.v')],
            'changed/unbound synthesized netlist')
    retiming = re.findall(r'^CHECKPOINT_RETIMING\t(\S+)\t(\S+)$', log, re.M)
    require(retiming and all(value == 'false' for _, value in retiming), 'production retiming unsupported')
    require(len(re.findall(r'^CHECKPOINT_PRESERVED_MEMORY\t', log, re.M)) == candidate['memory_instances'],
            'missing real synthesis memory preservation')
    fixture = ROOT / 'tools/checkpoint_formats/tests/fixtures/formal'
    models, adapter = architecture_cell_adapter(candidate, json.loads((fixture / 'cell-adapter.json').read_text()),
                                                (fixture / 'cells.v').read_text(), (architecture / 'memory-models.v').read_text())
    inventory = hierarchical_inventory((synthesis / 'netlist.v').read_text(), models, adapter, candidate['top'])
    physical_memories = [s for s in inventory['storage'] if s['kind'] == 'memory']
    expected_memories = [e for e in candidate['entries'] if e['kind'] == 'memory']
    from collections import Counter
    require(Counter((s['cell'], s['width'], s['depth']) for s in physical_memories) ==
            Counter((e['memory']['cell'], e['width'], e['depth']) for e in expected_memories),
            'lost/extra/reshaped physical macro state')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'models.v').write_text(models)
    (out / 'cell-adapter.json').write_bytes(canonical(adapter))
    (out / 'gate-storage-inventory.json').write_bytes(canonical(inventory))
    selected, binding = bind_concrete_models((synthesis / 'netlist.v').read_text(), models, adapter, candidate['top'])
    (out / 'netlist-design.v').write_text(selected)
    (out / 'model-binding.json').write_bytes(canonical(binding))
    result = dict(audit='passed', run=str(run), original_state_entries=candidate['state_entries'],
                  original_state_bits=candidate['state_bits'], physical_bits=inventory['physical_bits'],
                  physical_words=inventory['physical_words'], physical_memory_instances=len(physical_memories),
                  physical_register_bits=sum(s['width'] for s in inventory['storage'] if s['kind'] == 'register'),
                  netlist_sha256=inventory['netlist_sha256'], models_sha256=inventory['models_sha256'],
                  retiming=False, formal_state_map_complete=False, proof_status='unproven', gate_restore_authorized=False)
    (out / 'audit.json').write_bytes(canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    if destination.exists():
        destination = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination)) / 'evidence'
    result = audit(args.run, destination)
    (args.out / 'selection.json').write_bytes(canonical(dict(evidence=str(destination), audit=str(destination / 'audit.json'))))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
