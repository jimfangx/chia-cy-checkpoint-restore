"""Audit local capture permission in the actual emitted, occupied wrapper.

These are directed component transactions, not FPGA checkpoints or CPU cuts.
The enclosing verifier binds native synthesis and fresh EDA VCS to all inputs.
"""
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.tests.audit_live_readout_capture_wave import audit as audit_capture

TB = 'tools/checkpoint_formats/tests/live_readout_permission_tb.sv'
SELF = 'tools/checkpoint_formats/tests/verify_live_readout_permission.py'


def rows(path, targets):
    codes, values, scopes = {}, {}, []
    def sample():
        require(codes.keys() == targets.keys(), 'missing permission/staging raw fields')
        return {n: int(values[c], 2) if re.fullmatch('[01]+', values.get(c, 'x')) else None
                for n, c in codes.items()}
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == '$scope': scopes.append(parts[2])
        elif parts[0] == '$upscope': scopes.pop()
        elif parts[0] == '$var':
            name = '.'.join(scopes + [parts[4].lstrip('\\')])
            for role, target in targets.items():
                if name == target: codes[role] = parts[3]
        elif line.startswith('#'): yield sample()
        elif line[0] in 'bB' and len(parts) == 2: values[parts[1]] = parts[0][1:].lower()
        elif line[0] in '01xXzZ': values[line[1:].strip()] = line[0].lower()
    yield sample()


def audit(path, bits, *, stage_bit=None, failed=False):
    top = 'live_readout_permission_tb.'
    names = ('clock', 'bank_reset', 'snapshot_reset', 'capture_hold', 'permission', 'borrow_enable',
             'failed', 'stage_valid', 'staging_state', 'value', 'target_cycle',
             'request_valid', 'request_ready', 'response_valid', 'response_ready')
    targets = {n: top+n for n in names}
    owner = top+'dut.shell.checkpoint_shell_live_snapshot_adapter.'
    targets.update({n: owner+n for n in ('payload', 'occupied', 'cut_cycle', 'error')})
    held = accepted = acknowledged = 0
    first_fault = None
    previous = None
    for now in rows(path, targets):
        if now['snapshot_reset'] == 0:
            require(all(v is not None for v in now.values()), 'unknown initialized staging owner')
            packed = (now['payload'] | now['occupied'] << bits | now['cut_cycle'] << (bits+1) |
                      now['error'] << (bits+65))
            observed = now['staging_state'] ^ (0 if stage_bit is None else 1 << stage_bit)
            require(observed == packed, 'omitted original staging/control register bit')
            require(now['permission'] == (now['borrow_enable'] and not now['capture_hold']),
                    'permission withdrawal is not the source-bound combinational mask')
            # The test withdraws request/release after their accepting edge.
            # NBA occupancy can briefly flag a duplicate until that stimulus
            # settles; it is never sampled into the owner's sticky errors.
            # Record settled low-phase faults, before the next possible edge.
            if now['failed'] and now['clock'] == 0 and first_fault is None:
                first_fault = dict(target_cycle=now['target_cycle'], acknowledged=acknowledged,
                                   value=now['value'])
            if first_fault:
                require(not now['request_ready'] and not now['response_valid'] and
                        now['value'] == first_fault['value'], 'fault acknowledged or advanced functional state')
            if previous and previous['clock'] == 0 and now['clock'] == 1:
                p = previous
                if p['capture_hold'] and not p['failed'] and not now['failed']:
                    require(p['staging_state'] == now['staging_state'] and p['value'] == now['value'] and
                            p['borrow_enable'] == now['borrow_enable'] == 1,
                            'local capture released/faulted/changed the occupied staging owner')
                    held += 1
                if p['request_valid'] and p['request_ready']:
                    require(not p['capture_hold'] and p['permission'] and p['borrow_enable'],
                            'request accepted outside staged permission')
                    accepted += 1
                if p['response_valid'] and p['response_ready']:
                    require(first_fault is None and not p['capture_hold'] and p['permission'],
                            'response acknowledged after permission withdrawal or fault')
                    acknowledged += 1
        previous = now
    require(held >= 9 and bool(first_fault) == failed, 'incomplete occupied-staging capture/fault')
    return dict(staging_bits=bits+71, raw_staging_registers=4, held_edges=held,
                accepted=accepted, acknowledged=acknowledged, first_fault=first_fault)


def geometry(out):
    """Emit selectors from the actual source-bound descriptor mapping."""
    binding = json.loads((out/'generated/binding.json').read_text())
    mapping = json.loads((out/'permission-mapping.json').read_text())
    count = next(r for r in mapping['state'] if r['hierarchy'] == 'LiveTop.shell.count')
    memory = next(r for r in mapping['state'] if r['hierarchy'] == 'LiveTop.shell.mem')
    require(binding['entry']['bank'] == max(r['bank'] for r in mapping['state'])+1,
            'permission selectors differ from emitted descriptor table')
    require(binding['local_readout_capture_permission_withdrawal'] ==
            'capture_hold_masks_local_permission_preserving_staging_owner' and
            binding['local_readout_capture_permission_extra_storage_bits'] == 0 and
            binding['global_capture_permission_owner_bound'] is False,
            'unproven permission/epoch admission')
    values = dict(BITS=binding['payload_bits'], WORDS=binding['entry']['depth'],
                  SNAPSHOT_BANK=binding['entry']['bank'], COUNT_BANK=count['bank'], COUNT_SLOT=count['slot'],
                  MEM_BANK=memory['bank'], MEM_SLOT=memory['slot'])
    (out/'permission-geometry.svh').write_text(''.join(
        f'localparam integer {n} = {v};\n' for n,v in values.items()))
    return values


