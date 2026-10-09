"""Entry-bounded Level-1 aggregate encoding for large generated RAMs.

One FSCKPT record owns one manifested entry, including EVERY RAM address.
Ascending addresses concatenate fixed-length, nibble-padded hexadecimal words.
This encoding is explicitly bound in a v2 runtime manifest; it cannot be mixed
with the existing per-word fixture profile. Native validation remains the
compiled coordinator's responsibility. Production plusargs remain disabled.
"""
import json
from pathlib import Path
import re

from .aggregate import digest, runtime_manifest as word_manifest
from .codec import HEX, decode, encode, keys, natural, require, unique_object
from .durable import atomic_output
from .harness_restore import harness_capture, harness_restore_text

ENCODING = 'ascending_nibble_padded_words_v1'
SCHEMA = 'firesim.aggregate.lowclock.v2'


def runtime_manifest(profile, generated, layout, owners, native_hash, target_cycle_owner=None):
    manifest = word_manifest(profile, generated, layout, owners, native_hash)
    manifest = dict(manifest, schema=SCHEMA, generated_encoding=ENCODING)
    if target_cycle_owner is not None:
        require(type(target_cycle_owner) is str, 'invalid target cycle binding')
        matches = [e for e in generated['state'] if e['hierarchy'] == target_cycle_owner]
        require(len(matches) == 1 and matches[0]['kind'] == 'register'
                and matches[0]['width'] == 64 and matches[0]['depth'] == 1,
                'target cycle binding requires one manifested 64-bit register')
        manifest.update(schema='firesim.aggregate.lowclock.v3', cut_contract=dict(
            target_cycle_owner=target_cycle_owner,
            target_cycle_path=layout['root']+'.'+target_cycle_owner,
            target_cycle_semantics='fased_model_tCycle_at_settled_host_negedge',
            host_sample_semantics='completed_host_rising_edges_before_cut'))
    return manifest


def entry_value(entry, value):
    digits = (entry['width'] + 3) // 4
    require(type(value) is str and len(value) == digits * entry['depth']
            and HEX.fullmatch(value), 'incomplete/invalid generated entry')
    if entry['width'] % 4:
        limit = 1 << (entry['width'] % 4)
        # Check padding on EVERY address, not just the aggregate's first nibble.
        require(all(int(c, 16) < limit for c in value[::digits]), 'nonzero generated word padding')
    if entry['adapter'] == 'metasim-bufgce-v1':
        require(not value.strip('0'), 'high generated clock output would advance target time')


def read_generated_cut(generated, path):
    """Read one complete parked low-clock VCS diagnostic, one RAM at a time."""
    with Path(path).open() as stream:
        def row():
            line = stream.readline()
            require(bool(line), 'incomplete generated stream')
            return json.loads(line, object_pairs_hook=unique_object)
        header = row()
        keys(header, {'capture_version', 'capture_type', 'scope', 'external_runtime_required',
                      'manifest_sha256', 'sample_phase', 'host_sample', 'stage'})
        require(type(header['capture_version']) is int and header['capture_version'] == 2
                and header['capture_type'] == 'generated_rtl_diagnostic'
                and header['scope'] == 'generated_rtl_only'
                and header['external_runtime_required'] is True
                and header['manifest_sha256'] == digest(generated)
                and header['sample_phase'] == 'settled_host_negedge_parked_driver'
                and type(header['stage']) is int and header['stage'] == 0, 'incompatible generated cut')
        natural(header['host_sample'])
        records = []
        for entry in generated['state']:
            r = row()
            keys(r, {'state_id', 'width', 'depth', 'values'})
            require(r['state_id'] == entry['state_id'] and type(r['width']) is int
                    and type(r['depth']) is int and (r['width'], r['depth']) == (entry['width'], entry['depth'])
                    and type(r['values']) is list and len(r['values']) == entry['depth'],
                    'changed generated entry membership/order/shape')
            digits = (entry['width'] + 3) // 4
            require(all(type(v) is str and len(v) == digits for v in r['values']),
                    'changed generated word length')
            value = ''.join(r['values'])
            entry_value(entry, value)
            records.append(dict(owner='generated-entry/'+entry['hierarchy'],
                                width=4*digits*entry['depth'], value=value))
        require(not stream.read(1), 'trailing generated stream')
    return header['host_sample'], records


