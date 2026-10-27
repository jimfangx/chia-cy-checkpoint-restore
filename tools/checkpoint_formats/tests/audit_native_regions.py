"""Independently audit a multi-region graft's hierarchy, clocks and ownership.

Structural component evidence only. No production owner or FPGA admission.
"""
import json
from pathlib import Path
import re
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha


def digest(doc):
    import hashlib
    return hashlib.sha256(canonical(doc)).hexdigest()


def audit(directory):
    directory = Path(directory)
    read = lambda n: json.loads((directory / n).read_text())
    old = parse_modules((directory / 'host.fir').read_text())
    merged = parse_modules((directory / 'instrumented.fir').read_text())
    new = parse_modules((directory / 'grafted.fir').read_text())
    binding, descriptor_binding, manifest, routing = map(read, ('binding.json', 'descriptor-binding.json', 'manifest.json', 'routing.json'))
    root = re.search(r'^circuit (\w+) :', (directory/'host.fir').read_text(), re.M)[1]
    require(binding['regions_version'] == 1 and binding['scope'] == 'existing_disjoint_native_executions_only' and
        binding['host_sha256'] == sha(directory/'host.fir') and binding['instrumented_sha256'] == sha(directory/'instrumented.fir') and
        binding['descriptor_manifest_sha256'] == digest(manifest) and binding['descriptor_binding_sha256'] == digest(descriptor_binding) and
        binding['routing_sha256'] == digest(routing), 'changed source/network/descriptor binding')
    for doc in (binding, descriptor_binding, manifest):
        require(all(doc[n] is False for n in ('complete_fpga_capture','deployable_capture_image','production_freeze_owners_bound','metasim_restore_supported')),
            'changed image admission')
    # Compare all selected logical storage against the original, independently
    # enumerated registers, memories and emitter-owned read pipeline words.
    original = inventory_from_firrtl((directory/'host.fir').read_text(), root)
    audit_routes(manifest,descriptor_binding,routing,original)
    by_id = {r['state_id']: r for r in original if r['adapter'] != 'metasim-bufgce-v1'}
    functional = [r for r in manifest['state'] if r['domain'] == 'functional']
    for row in functional:
        require(row['state_id'] in by_id and row['logical_state'] == by_id[row['state_id']], 'changed logical storage owner')
    uncovered = manifest['uncovered_functional_state']
    require({r['state_id'] for r in functional}.isdisjoint(r['state_id'] for r in uncovered) and
        sorted([r['logical_state'] for r in functional] + uncovered, key=lambda r:r['state_id']) == sorted(by_id.values(), key=lambda r:r['state_id']),
        'omitted or hidden functional owner')
    regions = binding['regions']
    require(len(regions) == len(routing['regions']) and [r['index'] for r in regions] == list(range(len(regions))), 'changed region order')
    selected, ancestors = {}, {}
    local_definitions = set(old)
    for region in regions:
        i = region['index']; prefix = f'checkpoint_inplace_region{i}_'
        require(region['sideband_prefix'] == prefix, 'changed namespace')
        pin = read(f'region-{i}-binding.json')
        target = re.fullmatch(r'~(\w+)\|([\w/>:]+)', region['target'])
        require(target and target[1] == root, 'unrooted concrete target')
        hops = target[2].split('/')
        require(hops[0] == root, 'changed enclosing root')
        parent = root
        for hop in hops[1:]:
            instance, child = hop.split(':')
            require(old[parent]['instances'].get(instance) == child, 'stale region execution')
            ancestors.setdefault(parent, []).append((i, instance, child))
            parent = child
        selected[parent] = i
        local = parse_modules((directory/f'region-{i}.fir').read_text())
        renames = {n:f'CheckpointRegion{i}_{n}' for n in local if n not in old}
        def rename(body):
            # Definitions and instance-module names are the only renamed text.
            return re.sub(r'(?m)^((?:extmodule|module) |  inst \w+ of )(' + '|'.join(map(re.escape,renames)) + r')(?=[ :\n]|$)',
                lambda m:m[1]+renames[m[2]], body) if renames else body
        for name, module in local.items():
            if name not in old or name == parent:
                emitted = renames.get(name,name)
                require(emitted in merged and merged[emitted]['body'] == rename(module['body']), 'changed banked definition '+emitted)
                local_definitions.add(emitted)
        require(pin['enclosing_raw_clock'] == binding['raw_clock'], 'different raw clock')
    require(set(merged) == local_definitions, 'unexpected or omitted definition')
    # Shared ancestors retain every original driver/effect. Only explicitly
    # namespaced sideband and raw access-clock connections may be added.
    for name, before in old.items():
        if name in selected:
            continue
        after = merged[name]
        if name not in ancestors:
            require(after == before, 'changed unrelated original definition '+name)
            continue
        require(after['instances'] == before['instances'], 'duplicated or relocated original execution')
        require(all(after['ports'].get(n) == p for n,p in before['ports'].items()), 'changed original port')
        require(all(after['drivers'].get(n) == v for n,v in before['drivers'].items()), 'changed original functional clock/driver')
        expected_ports, expected_drivers = dict(before['ports']), dict(before['drivers'])
        for i, instance, child in ancestors[name]:
            prefix=f'checkpoint_inplace_region{i}_'
            local = parse_modules((directory/f'region-{i}.fir').read_text())[name]
            for n,p in local['ports'].items():
                if n not in before['ports']:
                    require(n.startswith(prefix), 'non-namespaced addition')
                    expected_ports[n]=p
            for n,v in local['drivers'].items():
                if n not in before['drivers']:
                    require(n not in expected_drivers, 'duplicate sideband driver')
                    expected_drivers[n]=v
        require(after['ports'] == expected_ports and after['drivers'] == expected_drivers, 'crossed sideband/raw-clock connection')
        require([e[1:] for e in after['events']] == [e[1:] for e in before['events']], 'changed original sequential effects')
    # The single in-place adapter replaces ONLY the root's exposed sideband.
    graft = read('FireSim-generated.native-region-graft.json')
    adapter = root+'CheckpointRegionReadoutAdapter'; instance='checkpoint_region_readout_adapter'
    require(set(new) == set(merged)|{adapter}, 'extra transport or execution definition')
    require(all(new[n] == merged[n] for n in merged if n != root), 'graft changed native execution')
    access = {n:p for n,p in merged[root]['ports'].items() if n not in old[root]['ports']}
    require(new[root]['instances'] == merged[root]['instances']|{instance:adapter}, 'duplicate shared transport')
    require(not any(n in new[root]['ports'] for n in access), 'unconnected root sideband')
    extra={}
    for n,(direction,tpe) in access.items():
        require(new[adapter]['ports'][n] == ('output' if direction=='input' else 'input',tpe), 'reshaped/reversed adapter pin')
        if direction=='input': extra[n]=instance+'.'+n
        else: extra[instance+'.'+n]=n
    for n,(direction,tpe) in new[root]['ports'].items():
        if n.startswith('capture_'):
            extra[(instance+'.'+n) if direction=='input' else n] = n if direction=='input' else instance+'.'+n
    extra[instance+'.'+binding['raw_clock']]=binding['raw_clock']
    require(new[root]['drivers'] == merged[root]['drivers']|extra, 'changed root readout wiring or raw clock')
    require(graft['regions_binding_sha256'] == digest(binding) and graft['grafted_sha256'] == sha(directory/'grafted.fir') and
        graft['descriptor_manifest_sha256'] == digest(manifest) and graft['common_mask_and_sample_interface'] is True and
        all(graft[k] is False for k in ('complete_fpga_capture','deployable_capture_image','production_freeze_owners_bound','metasim_restore_supported')),
        'changed graft scope/binding')
    for suffix,value in graft['files'].items():
        require(sha(directory/('FireSim-generated'+suffix)) == value, 'changed compiled readout file')
    rtl=(directory/'FireSim-generated.native-region-graft.sv').read_text()
    require(rtl.count('CheckpointRegionStateRouter #(')==1 and f'.clock({binding["raw_clock"]}), .reset(capture_reset)' in rtl, 'wrong raw transport')
    for i,allocation in enumerate(routing['regions']):
        ce=f'[{allocation["ce_base"]} +: {allocation["ce_count"]}]'
        for n in ('captured_ce','logical_ce'):
            require(f'.capture_{n}(capture_{n}{ce})' in rtl,'crossed regional CE order')
        require(rtl.count('.capture_clock_mask(capture_clock_mask)')==len(regions) and
            rtl.count('.capture_reset(capture_reset)')==len(regions) and
            rtl.count('.capture_read_enable(capture_read_enable)')==len(regions), 'unbound common mask/reset/read permission')
    annotations=audit_annotations(directory,root,old,merged)
    return dict(annotations=annotations,status='pass',scope='independent multi-region hierarchy/readout audit only',regions=len(regions),
        entries=len(manifest['state']),functional_entries=len(functional),uncovered_functional_entries=len(uncovered),
        shared_raw_clock=binding['raw_clock'],physical_fpga_capture=False)


