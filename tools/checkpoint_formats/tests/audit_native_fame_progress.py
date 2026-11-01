"""Audit FAME role/StateID bindings in a native bank companion's actual emission.

This is compiler evidence. It grants neither physical cut nor image admission.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_physical_clock_plan import IDENT, parse_modules

SUFFIXES = ('-emitted.fir', '-emitted-progress.anno.json', '-fame-clock-progress.json')
COMMON = ('host_clock', 'host_reset', 'finishing', 'completed_steps', 'overflow')
DOMAIN = ('consume', 'launch', 'pending', 'consumed', 'applied', 'pending_flag', 'gate_ce', 'gate_output')
STORED = {'completed_steps', 'overflow', 'consumed', 'applied', 'pending_flag'}
WIDE = {'completed_steps', 'consumed', 'applied'}


def metadata(annotations):
    models = [a for a in annotations if a['class'].endswith('.FAMEClockProgressModelAnnotation')]
    signals = [a for a in annotations if a['class'].endswith('.FAMEClockProgressSignalAnnotation')]
    require(models and len({a['model'] for a in models}) == len(models), 'missing/duplicate FAME model')
    expected = set()
    for model in models:
        domains = model['domains']
        require(model['model'] and domains and len(set(domains)) == len(domains), 'invalid FAME domains')
        expected.update((model['model'], '', role) for role in COMMON)
        expected.update((model['model'], domain, role) for domain in domains for role in DOMAIN)
    keyed = {(a['model'], a['domain'], a['role']): a for a in signals}
    require(len(keyed) == len(signals) and set(keyed) == expected, 'incomplete/duplicated FAME roles')
    return sorted(models, key=lambda a: a['model']), keyed


def location(modules, root, target):
    match = re.fullmatch(r'~(' + IDENT + r')\|(' + IDENT + r')((?:/' + IDENT + ':' + IDENT + r')*)>(' + IDENT + r')', target)
    require(match is not None and match[1] == root, 'foreign/reshaped FAME target')
    # Targets may start in the linked inner root. Find its one actual execution
    # independently instead of treating a module name as a hierarchy path.
    paths = []
    def walk(name, path, seen=frozenset()):
        require(name not in seen and name in modules, 'invalid FAME hierarchy')
        if name == match[2]:
            paths.append(path)
        for instance, child in modules[name]['instances'].items():
            walk(child, path + [instance], seen | {name})
    walk(root, [root])
    require(len(paths) == 1, 'replicated/unreachable FAME target root')
    path, owner = paths[0], match[2]
    for instance, child in re.findall('/(' + IDENT + '):(' + IDENT + ')', match[3]):
        require(modules[owner]['instances'].get(instance) == child, 'FAME target instance mismatch')
        path.append(instance)
        owner = child
    return '.'.join(path + [match[4]]), modules[owner], match[4]


def audit(directory, prefix='FireSim-generated'):
    directory = Path(directory)
    path = lambda suffix: directory / (prefix + '.native-functional' + suffix)
    read = lambda suffix: json.loads(path(suffix).read_text())
    binding, bank = read('-fame-clock-progress.json'), read('-binding.json')
    emission = read('-emission.json')
    for suffix in SUFFIXES + ('-reference.fir', '-reference.anno.json', '-simulator-state.json',
                              '-binding.json', '-instrumented.fir', '.sv'):
        require(emission['inputs'].get('.native-functional' + suffix) == file_sha(path(suffix)),
                'native FAME emission input changed: ' + suffix)
    require(binding['binding_version'] == 1 and
            binding['scope'] == 'native-banked-fame-clock-progress-role-map-only' and
            all(binding[k] is False for k in ('capture_supported', 'global_target_cut_proven', 'deployable_capture_image')),
            'native FAME binding scope/admission changed')
    for key, suffix in [('bank_binding_sha256', '-binding.json'), ('bank_input_reference_sha256', '-reference.fir'),
                        ('bank_instrumented_sha256', '-instrumented.fir'), ('emitted_verilog_sha256', '.sv'),
                        ('emission_reference_sha256', '-emitted.fir')]:
        require(binding[key] == file_sha(path(suffix)), 'native FAME input hash differs: ' + suffix)
    before_models, before = metadata(read('-reference.anno.json'))
    after_models, after = metadata(read('-emitted-progress.anno.json'))
    require(before_models == after_models and set(before) == set(after), 'FAME identities changed across banking/emission')
    rows = binding['signals']
    keyed = {(r['model_identity'], r['domain_identity'], r['role']): r for r in rows}
    require(len(keyed) == len(rows) == len(after) and set(keyed) == set(after), 'incomplete native FAME map')
    require(len({r['rtl_path'] for r in rows}) == len(rows), 'aliased native FAME paths')
    inventory = read('-simulator-state.json')
    original = {r['hierarchy']: r for r in inventory['state']}
    entries = {r['state_id']: r for r in bank['state']}
    require(len(entries) == len(bank['state']), 'duplicate native bank StateID')
    reference_modules = parse_modules(path('-reference.fir').read_text())
    modules = parse_modules(path('-emitted.fir').read_text())
    bits = 0
    for key, row in keyed.items():
        require(row['target'] == after[key]['target'], 'native FAME annotation target changed')
        actual_path, owner, ref = location(modules, inventory['root_module'], row['target'])
        require(actual_path == row['rtl_path'], 'native FAME RTL path differs from actual hierarchy')
        stored = key[2] in STORED
        width = 64 if key[2] in WIDE else 1
        require(row['storage'] is stored and row['type'] == ('Clock' if key[2] in ('host_clock', 'gate_output') else f'UInt<{width}>'),
                'native FAME role kind/width differs')
        if stored:
            old_path, _, _ = location(reference_modules, inventory['root_module'], before[key]['target'])
            entry = original[old_path]
            access = entries[entry['state_id']]
            expected_id = hashlib.sha256(canonical(dict(namespace='generated-simulator-state-v1',
                                                        hierarchy=old_path, kind='register'))).hexdigest()
            require(entry['kind'] == 'register' and entry['depth'] == 1 and entry['width'] == width and
                    row['generated_state_id'] == entry['state_id'] == expected_id and row['bank'] == access['bank'] and
                    row['slot'] == access['slot'] and row['input_storage_hierarchy'] == access['storage_hierarchy'],
                    'native FAME StateID/selector differs from original functional owner')
            require(re.search(r'^  reg ' + re.escape(ref) + r' : UInt<' + str(width) + r'>,', owner['body'], re.M),
                    'native FAME emitted register missing/reshaped')
            bits += width
    return dict(roles=len(rows), stored_bits=bits, model_identities=len(before_models),
                global_target_cut_proven=False, physical_fpga_capture=False)
