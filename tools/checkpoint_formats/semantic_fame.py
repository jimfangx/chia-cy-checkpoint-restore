"""Audit compiler-carried semantic identities against actual generated storage.

A storage map does not establish a coherent clock cut, boundary trace, or
checkpoint. Those remain separate obligations before CPU replay is admitted.
"""
import hashlib

from .codec import canonical, keys, require
from .semantic import manifest_hash, validate_manifest
from .simulator import check_generated_rtl


def audit_mapping(manifest, mapping, generated, reference, rtl, bufgce, plusarg, gate=''):
    validate_manifest(manifest)
    keys(mapping, {'map_version', 'scope', 'state_manifest_sha256',
                   'generated_rtl_sha256', 'generated_manifest_sha256',
                   'capture_supported', 'state'})
    require(type(mapping['map_version']) is int and mapping['map_version'] == 1
            and mapping['scope'] == 'semantic-storage-map-only'
            and mapping['capture_supported'] is False, 'unsupported semantic FAME map scope')
    require(mapping['state_manifest_sha256'] == manifest_hash(manifest), 'semantic manifest mismatch')
    require(mapping['generated_rtl_sha256'] == hashlib.sha256(rtl.encode()).hexdigest(),
            'generated RTL mismatch')
    require(mapping['generated_manifest_sha256'] == hashlib.sha256(canonical(generated)).hexdigest(),
            'generated manifest mismatch')
    for instance in generated['instances']:
        if instance['module'] == 'AbstractClockGate':
            require(hashlib.sha256(gate.encode()).hexdigest() == instance['implementation_sha256'],
                    'clock gate implementation mismatch')
    check_generated_rtl(generated, reference, rtl + bufgce + plusarg + gate, bufgce, plusarg_model=plusarg)
    require(type(mapping['state']) is list, 'missing semantic FAME entries')
    for binding in mapping['state']:
        keys(binding, {'state_id', 'rtl_path', 'generated_state_id'})
        require(all(type(v) is str for v in binding.values()), 'invalid semantic FAME binding')
    require([b['state_id'] for b in mapping['state']] == [e['state_id'] for e in manifest['state']],
            'missing/duplicate/reordered semantic owner')
    paths = [b['rtl_path'] for b in mapping['state']]
    require(len(set(paths)) == len(paths), 'aliased semantic storage')
    actual = {e['hierarchy']: e for e in generated['state']}
    for e, binding in zip(manifest['state'], mapping['state']):
        require(binding['rtl_path'] in actual, 'missing transformed semantic storage')
        owner = actual[binding['rtl_path']]
        require(binding['generated_state_id'] == owner['state_id'], 'generated StateID mismatch')
        require(all(e[k] == owner[k] for k in ('width', 'depth', 'kind', 'signed')),
                'reshaped transformed semantic owner')
    return dict(status='passed', scope='complete declared semantic storage mapping; coherent CPU capture pending',
                semantic_entries=len(paths), semantic_words=sum(e['depth'] for e in manifest['state']),
                generated_entries=len(generated['state']),
                semantic_manifest_sha256=manifest_hash(manifest),
                mapping_sha256=hashlib.sha256(canonical(mapping)).hexdigest(),
                CPU_level1_verified=False, CPU_level2_verified=False)