def audit_annotations(directory, root, before, after):
    """Bounded, independent original-XDC projection for the directed fixture."""
    from tools.checkpoint_formats.tests.audit_native_inplace_annotations import XDC, NO_DEDUP, protocol_json, HEADER
    directory=Path(directory)
    source=json.loads((directory/'host-annotations.json').read_text())
    actual=json.loads((directory/'instrumented-annotations.json').read_text())
    grafted=json.loads((directory/'grafted-annotations.json').read_text())
    def executions(modules):
        result={}
        def walk(module,path):
            require(path not in result,'duplicated annotation execution');result[path]=module
            for i,m in modules[module]['instances'].items():walk(m,path+'.'+i)
        walk(root,root);return result
    old,new=executions(before),executions(after)
    def target(text):
        m=re.fullmatch(r'~(\w+)\|(\w+)((?:/\w+:\w+)*)>(\w+(?:\.\w+)?)',text)
        require(m and m[1]==root,'foreign/unsupported constraint target')
        return m[2],re.findall(r'/(\w+):(\w+)',m[3]),m[4]
    def annotation_key(a):
        if a['class']==NO_DEDUP:return 'NoCircuitDedupAnnotation'
        require(a['class'] in XDC,'unsupported directed annotation hash contract')
        destination=a['destinationFile']['class'].split('$')[-2]
        return a['class'].split('.')[-1]+'('+destination+','+a['formatString']+',List('+', '.join(a['argumentList'])+'))'
    import hashlib
    provenance=json.loads((directory/'binding.json').read_text())
    for label,annotations in [('host',source),('instrumented',actual)]:
        values={canonical(a):a for a in annotations}
        encoded=protocol_json(sorted(values.values(),key=annotation_key)).encode()
        require(provenance[label+'_annotations_sha256']==hashlib.sha256(encoded).hexdigest(), 'unbound original/projected annotations')
    expected=[]
    for a in source:
        if a['class']==NO_DEDUP:expected.append(a);continue
        require(a['class'] in XDC,'unsupported directed source annotation')
        args=list(map(target,a['argumentList']))
        require(args and len({a[0] for a in args})==1,'uncorrelated source constraint')
        module=args[0][0]
        paths=sorted(old) if before[module]['kind']=='extmodule' else list(old)
        for path in paths:
            if old[path]!=module:continue
            values=[]
            for _,hops,ref in args:
                current=path
                if before[module]['kind']=='extmodule':
                    value='~'+root+'|'+new[root];prefix=root
                    for instance in path.split('.')[1:]:
                        prefix+='.'+instance;value+='/'+instance+':'+new[prefix]
                else:value='~'+root+'|'+new[path]
                parent=module
                for i,child in hops:
                    require(before[parent]['instances'].get(i)==child,'stale original constraint hop')
                    current+='.'+i;value+='/'+i+':'+new[current];parent=child
                values.append(value+'>'+ref)
            expected.append(dict(a,argumentList=values))
    require(len(actual)==len({canonical(a) for a in actual}) and {canonical(a) for a in expected}=={canonical(a) for a in actual},
        'lost/duplicated/crossed original constraint')
    require(grafted==actual,'readout graft changed annotations')
    emitted={'Synthesis':[],'Implementation':[]}
    for a in expected:
        if a['class'] not in XDC:continue
        args=list(map(target,a['argumentList']));destination=a['destinationFile']['class'].split('$')[-2]
        for path,module in new.items():
            if module!=args[0][0]:continue
            prefix=('shell/CL/' if destination=='Implementation' else '')
            if path!=root:prefix+=path.split('.',1)[1].replace('.','/')+'/'
            vals=[prefix+'/'.join([i for i,_ in hops]+ref.split('.')) for _,hops,ref in args]
            pieces=a['formatString'].split('{}')
            emitted[destination].append(''.join(s+(vals[i] if i<len(vals) else '') for i,s in enumerate(pieces)))
    for name,lines in emitted.items():
        require((directory/('instrumented.'+name.lower()+'.xdc')).read_text()=='\n'.join([HEADER]+lines),
            'emitted constraint omitted or applied to wrong execution')
    return dict(source_annotations=len(source),projected_annotations=len(actual),xdc_lines=sum(map(len,emitted.values())))


