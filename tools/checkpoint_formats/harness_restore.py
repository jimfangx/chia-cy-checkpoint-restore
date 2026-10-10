"""Fresh, non-debug VCS harness bank staging; no dispatcher or .fsckpt load.

The audited top.sv has synchronous reset, two AXI latch phases, and a clock
generator. Only post-startup, settled low-clock cuts are supported. Its initial
reset deassertion is harmless after loading reset=0. DEBUG waveform waiters,
gate-level startup, and changes to this audited source fail explicitly.
"""
import hashlib
import json
from pathlib import Path
import re

from .codec import HASH, bit_value, canonical, keys, natural, require
from .replay import IDENT

AUDITED_TOP = 'ff1a76a3bf251037e9add817ec7f5477ad4fdd6bd5c3bcbbfdbabfe66c0120e8'


def harness_layout(top, constants, defines, generated_build_hash, root='emul'):
    require(hashlib.sha256(top.encode()).hexdigest() == AUDITED_TOP,
            'unsupported harness source revision')
    require(type(generated_build_hash) is str and HASH.fullmatch(generated_build_hash),
            'invalid generated build hash')
    require(type(root) is str and all(re.fullmatch(IDENT, p) for p in root.split('.')),
            'invalid harness root')
    require(not re.search(r'`define\s+(?:DEBUG|FSDB|GATE_LEVEL_SIM)\b', constants + defines),
            'unsupported debug/gate-level harness')
    macros = dict(re.findall(r'^`define\s+(\w+_BITS)\s+(\d+)\s*$', constants, re.M))
    width = lambda bits: bits if bits else 2
    widths = {}
    for name in ('CTRL', 'MEM', 'CPU_MANAGED_AXI4', 'FPGA_MANAGED_AXI4'):
        values = [int(macros.get(name+'_'+part+'_BITS', '0')) for part in ('ADDR', 'DATA', 'ID')]
        require(all(0 <= v <= 4096 for v in values), 'unsupported AXI geometry')
        if name in ('CTRL', 'MEM') or re.search(r'`define\s+'+name+'_PRESENT\b', constants + defines):
            require(all(v > 0 for v in values) and values[1] % 8 == 0,
                    'incomplete AXI geometry')
        else:
            require(values == [0, 0, 0], 'unsupported absent AXI geometry')
        addr, data, ident = values
        # In the unchanged top.sv, absent [-1:0] members are two bits wide.
        widths[name.lower()+'_fwd_t'] = 10 + 2*width(ident) + width(data)
        widths[name.lower()+'_rev_t'] = (28 + 2*width(addr) + 2*width(ident)
                                       + width(data//8) + width(data))
    qsfp = int(macros.get('QSFP_DATA_BITS', '0'))
    require(0 <= qsfp <= 4096, 'unsupported QSFP geometry')
    widths['qsfp_fwd_t'] = widths['qsfp_rev_t'] = 64 + (qsfp if qsfp else 2)
    body = re.search(r'typedef struct packed \{\n  bit \[63:0\] trace_count;(.*?)\} harness_banks_t;', top, re.S)
    require(body is not None, 'missing harness bank inventory')
    banks = re.findall(r'\b(\w+_t)\s+(\w+);', body[1])
    require(len(banks) == 27 and len({name for _, name in banks}) == 27,
            'incomplete harness bank inventory')
    rows = [dict(owner=root+'.'+name, width=widths[kind]) for kind, name in banks]
    rows += [dict(owner=root+'.reset', width=1), dict(owner=root+'.fin', width=1)]
    layout = dict(schema='firesim.component.harness-banks.v1', root=root,
                  generated_build_hash=generated_build_hash,
                  source_hash=hashlib.sha256(canonical(dict(top=top, constants=constants, defines=defines))).hexdigest(),
                  sample_phase='settled_host_negedge', records=rows)
    return layout


def harness_capture(layout, values, host_sample):
    natural(host_sample)
    require(type(values) is list and len(values) == len(layout['records']),
            'incomplete harness capture')
    capture = dict(schema=layout['schema'], layout_sha256=hashlib.sha256(canonical(layout)).hexdigest(),
                   sample_phase=layout['sample_phase'], host_sample=host_sample,
                   records=[dict(**row, value=value) for row, value in zip(layout['records'], values)])
    validate_harness_capture(layout, capture)
    return capture


def validate_harness_capture(layout, capture):
    keys(capture, {'schema', 'layout_sha256', 'sample_phase', 'host_sample', 'records'})
    require(capture['schema'] == layout['schema'] and capture['layout_sha256'] == hashlib.sha256(canonical(layout)).hexdigest()
            and capture['sample_phase'] == 'settled_host_negedge', 'incompatible harness cut')
    natural(capture['host_sample'])
    require(type(capture['records']) is list and len(capture['records']) == len(layout['records']),
            'incomplete harness capture')
    for expected, record in zip(layout['records'], capture['records']):
        keys(record, {'owner', 'width', 'value'})
        require(record['owner'] == expected['owner'] and type(record['width']) is int
                and record['width'] == expected['width'], 'changed harness membership/order/shape')
        bit_value(record)
        if record['owner'] in (layout['root']+'.reset', layout['root']+'.fin'):
            require(int(record['value'], 16) == 0, 'unsupported reset/finished harness cut')


def prepare_harness_loader(layout, out):
    out = Path(out)
    digest = hashlib.sha256(canonical(layout)).hexdigest()
    source = (f'static const char *manifest_hash = {json.dumps(digest)};\n'
              f'static const char *build_hash = {json.dumps(layout["source_hash"])};\n'
              f'static const char *clock_path = {json.dumps(layout["root"]+".clock")};\n'
              'static const Entry entries[] = {\n' + ',\n'.join(
                  '{%s, %d, 1, false, %s}' % (json.dumps(row['owner']), row['width'],
                      str(row['owner'] in (layout['root']+'.reset', layout['root']+'.fin')).lower())
                  for row in layout['records']) + '\n};\n'
              f'static const char *clock_paths[] = {{{json.dumps(layout["root"]+".clock")}}};\n')
    source += ('static const char *unsupported_paths[] = {' +
               json.dumps(layout['root']+'.trace_count') + ', "glbl.GSR"};\n')
    out.mkdir(parents=True, exist_ok=True)
    (out/'harness-restore-table.h').write_text(source)


def prepare_harness_restore(layout, capture, destination):
    Path(destination).write_text(harness_restore_text(layout, capture))
    return len(capture['records'])


def harness_restore_text(layout, capture):
    """Validate and render a component without publishing any staging file."""
    validate_harness_capture(layout, capture)
    rows = [f'FSHRNS1 {capture["layout_sha256"]} {layout["source_hash"]} settled_host_negedge {len(layout["records"])}']
    rows.extend(f'{r["owner"]} {r["width"]} {r["value"]}' for r in capture['records'])
    return '\n'.join(rows)+'\n'
