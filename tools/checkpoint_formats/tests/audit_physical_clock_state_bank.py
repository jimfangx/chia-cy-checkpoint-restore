"""Reconstruct physical CE StateIDs/slots from concrete native instances.

This validates a readout companion, never production freeze or restore support.
"""
import hashlib
import json
from pathlib import Path

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def audit(directory):
    directory = Path(directory)
    paths = {n: directory/n for n in ('reference.fir', 'manifest.json', 'physical-clock-plan.json',
        'physical-clock-dependencies.json', 'physical-clock-state-bank.json', 'physical-clock-state-bank.sv')}
    audit_dependencies(paths['reference.fir'], paths['manifest.json'], paths['physical-clock-plan.json'],
                       paths['physical-clock-dependencies.json'])
    inventory = json.loads(paths['manifest.json'].read_text())
    root = inventory['root_module']
    modules = parse_modules(paths['reference.fir'].read_text())
    native = []

    def visit(module, path, ancestors=frozenset()):
        require(module not in ancestors, 'recursive physical bank hierarchy')
        row = modules[module]
        if row['kind'] == 'extmodule':
            require(row['body'].endswith('defname = BUFGCE'), 'opaque physical bank owner')
            native.append(path)
        else:
            for name, child in row['instances'].items():
                visit(child, path+'.'+name, ancestors | {module})
    visit(root, root)
    require(0 < len(native) <= 65536, 'invalid physical bank size')
    rows = []
    for index, path in enumerate(sorted(native)):
        logical = path+'.CE_latch'
        state_id = identity(dict(namespace='physical-bufgce-ce-latch-v1', hierarchy=logical))
        metasim_id = identity(dict(namespace='generated-simulator-state-v1', hierarchy=path+'.O', kind='register'))
        require(state_id != metasim_id, 'physical CE cannot alias metasim O')
        rows.append(dict(state_id=state_id, hierarchy=logical, ce_bit=index, bank=255, slot=index,
                         width=1, depth=1, metasim_output_state_id=metasim_id, restore_adapter='unsupported'))
    expected = dict(bank_version=1, scope='physical_ce_readout_companion_only', root_module=root,
        endpoint_module=root+'CheckpointPhysicalCEBank', complete_fpga_capture=False, deployable_capture_image=False,
        production_freeze_owners_bound=False, metasim_restore_supported=False,
        reference_sha256=sha(paths['reference.fir']), simulator_manifest_sha256=sha(paths['manifest.json']),
        plan_sha256=sha(paths['physical-clock-plan.json']), dependencies_sha256=sha(paths['physical-clock-dependencies.json']),
        endpoint_sha256=sha(paths['physical-clock-state-bank.sv']),
        sample_contract='common_low_phase_unmasked_captured_ce_with_read_enable',
        access_clock='ungated_common_source', reset_contract='same_reset_as_sampler_transport_and_bank_endpoints',
        bank_reservation=255, state=rows)
    require(json.loads(paths['physical-clock-state-bank.json'].read_text()) == expected,
            'changed physical CE bank layout, input binding or unsupported admission')
    return dict(status='pass', physical_gates=len(native), physical_state_ids=[r['state_id'] for r in rows],
                bank=255, physical_fpga_capture=False, metasim_restore_supported=False)
