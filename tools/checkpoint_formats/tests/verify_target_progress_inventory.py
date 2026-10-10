"""Audit the actual compiler inventory and reject altered progress semantics."""
import argparse
import copy
import json
from pathlib import Path

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.metasim_build import TARGET_PROGRESS, TARGET_INITIALIZATION, audit_target_progress
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads((args.production/'generated-manifest.json').read_text())
    inputs=json.loads((args.production/'native-build-inputs.json').read_text())
    header=next(name for name in inputs['sources'] if name.endswith('FireSim-generated.const.h'))
    fir=(ROOT/header).with_name('FireSim-generated.simulator-reference.fir').read_text()
    expected=json.loads((args.production/'target-progress-inventory.json').read_text())
    require(audit_target_progress(manifest,fir)==expected,'compiled progress inventory differs from audit')
    rejected=[]
    def reject(name, inventory, source):
        try:
            audit_target_progress(inventory,source)
        except FormatError:
            rejected.append(name)
        else:
            raise AssertionError('accepted altered progress inventory: '+name)
    index=next(i for i,e in enumerate(manifest['state']) if e['hierarchy']==TARGET_PROGRESS)
    for key,value in dict(hierarchy='FPGATop.unknown.num_resps',width=15,depth=2,kind='memory',
                          signed=True,adapter='opaque-v1',clock_expression='otherClock',
                          reset_expression='UInt<1>("h1")').items():
        changed=copy.deepcopy(manifest); changed['state'][index][key]=value
        reject(key,changed,fir)
    changed=copy.deepcopy(manifest); changed['state'].pop(index); reject('missing',changed,fir)
    changed=copy.deepcopy(manifest); changed['state'].append(changed['state'][index]); reject('duplicate',changed,fir)
    wipe_index=next(i for i,e in enumerate(manifest['state']) if e['hierarchy']==TARGET_INITIALIZATION)
    for key,value in dict(hierarchy='FPGATop.unknown.wipeIndex',width=21,depth=2,kind='memory',
                          signed=True,adapter='opaque-v1',clock_expression='otherClock',
                          reset_expression='UInt<1>("h1")').items():
        changed=copy.deepcopy(manifest); changed['state'][wipe_index][key]=value
        reject('initialization-'+key,changed,fir)
    changed=copy.deepcopy(manifest); changed['state'].pop(wipe_index); reject('initialization-missing',changed,fir)
    changed=copy.deepcopy(manifest); changed['state'].append(changed['state'][wipe_index]); reject('initialization-duplicate',changed,fir)
    for name,old,new in [('reset','mux(reset, UInt<14>("h2710"), mux(and(auto_out_d_valid, d_last)',
                         'mux(reset, UInt<14>("h270f"), mux(and(auto_out_d_valid, d_last)'),
                        ('completion','mux(and(auto_out_d_valid, d_last), _num_resps_T_1, num_resps)',
                         'mux(auto_out_d_valid, _num_resps_T_1, num_resps)'),
                        ('decrement','subw(num_resps, UInt<14>("h1"))','subw(num_resps, UInt<14>("h2"))'),
                        ('module','  module TLFuzzer ','  module OtherFuzzer ')]:
        require(old in fir,'missing real compiler mutation site: '+name)
        reject(name,manifest,fir.replace(old,new))
    for name,old,new in [('wipe-update','addw(wipeIndex, _GEN_384)','addw(wipeIndex, UInt<20>("h1"))'),
                        ('wipe-bound','not(bits(wipeIndex, 19, 19))','not(bits(wipeIndex, 18, 18))')]:
        require(old in fir,'missing real initialization mutation site: '+name)
        reject(name,manifest,fir.replace(old,new))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'summary.json').write_bytes(canonical(dict(inventory=expected,rejections=rejected,
                                                      actual_compiler_inventory=True)))
    print(f'PASS: actual completed-response inventory and {len(rejected)} altered shape/semantics rejections')


if __name__=='__main__': main()
