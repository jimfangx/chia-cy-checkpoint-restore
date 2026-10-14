"""Independent emitted-RTL storage/clock audit for discovery-only schema 3.

This does not authorize a semantic image, manufacture a checkpoint cut, or
invent frequencies from clock names. The eventual capture backend must bind
actual clock events/phases and complete CPU runtime ownership independently.
"""
import hashlib
import re

from .codec import keys, require
from .replay import IDENT, RANGE, audit_semantic_rtl
from .semantic import PATH, manifest_hash, validate_manifest


def access_paths(manifest, boundary, clean, access):
    keys(access, {'access_version', 'scope', 'state_manifest_sha256', 'clean_rtl_sha256', 'dut_module', 'state'})
    require(type(access['access_version']) is int and access['access_version'] == 1 and
            access['scope'] == 'clean-rtl-inventory-only' and access['state_manifest_sha256'] == manifest_hash(manifest) and
            access['clean_rtl_sha256'] == hashlib.sha256(clean.encode()).hexdigest() and
            access['dut_module'] == boundary['dut_module'], 'incompatible clean storage access mapping')
    require(type(access['state']) is list, 'invalid clean storage access mapping')
    paths = {}
    identities = []
    for entry in access['state']:
        keys(entry, {'state_id', 'rtl_path'})
        require(type(entry['state_id']) is str and type(entry['rtl_path']) is str and PATH.fullmatch(entry['rtl_path']),
                'invalid emitted clean storage path')
        identities.append(entry['state_id']); paths[entry['state_id']] = entry['rtl_path']
    require(identities == [e['state_id'] for e in manifest['state']] and len(set(paths.values())) == len(paths),
            'incomplete/duplicate/aliased clean storage access mapping')
    return paths


def boundary_ports(manifest, boundary):
    validate_manifest(manifest)
    require(manifest['manifest_version'] == 3, 'multi-clock inventory requires schema 3')
    keys(boundary, {'boundary_version', 'dut_module', 'dut_root', 'sample_phase',
                    'clock_inputs', 'clock_aliases', 'ports'})
    require(type(boundary['boundary_version']) is int and boundary['boundary_version'] == 3 and
            boundary['sample_phase'] == 'before_clock_event' and boundary['dut_root'] == manifest['dut_root'] and
            boundary['clock_inputs'] == manifest['clock_inputs'] and boundary['clock_aliases'] == manifest['clock_aliases'],
            'incompatible multi-clock boundary ownership')
    require(type(boundary['dut_module']) is str and re.fullmatch(IDENT, boundary['dut_module']), 'invalid DUT module')
    ports = boundary['ports']
    require(type(ports) is list, 'invalid multi-clock data boundary')
    names = set()
    clock_names = {c[len(manifest['dut_root']) + 1:] for c in boundary['clock_inputs']}
    clock_names.update(a['name'] for a in boundary['clock_aliases'])
    for port in ports:
        keys(port, {'name', 'direction', 'width'})
        require(type(port['name']) is str and re.fullmatch(IDENT, port['name']) and
                port['direction'] in ('input', 'output') and type(port['width']) is int and port['width'] > 0 and
                port['name'] not in names | clock_names, 'duplicate/reshaped multi-clock data port')
        names.add(port['name'])
    return ports


def sequential_blocks(body):
    for match in re.finditer(r'\balways\s*@\(posedge\s+(' + IDENT + r')\)\s+begin\b', body):
        depth = 1
        for token in re.finditer(r'\b(begin|end)\b', body[match.end():]):
            depth += 1 if token[1] == 'begin' else -1
            if depth == 0:
                yield match[1], body[match.end():match.end() + token.start()]
                break
        else:
            require(False, 'unterminated emitted sequential block')


