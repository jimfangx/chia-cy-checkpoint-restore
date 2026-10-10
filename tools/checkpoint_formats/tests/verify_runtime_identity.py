"""Native ASan/UBSan runtime compatibility against an independent SHA256 oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    cc=ROOT/'sims/firesim/sim/midas/src/main/cc'
    source=ROOT/'tools/checkpoint_formats'
    compiler=os.environ.get('CXX','/usr/bin/g++-13')
    run([compiler,'-std=c++20','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',
         f'-I{cc}',source/'runtime_identity.cc',source/'tests/runtime_identity_native.cc',
         '-lcrypto','-ldl','-o',out/'verify'],out/'build.log')
    common=['+memsize=4194304','+max-cycles=1000000','+vcs+initreg+0','+vcs+initmem+0']
    good=out/'identity.bin'
    run([out/'verify','save',good,'-',*common],out/'save.log')
    run([out/'verify','load',good,'-',*reversed(common),'+fuzz-host-timing=1','+fuzz-seed=0'],out/'load.log')
    data=good.read_bytes();pos=0
    def u64():
        nonlocal pos
        value,=struct.unpack_from('<Q',data,pos);pos+=8;return value
    def string():
        nonlocal pos
        count=u64();value=data[pos:pos+count].decode();pos+=count;return value
    require(string()=='FCFS_RUNTIME1','configuration schema oracle')
    configuration_offset=pos
    require([u64() for _ in range(4)]==[4194304,1000000,1,0], 'configuration oracle')
    paths=[];digest_offsets=[]
    for _ in range(u64()):
        path=string();digest_offsets.append(pos);value=data[pos:pos+32];pos+=32
        require(hashlib.sha256(Path(path).read_bytes()).digest()==value,'loaded ELF SHA256 differs from oracle')
        paths.append(path)
    require(pos==len(data) and paths==sorted(set(paths)) and str(out/'verify') in paths,'incomplete ELF inventory')
    rejections=0
    # Corrupt every digest, every configuration word and the late tail. The
    # immutable owner must reject without replacing current configuration.
    for index,offset in enumerate([configuration_offset+8*i for i in range(4)]+digest_offsets+[len(data)-1]):
        changed=bytearray(data);changed[offset]^=1;bad=out/f'bad-{index}.bin';bad.write_bytes(changed)
        text=run([out/'verify','reject',bad,'-',*common],out/f'bad-{index}.log')
        require('REJECT unchanged_owner=1' in text,'payload rejection oracle');rejections+=1
    for label,extra in [('memory',['+memsize=4194305']),('horizon',['+max-cycles=1000001']),
                        ('delay',['+fuzz-host-timing=2']),('seed',['+fuzz-seed=18446744073709551615'])]:
        replaced={v.split('=')[0] for v in extra}
        args=[v for v in common if v.split('=')[0] not in replaced]+extra
        text=run([out/'verify','reject',good,'-',*args],out/f'{label}.log')
        require('REJECT unchanged_owner=1' in text,'configuration rejection');rejections+=1
    invalid=[['+memsize=0'],['+memsize=-1'],['+memsize=9223372036854775808'],['+memsize=1junk'],
             ['+max-cycles=0'],['+max-cycles=18446744073709551616'],['+fuzz-host-timing=0'],
             ['+fuzz-host-timing=2147483648'],['+fuzz-seed=-1'],['+vcs+initreg+random'],
             ['+loadmem=unbound'],['+expect_reads=1'],['+profile-interval=5'],['+unknown=1'],
             ['+max-cycles=1','+max-cycles=2'],['+memsize'],['+vcs+initmem+0','+vcs+initmem+0']]
    for index,extra in enumerate(invalid):
        replaced={v.split('=')[0] for v in extra}
        args=[v for v in common if v.split('=')[0] not in replaced]+extra
        text=run([out/'verify','bad-args',good,'-',*args],out/f'args-{index}.log')
        require('ENTRY_ERROR runtime identity:' in text,'unsupported arguments accepted');rejections+=1
    for name in ('LD_PRELOAD','LD_AUDIT'):
        # Empty-entry configuration rejection is checked without depending on
        # the system loader accepting the deliberately absent hook filename.
        text=run(['env',f'{name}=/tmp/checkpoint-unsupported-hook.so',out/'verify','bad-args',good,'-',*common],
                 out/f'{name}.log')
        require('ENTRY_ERROR runtime identity: unsupported LD_PRELOAD/LD_AUDIT library hooks' in text,
                'unaudited library hook accepted');rejections+=1
    # Same pathname, new library bytes: path/SONAME-only binding is insufficient.
    libsource=out/'library.cc';lib=out/'library.so'
    for version in (1,2):
        libsource.write_text(f'extern "C" int identity_test_library() {{ return {version}; }}\n')
        run([compiler,'-shared','-fPIC',libsource,'-o',lib],out/f'library-build-{version}.log')
        if version==1:
            run([out/'verify','save',out/'library-identity.bin',lib,*common],out/'library-save.log')
        else:
            text=run([out/'verify','reject',out/'library-identity.bin',lib,*common],out/'library-reject.log')
            require('REJECT unchanged_owner=1' in text,'same-path changed ELF accepted');rejections+=1
    for mode in ('late-add','late-remove'):
        text=run([out/'verify',mode,good,lib,*common],out/(mode+'.log'))
        require('REJECT changed ELF inventory' in text,'late library change lacked explicit diagnosis')
        rejections+=1
    summary=dict(rejections=rejections,elf_sha256_comparisons=len(paths),sanitizers='ASan/UBSan',
                 same_path_changed_library_rejected=True,late_library_change_diagnostics=True,unchanged_owner=True)
    (out/'summary.json').write_bytes(canonical(summary));print('PASS:',json.dumps(summary))


if __name__=='__main__':main()
