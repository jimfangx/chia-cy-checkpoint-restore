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
    shells = binding.get('local_shells', [])
    require(len(regions) + len(shells) == len(routing['regions']) and
        [r['index'] for r in regions + shells] == list(range(len(regions) + len(shells))), 'changed region order')
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
    local_bases = {}
    for index, shell in enumerate(shells):
        local = parse_modules((directory/f'shell-{index}-generated.fir').read_text())
        reference = (directory/f'shell-{index}-reference.fir').read_text()
        selected_name = re.search(r'^circuit (\w+) :', reference, re.M)[1]
        pin = read(f'shell-{index}-binding.json')
        mapping = read(f'shell-{index}-mapping.json')
        require(pin['host_sha256'] == sha(directory/'host.fir') and pin['reference_sha256'] == sha(directory/f'shell-{index}-reference.fir') and
            pin['instrumented_sha256'] == sha(directory/f'shell-{index}-generated.fir') and
            pin['mapping_sha256'] == digest(mapping) and pin['banks_binding_sha256'] == sha(directory/f'shell-{index}-banks.json') and
            digest(pin) == shell['shell_binding_sha256'], 'changed local shell source/bank binding')
        require(pin['sideband_prefix'] == shell['sideband_prefix'] == f'checkpoint_shell_region{index}_' and
            pin['selected_execution'] == mapping['selected_execution'] and pin['child_executions_frozen'] is False and
            pin['transport_state_supported'] is False, 'changed local-only scope')
        require(all(pin[k] is False for k in ('complete_fpga_capture','deployable_capture_image',
            'production_freeze_owners_bound','metasim_restore_supported')), 'changed shell admission')
        prefix = mapping['selected_execution'] + '.'
        expected = [r for r in original if r['hierarchy'].startswith(prefix) and
            '.' not in r['hierarchy'][len(prefix):]]
        rows = mapping['state']
        require({r['state_id'] for r in rows} == {r['state_id'] for r in expected} and len(rows) == len(expected),
            'omitted/aliased original local owner')
        require(all(r['kind'] == 'register' for r in expected), 'directed mixed fixture expects local registers')
        endpoint=descriptor_binding['regions'][len(regions)+index]
        require(endpoint['binding']['shell_binding_sha256']==digest(pin) and
            endpoint['binding']['raw_clock']==binding['raw_clock'] and
            endpoint['manifest']['scope']=='selected_shell_global_identities_only' and
            endpoint['manifest']['ownership_scope']=='local_storage_only' and
            shell['identity_binding_sha256']==digest(endpoint['binding']), 'changed local descriptor/source identity')
        require(len(endpoint['manifest']['state'])==len(rows), 'incomplete local descriptor mapping')
        for row in rows:
            logical = by_id[row['state_id']]
            name = logical['hierarchy'].rsplit('.', 1)[1]
            require(row['hierarchy'] == row['storage_hierarchy'] == logical['hierarchy'] and
                row['width'] == row['transfer_width'] == logical['width'] == 64 and
                row['depth'] == row['transfer_depth'] == logical['depth'] == 1, 'changed local word/pipeline shape')
            descriptors=[r for r in endpoint['manifest']['state'] if r['state_id']==row['state_id']]
            require(len(descriptors)==1 and all(descriptors[0][k]==row[k] for k in
                ('hierarchy','storage_hierarchy','bank','slot')) and
                descriptors[0]['width']==row['transfer_width'] and descriptors[0]['depth']==row['transfer_depth'],
                'crossed local selector/storage mapping')
            require(local[selected_name]['drivers'][name] ==
                f'mux({shell["sideband_prefix"]}ckpt_freeze, {name}, mux(UInt<1>("h0"), {name}, {old[selected_name]["drivers"][name]}))',
                'local register freeze equation changed')
        require(selected_name not in selected and selected_name not in local_bases, 'overlapping local/subtree body')
        local_bases[selected_name] = local[selected_name]
        require(local[selected_name]['instances'] == old[selected_name]['instances'], 'changed local child execution')
        for name, definition in local.items():
            if name == selected_name or definition == old[name]: continue
            # Shell ancestors add only their prefixed child connections.
            require(name not in selected, 'local owner lies inside a selected subtree')
            ancestors.setdefault(name, []).append(('shell', index, definition))
    require(set(merged) == local_definitions, 'unexpected or omitted definition')
    # Shared ancestors retain every original driver/effect. Only explicitly
    # namespaced sideband and raw access-clock connections may be added.
    for name, before in old.items():
        if name in selected:
            continue
        after = merged[name]
        before = local_bases.get(name, before)
        if name not in ancestors:
            require(after == before, 'changed unrelated original definition '+name)
            continue
        require(after['instances'] == before['instances'], 'duplicated or relocated original execution')
        require(all(after['ports'].get(n) == p for n,p in before['ports'].items()), 'changed original port')
        require(all(after['drivers'].get(n) == v for n,v in before['drivers'].items()), 'changed original functional clock/driver')
        expected_ports, expected_drivers = dict(before['ports']), dict(before['drivers'])
        for i, instance, child in ancestors.get(name, []):
            if i == 'shell':
                prefix=f'checkpoint_shell_region{instance}_'; local = child
            else:
                prefix=f'checkpoint_inplace_region{i}_'
                local = parse_modules((directory/f'region-{i}.fir').read_text())[name]
            original_module = old[name]
            for n,p in local['ports'].items():
                if n not in original_module['ports']:
                    require(n.startswith(prefix), 'non-namespaced addition')
                    expected_ports[n]=p
            for n,v in local['drivers'].items():
                if n not in original_module['drivers']:
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
    for i,allocation in enumerate(routing['regions'][:len(regions)]):
        ce=f'[{allocation["ce_base"]} +: {allocation["ce_count"]}]'
        for n in ('captured_ce','logical_ce'):
            require(f'.capture_{n}(capture_{n}{ce})' in rtl,'crossed regional CE order')
        require(rtl.count('.capture_clock_mask(capture_clock_mask)')==len(regions) and
            rtl.count('.capture_reset(capture_reset)')==len(regions) and
            rtl.count('.capture_read_enable(capture_read_enable)')==len(regions), 'unbound common mask/reset/read permission')
    for j, shell in enumerate(shells):
        i=len(regions)+j; prefix=shell['sideband_prefix']
        require(routing['regions'][i]['ce_count']==0, 'local shell claims CE ownership')
        signals=dict(ckpt_clock=binding['raw_clock'],ckpt_reset='capture_reset',ckpt_freeze='capture_clock_mask',
            ckpt_bank='region_bank',ckpt_slot='region_slot',ckpt_address='region_address',
            ckpt_req_valid=f'region_request_valid[{i}]',ckpt_resp_ready=f'region_response_ready[{i}]')
        signals.update({n:f'region_{suffix}[{i}]' for n,suffix in
            [('ckpt_req_ready','request_ready'),('ckpt_resp_valid','response_valid'),('ckpt_resp_error','response_error')]})
        signals['ckpt_resp_data']=f'region_response_data[{i*64} +: 64]'
        for n,wire in signals.items():
            direction=access[prefix+n][0]
            equation=f'assign {wire} = {prefix+n};' if direction=='output' else f'assign {prefix+n} = {wire};'
            require(equation in rtl, 'crossed/unfrozen local endpoint '+n)
    annotations=audit_annotations(directory,root,old,merged)
    return dict(annotations=annotations,status='pass',scope='independent multi-region hierarchy/readout audit only',regions=len(regions),
        local_shells=len(shells),entries=len(manifest['state']),functional_entries=len(functional),uncovered_functional_entries=len(uncovered),
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


def audit_local_negatives(directory, output):
    """Rehash corrupt evidence throughout its dependency graph before auditing.

    The directed mixed fixture must reject at source/owner/equation validation,
    rather than merely noticing an unchanged parent checksum.
    """
    import shutil
    from tools.checkpoint_formats.codec import FormatError
    directory,output=Path(directory),Path(output)
    results=[]
    cases=dict(omitted_owner='sparse functional selector space',
        selector='crossed local selector/storage mapping', freeze='local register freeze equation changed',
        mask='crossed/unfrozen local endpoint', clock='crossed/unfrozen local endpoint',
        payload='crossed/unfrozen local endpoint', admission='changed shell admission', order='changed region order')
    for case,diagnostic in cases.items():
        d=output/case;shutil.copytree(directory,d)
        read=lambda n:json.loads((d/n).read_text())
        write=lambda n,v:(d/n).write_bytes(canonical(v))
        binding,descriptors,manifest=map(read,('binding.json','descriptor-binding.json','manifest.json'))
        shell=read('shell-0-binding.json');mapping=read('shell-0-mapping.json')
        graft=read('FireSim-generated.native-region-graft.json')
        if case=='omitted_owner':
            manifest['state']=[r for r in manifest['state'] if r['hierarchy']!='NativeHost.host_ticks']
            for i,row in enumerate(manifest['state']):row['ordinal']=i
            # Retain an internally consistent router/descriptor sequence while
            # hiding the missing original owner from its deficit inventory.
            endpoint=descriptors['regions'][2];endpoint['manifest']['state']=[]
        elif case=='selector':mapping['state'][0]['slot']+=1
        elif case=='freeze':
            prefix='checkpoint_shell_region0_'
            for name in ('shell-0-generated.fir','instrumented.fir','grafted.fir'):
                path=d/name;text=path.read_text();needle='mux('+prefix+'ckpt_freeze, host_ticks, '
                require(text.count(needle)==1,'ambiguous freeze fault')
                # Keep balanced FIRRTL while replacing the enable equation.
                path.write_text(text.replace(needle,'mux(UInt<1>("h0"), host_ticks, ',1))
        elif case in ('mask','clock','payload'):
            pin={'mask':'ckpt_freeze','clock':'ckpt_clock','payload':'ckpt_resp_data'}[case]
            path=d/'FireSim-generated.native-region-graft.sv';text=path.read_text()
            needle={'mask':'assign checkpoint_shell_region0_ckpt_freeze = capture_clock_mask;',
                'clock':'assign checkpoint_shell_region0_ckpt_clock = clock;',
                'payload':'assign region_response_data[128 +: 64] = checkpoint_shell_region0_ckpt_resp_data;'}[case]
            require(text.count(needle)==1,'ambiguous adapter fault '+pin)
            path.write_text(text.replace(needle,needle.replace(' = ',' = ~',1)))
        elif case=='admission':shell['complete_fpga_capture']=True
        else:binding['local_shells'].reverse()
        write('shell-0-mapping.json',mapping)
        shell.update(mapping_sha256=sha(d/'shell-0-mapping.json'),instrumented_sha256=sha(d/'shell-0-generated.fir'))
        write('shell-0-binding.json',shell)
        endpoint=descriptors['regions'][2];endpoint['binding']['shell_binding_sha256']=digest(shell)
        for endpoint in descriptors['regions']:
            endpoint['binding']['manifest_sha256']=digest(endpoint['manifest'])
            endpoint.update(manifest_sha256=digest(endpoint['manifest']),binding_sha256=digest(endpoint['binding']))
        for local in binding['local_shells']:
            index=int(re.search(r'region(\d+)_',local['sideband_prefix'])[1])
            local['shell_binding_sha256']=digest(read(f'shell-{index}-binding.json'))
            local['identity_binding_sha256']=descriptors['regions'][2+index]['binding_sha256']
        write('manifest.json',manifest)
        descriptors['manifest_sha256']=digest(manifest);write('descriptor-binding.json',descriptors)
        binding.update(instrumented_sha256=sha(d/'instrumented.fir'),descriptor_manifest_sha256=digest(manifest),
            descriptor_binding_sha256=digest(descriptors));write('binding.json',binding)
        graft.update(regions_binding_sha256=digest(binding),grafted_sha256=sha(d/'grafted.fir'),
            descriptor_manifest_sha256=digest(manifest))
        graft['files']={n:sha(d/('FireSim-generated'+n)) for n in graft['files']}
        write('FireSim-generated.native-region-graft.json',graft)
        try:audit(d)
        except FormatError as error:
            require(diagnostic in str(error),'wrong rehashed rejection '+case+': '+str(error))
            results.append(dict(case=case,status='rejected',diagnostic=str(error)))
        else:raise FormatError('accepted rehashed local corruption '+case)
    return results
