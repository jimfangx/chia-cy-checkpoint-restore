"""Own ELF-loader and coroutine resources in a build-local FESVR archive."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def build(library, include, output, cxx, flags=()):
    source = Path(__file__).resolve().with_name('owned_elfloader.cc')
    sources = {'elfloader.o': source, 'context.o': source.with_name('owned_context.cc')}
    library, include, output = (Path(p).resolve() for p in (library, include, output))
    if output == library:
        raise ValueError('checkpoint archive must not replace installed FESVR')
    members = subprocess.check_output(['ar', 't', library], text=True).splitlines()
    if len(members) != len(set(members)) or any(members.count(m) != 1 for m in sources):
        raise ValueError('unsupported FESVR archive member inventory')
    output.parent.mkdir(parents=True, exist_ok=True)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    before = sha(library.read_bytes())
    with tempfile.TemporaryDirectory(prefix='fesvr-build-', dir=output.parent) as directory:
        work = Path(directory)
        objects = []
        for member, replacement_source in sources.items():
            obj = work / member
            subprocess.run([*shlex.split(cxx), '-std=c++17', '-O2', '-fPIC', *flags,
                            '-I' + str(include), '-c', replacement_source, '-o', obj], check=True)
            objects.append(obj)
        archive = work / output.name
        shutil.copyfile(library, archive)
        subprocess.run(['ar', 'rcs', archive, *objects], check=True)
        if subprocess.check_output(['ar', 't', archive], text=True).splitlines() != members:
            raise ValueError('overlay changed FESVR member inventory')
        digests = {}
        for member in members:
            original = subprocess.check_output(['ar', 'p', library, member])
            replacement = subprocess.check_output(['ar', 'p', archive, member])
            if member not in sources and original != replacement:
                raise ValueError('overlay changed unrelated FESVR member: ' + member)
            digests[member] = dict(installed=sha(original), overlay=sha(replacement))
        if sha(library.read_bytes()) != before:
            raise ValueError('installed FESVR changed while building overlay')
        report = dict(status='passed', installed_archive=str(library),
                      installed_sha256=before, source=str(source), source_sha256=sha(source.read_bytes()),
                      output=str(output), output_sha256=sha(archive.read_bytes()),
                      sources={str(p): sha(p.read_bytes()) for p in sources.values()},
                      members=digests, cxx=cxx, extra_flags=list(flags))
        # Publish only a complete, independently checked archive.
        os.replace(archive, output)
        output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True)
    parser.add_argument('--include', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--cxxflag', action='append', default=[])
    args = parser.parse_args()
    build(args.library, args.include, args.out, args.cxx, args.cxxflag)