def audit_inventory(manifest, boundary, reference, clean, access):
    ports = boundary_ports(manifest, boundary)
    require(hashlib.sha256(reference.encode()).hexdigest() == manifest['reference_sha256'],
            'changed original multi-clock reference')
    root, module = manifest['dut_root'], boundary['dut_module']
    paths = access_paths(manifest, boundary, clean, access)
    mods, actual = audit_semantic_rtl(manifest, module, clean)
    expected = {paths[e['state_id']]: (e['width'], e['depth'], e['kind']) for e in manifest['state']}
    require(actual == expected, 'incomplete/unknown/reshaped emitted multi-clock state')
    declared = [dict(name=n, direction=d, width=int(w) + 1 if w else 1)
                for d, w, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', mods[module][0])]
    clock_ports = [dict(name=c[len(root) + 1:], direction='input', width=1) for c in manifest['clock_inputs']]
    alias_ports = [dict(name=a['name'], direction='output', width=1) for a in manifest['clock_aliases']]
    require(sorted(declared, key=lambda p: p['name']) == sorted(ports + clock_ports + alias_ports, key=lambda p: p['name']),
            'incomplete emitted multi-clock boundary')
    root_clocks = {p['name']: root + '.' + p['name'] for p in clock_ports}
    owners = {}
    # Audit actual posedge blocks and continuous connections, independently of
    # the FIRRTL compiler's clock resolver. Unsupported RTL expressions reject.
    class Scope:
        def __init__(self, name, prefix, parent=None, pins=None, ancestors=frozenset()):
            require(name in mods, 'opaque multi-clock RTL module')
            require(name not in ancestors, 'recursive emitted multi-clock hierarchy')
            self.prefix, self.parent, self.pins = prefix, parent, pins or {}
            header, self.body = mods[name]
            self.inputs = {n for d, w, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', header) if d == 'input'}
            self.aliases = dict(re.findall(rf'\bassign\s+({IDENT})\s*=\s*([^;]+);', self.body))
            self.aliases.update({
                n: expr for w, n, expr in re.findall(rf'\bwire\s+{RANGE}({IDENT})\s*=\s*([^;]+);', self.body)})
            self.children, self.outputs = {}, {}
            for child, instance, connections in re.findall(rf'^[ \t]*({IDENT})[ \t]+({IDENT})\s*\((.*?)\);', self.body, re.M | re.S):
                pins = dict(re.findall(rf'\.({IDENT})\s*\(([^()]*)\)', connections))
                self.children[instance] = Scope(child, prefix + instance + '.', self, pins, ancestors | {name})
                child_header = mods[child][0]
                for d, w, port in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', child_header):
                    if d == 'output' and port in pins:
                        self.outputs[pins[port].strip()] = (self.children[instance], port)

        def clock(self, expression, seen=frozenset()):
            expression = expression.strip()
            key = self.prefix + expression
            require(key not in seen and re.fullmatch(IDENT, expression), 'cyclic/derived emitted state clock ' + key)
            seen = seen | {key}
            if expression in self.inputs:
                if self.parent is None:
                    require(expression in root_clocks, 'emitted state clock reaches data input ' + key)
                    return root_clocks[expression]
                require(expression in self.pins, 'undriven emitted child clock ' + key)
                return self.parent.clock(self.pins[expression], seen)
            if expression in self.outputs:
                scope, port = self.outputs[expression]
                return scope.clock(port, seen)
            require(expression in self.aliases, 'undriven emitted clock alias ' + key)
            return self.clock(self.aliases[expression], seen)

        def walk(self):
            for clock, body in sequential_blocks(self.body):
                for storage in re.findall(rf'^[ \t]*({IDENT})(?:\[[^\n;]+?\])?\s*<=', body, re.M):
                    path = self.prefix + storage
                    require(path in expected, 'unknown emitted sequential storage ' + path)
                    domain = self.clock(clock)
                    require(path not in owners or owners[path] == domain, 'multiple emitted storage clocks ' + path)
                    owners[path] = domain
            for child in self.children.values():
                child.walk()

    scope = Scope(module, '')
    scope.walk()
    for model in manifest['external_models']:
        owners[model['hierarchy'][len(root) + 1:] + '.myplus'] = 'initial'
    expected_clocks = {paths[e['state_id']]: e['clock_domain'] for e in manifest['state']}
    require(owners == expected_clocks, 'complete emitted state-clock ownership differs from semantic manifest')
    for alias in boundary['clock_aliases']:
        require(scope.clock(alias['name']) == root + '.' + alias['source'], 'wrong emitted boundary clock alias')
    totals = {c: dict(entries=0, words=0) for c in manifest['clock_domains'] + (['initial'] if manifest['external_models'] else [])}
    for e in manifest['state']:
        totals[e['clock_domain']]['entries'] += 1
        totals[e['clock_domain']]['words'] += e['depth']
    return dict(status='passed', scope='independent emitted RTL multi-clock inventory; execution acceptance pending',
                semantic_manifest_sha256=manifest_hash(manifest), semantic_entries=len(expected),
                semantic_words=sum(e['depth'] for e in manifest['state']), clock_owners=totals,
                complete_emitted_storage_and_clock_ownership=True, CPU_level1_verified=False, CPU_level2_verified=False)