def audit_missing_mask(path):
    top = 'live_readout_permission_tb.'
    names = ('clock','capture_hold','borrow_enable','permission','request_valid','request_ready',
             'response_valid','response_ready','value','target_cycle')
    first = None
    previous = None
    for now in rows(path, {n:top+n for n in names}):
        if now['capture_hold'] == now['borrow_enable'] == now['permission'] == 1 and first is None:
            first = dict(component_cut=now['target_cycle'],value=now['value'])
        if first:
            require(now['value'] == first['value'] and now['target_cycle'] == first['component_cut'],
                    'compiled missing-mask execution advanced past first divergent observation')
        if previous and previous['clock'] == 0 and now['clock'] == 1:
            require(not (previous['request_valid'] and previous['request_ready']) and
                    not (previous['response_valid'] and previous['response_ready']),
                    'compiled missing-mask execution acknowledged a bank edge')
            require(first is None, 'compiled missing-mask execution acknowledged the divergent raw edge')
        previous = now
    require(first is not None, 'missing independent compiled-mask divergence')
    return dict(first_divergence=first,accepted=0,acknowledged=0,raw_edges_after_divergence=0)


def verify(out, run, common, retained):
    geometry_values = geometry(out)
    audits, corrupt_audits = [], []
    for paired in (False, True):
        tag = 'paired' if paired else 'capture-only'
        generated = out/('generated-restore' if paired else 'generated')/'wired.sv'
        simv = out/('permission-'+tag+'-simv')
        flags = ['+define+READOUT_PAIRED'] if paired else []
        compile_args = common+flags+['-top', 'live_readout_permission_tb', '+incdir+'+str(out),
            '-Mdir='+str(out/('permission-'+tag+'-csrc')), '-o', simv, generated,
            out/'sources'/retained.RTL, out/'sources'/retained.BANK, out/'sources'/retained.SNAPSHOT,
            out/'sources'/TB, out/'sources'/retained.EXIT]
        run(compile_args, 'permission-'+tag+'-compile')
        for case, cut in [('healthy', n) for n in (0,17,128,256)] + [
                (n,17) for n in ('request','response','release','drift','owner','freeze')]:
            name = f'permission-{tag}-{case}-{cut}'
            text = run([simv, '-no_save', '+CASE='+case, '+CUT='+str(cut)], name)
            require(('LIVE_PERMISSION_PASS ' if case == 'healthy' else
                     'LIVE_PERMISSION_NEGATIVE_PASS scenario='+case+' ') in text,
                    'occupied-wrapper permission execution incomplete')
            wave = out/(name+'.vcd')
            shutil.move(out/'live-readout-permission.vcd', wave)
            capture = audit_capture(wave, top='live_readout_permission_tb.',
                                    owner='dut.checkpoint_live_readout_adapter.')
            stage = audit(wave, geometry_values['BITS'], failed=case in ('release','drift','owner','freeze'))
            require(capture['acknowledgements'] == stage['acknowledged'], 'independent edge audits disagree')
            if case == 'healthy':
                require(stage['accepted'] == stage['acknowledged'] == geometry_values['WORDS']+5,
                        'incomplete continued snapshot/original/memory transactions')
            audits.append(dict(profile=tag, case=case, component_cut=cut, path=str(wave),
                               capture=capture, staging=stage))
        # Compile the actual emitted circuit with its mask removed. The first
        # held read must reject before any bank admission or response edge.
        source = generated.read_text()
        pattern = (r'(assign checkpoint_live_readout_adapter_permission = )'
                   r'checkpoint_shell_live_snapshot_borrow_enable\s*&\s*~\s*checkpoint_live_readout_capture_hold;')
        corrupt, count = re.subn(pattern, r'\1checkpoint_shell_live_snapshot_borrow_enable;', source)
        require(count == 1, 'ambiguous emitted permission-withdrawal mutation')
        broken = out/('permission-'+tag+'-corrupt.sv');broken.write_text(corrupt)
        bad_args = [broken if a == generated else a for a in compile_args]
        bad_args = [str(a).replace('permission-'+tag+'-csrc', 'permission-'+tag+'-corrupt-csrc')
                    .replace('permission-'+tag+'-simv', 'permission-'+tag+'-corrupt-simv') for a in bad_args]
        run(bad_args, 'permission-'+tag+'-corrupt-compile')
        text = run([out/('permission-'+tag+'-corrupt-simv'), '-no_save'],
                   'permission-'+tag+'-corrupt-run', expected=1)
        require('LIVE_PERMISSION_DIVERGENCE signal=local-revocation-preserves-staging-permission ' in text
                and 'captures=0 accepted=0 ack=0 ' in text, 'missing-mask fault missed first capture')
        wave = out/('permission-'+tag+'-corrupt.vcd')
        shutil.move(out/'live-readout-permission.vcd', wave)
        corrupt_audits.append(dict(profile=tag,path=str(wave),**audit_missing_mask(wave)))
    mutations = []
    healthy = next(a for a in audits if a['case'] == 'healthy')
    for bit in range(geometry_values['BITS']+71):
        try: audit(Path(healthy['path']), geometry_values['BITS'], stage_bit=bit)
        except FormatError as error: mutations.append(dict(bit=bit, error=str(error)))
        else: raise FormatError('permission audit omitted staging bit '+str(bit))
    return dict(scope='local permission withdrawal; no global cut or production transport attachment',
                geometry=geometry_values, audits=audits, staging_bit_mutations=mutations,
                compiled_missing_mask_rejections=2, compiled_corrupt_audits=corrupt_audits,
                physical_fpga_capture=False)
