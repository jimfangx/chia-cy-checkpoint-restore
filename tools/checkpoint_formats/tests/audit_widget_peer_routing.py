"""Independent reconstruction of reserved widget routes after native inlining.

This does not admit an image or supply the still unsupported transport owner.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_widget_reservation import audit as audit_reservation, PINS, SOURCES

PEERS = dict(clock_mask='clock_mask', read_enable='physical_read_enable', captured_ce='captured_ce',
             logical_ce='ce', descriptor_entry='descriptor_entry', descriptor_valid='descriptor_valid',
             descriptor_bank='descriptor_bank', descriptor_slot='descriptor_slot',
             descriptor_width='descriptor_width', descriptor_depth='descriptor_depth',
             request_valid='bank_request_valid', request_ready='bank_request_ready', bank='bank', slot='slot',
             address='address', response_valid='bank_response_valid', response_ready='bank_response_ready',
             response_data='bank_response_data', response_error='bank_response_error')
EXTRA = [
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointWidgetPeerRouting.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointWidgetPeerRoutingSpec.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/passes/ResolveSimulationInline.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointInPlaceGraft.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedExternalOwners.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SemanticStateInventory.scala',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    'tools/checkpoint_formats/codec.py',
    'tools/checkpoint_formats/tests/audit_widget_peer_routing.py',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(',', ':'))


def audit(before, generated):
    audit_reservation(before)
    original = json.loads((before/'reservation.json').read_text())
    inline_reservation = json.loads((generated/'inline-input-reservation.json').read_text())
    doc = json.loads((generated/'peer-routing.json').read_text())
    text = (generated/'native-inlined.fir').read_text()
    annotations = json.loads((generated/'native-inlined-annotations.json').read_text())
    modules = parse_modules(text)
    require(doc['scope'] == 'native_inlined_reserved_widget_peer_routes_only' and doc['peer_routing_version'] == 1,
            'changed peer scope')
    require(doc['reservation_sha256'] == sha(generated/'inline-input-reservation.json') and
            doc['source_sha256'] == sha(generated/'native-inlined.fir') and
            doc['annotations_sha256'] == sha(generated/'native-inlined-annotations.json'), 'stale peer inputs')
    require(doc['host'] == original['host'] == 'FPGATop' and doc['target'] == original['target'], 'changed host/target')
    require(doc['external_transport_state_owner'] == 'unsupported_no_state_adapter' and
            all(doc[k] is False for k in ('in_place_checkpoint_widget_connected', 'production_freeze_owners_bound',
                                         'complete_fpga_capture', 'deployable_capture_image', 'metasim_restore_supported')),
            'peer routes falsely admit capture')
    history = [a for a in annotations if a['class'] == 'midas.passes.SimulationInlineResultAnnotation']
    require(len(history) == 1 and hashlib.sha256(history[0]['body'].encode()).hexdigest() == doc['inline_history_sha256'],
            'changed inline history')
    context = json.loads(history[0]['body'])
    require(context['input_sha256'] == sha(before/'reserved.fir') and context['output_sha256'] == doc['source_sha256'],
            'inline circuit binding')
    old_annotations = json.loads((before/'reserved-annotations.json').read_text())
    input_annotations = json.loads((generated/'inline-input-annotations.json').read_text())
    require(input_annotations[:-1] == old_annotations and input_annotations[-1] ==
            {'class': 'firrtl.stage.RunFirrtlTransformAnnotation', 'transform': 'firrtl.passes.InlineInstances'},
            'inline input must add only the real inline-pass request')
    expected_reservation = dict(original, annotations_sha256=sha(generated/'inline-input-annotations.json'))
    require(inline_reservation == expected_reservation and
            context['input_annotations_sha256'] == expected_reservation['annotations_sha256'],
            'inline reservation phase identity')
    host = modules['FPGATop']
    require(host['ports'].get('clock') == ('input', 'Clock') and
            host['ports'].get('reset') == ('input', 'UInt<1>'), 'missing raw host clock/reset ports')
    transports = [n for n, m in host['instances'].items() if m == 'CheckpointPhysicalCaptureTransport']
    require(len(transports) == 1 and doc['transport'] == 'FPGATop.'+transports[0], 'physical peer transport')
    transport = transports[0]
    require(hashlib.sha256(modules['CheckpointPhysicalCaptureTransport']['body'].encode()).hexdigest() ==
            original['transport_definition_sha256'], 'physical peer ABI/parameters')
    pins = [a for a in annotations if a['class'] == 'midas.checkpoint.NativeCheckpointWidgetPinAnnotation']
    require(sorted(pins, key=canonical) == sorted(
        [a for a in old_annotations if a['class'] == 'midas.checkpoint.NativeCheckpointWidgetPinAnnotation'], key=canonical),
        'changed endpoint markers')
    for name, digest in original['transport_sources'].items():
        sources = [a for a in annotations if a['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and a['name'] == name]
        require(len(sources) == 1 and hashlib.sha256(sources[0]['text'].encode()).hexdigest() == digest,
                'changed physical source '+name)

    def route(start, stop, casts=False):
        seen = []
        while True:
            require(start not in seen, 'peer alias cycle')
            seen.append(start)
            if start == stop:
                return seen
            require(start in host['drivers'], 'missing peer driver '+start)
            value = host['drivers'][start]
            cast = re.fullmatch(r'asUInt\(([\w.$]+)\)', value or '')
            if casts and cast:
                value = cast[1]
            require(re.fullmatch(r'[\w.$]+', value or '') is not None, 'non-alias peer driver')
            start = value

    require(route(transport+'.clock', 'clock') == doc['raw_clock_route'], 'changed raw clock route')
    require(route(transport+'.reset', 'reset', True) == doc['reset_route'], 'changed reset route')
    rows = []
    for pin in sorted(pins, key=lambda p: p['role']):
        role = pin['role']
        match = re.fullmatch(r'~FPGATop\|FPGATop>(\w+)', pin['target'])
        require(match is not None and role in PINS, 'foreign peer pin')
        _, width, source = PINS[role]
        name = match[1]
        physical = 'reset' if role == 'reset' else transport+'.'+PEERS[role]
        path = route(name, physical, role == 'reset') if source else route(physical, name)
        if not source:
            value = name
            seen = set()
            while value in host['drivers']:
                require(value not in seen, 'placeholder cycle')
                seen.add(value)
                value = host['drivers'][value]
            require(value == f'UInt<{width}>("h0")', 'changed zero placeholder')
        rows.append(dict(role=role, target=pin['target'], direction='from_transport' if source else 'to_transport',
                         physical_pin=physical, route=path))
    require(rows == doc['pins'] and len(rows) == 20, 'changed peer route receipt')
    return dict(pins=len(rows), route_hops=sum(len(r['route'])-1 for r in rows),
                physical_fpga_capture=False, transport_state_owner='unsupported_no_state_adapter')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--backend', choices=('f2', 'eda'), required=True)
    args = parser.parse_args()
    result = audit(args.before, args.generated)
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='peer-audit-', dir=args.out))
    rejections = []
    receipt = json.loads((args.generated/'peer-routing.json').read_text())
    for name, mutate in [
        ('capture-admission', lambda d: d.update(complete_fpga_capture=True)),
        ('owner-admission', lambda d: d.update(external_transport_state_owner='invented_adapter')),
        ('clock-route', lambda d: d['raw_clock_route'].append('reset')),
        ('dropped-pin', lambda d: d['pins'].pop()),
        ('route-swap', lambda d: d['pins'][0].update(route=d['pins'][1]['route'])),
        ('wrong-physical-pin', lambda d: d['pins'][0].update(physical_pin='invented.port')),
        ('stale-history', lambda d: d.update(inline_history_sha256='0'*64)),
    ]:
        case = out/name
        case.mkdir()
        for p in args.generated.iterdir():
            if p.is_file():
                (case/p.name).write_bytes(p.read_bytes())
        changed = copy.deepcopy(receipt)
        mutate(changed)
        (case/'peer-routing.json').write_text(canonical(changed))
        try:
            audit(args.before, case)
        except FormatError as error:
            rejections.append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('accepted peer receipt mutation '+name)
    inputs = {str(p): sha(p) for directory in (args.before, args.generated) for p in directory.iterdir() if p.is_file()}
    sources = {n: sha(n) for n in SOURCES+EXTRA}
    (out/'summary.json').write_text(json.dumps(dict(status='pass', backend=args.backend,
        observed_utc=datetime.now(timezone.utc).isoformat(), audit=result, inputs=inputs, sources=sources,
        rejected_corruptions=rejections), indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
