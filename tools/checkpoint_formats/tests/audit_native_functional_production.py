"""Independently audit complete native functional-bank output from a real recipe.

Readout netlists are not production cut/transport integration or FPGA capture.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import digest, sha, FLAGS


def audit(directory, prefix='FireSim-generated'):
    directory=Path(directory)
    path=lambda name:directory/(prefix+'.native-functional'+name)
    read=lambda name:json.loads(path(name).read_text())
    emission=read('-emission.json')
    require(emission==dict(binding_version=2,scope='native_functional_readout_companion_only',
        inputs=emission['inputs'],**FLAGS),'native emission scope/admission changed')
    expected_suffixes=['-reference.fir','-reference.anno.json','-context.anno.json','-context.json','-simulator-state.json','-plan.json','-dependencies.json',
        '-inventory.json','-instrumented.fir','-binding.json','.sv','.synthesis.xdc','.implementation.xdc']
    require(set(emission['inputs'])=={'.native-functional'+s for s in expected_suffixes},'incomplete native emission files')
    for suffix in expected_suffixes:
        require(sha(path(suffix))==emission['inputs']['.native-functional'+suffix], 'native emission input changed '+suffix)
    dependency_result=audit_dependencies(path('-reference.fir'),path('-simulator-state.json'),path('-plan.json'),
        path('-dependencies.json'))
    manifest, inventory, binding, plan=map(read,('-simulator-state.json','-inventory.json','-binding.json','-plan.json'))
    expected=dict(manifest,manifest_type='fsckpt-native-functional-companion',
        state=[r for r in manifest['state'] if r['adapter']!='metasim-bufgce-v1'],
        complete_fpga_capture=False,deployable_capture_image=False)
    require(inventory==expected,'native inventory is not the complete concrete reference storage')
    require(binding['scope']=='native_functional_readout_companion_only' and
        all(binding.get(k) is v for k,v in FLAGS.items()), 'native bank admission changed')
    require(binding['reference_sha256']==manifest['reference_sha256']==sha(path('-reference.fir')) and
        binding['manifest_sha256']==digest(inventory) and binding['instrumented_sha256']==sha(path('-instrumented.fir')),
        'native reference/instrumented bindings changed')
    require(binding['access_clock']=='ckpt_clock' and
        binding['freeze_contract']=='externally_held_all_functional_owners_before_access_until_drain' and
        binding['functional_clock_domains']==plan['clock_domains'], 'native clock/freeze provenance changed')
    rows=inventory['state'];bound=binding['state']
    require(len(rows)==len(bound) and rows and [r['state_id'] for r in rows]==sorted(r['state_id'] for r in rows),
        'native state count/order mismatch')
    require(binding['access_version']==2 and binding['protocol']=='latched-banked64-chunked-v2',
        'wide native recipe requires chunked banks')
    modules=parse_modules(path('-instrumented.fir').read_text())
    storage={};native=[]

    def walk(name,hierarchy,ancestors=frozenset()):
        require(name not in ancestors,'recursive native bank hierarchy')
        m=modules[name]
        if m['kind']=='extmodule':
            require(m['body'].endswith('defname = BUFGCE'),'unmapped opaque bank owner')
            native.append(hierarchy);return
        for reg,width in re.findall(r'^  reg ([A-Za-z_][A-Za-z0-9_$]*) : (?:UInt|SInt)<(\d+)>,',m['body'],re.M):
            storage[hierarchy+'.'+reg]=(int(width),1)
        for memory,body in re.findall(r'^  mem ([A-Za-z_][A-Za-z0-9_$]*) :[^\n]*\n((?:    [^\n]*\n?)*)',m['body'],re.M):
            width=re.search(r'\bdata-type => (?:UInt|SInt)<(\d+)>',body)
            depth=re.search(r'\bdepth => (\d+)',body)
            require(width and depth,'unresolved native memory shape')
            storage[hierarchy+'.'+memory]=(int(width[1]),int(depth[1]))
        for instance,child in m['instances'].items():
            walk(child,hierarchy+'.'+instance,ancestors|{name})
    walk(inventory['root_module'],inventory['root_module'])
    require(sorted(native)==binding['native_clock_gate_paths']==[g['hierarchy'] for g in plan['physical_gates']],
        'native primitive ownership changed')
    selectors=set();actual_storage=set();total_words=0
    for row,access in zip(rows,bound):
        require(all(row[k]==access[k] for k in ('state_id','hierarchy','width','depth')),
            'native state omitted/reordered/reshaped')
        require(row['state_id']==digest(dict(namespace='generated-simulator-state-v1',
            hierarchy=row['hierarchy'],kind=row['kind'])),'native state identity changed')
        require(storage.get(access['storage_hierarchy'])==(row['width'],row['depth']),
            'native emitted storage missing or reshaped '+row['hierarchy'])
        selector=(access['bank'],access['slot'])
        require(selector not in selectors and access['bank']!=255,'native selector alias/reservation')
        selectors.add(selector);actual_storage.add(access['storage_hierarchy'])
        chunks=(row['width']+63)//64;words=row['depth']*chunks
        require(access['chunks']==chunks and access['transfer_width']==min(64,row['width']) and
            access['transfer_depth']==words,'native flattened word mapping changed')
        total_words+=words
    require(len(actual_storage)==len(bound),'native storage path alias')
    endpoint={inventory['root_module']+'.'+n for n in ('ckpt_pending','ckpt_saved_data','ckpt_saved_error')}
    require(set(storage)==actual_storage|endpoint,'native netlist has hidden/uninventoried storage')
    rtl=path('.sv').read_text()
    require('module BUFGCE' not in rtl and len(re.findall(r'\bBUFGCE [A-Za-z_][A-Za-z0-9_$]* \(',rtl))==len(native),
        'native primitive was substituted or omitted in emitted RTL')
    return dict(status='pass',scope='complete concrete FIRRTL storage readout companion, not complete CPU checkpoint',
        physical_fpga_capture=False,production_rocket_integrated=False,metasim_restore_supported=False,
        descriptors=len(bound),transfer_words=total_words,transfer_payload_bytes=total_words*8,
        native_clock_gates=native,concrete_state_owners=len(actual_storage),endpoint_state_owners=len(endpoint),
        original_directory=str(directory.resolve()),dependency_audit=dependency_result,
        artifacts={str(path(s).resolve()):sha(path(s)) for s in expected_suffixes+['-emission.json']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    require(args.out.resolve().is_relative_to(root/'automations/checkpoint_loop/runs'),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='audit-',dir=args.out.resolve()))
    result=audit(args.generated)
    result.update(observed_utc=datetime.now(timezone.utc).isoformat(),auditor_sha256=sha(__file__))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
