"""Bound Level-1 aggregate for an explicitly audited runtime profile.

The production FCFS profile is not enabled here. A profile must enumerate all
its native owners, bind their implementation/configuration, and supply emitted
generated coverage plus the audited harness layout. Decode binds the actual
executable as well. Staging is a trusted local intermediary, not a second
durable checkpoint; the VCS consumer prevalidates all native/VPI owners before
loading anything. Level-2 formats are independent.
"""
import hashlib
import json
from pathlib import Path
import re

from .codec import HASH, canonical, decode, encode, keys, require
from .generated_restore import generated_restore_text
from .harness_restore import harness_capture, harness_restore_text
from .simulator import generated_capture, generated_words

TOKEN = re.compile(r'[A-Za-z0-9_./-]+\Z')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def runtime_manifest(profile, generated, layout, native_owners, native_build_hash):
    """The caller's audit, not schema presence alone, authorizes this profile."""
    require(type(profile) is str and TOKEN.fullmatch(profile), 'invalid runtime profile')
    require(type(native_build_hash) is str and HASH.fullmatch(native_build_hash), 'invalid native build')
    require(type(native_owners) is list and native_owners, 'empty native owner inventory')
    names = []
    for row in native_owners:
        keys(row, {'owner', 'schema'})
        for value in row.values():
            require(type(value) is str and TOKEN.fullmatch(value), 'unsupported/invalid native owner')
        names.append(row['owner'])
    require(len(set(names)) == len(names), 'duplicate native owner')
    # Validate the complete component inventories without publishing files.
    g = generated_capture(generated, ['0'*((w['width']+3)//4) for w in generated_words(generated)], 0)
    generated_restore_text(generated, g, layout['generated_build_hash'], layout['root']+'.'+generated['root_module'])
    harness_restore_text(layout, harness_capture(layout, ['0'*((r['width']+3)//4) for r in layout['records']], 0))
    return dict(schema='firesim.aggregate.lowclock.v1', profile=profile,
                phase='settled_host_negedge_parked_driver_pre_bootstrap',
                generated_manifest_hash=digest(generated), harness_layout_hash=digest(layout),
                native_build_hash=native_build_hash, native_owners=native_owners)


def build_identity(manifest, generated, layout, executable):
    require(manifest['generated_manifest_hash'] == digest(generated)
            and manifest['harness_layout_hash'] == digest(layout), 'changed component inventory')
    return dict(target_configuration=manifest['profile'], rtl_build_hash=generated['reference_sha256'],
                golden_gate_build_hash=layout['generated_build_hash'],
                simulator_build_hash=hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
                state_manifest_hash=digest(manifest))


def _components(doc, manifest, generated, layout):
    keys(manifest, {'schema', 'profile', 'phase', 'generated_manifest_hash', 'harness_layout_hash',
                    'native_build_hash', 'native_owners'})
    require(manifest == runtime_manifest(manifest['profile'], generated, layout, manifest['native_owners'],
                                        manifest['native_build_hash']), 'changed runtime inventory/phase')
    require(doc['target_cycle'] < 2**64, 'unsupported target cycle range')
    require(doc['build']['state_manifest_hash'] == digest(manifest)
            and doc['build']['target_configuration'] == manifest['profile']
            and doc['build']['rtl_build_hash'] == generated['reference_sha256']
            and doc['build']['golden_gate_build_hash'] == layout['generated_build_hash'],
            'incompatible aggregate identity')
    expected = {'cut/host_sample'}
    expected.update('generated/'+w['owner'] for w in generated_words(generated))
    expected.update('harness/'+r['owner'] for r in layout['records'])
    expected.update('host/'+r['owner'] for r in manifest['native_owners'])
    rows = {r['owner']: r for r in doc['records']}
    require(set(rows) == expected and len(rows) == len(doc['records']), 'incomplete aggregate membership')
    sample = rows['cut/host_sample']
    require(sample['width'] == 64, 'invalid host sample width')
    sample = int(sample['value'], 16)
    g = generated_capture(generated, [rows['generated/'+w['owner']]['value'] for w in generated_words(generated)], sample)
    for r in g['records']:
        require(rows['generated/'+r['owner']]['width'] == r['width'], 'changed generated shape')
    h = harness_capture(layout, [rows['harness/'+r['owner']]['value'] for r in layout['records']], sample)
    for r in h['records']:
        require(rows['harness/'+r['owner']]['width'] == r['width'], 'changed harness shape')
    native = []
    for r in manifest['native_owners']:
        row = rows['host/'+r['owner']]
        require(row['width'] > 0 and row['width'] % 8 == 0, 'invalid opaque native bytes')
        native.append(bytes.fromhex(row['value']))
    # Both renderers perform semantic cut validation, including low gates,
    # reset/finish flags and exact membership, without creating any files.
    return native, generated_restore_text(generated, g, layout['generated_build_hash'],
                                          layout['root']+'.'+generated['root_module']), harness_restore_text(layout, h), sample


def encode_aggregate(build, manifest, generated, layout, g, h, native, target_cycle):
    require(g['host_sample'] == h['host_sample'], 'incoherent component samples')
    require(type(native) is dict and set(native) == {r['owner'] for r in manifest['native_owners']},
            'incomplete native membership')
    records = [dict(owner='cut/host_sample', width=64, value=f"{g['host_sample']:016x}")]
    # Validate the original captures before reconstructing their aggregate form.
    generated_restore_text(generated, g, layout['generated_build_hash'], layout['root']+'.'+generated['root_module'])
    harness_restore_text(layout, h)
    for prefix, capture in (('generated/', g), ('harness/', h)):
        records.extend(dict(r, owner=prefix+r['owner']) for r in capture['records'])
    for row in manifest['native_owners']:
        payload = native[row['owner']]
        require(type(payload) is bytes and payload, 'empty/invalid native payload')
        records.append(dict(owner='host/'+row['owner'], width=len(payload)*8, value=payload.hex()))
    doc = dict(format_version=1, checkpoint_type='fsckpt', target_cycle=target_cycle,
               target_clock_phase='before_rising_edge', build=build,
               records=sorted(records, key=lambda r:r['owner']))
    data = encode('fsckpt', doc)
    _components(doc, manifest, generated, layout)
    return data


def decode_aggregate(data, expected_build, manifest, generated, layout):
    doc = decode(data, 'fsckpt', expected_build)
    _components(doc, manifest, generated, layout)
    return doc


def prepare_aggregate_restore(data, expected_build, manifest, generated, layout, destination):
    doc = decode_aggregate(data, expected_build, manifest, generated, layout)
    native, g, h, sample = _components(doc, manifest, generated, layout)
    text = f"FSAGG1 {digest(manifest)} {doc['target_cycle']} {sample} {len(native)}\n"
    for row, payload in zip(manifest['native_owners'], native):
        text += f"HOST {row['owner']} {row['schema']} {len(payload)} {payload.hex()}\n"
    for name, component in (('GENERATED', g), ('HARNESS', h)):
        text += f'{name} {len(component.encode("ascii"))}\n'+component
    Path(destination).write_text(text, encoding='ascii')
    return doc


def prepare_aggregate_loader(manifest, out):
    """Compile the expected profile/native membership; never trust file schemas."""
    out = Path(out)
    text = f'static const char *aggregate_manifest_hash = {json.dumps(digest(manifest))};\n'
    text += 'static const NativeIdentity native_identities[] = {\n'
    text += ',\n'.join('{%s, %s}' % (json.dumps(r['owner']), json.dumps(r['schema']))
                      for r in manifest['native_owners'])+'\n};\n'
    (out/'aggregate-restore-table.h').write_text(text)
