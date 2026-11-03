"""Reconstruct live-register staging from raw original and instrumented FIRRTL.

This checks source preservation, complete concrete storage, every observation
route and the actual staging pins. Producer hashes alone grant no coverage.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

PREFIX = 'checkpoint_register_snapshot_'
OBS = PREFIX + 'live'
ADAPTER = PREFIX + 'adapter'


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def bind_reference_receipt(binding, receipt):
    """Pin every consumed oracle file to the exact emitter-receipt path/hash."""
    binding, receipt = Path(binding).resolve(), Path(receipt).resolve()
    require(binding.name == 'binding.json', 'oracle binding must name the emitted binding artifact')
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['returncode'] == 0, 'oracle emission did not pass')
    for name in ('binding.json', 'reference.sv', 'original.fir',
                 'original-annotations.json', 'preserved-annotations.json'):
        path = binding.parent/name
        require(path.is_file() and not path.is_symlink() and
                path.resolve().is_relative_to(receipt.parent), 'oracle artifact is outside its emitter receipt')
        key = str(path.relative_to(receipt.parent))
        require(doc['artifacts'].get(key) == hashlib.sha256(path.read_bytes()).hexdigest(),
                'consumed oracle artifact is not authenticated by emitter receipt: '+key)
    return doc


def audit_reference(directory, generated):
    """Authenticate an original oracle whose unused registers survive DCE."""
    directory, generated = Path(directory), Path(generated)
    binding = json.loads((directory/'binding.json').read_text())
    text = (generated/'host.fir').read_text()
    annotations = (generated/'host-annotations.json').read_text()
    require(binding['reference_version'] == 1 and binding['scope'] ==
            'original_register_oracle_donttouch_only', 'unknown original reference policy')
    require(all(binding[k] is False for k in ('original_equations_changed', 'capture_logic_added',
                                            'physical_fpga_capture')), 'reference changed original semantics')
    require((directory/'original.fir').read_text() == text and
            (directory/'original-annotations.json').read_text() == annotations and
            binding['original_sha256'] == sha(text) and
            binding['original_annotations_sha256'] == sha(annotations), 'reference original input drift')
    modules = parse_modules(text)
    root = re.search(r'^circuit (\w+) :', text, re.M)[1]
    targets = sorted('~'+root+'|'+name+'>'+n for name, m in modules.items()
                     for n, kind, _ in m['consumers'] if kind == 'register')
    require(binding['targets'] == targets and targets, 'reference omitted an original register')
    preserved = (directory/'preserved-annotations.json').read_text()
    expected = json.loads(annotations) + [dict(class_='firrtl.transforms.DontTouchAnnotation', target=t)
                                          for t in targets]
    expected = [{('class' if k == 'class_' else k): v for k, v in a.items()} for a in expected]
    actual = json.loads(preserved)
    # The existing annotation prefix stays exact; only the complete set of
    # local original-register DontTouch annotations may follow it.
    prefix = len(json.loads(annotations))
    require(actual[:prefix] == expected[:prefix] and
            sorted(actual[prefix:], key=lambda a: a['target']) == expected[prefix:] and
            binding['preserved_annotations_sha256'] == sha(preserved), 'unrecognized oracle annotation')
    rtl = (directory/'reference.sv').read_text()
    require(binding['reference_verilog_sha256'] == sha(rtl) and PREFIX not in rtl and
            'CheckpointNativeStateSnapshot' not in rtl, 'reference contains capture logic or changed RTL')
    for name, m in modules.items():
        if m['kind'] != 'module':
            continue
        body = re.search(r'\bmodule\s+'+re.escape(name)+r'\s*\([\s\S]*?\bendmodule\b', rtl)
        require(body is not None, 'original reference definition missing '+name)
        for n, kind, _ in m['consumers']:
            require(kind == 'register' and re.search(r'\breg\s+(?:signed\s+)?(?:\[[^\]]+\]\s+)?'+
                    re.escape(n)+r'\s*;', body[0]), 'original reference register was optimized away '+name+'.'+n)
    return dict(status='pass', preserved_register_definitions=len(targets),
                original_equations_changed=False, capture_logic_added=False)


def audit(directory):
    directory = Path(directory)
    original_text = (directory / 'host.fir').read_text()
    actual_text = (directory / 'instrumented.fir').read_text()
    binding = json.loads((directory / 'binding.json').read_text())
    require(binding['snapshot_version'] == 1 and binding['scope'] ==
            'concrete_raw_clock_register_subtree_staging_only', 'unknown staging contract')
    require(binding['source_sha256'] == sha(original_text) and
            binding['instrumented_sha256'] == sha(actual_text), 'changed circuit binding')
    annotation_path = directory / 'host-annotations.json'
    if annotation_path.is_file():
        annotations = annotation_path.read_text()
        require(sha(annotations) == binding['source_annotations_sha256'] and
                annotations == (directory / 'instrumented-annotations.json').read_text(),
                'changed or unbound original annotations')
    for flag in ('cut_certificates_bound', 'host_owner_bound', 'original_restore_supported',
                 'staging_restore_supported', 'complete_fpga_capture', 'deployable_capture_image',
                 'metasim_restore_supported'):
        require(binding[flag] is False, 'staging cannot grant ' + flag)
    require(binding['source_registers_keep_running'] is True and binding['sampling_contract'] ==
            'all_original_registers_before_one_positive_raw_clock_edge', 'changed sampling contract')
    original, actual = parse_modules(original_text), parse_modules(actual_text)
    require(set(actual) == set(original) | {'CheckpointNativeStateSnapshot'}, 'unexpected definitions')
    selected = binding['selected_execution'].split('.')
    root = re.search(r'^circuit (\w+) :', original_text, re.M)[1]
    require(selected[0] == root, 'unrooted execution')
    chain = [root]
    for part in selected[1:]:
        require(part in original[chain[-1]]['instances'], 'stale selected execution')
        chain.append(original[chain[-1]]['instances'][part])

    def executable(module):
        return [line for line in module['body'].splitlines()[1:] if line.strip() and
                not re.match(r'^  (input|output) ', line)]

    for name, before in original.items():
        after = actual[name]
        require(before['kind'] == after['kind'] and all(after['ports'].get(n) == t
                for n, t in before['ports'].items()), 'original ports changed ' + name)
        old, new = executable(before), executable(after)
        require(new[:len(old)] == old, 'original declarations/equations/effects changed ' + name)
        require(all(after['drivers'].get(n) == e for n, e in before['drivers'].items()),
                'original next-state or connection changed ' + name)
    layouts, vectors, clocks = [], {}, {}

    def clock_port(module):
        names = [n for n, t in module['ports'].items() if t == ('input', 'Clock')]
        require(len(names) == 1, 'one original input clock required')
        return names[0]

    def origin(module, expression, seen=frozenset()):
        require(expression not in seen, 'clock alias cycle')
        if module['ports'].get(expression) == ('input', 'Clock'):
            return expression
        require(expression in module['aliases'] and expression in module['drivers'],
                'derived or opaque raw clock')
        return origin(module, module['drivers'][expression], seen | {expression})

    def check_child(parent, instance, child):
        require(origin(parent, parent['drivers'].get(instance + '.' + clock_port(child))) ==
                clock_port(parent), 'child raw clock mismatch')

    require(clock_port(original[root]) == binding['raw_clock'], 'root clock mismatch')
    for i, parent in enumerate(chain[:-1]):
        check_child(original[parent], selected[i+1], original[chain[i+1]])

    def walk(name, path, offset, ancestors=frozenset()):
        require(name not in ancestors and name in original, 'recursive/missing module')
        module = original[name]
        require(module['kind'] == 'module' and not re.search(r'^  (?:mem|cmem|smem) ',
                module['body'], re.M), 'memory/opaque subtree needs its own adapter')
        registers = {n: (kind, clock) for n, kind, clock in module['consumers']}
        fields = re.findall(r'^  reg (\w+) : (UInt|SInt)<(\d+)>,', module['body'], re.M)
        require(len(fields) == len(registers), 'incomplete original storage census')
        start = offset
        expressions = []
        for register, kind, width in sorted(fields):
            width = int(width)
            require(registers[register][0] == 'register' and origin(module, registers[register][1]) ==
                    clock_port(module), 'original register raw clock mismatch')
            hierarchy = path + '.' + register
            state_id = sha(json.dumps(dict(hierarchy=hierarchy, kind='register',
                                          namespace='generated-simulator-state-v1'),
                                     sort_keys=True, separators=(',', ':')))
            layouts.append(dict(state_id=state_id, hierarchy=hierarchy, module=name, width=width,
                                offset=offset, signed=kind == 'SInt'))
            expressions.append(f'asUInt({register})' if kind == 'SInt' else register)
            offset += width
        for instance, child in sorted(module['instances'].items()):
            end = walk(child, path + '.' + instance, offset, ancestors | {name})
            if end > offset:
                check_child(module, instance, original[child])
                expressions.append(instance + '.' + OBS)
            offset = end
        if offset > start:
            expression = expressions[-1]
            for operand in reversed(expressions[:-1]):
                expression = f'cat({expression}, {operand})'
            require(actual[name]['ports'].get(OBS) == ('output', f'UInt<{offset-start}>') and
                    actual[name]['drivers'].get(OBS) == expression, 'wrong observation vector ' + name)
            vectors[name] = offset - start
            clocks[name] = clock_port(module)
        return offset

    bits = walk(chain[-1], '.'.join(selected), 0)
    require(bits == binding['bits'] and (bits + 63) // 64 == binding['words'] and
            binding['staging_owner_bits'] == bits + 71, 'incomplete vector or staging owner')
    rows = binding['state']
    require(len(rows) == len(layouts) and all(all(row.get(k) == v for k, v in expected.items())
            for row, expected in zip(rows, layouts)), 'incomplete/reordered/aliased concrete storage')
    for row in rows:
        # Hash the actual original FIRRTL statements, with exactly the emitter's
        # local indentation. This does not trust the producer's state table.
        raw = re.search(r'^  module ' + re.escape(row['module']) +
                        r' :[^\n]*\n([\s\S]*?)(?=^  (?:module|extmodule) |\Z)', original_text, re.M)[1]
        register = row['hierarchy'].rsplit('.', 1)[1]
        declaration = re.search(r'^    reg ' + re.escape(register) +
                                r' :[^\n]+\n(?:      [^\n]+\n)*', raw, re.M)
        driver = re.search(r'^    ' + re.escape(register) + r' <= [^\n]+', raw, re.M)
        require(declaration is not None and driver is not None, 'missing exact original register statement')
        statement = '\n'.join(line[4:] for line in declaration[0].rstrip('\n').splitlines())
        require(row['declaration_sha256'] == sha(statement) and row['driver_sha256'] == sha(driver[0][4:]),
                'unbound register declaration/equation hash')
    for i, parent in enumerate(chain[:-1]):
        require(actual[parent]['ports'].get(OBS) == ('output', f'UInt<{bits}>') and
                actual[parent]['drivers'].get(OBS) == selected[i+1] + '.' + OBS,
                'broken ancestor observation route')
    expected_inputs = dict(clock=binding['raw_clock'], live_state=OBS,
                           restore_hold='UInt<1>("h0")', restore_load='UInt<1>("h0")',
                           restore_state=f'UInt<{bits+71}>("h0")', reader_idle='UInt<1>("h1")',
                           borrow_attempt='UInt<1>("h0")')
    inputs = dict(reset=1, request=1, release_snapshot=1, owners_present=1,
                  functional_frozen=1, target_cycle=64, word_address=32)
    outputs = dict(request_ready=1, valid=1, failed=1, word_data=64, word_error=1,
                   cut_cycle=64, error=6, control_state=bits+71)
    expected_inputs.update({n: PREFIX+n for n in inputs})
    for name, expression in expected_inputs.items():
        require(actual[root]['drivers'].get(ADAPTER + '.' + name) == expression,
                'wrong staging input ' + name)
    for name, width in inputs.items():
        require(actual[root]['ports'].get(PREFIX+name) == ('input', f'UInt<{width}>'),
                'missing/changed control input ' + name)
    for name, width in outputs.items():
        require(actual[root]['ports'].get(PREFIX+name) == ('output', f'UInt<{width}>') and
                actual[root]['drivers'].get(PREFIX+name) == ADAPTER + '.' + name,
                'wrong staging output ' + name)
    require(actual[root]['instances'].get(ADAPTER) == 'CheckpointNativeStateSnapshot', 'wrong staging instance')
    ext = actual['CheckpointNativeStateSnapshot']['body']
    require(re.search(r'^  parameter BITS = ' + str(bits) + '$', ext, re.M) and
            re.search(r'^  parameter RESTORE_ENABLE = 0$', ext, re.M) and
            '  defname = CheckpointNativeStateSnapshot' in ext, 'wrong staging specialization')
    expected_ports = {'clock': ('input', 'Clock')}
    expected_ports.update({n: ('input', f'UInt<{w}>') for n, w in
                          (inputs | dict(restore_hold=1, restore_load=1, restore_state=bits+71,
                                         reader_idle=1, borrow_attempt=1, live_state=bits)).items()})
    expected_ports.update({n: ('output', f'UInt<{w}>') for n, w in
                          (outputs | dict(restore_ready=1, borrow_enable=1, snapshot_state=bits)).items()})
    require(actual['CheckpointNativeStateSnapshot']['ports'] == expected_ports, 'changed staging ABI')
    rtl = (directory / 'generated.register-snapshot.sv').read_text()
    require(sha(rtl) == binding['staging_source_sha256'], 'changed actual staging source')
    native = Path(__file__).resolve().parents[3] / 'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv'
    require(rtl == native.read_text(), 'unrecognized staging implementation')
    # No extra storage, equations, instance, input or output may hide behind a
    # valid projection of the originals. Shared definitions can expose only a
    # combinational observation, including their unselected concrete executions.
    for name, module in original.items():
        changed = actual[name]
        extras = set(changed['ports']) - set(module['ports'])
        expected = ({OBS} if name in vectors or name in chain else set())
        if name == root:
            expected |= {PREFIX+n for n in (*inputs, *outputs)}
        require(extras == expected, 'unaccounted added ports ' + name)
        require(changed['consumers'] == module['consumers'] and changed['effects'] == module['effects'],
                'unaccounted original clocked state/effect ' + name)
        require(changed['instances'] == (module['instances'] | {ADAPTER: 'CheckpointNativeStateSnapshot'}
                if name == root else module['instances']), 'unaccounted instance ' + name)
        extra_drivers = set(changed['drivers']) - set(module['drivers'])
        expected_drivers = {OBS} if OBS in expected else set()
        if name == root:
            expected_drivers |= {ADAPTER+'.'+n for n in expected_inputs} | {PREFIX+n for n in outputs}
        require(extra_drivers == expected_drivers, 'unaccounted added driver ' + name)
    return dict(status='pass', entries=len(rows), bits=bits, words=(bits+63)//64,
                staging_owner_bits=bits+71, original_equations_preserved=True,
                raw_clock_routes_checked=True, complete_fpga_capture=False)