def _components(doc, manifest, generated, layout):
    fields = {'schema', 'profile', 'phase', 'generated_manifest_hash', 'harness_layout_hash',
              'native_build_hash', 'native_owners', 'generated_encoding'}
    contract = manifest.get('cut_contract')
    if contract is not None:
        fields.add('cut_contract')
        keys(contract, {'target_cycle_owner', 'target_cycle_path', 'target_cycle_semantics', 'host_sample_semantics'})
    keys(manifest, fields)
    require(manifest == runtime_manifest(manifest['profile'], generated, layout,
                                        manifest['native_owners'], manifest['native_build_hash'],
                                        contract['target_cycle_owner'] if contract is not None else None),
            'changed packed runtime inventory/encoding')
    require(type(doc['target_cycle']) is int and 0 <= doc['target_cycle'] < 2**64,
            'unsupported target cycle range')
    require(doc['build']['state_manifest_hash'] == digest(manifest)
            and doc['build']['target_configuration'] == manifest['profile']
            and doc['build']['rtl_build_hash'] == generated['reference_sha256']
            and doc['build']['golden_gate_build_hash'] == layout['generated_build_hash'],
            'incompatible packed aggregate identity')
    expected = {'cut/host_sample'}
    expected.update('generated-entry/'+e['hierarchy'] for e in generated['state'])
    expected.update('harness/'+r['owner'] for r in layout['records'])
    expected.update('host/'+r['owner'] for r in manifest['native_owners'])
    rows = {r['owner']: r for r in doc['records']}
    require(set(rows) == expected and len(rows) == len(doc['records']), 'incomplete packed aggregate membership')
    sample = rows['cut/host_sample']
    require(sample['width'] == 64, 'invalid host sample width')
    sample = int(sample['value'], 16)
    for entry in generated['state']:
        r = rows['generated-entry/'+entry['hierarchy']]
        require(r['width'] == 4*((entry['width']+3)//4)*entry['depth'], 'changed generated entry shape')
        entry_value(entry, r['value'])
    if contract is not None:
        require(int(rows['generated-entry/'+contract['target_cycle_owner']]['value'], 16) == doc['target_cycle'],
                'target cycle disagrees with bound generated counter')
    h = harness_capture(layout, [rows['harness/'+r['owner']]['value'] for r in layout['records']], sample)
    require(all(rows['harness/'+r['owner']]['width'] == r['width'] for r in layout['records']),
            'changed harness shape')
    native = []
    for owner in manifest['native_owners']:
        r = rows['host/'+owner['owner']]
        require(r['width'] > 0 and r['width'] % 8 == 0, 'invalid opaque native bytes')
        native.append(bytes.fromhex(r['value']))
    return rows, native, h, sample


def encode_aggregate(build, manifest, generated, layout, sample, entries, harness, native, target_cycle):
    natural(sample)
    require(sample < 2**64 and sample == harness['host_sample'], 'incoherent component sample')
    require(type(native) is dict and set(native) == {r['owner'] for r in manifest['native_owners']},
            'incomplete native membership')
    harness_restore_text(layout, harness)
    records = [dict(owner='cut/host_sample', width=64, value=f'{sample:016x}'), *entries]
    records.extend(dict(r, owner='harness/'+r['owner']) for r in harness['records'])
    for r in manifest['native_owners']:
        b = native[r['owner']]
        require(type(b) is bytes and b, 'empty/invalid native payload')
        records.append(dict(owner='host/'+r['owner'], width=len(b)*8, value=b.hex()))
    doc = dict(format_version=1, checkpoint_type='fsckpt', target_cycle=target_cycle,
               target_clock_phase='before_rising_edge', build=build, records=sorted(records, key=lambda r:r['owner']))
    _components(doc, manifest, generated, layout)
    return encode('fsckpt', doc)


def decode_aggregate(data, build, manifest, generated, layout):
    doc = decode(data, 'fsckpt', build)
    _components(doc, manifest, generated, layout)
    return doc


def publish_aggregate(data, build, manifest, generated, layout, destination):
    """Validate every packed word/owner/cycle before durable atomic publication."""
    doc = decode_aggregate(data, build, manifest, generated, layout)
    with atomic_output(destination, binary=True) as stream:
        stream.write(data)
    return doc


def prepare_aggregate_restore(data, build, manifest, generated, layout, destination):
    doc = decode_aggregate(data, build, manifest, generated, layout)
    rows, native, h, sample = _components(doc, manifest, generated, layout)
    words = sum(e['depth'] for e in generated['state'])
    prefix = f'FSGRTL2 {digest(generated)} {layout["generated_build_hash"]} settled_host_negedge {words}\n'
    lines = [prefix]
    for entry in generated['state']:
        path = layout['root']+'.'+entry['hierarchy']
        lines.append(f'{path} {entry["width"]} {entry["depth"]} {rows["generated-entry/"+entry["hierarchy"]]["value"]}\n')
    g = ''.join(lines)
    h = harness_restore_text(layout, h)
    # Every semantic check precedes temporary creation; readers see one complete
    # staging file, even on interrupted writes or replacement of an older cut.
    with atomic_output(destination) as stream:
        stream.write(f'FSAGG1 {digest(manifest)} {doc["target_cycle"]} {sample} {len(native)}\n')
        for row, payload in zip(manifest['native_owners'], native):
            stream.write(f'HOST {row["owner"]} {row["schema"]} {len(payload)} {payload.hex()}\n')
        for name, component in (('GENERATED', g), ('HARNESS', h)):
            stream.write(f'{name} {len(component)}\n')
            stream.write(component)
    return doc
