"""Fresh complete production VCS replay and atomic loader rejection checks.

Source both repository environments and vcs-env.sh LAST. This accepts only the
actual completed FCFS metasim sample, never the small formal-map fixtures.
The ordinary replay argument must be a separately completed fresh RTL replay.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, decode, require
from tools.checkpoint_formats.production_gate_replay import validate_checkpoint
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from .audit_production_gate_restore import audit, audit_spans
from .verify_production_dut import CONFIGURATION, file_sha
from .verify_formal_state_map import ROOT


def invalid_spans(data):
    headers = list(re.finditer(rb'(?m)^([RM]) (\S+) (\d+) (\d+)\n',data))
    regs = [h for h in headers if h[1] == b'R']
    mem = next(h for h in headers if h[1] == b'M')
    first, second = regs[:2]
    def replace(match, value):
        return data[:match.start()]+value+data[match.end():]
    tail = data.index(b'END ',headers[-1].end())
    padding = next(h for h in reversed(headers) if int(h[3])%4)
    return {
        'unknown_scalar': replace(first,b'R production_gate_tb.dut.absent.state 1 1\n'),
        'scalar_shape': replace(first,b'R '+first[2]+b' 2 1\n'),
        'duplicate_scalar': replace(second,b'R '+first[2]+b' 1 1\n'),
        'memory_shape': replace(mem,b'M '+mem[2]+b' '+mem[3]+b' '+str(int(mem[4])+1).encode()+b'\n'),
        'unknown_last_word': data[:tail-2]+b'z'+data[tail-1:],
        'nonzero_padding': data[:padding.end()]+b'f'+data[padding.end()+1:],
        'missing_span': data[:headers[-1].start()]+data[tail:],
        'missing_end': data[:tail],
        'extra_data': data+b'00\n',
    }


def complement_file(source, destination):
    """Every word differs from the attempted restore, detecting any partial write."""
    with Path(source).open() as incoming, Path(destination).open('w') as outgoing:
        outgoing.write(incoming.readline())
        for line in incoming:
            f = line.split()
            if f[0] == 'END':
                outgoing.write(line)
                break
            outgoing.write(line)
            width, depth = int(f[2]), int(f[3])
            mask = (1 << width)-1
            for _ in range(depth):
                value = incoming.readline().strip()
                outgoing.write(format(int(value,16)^mask,f'0{(width+3)//4}x')+'\n')
        require(not incoming.read(1),'extra complement source bytes')


def compare_observations(request, gate_path, ordinary_path):
    """Compare observed gates, the ordinary-RTL checked rows and metasim oracle."""
    mapping = json.loads(Path(request['map']).read_text())
    binding = json.loads((Path(mapping['proof_components']['original'])/'binding.json').read_text())
    arch = Path(binding['architecture'])
    manifest, boundary = [json.loads((arch/n).read_text()) for n in ('manifest.json','boundary.json')]
    trace = decode(Path(request['trace']).read_bytes(),'trace',builds(manifest,boundary,request['configuration'])[1])
    ports = request['ports']
    with Path(gate_path).open() as gates, Path(ordinary_path).open() as rtl:
        for record in trace['records']:
            rows = [s.readline().split() for s in (gates,rtl)]
            for row in rows:
                require(len(row)==len(ports)+2 and row[:2]==['DATA',str(record['cycle'])], 'missing/extra production observation')
                for p,value in zip(ports,row[2:]):
                    require(re.fullmatch('[0-9a-f]+',value) is not None and
                            int(value,16)==int(record[p['direction']+'s'][p['name']]['value'],16),
                            'production observation mismatch '+str(record['cycle'])+' '+p['name'])
            require([int(x,16) for x in rows[0][2:]]==[int(x,16) for x in rows[1][2:]],'gate/ordinary observation differs')
        require(not gates.read(1) and not rtl.read(1),'extra production observations')
    return dict(samples=len(trace['records']), all_boundary_values=len(ports)*len(trace['records']),
                output_comparisons=sum(p['direction']=='output' for p in ports)*len(trace['records']))


def corruption_record(memory, address):
    require(memory['kind']=='memory' and memory['mapping']['classification']=='mapped_full_array' and
            memory['mapping']['storage']=='contents' and type(address) is int and 0 <= address < memory['depth'],
            'unsupported/out-of-range mapped corruption')
    return dict(cycle=524453,edges=0,signal='ep_axi4_ar_bits_qos',semantic_state_id=memory['state_id'],
                address=address,bit=0,path='.'.join(['production_gate_tb','dut',*memory['mapping']['instance_components'],
                                                 'contents'])+f'[{address}]',first_divergence=True)


def verify(replay, ordinary, out):
    replay, ordinary, out = [Path(p).resolve() for p in (replay,ordinary,out)]
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CC')=='/usr/bin/gcc-13' and os.environ.get('CXX')=='/usr/bin/g++-13',
            'source vcs-env.sh LAST before production gate verification')
    out.mkdir(parents=True,exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-',dir=out))
    request = json.loads((replay/'request.json').read_text())
    require(request['configuration']==CONFIGURATION and request['first_cycle']==524453 and request['samples']==250185 and
            request['gate_storage_words']==13509222 and request['gate_storage_bits']==102992412 and request['predicate_bits']==130,
            'production acceptance requires the complete actual metasim DUT/sample')
    report = audit(replay)
    (run/'restore-audit.json').write_bytes(canonical(report))
    print('COMPLETE_PRODUCTION_RESTORE_AUDIT_PASS',flush=True)
    commands = []
    env = dict(os.environ,TMPDIR=str(run))
    def tool(argv,name,expected=0):
        log = run/(name+'.log')
        cmd = dict(cwd=str(run.relative_to(ROOT)),argv=[str(a) for a in argv],log=str(log),expected_exit=expected)
        commands.append(cmd)
        (run/'commands.json').write_bytes(canonical(commands))
        with log.open('w') as stream:
            result = subprocess.run(cmd['argv'],cwd=run,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=3600)
        cmd['exit_code'] = result.returncode
        (run/'commands.json').write_bytes(canonical(commands))
        require(result.returncode==expected,'unexpected production VCS exit: '+str(log))
        return log.read_text()
    compiled = dict(request['sources'],bench=str(replay/'tb.sv'),loader=str(ROOT/'tools/checkpoint_formats/production_gate_restore.cc'))
    before = {p:file_sha(p) for p in compiled.values()}
    tool([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-debug_access+all','+vpi',
          '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-CFLAGS','-std=c++17','-timescale=1ns/1ps',
          '-top','production_gate_tb','-Mdir='+str(run/'csrc'),'-o',run/'simv',*compiled.values()],'build')
    common = [run/'simv','-no_save','+trace='+str(replay/'trace.txt')]
    healthy = tool(common+['+restore='+str(replay/'restore.spans'),'+audit='+str(run/'matched.txt')],'healthy')
    require('PRODUCTION_GATE_ZERO_EDGE cycle=524453 words=13509222 bits=102992412 edges=0' in healthy and
            'PRODUCTION_GATE_END first=524453 end=774638 edges=250185 outputs_per_cycle=34' in healthy,
            'incomplete healthy production gate restore/replay')
    ordinary_log = (ordinary/'replay.log').read_text()
    require('FINITE_PRE_EDGE cycle=524453 words=13503308 target_edges=0' in ordinary_log and
            'PASS: standalone finite replay first=524453 end=774638 target_edges=250185 outputs_per_cycle=34' in ordinary_log,
            'ordinary production RTL replay did not complete')
    observations = compare_observations(request,run/'matched.txt',ordinary/'matched.txt')
    print('COMPLETE_PRODUCTION_GATE_REPLAY_PASS '+json.dumps(observations),flush=True)
    mapping = json.loads(Path(request['map']).read_text())
    binding = json.loads((Path(mapping['proof_components']['original'])/'binding.json').read_text())
    arch = Path(binding['architecture'])
    manifest, boundary = [json.loads((arch/n).read_text()) for n in ('manifest.json','boundary.json')]
    checkpoint = decode_semantic(Path(request['checkpoint']).read_bytes(),builds(manifest,boundary,CONFIGURATION)[0],manifest)
    entries = {e['original_path']:e for e in mapping['entries']}
    values = {r['state_id']:r for r in checkpoint['records']}
    pointer = entries['axi4buf.nodeOut_ar_deq_q.deq_ptr_value']
    address = int(values[pointer['state_id']]['values'][0],16)
    memory = entries['axi4buf.nodeOut_ar_deq_q.ram_flattened']
    mapped_corruption = corruption_record(memory,address)
    path = mapped_corruption['path']
    fault = tool(common+['+restore='+str(replay/'restore.spans'),'+audit='+str(run/'fault-matched.txt'),
                        '+fault_path='+path,'+fault_cycle=524453','+fault_bit=0'],'fault',1)
    require('PRODUCTION_GATE_ZERO_EDGE cycle=524453 words=13509222 bits=102992412 edges=0' in fault and
            'PRODUCTION_GATE_FLIP: path='+path+' bit=0 verified=1' in fault and
            re.search(r'FIRST_MISMATCH cycle=524453 signal=ep_axi4_ar_bits_qos expected=0 actual=1 target_edges=0',fault) and
            'PRODUCTION_GATE_END' not in fault and (run/'fault-matched.txt').stat().st_size==0,
            'mapped production corruption did not stop at its first divergent boundary')
    print('COMPLETE_PRODUCTION_FIRST_DIVERGENCE_PASS',flush=True)
    negatives = run/'invalid-spans'
    negatives.mkdir()
    complement_file(replay/'restore.spans',run/'complement.spans')
    rejections = {}
    for name,data in invalid_spans((replay/'restore.spans').read_bytes()).items():
        path = negatives/(name+'.spans')
        path.write_bytes(data)
        try:
            audit_spans(mapping,checkpoint,path)
        except FormatError as error:
            independent_rejection = str(error)
        else:
            raise AssertionError('Invalid actual production spans passed independent audit: '+name)
        log = tool(common+['+restore='+str(run/'complement.spans'),'+audit='+str(run/(name+'-matched.txt')),
                           '+reject='+str(path)],name)
        require('PRODUCTION_GATE_RESTORE_ERROR:' in log and
                'PRODUCTION_GATE_ATOMIC_REJECTION words=13509222 bits=102992412 edges=0' in log and
                log.count('PRODUCTION_GATE_READBACK: words=13509222 bits=102992412 before_first_edge=1')==2 and
                (run/(name+'-matched.txt')).stat().st_size==0,'incomplete full-state atomic rejection: '+name)
        rejections[name] = dict(artifact=str(path),independent_rejection=independent_rejection,all_words_unchanged=True)
        print('COMPLETE_PRODUCTION_ATOMIC_REJECTION_PASS '+name,flush=True)
    # Four changes to the fully decoded actual metasim checkpoint exercise
    # this translator's pre-publication predicate checks. They are separate
    # from the native mapped gate-state corruption above.
    predicate_rejections = {}
    for entry,bit in [(e,b) for e in mapping['entries'] if e['kind']=='register' for b in e['bits']
                      if b['classification']=='preserved_predicate'][::43]:
        record = values[entry['state_id']]
        previous = record['values'][0]
        record['values'][0] = format(int(previous,16)^(1 << bit['bit']),f'0{(entry["width"]+3)//4}x')
        try:
            validate_checkpoint(mapping,manifest,checkpoint)
        except FormatError as error:
            require(entry['original_path'] in str(error),'unrelated predicate rejection')
            predicate_rejections[entry['original_path']+f' bit {bit["bit"]}'] = str(error)
        else:
            raise AssertionError('Actual checkpoint predicate fault was accepted')
        finally:
            record['values'][0] = previous
    require(validate_checkpoint(mapping,manifest,checkpoint)==values,'predicate negatives changed actual checkpoint')
    require(before=={p:file_sha(p) for p in compiled.values()},'compiled production inputs changed during VCS checks')
    require(all(file_sha(p)==h for p,h in request['dependency_artifacts'].items()),'production proof inputs changed during VCS checks')
    summary = dict(status='passed',run=str(run),replay=str(replay),ordinary=str(ordinary),request_sha256=file_sha(replay/'request.json'),
                   restore=report,observations=observations,mapped_corruption=mapped_corruption,
                   atomic_rejections=rejections,predicate_rejections=predicate_rejections,compiled_inputs=compiled,
                   compiled_input_sha256=before,simv_sha256=file_sha(run/'simv'),gate_replay_verified=True,
                   fpga_validation=False,power_analysis=False)
    (run/'summary.json').write_bytes(canonical(summary))
    (out/'selection.json').write_bytes(canonical(dict(run=str(run),summary=str(run/'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('replay','ordinary','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    result = verify(args.replay,args.ordinary,args.out)
    print(json.dumps(dict(status=result['status'],run=result['run'],samples=result['observations']['samples'],
                          atomic_rejections=len(result['atomic_rejections']),gate_replay_verified=True)))


if __name__ == '__main__':
    main()
