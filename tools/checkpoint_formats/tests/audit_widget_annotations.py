"""Reconstruct bounded widget storage projection from actual old/new hierarchy.

This checks the fixture's typed contracts independently of the Scala mapping
receipt. It never interprets a storage constraint as a physical state owner.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_native_inplace_annotations import protocol_json, HEADER
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

NO_DEDUP = 'firrtl.transforms.NoCircuitDedupAnnotation$'
CACHE = 'firrtl.transforms.CombinationalPath'
TOUCH = 'firrtl.transforms.DontTouchAnnotation'
MEMORY = 'midas.targetutils.FirrtlMemModelAnnotation'
BOX = 'midas.core.TargetBoxAnnotation'
HISTORY = 'firrtl.transforms.DedupedResult'
XDC = ('midas.InternalXDCAnnotation', 'midas.targetutils.xdc.XDCAnnotation')
NO_SYNTH_INIT = 'firrtl.annotations.MemoryNoSynthInit$'
TYPED = {NO_SYNTH_INIT, NO_DEDUP, CACHE, TOUCH, MEMORY, BOX, HISTORY, *XDC}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def serialized(a):
    kind = a['class']
    if kind in (NO_DEDUP, NO_SYNTH_INIT):
        return kind.split('.')[-1].removesuffix('$')
    if kind in (TOUCH, MEMORY, BOX):
        return kind.split('.')[-1] + '(' + a['target'] + ')'
    if kind == HISTORY:
        return 'DedupedResult(' + a['original'] + ',' + ('None' if a['duplicate'] is None else
            'Some(' + a['duplicate'] + ')') + ',' + str(a['index']) + ')'
    if kind == CACHE:
        return 'CombinationalPath(' + a['sink'] + ',List(' + ', '.join(a['sources']) + '))'
    require(kind in XDC, 'unsupported bounded projection serialization')
    return kind.split('.')[-1] + '(' + a['destinationFile']['class'].split('$')[-2] + ',' + \
        a['formatString'] + ',List(' + ', '.join(a['argumentList']) + '))'


def reconstruct(source, before, after, root):
    from tools.checkpoint_formats.tests.audit_widget_graft import instances
    old, new = dict(instances(before, root)), dict(instances(after, root))
    require(all(path in new for path in old), 'lost original annotation execution')
    storage = [a for a in source if a['class'] in TYPED]
    retained = [a for a in source if a['class'] not in TYPED]
    def copies(text, reference=False, anchor=False):
        pattern = r'~(\w+)\|(\w+)((?:/\w+:\w+)*)' + (r'>(\w+(?:\.\w+)?)' if reference else '')
        match = re.fullmatch(pattern, text)
        require(match and match[1] == root and match[2] in old.values(), 'foreign/stale annotation target')
        owner = match[2]
        hops = re.findall(r'/(\w+):(\w+)', match[3])
        for instance, child in hops:
            require(before[owner]['instances'].get(instance) == child, 'stale annotation path')
            owner = child
        if reference:
            ref, *fields = match[4].split('.')
            definition = before[owner]
            require(ref in definition['ports'] or re.search(r'^  (?:reg|mem|node|wire) ' + re.escape(ref) +
                    r'(?:\s|\s*:)', definition['body'], re.M) or ref in definition['instances'],
                    'missing original annotation declaration')
            if fields:
                require(len(fields) == 1 and ref in definition['instances'] and
                        fields[0] in before[definition['instances'][ref]]['ports'], 'hidden annotation pin')
        result = []
        executions = sorted(old.items()) if anchor else old.items()
        for path, module in executions:
            if module != match[2]:
                continue
            current = path
            for instance, _ in hops:
                current += '.' + instance
            renamed = '~' + root + '|' + new[current]
            if anchor:
                renamed = '~' + root + '|' + new[root]
                prefix = root
                for instance in current.split('.')[1:]:
                    prefix += '.' + instance
                    renamed += '/' + instance + ':' + new[prefix]
            elif not reference:
                renamed = '~' + root + '|' + new[path]
                prefix = path
                for instance, _ in hops:
                    prefix += '.' + instance
                    renamed += '/' + instance + ':' + new[prefix]
            if reference:
                renamed += '>' + match[4]
            result.append(renamed)
        return result

    expected, mappings = [], []
    for a in storage:
        kind = a['class']
        if kind == CACHE:
            continue
        if kind in (NO_DEDUP, NO_SYNTH_INIT):
            expected.append(a)
            continue
        if kind == HISTORY:
            values = [dict(a, duplicate=t) for t in copies(a['duplicate'])] if a['duplicate'] else [a]
            targets = list(map(serialized, values))
        elif kind in (TOUCH, MEMORY, BOX):
            if kind in (TOUCH, MEMORY):
                owner = re.findall(r':(\w+)', a['target'].split('>')[0])
                owner = owner[-1] if owner else a['target'].split('|')[1].split('>')[0]
                require(before[owner]['kind'] == 'module', 'opaque storage annotation')
                if kind == MEMORY:
                    require(re.search(r'^  mem ' + re.escape(a['target'].split('>')[1]) + r' :',
                            before[owner]['body'], re.M), 'memory annotation changed kind')
            values = [dict(a, target=t) for t in copies(a['target'], reference=kind != BOX)]
            targets = [a['target'] for a in values]
        else:
            require(kind in XDC, 'unsupported typed annotation in bounded widget audit')
            require(a['formatString'].count('{}') == len(a['argumentList']), 'constraint arity changed')
            if not a['argumentList']:
                values = [a]
            else:
                roots = [re.fullmatch(r'~\w+\|(\w+).*', t)[1] for t in a['argumentList']]
                require(len(set(roots)) == 1, 'uncorrelated XDC roots')
                # Keep the root and correlated hops for concrete constraints;
                # anchor primitive-local pins to ORIGINAL executions only.
                anchor = before[roots[0]]['kind'] == 'extmodule'
                args = []
                for text in a['argumentList']:
                    if anchor:
                        args.append(copies(text, reference=True, anchor=True))
                    else:
                        owner, ref = text.split('>')
                        args.append([t + '>' + ref for t in copies(owner)])
                require(len({len(v) for v in args}) == 1, 'uncorrelated XDC expansion')
                values = [dict(a, argumentList=list(v)) for v in zip(*args)]
            targets = list(map(serialized, values))
        expected.extend(values)
        mappings.append(dict(source=serialized(a), targets=targets))
    expected.append({'class': NO_DEDUP})
    unique = list({canonical(a): a for a in expected}.values())
    return unique, retained, mappings, storage


def audit_source(directory, host_expected):
    """Rebuild the source projection and typed rebase without trusting its rows."""
    from tools.checkpoint_formats.tests.audit_widget_graft import sha
    directory = Path(directory)
    load = lambda name: json.loads((directory / name).read_text())
    doc = load('source-policy.json')
    connection = load('connection.json')
    require(doc['source_policy_version'] == 1 and doc['scope'] == 'typed_selected_source_contract_merge_only' and
            all(doc[k] is False for k in ('complete_fpga_capture', 'production_annotations_translated',
                'deployable_capture_image', 'production_freeze_owners_bound')), 'changed source policy admission')
    require(connection['source_annotation_projection_sha256'] == sha(directory / 'source-policy.json'),
            'unbound source policy')
    for key, name in (('source_sha256', 'original-selected.fir'), ('graft_sha256', 'graft.fir'),
                      ('connected_sha256', 'connected.fir'),
                      ('source_annotations_sha256', 'original-selected-annotations.json'),
                      ('graft_annotations_sha256', 'graft-annotations.json'),
                      ('merged_annotations_sha256', 'connected-annotations.json')):
        require(doc[key] == sha(directory / name), 'changed source policy input ' + key)
    require(doc['host_annotations_sha256'] == digest(protocol_json(host_expected)), 'changed source policy host')
    source = load('original-selected-annotations.json')
    require(all(a['class'] in TYPED for a in source) and
            source.count({'class': NO_DEDUP}) == 1, 'unsupported source annotation policy')
    before, after = (parse_modules((directory / (n + '.fir')).read_text()) for n in ('original-selected', 'graft'))
    root = re.search(r'^circuit (\w+) :', (directory / 'original-selected.fir').read_text(), re.M)[1]
    enclosing = re.search(r'^circuit (\w+) :', (directory / 'connected.fir').read_text(), re.M)[1]
    expected, retained, _, _ = reconstruct(source, before, after, root)
    require(not retained and expected == load('graft-annotations.json'),
            'source contracts differ from original concrete executions')
    rebased = copy.deepcopy(expected)
    def target(text):
        require(text.startswith('~' + root + '|'), 'foreign selected annotation target')
        return '~' + enclosing + text[len(root) + 1:]
    for a in rebased:
        if 'target' in a:
            a['target'] = target(a['target'])
        if 'argumentList' in a:
            a['argumentList'] = list(map(target, a['argumentList']))
        if a['class'] == HISTORY and a['duplicate'] is not None:
            a['duplicate'] = target(a['duplicate'])
        if set(a) == {'class'}:
            require(a in host_expected, 'global source policy absent from enclosing host')
    require(doc['rebased_annotations_sha256'] == digest(protocol_json(rebased)), 'changed typed source rebase')
    normalize = lambda s: s.replace(',ArraySeq(', ',List(')
    require(list(map(normalize, doc['rebased_annotations'])) == list(map(serialized, rebased)),
            'source rebase receipt differs from typed targets')
    merged = host_expected + [a for a in rebased if a not in host_expected]
    require(doc['merged_annotations_sha256'] == digest(protocol_json(merged)), 'changed merged source policies')
    return dict(source=len(source), rebased=len(rebased), global_policy_matched=True,
                physical_fpga_capture=False), merged


def audit(directory):
    from tools.checkpoint_formats.tests.audit_widget_graft import instances, sha
    directory = Path(directory)
    load = lambda name: json.loads((directory / name).read_text())
    doc = load('annotation-projection.json')
    connection = load('connection.json')
    source, actual = (load(n + '-annotations.json') for n in ('native-inlined', 'connected'))
    before, after = (parse_modules((directory / (n + '.fir')).read_text())
                     for n in ('native-inlined', 'connected'))
    root = re.search(r'^circuit (\w+) :', (directory / 'native-inlined.fir').read_text(), re.M)[1]
    old, new = dict(instances(before, root)), dict(instances(after, root))
    require(all(path in new for path in old), 'lost original annotation execution')
    require(doc['projection_version'] == 1 and doc['scope'] == 'enclosing_host_typed_storage_annotations_only' and
            all(doc[k] is False for k in ('complete_fpga_capture', 'production_annotations_translated',
                'deployable_capture_image', 'production_freeze_owners_bound')), 'changed projection admission')
    require(connection['host_annotation_projection_sha256'] == sha(directory / 'annotation-projection.json'),
            'unbound widget annotation projection')
    for key, name in (('source_sha256', 'native-inlined.fir'), ('connected_sha256', 'connected.fir'),
                      ('source_annotations_sha256', 'native-inlined-annotations.json')):
        require(doc[key] == sha(directory / name), 'changed projection input ' + key)
    storage = [a for a in source if a['class'] in TYPED]
    retained = [a for a in source if a['class'] not in TYPED]
    require(doc['retained_annotations_sha256'] == digest(protocol_json(retained)), 'changed retained metadata')

    unique, retained, mappings, storage = reconstruct(source, before, after, root)
    host_expected = unique + retained
    require(doc['projected_annotations_sha256'] == digest(protocol_json(host_expected)),
            'changed host projection annotation digest')
    merged = host_expected
    source_policy = None
    if (directory / 'source-policy.json').is_file():
        source_policy, merged = audit_source(directory, host_expected)
    else:
        require('source_annotation_projection_sha256' not in connection, 'missing bound source policy')
    require(actual == merged, 'lost changed duplicated or broadened annotation')
    normalize = lambda s: s.replace(',ArraySeq(', ',List(')
    normrow = lambda r: dict(source=normalize(r['source']), targets=list(map(normalize, r['targets'])))
    translation = doc['translation']
    require(translation['translation_version'] == 2 and
            sorted(map(normrow, translation['mappings']), key=canonical) == sorted(mappings, key=canonical),
            'projection mapping differs from original concrete hierarchy')
    for key, values in (('source_sha256', storage), ('translated_sha256', unique)):
        ordered = sorted((a for a in values if a['class'] != CACHE), key=serialized)
        require(translation[key] == digest(protocol_json(ordered)), 'changed translation annotation digest')
    require(sorted(map(normalize, doc['invalidated_path_caches'])) ==
            sorted(serialized(a) for a in storage if a['class'] == CACHE), 'lost invalidated cache history')
    emitted = {'Synthesis': [], 'Implementation': []}
    for a in merged:
        if a['class'] not in XDC:
            continue
        args = a['argumentList']
        destination = a['destinationFile']['class'].split('$')[-2]
        module = re.fullmatch(r'~\w+\|(\w+).*', args[0])[1] if args else root
        for path, owner in new.items():
            if owner != module:
                continue
            prefix = ''  # Fixture explicitly requests no pre/post placement prefix.
            if path != root:
                prefix += path.split('.', 1)[1].replace('.', '/') + '/'
            paths = []
            for text in args:
                base, ref = text.split('>')
                hops = re.findall(r'/(\w+):\w+', base)
                paths.append(prefix + '/'.join(hops + ref.split('.')))
            pieces = a['formatString'].split('{}')
            emitted[destination].append(''.join(s + (paths[i] if i < len(paths) else '') for i, s in enumerate(pieces)))
    for destination, body in emitted.items():
        require((directory / ('projected.' + destination.lower() + '.xdc')).read_text() ==
                '\n'.join([HEADER] + body), 'emitted XDC differs from original correlated constraints')
    component = directory / 'projected-component.implementation.xdc'
    if component.exists():
        expected_text = '\n'.join([HEADER] + emitted['Implementation'])
        for a in merged:
            if a['class'] in XDC and not a['argumentList'] and a['destinationFile']['class'].endswith('$Implementation$'):
                require(expected_text.count(a['formatString']) == 1, 'ambiguous deferred shell constraint')
                expected_text = expected_text.replace(a['formatString'], '', 1)
        require(component.read_text() == expected_text, 'OOC constraints lost a hierarchy-bound original target')
    return dict(source=len(source), projected=len(actual), storage=len(storage), retained=len(retained),
                native_constraints_anchored=True, source_policy=source_policy, physical_fpga_capture=False)


def corruptions(directory, out):
    import shutil
    from tools.checkpoint_formats.codec import FormatError
    from tools.checkpoint_formats.tests.audit_widget_graft import audit as audit_graft, sha
    directory, out = Path(directory), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rejected = []
    names = ['drop-constraint', 'stale-target', 'mask-alias', 'primitive-local-expansion',
                 'cross-instance', 'changed-format', 'drop-register', 'duplicate-host-metadata',
                 'projection-admission', 'mapping-loss', 'cache-history', 'xdc-output']
    if (directory / 'projected-component.implementation.xdc').exists():
        names.append('ooc-constraint-loss')
    if (directory / 'source-policy.json').is_file():
        names.extend(('source-admission', 'source-row', 'source-graft-loss', 'source-original-target',
                      'source-global-loss', 'source-format'))
    for name in names:
        case = out / name
        shutil.copytree(directory, case)
        annotations = json.loads((case / 'connected-annotations.json').read_text())
        projection = json.loads((case / 'annotation-projection.json').read_text())
        doc = json.loads((case / 'connection.json').read_text())
        constraint = next(a for a in annotations if a['class'] in XDC and
                          a['formatString'].startswith('set checkpoint_pins'))
        if name == 'drop-constraint':
            annotations.remove(constraint)
        elif name == 'stale-target':
            next(a for a in annotations if a['class'] == TOUCH and a['target'].endswith('>value'))['target'] = '~FPGATop|Leaf>value'
        elif name == 'mask-alias':
            constraint['argumentList'][0] = '~FPGATop|FPGATop/sim:SimWrapper/network:NativeStorage>checkpoint_native_root_gate.CE'
        elif name == 'primitive-local-expansion':
            constraint['argumentList'] = ['~FPGATop|Native>CE', '~FPGATop|Native>O']
        elif name == 'cross-instance':
            constraint['argumentList'][1] = constraint['argumentList'][1].replace('/left_:', '/right_:')
        elif name == 'changed-format':
            constraint['formatString'] = constraint['formatString'].replace('DONT_TOUCH true', 'DONT_TOUCH false')
        elif name == 'drop-register':
            annotations.remove(next(a for a in annotations if a['class'] == TOUCH and a['target'].endswith('>value')))
        elif name == 'duplicate-host-metadata':
            annotations.append(next(a for a in annotations if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation'))
        elif name == 'projection-admission':
            projection['complete_fpga_capture'] = True
        elif name == 'mapping-loss':
            projection['translation']['mappings'].pop()
        elif name == 'cache-history':
            projection['invalidated_path_caches'].append('Invented_cache')
        elif name == 'xdc-output':
            path = case / 'projected.implementation.xdc'
            path.write_text(path.read_text() + '\nset_property INVENTED 1 [current_design]\n')
        elif name == 'ooc-constraint-loss':
            path = case / 'projected-component.implementation.xdc'
            text = path.read_text()
            line = next(line for line in text.splitlines() if line.startswith('set checkpoint_pins'))
            path.write_text(text.replace(line, '', 1))
        elif name.startswith('source-'):
            policy = json.loads((case / 'source-policy.json').read_text())
            if name == 'source-admission':
                policy['complete_fpga_capture'] = True
            elif name == 'source-row':
                policy['rebased_annotations'][-1] += '_invented'
            elif name in ('source-graft-loss', 'source-original-target'):
                filename = 'graft-annotations.json' if name == 'source-graft-loss' else 'original-selected-annotations.json'
                values = json.loads((case / filename).read_text())
                touch = next(a for a in values if a['class'] == TOUCH)
                if name == 'source-graft-loss':
                    values.remove(touch)
                else:
                    touch['target'] = '~SimWrapper|Leaf>missing'
                (case / filename).write_text(protocol_json(values))
                policy['graft_annotations_sha256' if name == 'source-graft-loss' else 'source_annotations_sha256'] = sha(case / filename)
            elif name == 'source-global-loss':
                annotations.remove(next(a for a in annotations if a['class'] == NO_SYNTH_INIT))
            elif name == 'source-format':
                constraint['formatString'] += '; set INVENTED 1'
            (case / 'source-policy.json').write_bytes(canonical(policy))
        (case / 'connected-annotations.json').write_text(protocol_json(annotations))
        projection['projected_annotations_sha256'] = sha(case / 'connected-annotations.json')
        if (case / 'source-policy.json').is_file():
            # The host projection precedes the merge. Keep that original pin
            # while coherently rehashing the claimed final source union.
            projection['projected_annotations_sha256'] = json.loads(
                (directory / 'annotation-projection.json').read_text())['projected_annotations_sha256']
            policy = json.loads((case / 'source-policy.json').read_text())
            policy['merged_annotations_sha256'] = sha(case / 'connected-annotations.json')
            (case / 'source-policy.json').write_bytes(canonical(policy))
            doc['source_annotation_projection_sha256'] = sha(case / 'source-policy.json')
        (case / 'annotation-projection.json').write_bytes(canonical(projection))
        doc['host_annotation_projection_sha256'] = sha(case / 'annotation-projection.json')
        (case / 'connection.json').write_bytes(canonical(doc))
        try:
            audit_graft(case)
        except FormatError as error:
            rejected.append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('accepted rehashed widget annotation corruption ' + name)
    return rejected
