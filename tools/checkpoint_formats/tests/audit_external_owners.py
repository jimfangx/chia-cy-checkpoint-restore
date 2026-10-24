"""Independently reconstruct external-owner reachability from emitted FIRRTL.

This understands the emitter's diagnostic instance-connector syntax as well as
ordinary instances. It audits coverage; unsupported external owners stay
unsupported. It cannot establish physical primitive or source equivalence.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def audit(reference: Path, manifest: Path, report: Path):
    text=reference.read_text()
    inventory=json.loads(manifest.read_text())
    doc=json.loads(report.read_text())
    root=inventory['root_module']
    require(doc['audit_version']==1 and doc['scope']=='external_owner_admission_only' and
            doc['root_module']==root and doc['reference_sha256']==inventory['reference_sha256']==digest(text),
            'unbound external-owner reference')
    require(doc['complete_fpga_capture'] is False and doc['deployable_capture_image'] is False,
            'external audit cannot claim physical capture')
    headers=list(re.finditer(r'^  (extmodule|module) ([A-Za-z_][A-Za-z0-9_$]*) :[^\n]*',text,re.M))
    require(headers and len({h[2] for h in headers})==len(headers), 'duplicate/missing definition')
    modules={}
    for index,h in enumerate(headers):
        body=text[h.start():headers[index+1].start() if index+1<len(headers) else len(text)].rstrip('\n')
        body='\n'.join(line[2:] if line.startswith('  ') else line for line in body.splitlines())
        modules[h[2]]=(h[1],body)
    instances=[]; external={}; live=set(); paths=set()

    def walk(name,path,ancestors):
        require(name in modules and name not in ancestors, 'missing/recursive instance')
        kind,body=modules[name]
        require(path not in paths, 'duplicate instance path')
        paths.add(path)
        instances.append((path,name));live.add(name)
        if kind=='extmodule':
            external[path]=name
        else:
            for inst,child in re.findall(r'^\s+inst ([A-Za-z_][A-Za-z0-9_$]*) of ([A-Za-z_][A-Za-z0-9_$]*)(?:\s|$)',body,re.M):
                walk(child,path+'.'+inst,ancestors|{name})
    walk(root,root,set())
    require(sorted(instances)==sorted((i['hierarchy'],i['module']) for i in inventory['instances']),
            'incomplete independent instance inventory')
    rows=doc['reachable_external_instances']
    require([(r['hierarchy'],r['module']) for r in rows]==sorted(external.items()),
            'missing/reordered/duplicate external owner')

    def definition(row,name):
        kind,body=modules[name]
        defs=re.findall(r'^  defname = ([A-Za-z_][A-Za-z0-9_$]*)$',body,re.M)
        require(kind=='extmodule' and len(defs)==1 and row['defname']==defs[0] and
                row['definition_sha256']==digest(body), 'altered external definition')
        for inline in row['inline_sources']:
            require(set(inline)=={'circuit','filename','source_sha256'} and
                    inline['circuit']==inventory['circuit'] and isinstance(inline['filename'],str) and
                    re.fullmatch('[0-9a-f]{64}',inline['source_sha256']), 'malformed inline provenance')
        return defs[0]
    for row in rows:
        defname=definition(row,row['module'])
        require(row['physical_primitive'] is (defname=='BUFGCE') and
                row['requires_explicit_owner'] is True and row['physical_capture_binding']=='unsupported',
                'external audit cannot supply physical state adapter')
    unused=doc['unused_external_definitions']
    require([r['module'] for r in unused]==sorted(n for n,(k,_) in modules.items() if k=='extmodule' and n not in live),
            'missing/reordered/duplicate unused definition')
    for row in unused:definition(row,row['module'])
    return dict(status='pass',scope='independent external-owner coverage only',physical_fpga_capture=False,
                reference_sha256=digest(text),external_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                complete_instance_count=len(instances),reachable_external_count=len(rows),
                physical_primitive_instances=[r['hierarchy'] for r in rows if r['physical_primitive']],
                unused_external_count=len(unused))
