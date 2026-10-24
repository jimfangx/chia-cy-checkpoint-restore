"""Independent complete structural oracle for the detached physical clock wiring.

No state capture or image admission is established by this wiring audit.
"""
import argparse
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import arguments, digest, parse_modules

PREFIX = 'checkpoint_physical_'
MASK, RAW, CE, ROOT_GATE = [PREFIX + x for x in ('mask', 'source_clock', 'logical_ce', 'root_gate')]


def audit(reference, manifest, plan, wired, binding, verilog, emission, native_generated=None):
    text = Path(reference).read_text()
    native_binding = None
    if native_generated is not None:
        from tools.checkpoint_formats.tests.audit_native_functional_production import audit as audit_native
        audit_native(native_generated)
        native_generated = Path(native_generated)
        prefix = native_generated/'FireSim-generated'
        native_path = lambda suffix: Path(str(prefix)+'.native-functional'+suffix)
        require(Path(reference).read_bytes() == native_path('-reference.fir').read_bytes() and
                Path(manifest).read_bytes() == native_path('-simulator-state.json').read_bytes() and
                Path(plan).read_bytes() == native_path('-plan.json').read_bytes(),
                'native wiring inputs differ from independently audited functional source')
        native_binding = json.loads(native_path('-binding.json').read_text())
        baseline_text = native_path('-instrumented.fir').read_text()
    else:
        baseline_text = text
    original = parse_modules(baseline_text)
    result_text = Path(wired).read_text()
    result = parse_modules(result_text)
    source_plan = json.loads(Path(plan).read_text())
    inventory = json.loads(Path(manifest).read_text())
    doc = json.loads(Path(binding).read_text())
    root, clock = inventory['root_module'], source_plan['common_source_clock']
    require(source_plan['reference_sha256'] == inventory['reference_sha256'] == digest(text), 'stale reference')
    require(source_plan['simulator_manifest_sha256'] == digest(Path(manifest).read_text()), 'stale manifest')
    require(result.keys() == original.keys(), 'module loss or addition')

    def gates(module, seen=frozenset()):
        require(module not in seen, 'recursive hierarchy')
        m = original[module]
        if m['kind'] == 'extmodule':
            require(m['body'].endswith('defname = BUFGCE'), 'opaque owner')
            return ['']
        return sorted(name + ('.' + p if p else '') for name, child in m['instances'].items()
                      for p in gates(child, seen | {module}))

    top_gates = [root + '.' + p for p in gates(root)]
    require(top_gates == [r['hierarchy'] for r in source_plan['physical_gates']], 'incomplete input gate order')
    expected = dict(wiring_version=1, scope='physical_clock_wiring_probe_only', complete_fpga_capture=False,
        deployable_capture_image=False, ce_dependency_closure_proven=False, production_annotations_translated=False,
        reference_sha256=digest(text), simulator_manifest_sha256=digest(Path(manifest).read_text()),
        plan_sha256=digest(Path(plan).read_text()), wired_reference_sha256=digest(result_text),
        root_module=root, common_source_clock=clock, mask_port=MASK, logical_ce_port=CE,
        mask_contract='externally_registered_common_source_falling_edge', root_gate=root + '.' + ROOT_GATE,
        logical_ce_bit_order=top_gates, remaining_obligations=['connected_atomic_cut_controller',
            'external_ce_reset_and_memory_writer_freeze', 'physical_latch_bank_and_metasim_restore_mapping',
            'production_annotation_and_xdc_translation', 'functional_memory_timing_bridge_host_and_pre_fame_ownership',
            'connected_ungated_mmio_dma_transport'])
    if native_binding is not None:
        expected.update(scope='native_functional_clock_cut_companion_only',
            functional_binding_sha256=digest(native_path('-binding.json').read_text()),
            functional_instrumented_sha256=digest(baseline_text), access_clock='ckpt_clock',
            access_clock_contract='tie_to_ungated_common_source',
            functional_freeze_contract='hold_clock_mask_through_endpoint_drain',
            bank_annotations_preserved=True, production_freeze_owners_bound=False, metasim_restore_supported=False)
    require(doc == expected, 'changed wiring binding or ownership claim')
    if native_binding is None:
        require(json.loads(Path(emission).read_text()) == dict(wiring_binding_sha256=digest(Path(binding).read_text()),
                wired_verilog_sha256=digest(Path(verilog).read_text())), 'unbound emitted wiring')
    else:
        suffixes = ['.native-clock-cut'+s for s in ('.fir','.json','.sv','.synthesis.xdc','.implementation.xdc')]
        suffixes += ['.native-functional-emission.json','.native-descriptors-emission.json']
        inputs = {s: digest(Path(str(prefix)+s).read_text()) for s in suffixes}
        require(json.loads(Path(emission).read_text()) == dict(binding_version=1,
            scope='native_functional_clock_cut_companion_only', inputs=inputs, complete_fpga_capture=False,
            deployable_capture_image=False, production_freeze_owners_bound=False, metasim_restore_supported=False),
            'native wiring emission/source/annotation binding changed')
        require(inputs['.native-clock-cut.fir'] == digest(result_text) and
                inputs['.native-clock-cut.json'] == digest(Path(binding).read_text()) and
                inputs['.native-clock-cut.sv'] == digest(Path(verilog).read_text()), 'native wiring output substitution')
        for suffix in ('.synthesis.xdc','.implementation.xdc'):
            require(Path(str(prefix)+'.native-clock-cut'+suffix).read_bytes() == native_path(suffix).read_bytes(),
                    'native pin constraints changed during clock wiring')
    visited = set()
    consumer_count = 0

    def first_native(module):
        # Final compiler output may retain unreachable bridge extmodules.
        # Select the first *reachable* native definition in declaration order.
        if original[module]['kind'] == 'extmodule':
            require(original[module]['body'].endswith('defname = BUFGCE'), 'opaque live owner')
            return module
        for child in original[module]['instances'].values():
            found = first_native(child)
            if found is not None:
                return found
        return None
    primitive = first_native(root)

    def check(module):
        nonlocal consumer_count
        if module in visited:
            return
        visited.add(module)
        before, after = original[module], result[module]
        if before['kind'] == 'extmodule':
            require(before == after, 'changed native primitive')
            return
        own = gates(module)
        ports = dict(before['ports'])
        if module == root or own:
            if module != root:
                ports[RAW] = ('input', 'Clock')
            ports.update({MASK: ('input', 'UInt<1>'), CE: ('output', f'UInt<{len(own)}>')})
        require(after['ports'] == ports, 'changed/missing hierarchy ports ' + module)
        instances = dict(before['instances'])
        if module == root:
            instances[ROOT_GATE] = primitive
        require(after['instances'] == instances, 'changed hierarchy ' + module)

        def rewrite(expr):
            if expr is None or module != root:
                return expr
            return re.sub(r'(?<![A-Za-z0-9_$.])' + re.escape(clock) + r'(?![A-Za-z0-9_$])', ROOT_GATE + '.O', expr)

        expected_drivers = {name: rewrite(value) for name, value in before['drivers'].items()}
        source = clock if module == root else RAW
        if module == root:
            expected_drivers.update({ROOT_GATE + '.I': clock, ROOT_GATE + '.CE': f'not({MASK})'})
        for name, child in before['instances'].items():
            if original[child]['kind'] == 'extmodule':
                index = own.index(name)
                wire = PREFIX + 'ce_' + str(index)
                expected_drivers[wire] = rewrite(before['drivers'][name + '.CE'])
                expected_drivers[name + '.I'] = source
                expected_drivers[name + '.CE'] = f'and({wire}, not({MASK}))'
            elif gates(child):
                expected_drivers.update({name + '.' + RAW: source, name + '.' + MASK: MASK})
        if own:
            bits = []
            for p in reversed(own):
                if '.' not in p:
                    bits.append(PREFIX + 'ce_' + str(own.index(p)))
                else:
                    head, rest = p.split('.', 1)
                    index = gates(before['instances'][head]).index(rest)
                    bits.append(f'bits({head}.{CE}, {index}, {index})')
            value = bits[0]
            for b in bits[1:]:
                value = f'cat({value}, {b})'
            expected_drivers[CE] = value
        for name, value in expected_drivers.items():
            # Preserve the unmasked alias rather than expanding it into masked
            # CE expressions. This also proves CE readout bit ordering.
            actual = after['drivers'].get(name, 'MISSING')
            require(actual == value, f'changed driver {module}.{name}: {actual!r} != {value!r}')
        extra = set(after['drivers']) - set(expected_drivers)
        require(not extra, 'unexpected functional driver ' + str(extra))
        require(after['consumers'] == [(n, k, rewrite(e)) for n, k, e in before['consumers']],
                'changed sequential clock/state ' + module)
        require(after['effects'] == [(k, rewrite(e)) for k, e in before['effects']], 'changed clocked effect ' + module)
        # Declaration/reset/memory dimensions and non-clocked operations must
        # also survive. Comparing source lines catches edits outside drivers.
        def declarations(row, change=False):
            return [rewrite(line) if change else line for line in row['body'].splitlines()
                    if re.match(r'  (reg |mem |    |reset =>)', line) or line.startswith('    ')]
        require(declarations(after) == declarations(before, True), 'changed storage/reset declaration ' + module)
        consumer_count += len(before['consumers']) + len(before['effects'])
        for child in before['instances'].values():
            check(child)
    check(root)
    if native_binding is not None:
        root_consumers = {name: expression for name, kind, expression in result[root]['consumers'] if kind == 'register'}
        # The complete structural oracle above also checks every update/reset,
        # not just these clock names. This explicit check catches accidental
        # remasking of the endpoint in a coherently changed native input.
        for name in ('ckpt_pending','ckpt_saved_data','ckpt_saved_error'):
            require(root_consumers.get(name) == 'ckpt_clock', 'native endpoint clock was masked or changed')
    return dict(status='pass', scope='independent complete clock-wiring structural audit',
                physical_fpga_capture=False, deployable_capture_image=False, native_gates=len(top_gates) + 1,
                checked_module_definitions=len(visited), checked_consumer_definitions=consumer_count,
                wired_reference_sha256=digest(result_text), logical_ce_bit_order=top_gates)