def audit_routes(manifest, binding, routing, original):
    originals=[];allocations=[];physical_order=[];bank_base=ce_base=0
    physical_global={r['hierarchy'].removesuffix('.O')+'.CE_latch' for r in original if r['adapter']=='metasim-bufgce-v1'}
    for index,region in enumerate(binding['regions']):
        local=region['manifest'];scope=local['selected_scope']
        require(region['manifest_sha256']==digest(local) and region['binding_sha256']==digest(region['binding']) and
            region['binding']['manifest_sha256']==digest(local),'changed original local descriptor binding')
        rows=local['state'];functional=[r for r in rows if r['domain']=='functional'];physical=[r for r in rows if r['domain']=='physical_ce']
        require([r['ordinal'] for r in rows]==list(range(len(rows))) and
            [r['slot'] for r in physical]==list(range(len(physical))),'changed local descriptor order')
        banks=sorted({r['bank'] for r in functional})
        require(banks==list(range(len(banks))) and len(banks)>0,'sparse functional selector space')
        allocations.append(dict(index=index,bank_base=bank_base,bank_count=len(banks),ce_base=ce_base,ce_count=len(physical)))
        physical_order.append(dict(selected_scope=scope,base=ce_base,count=len(physical)))
        for row in rows:
            is_ce=row['domain']=='physical_ce'
            require(row['hierarchy'].startswith(scope+'.'),'row outside selected execution')
            expected=dict(row,region=index,local_bank=row['bank'],local_slot=row['slot'],local_ordinal=row['ordinal'])
            if is_ce:
                require(row['hierarchy'] in physical_global and row['state_id']==digest(dict(namespace='physical-bufgce-ce-latch-v1',hierarchy=row['hierarchy'])) and
                    row['bank']==255 and row['width']==row['depth']==1 and row['ce_bit']==row['slot'],'changed physical owner')
                expected.update(slot=row['slot']+ce_base,local_ce_bit=row['ce_bit'],ce_bit=row['ce_bit']+ce_base)
            else:expected['bank']+=bank_base
            originals.append(expected)
        bank_base+=len(banks);ce_base+=len(physical)
    expected=[dict(r,ordinal=i) for i,r in enumerate([r for r in originals if r['domain']=='functional']+[r for r in originals if r['domain']=='physical_ce'])]
    require(manifest['state']==expected and routing['regions']==allocations and manifest['physical_ce_order']==physical_order,
        'changed global/local selectors, ordinals or CE bits')
    require(len({r['state_id'] for r in expected})==len(expected) and len({(r['bank'],r['slot']) for r in expected})==len(expected),'duplicate state/selector')
    selected={r['hierarchy'] for r in expected if r['domain']=='physical_ce'}
    require({r['logical_latch_hierarchy'] for r in manifest['uncovered_physical_gates']}==physical_global-selected,'hidden physical owner')
