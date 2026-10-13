"""Independently check every production deposit against the semantic image.

Does not import the production translator. The independently audited map is
the authority for each full array and scalar relationship; saved request/PASS
labels do not establish its completeness. Values are checked in a streaming
walk, including every address of every actual captured memory.
"""

import argparse
import json
from pathlib import Path

from tools.checkpoint_formats.codec import canonical, decode, require
from tools.checkpoint_formats.finite_replay import ports_for
from tools.checkpoint_formats.formal_state_map import sha
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from .audit_production_state_map import audit_components, audit_map


def audit_spans(mapping, checkpoint, path):
    records = {r['state_id']: r for r in checkpoint['records']}
    expected = {}
    predicates = 0
    for entry in mapping['entries']:
        record = records[entry['state_id']]
        if entry['kind'] == 'memory':
            m = entry['mapping']
            name = '.'.join(['production_gate_tb','dut',*m['instance_components'],m['storage']])
            require(name not in expected, 'duplicate independently derived memory span')
            expected[name] = ('M',entry['width'],entry['depth'],record['values'])
        else:
            value = int(record['values'][0],16)
            for bit in entry['bits']:
                if bit['classification'] == 'preserved_predicate':
                    require((value >> bit['bit']) & 1 == bit['value'], 'independent checkpoint predicate mismatch')
                    predicates += 1
                elif bit['classification'] == 'mapped':
                    g = bit['gate']
                    name = '.'.join(['production_gate_tb','dut',*g['instance_components'],g['storage']])
                    require(name not in expected and g['bit'] == g['xor'] == 0, 'duplicate/unsupported independent scalar span')
                    expected[name] = ('R',1,1,[str((value >> bit['bit']) & 1)])
                else:
                    require(bit['classification'] == 'irrelevant','unproven independent checkpoint bit')
    seen, words, bits = set(), 0, 0
    with Path(path).open() as stream:
        require(stream.readline() == 'PRODUCTION_GATE_RESTORE_V1\n', 'independent span header mismatch')
        for line in stream:
            fields = line.split()
            if fields and fields[0] == 'END':
                require(line == f'END {words} {bits}\n' and not stream.read(1), 'independent span totals/trailing bytes mismatch')
                break
            require(len(fields) == 4 and fields[1] in expected and fields[1] not in seen, 'unknown/duplicate independent span')
            kind, name, width, depth = fields
            ek, ew, ed, values = expected[name]
            require((kind,width,depth) == (ek,str(ew),str(ed)), 'independent span shape mismatch')
            for address,value in enumerate(values):
                require(stream.readline() == value+'\n', 'independent deposited word mismatch: '+name+f'[{address}]')
            seen.add(name)
            words += ed
            bits += ew*ed
        else:
            require(False, 'missing independent span END')
    require(seen == set(expected) and predicates == mapping['predicate_bits'] and
            words == mapping['gate_storage_words'] and bits == mapping['gate_storage_bits'], 'incomplete independent production restore')
    return dict(status='passed', spans=len(seen), words=words, bits=bits, checkpoint_predicates=predicates,
                target_cycle=checkpoint['target_cycle'], complete_physical_inventory=True)


def audit(replay):
    replay = Path(replay).resolve()
    request = json.loads((replay/'request.json').read_text())
    require(request['production_gate_request_version'] == 1, 'unsupported production gate request')
    for name,digest in request['dependency_artifacts'].items():
        require(sha(Path(name).read_bytes()) == digest, 'changed production replay prerequisite: '+name)
    for name,digest in request['generated_artifacts'].items():
        require(sha((replay/name).read_bytes()) == digest, 'changed production replay artifact: '+name)
    mapping = json.loads(Path(request['map']).read_text())
    context = audit_components(mapping['proof_components']['original'],mapping['proof_components']['memory'])
    map_report = audit_map(context,request['map'])
    manifest = context['manifest']
    boundary = json.loads((Path(context['original']['architecture'])/'boundary.json').read_text())
    image = decode_semantic(Path(request['checkpoint']).read_bytes(),builds(manifest,boundary,request['configuration'])[0],manifest)
    report = audit_spans(mapping,image,replay/'restore.spans')
    trace = decode(Path(request['trace']).read_bytes(),'trace',builds(manifest,boundary,request['configuration'])[1])
    ports = ports_for(boundary)
    require(request['ports'] == ports and request['first_cycle'] == image['target_cycle'] == trace['target_cycle'] and
            request['end_cycle'] == image['target_cycle']+len(trace['records']) and request['samples'] == len(trace['records']) and
            request['output_comparisons'] == len(trace['records'])*sum(p['direction']=='output' for p in ports) and
            request['gate_storage_words'] == report['words'] and request['gate_storage_bits'] == report['bits'] and
            request['storage_spans'] == report['spans'] and request['predicate_bits'] == report['checkpoint_predicates'],
            'independent production request scope mismatch')
    with (replay/'trace.txt').open() as stream:
        for record in trace['records']:
            for direction in ('input','output'):
                require({n:v['width'] for n,v in record[direction+'s'].items()} ==
                        {p['name']:p['width'] for p in ports if p['direction']==direction}, 'independent production trace shape mismatch')
            expected = 'DATA '+str(record['cycle'])+' '+' '.join(record[p['direction']+'s'][p['name']]['value'] for p in ports)+'\n'
            require(stream.readline() == expected,'independent production trace row mismatch')
        require(not stream.read(1),'extra independent production trace rows')
    evidence = Path(context['memory']['synthesis_evidence'])
    require(request['sources'] == {k:str(evidence/v) for k,v in (('netlist','netlist-design.v'),('models','models.v'))},
            'unproven production compilation design')
    require(all(request['dependency_artifacts'].get(p)==h for p,h in mapping['dependency_artifacts'].items()),
            'missing production request CAD dependency')
    # Reproduction binds the harness to the current source as well as the
    # independently derived interval, boundary and complete physical inventory.
    # Deposit verification above deliberately does not use this implementation.
    from tools.checkpoint_formats.production_gate_replay import bench
    require((replay/'tb.sv').read_text() == bench(mapping['top'],ports,request['first_cycle'],request['end_cycle'],report['words'],report['bits']),
            'changed production replay harness')
    report.update(map_audit=map_report, replay=str(replay), request_sha256=sha((replay/'request.json').read_bytes()))
    report['trace_samples'] = len(trace['records'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    report = audit(args.replay)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(canonical(report))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