def main():
    parser = argparse.ArgumentParser(__doc__)
    for key in ('reference', 'manifest', 'plan', 'wired', 'binding', 'verilog', 'emission', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='clock-wiring-', dir=args.out))
    kwargs = {k: getattr(args, k) for k in ('reference', 'manifest', 'plan', 'wired', 'binding', 'verilog', 'emission')}
    result = audit(**kwargs)
    result['rejected'] = []
    original_text = args.wired.read_text()
    original_binding = json.loads(args.binding.read_text())
    # Rehash the changed netlist/binding coherently: structural checks, rather
    # than stale hashes, must reject these substitutions.
    for name in ('root-bypass', 'native-source-cascade', 'native-mask-bypass', 'logical-ce-swap',
                 'state-clock-bypass', 'changed-functional-update', 'claim-ce-closure', 'claim-capture'):
        text, doc = original_text, dict(original_binding)
        clock = doc['common_source_clock']
        if name == 'root-bypass': text = text.replace(ROOT_GATE + '.CE <= not(' + MASK + ')', ROOT_GATE + '.CE <= UInt<1>("h1")', 1)
        elif name == 'native-source-cascade': text = text.replace('.I <= ' + RAW, '.I <= clock', 1)
        elif name == 'native-mask-bypass': text = text.replace('and(' + PREFIX + 'ce_0, not(' + MASK + '))', PREFIX + 'ce_0', 1)
        elif name == 'logical-ce-swap': doc['logical_ce_bit_order'] = list(reversed(doc['logical_ce_bit_order']))
        elif name == 'state-clock-bypass':
            text = text.replace(', ' + ROOT_GATE + '.O with :', ', ' + clock + ' with :', 1)
            if text == original_text:
                text = text.replace('.clock <= ' + ROOT_GATE + '.O', '.clock <= ' + clock, 1)
        elif name == 'changed-functional-update': text = text.replace('add(', 'sub(', 1)
        elif name == 'claim-ce-closure': doc['ce_dependency_closure_proven'] = True
        else: doc['complete_fpga_capture'] = True
        require(text != original_text or doc != original_binding, 'ineffective mutation ' + name)
        doc['wired_reference_sha256'] = digest(text)
        bad_wired, bad_binding, bad_emission = [out / (name + suffix) for suffix in ('.fir', '.json', '-emission.json')]
        bad_wired.write_text(text)
        bad_binding.write_text(json.dumps(doc))
        bad_emission.write_text(json.dumps(dict(wiring_binding_sha256=digest(bad_binding.read_text()),
            wired_verilog_sha256=digest(args.verilog.read_text()))))
        try:
            audit(**dict(kwargs, wired=bad_wired, binding=bad_binding, emission=bad_emission))
        except ValueError as error:
            result['rejected'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('accepted coherently rehashed corruption ' + name)
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
