"""Native ASan/UBSan transport checks with independent socket peers."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


IDENTITY = 'a' * 64


def receive(peer):
    data = bytearray()
    while not data.endswith(b'\n'):
        b = peer.recv(1)
        require(bool(b), 'fixture peer disconnected')
        data += b
    return bytes(data).decode().rstrip('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    native = ROOT / 'tools/checkpoint_formats'
    binary = out / 'transport'
    run([os.environ.get('CXX', 'g++'), '-std=c++17', '-g', '-O1', '-fno-omit-frame-pointer',
         '-fsanitize=address,undefined', '-fno-pie', '-no-pie', '-Wall', '-Wextra', '-Werror',
         native / 'tests/live_shadow_transport_fixture.cc', native / 'live_shadow_transport.cc',
         '-o', binary], out / 'build.log')
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
    results = []

    def start(role, name, path):
        log = (out / (name + '.log')).open('w')
        argv = [str(binary), role, str(path)]
        log.write('argv=' + json.dumps(argv) + '\n')
        log.flush()
        return subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env), log

    def finish(process, log, name, expected):
        try:
            code = process.wait(timeout=40)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            log.close()
        text = (out / (name + '.log')).read_text()
        require(code == expected, f'wrong native exit {code} for {name}; see {out}')
        require('AddressSanitizer' not in text and 'runtime error:' not in text, 'native sanitizer failure')
        require(('PASS:' if expected == 0 else 'SHADOW_PROTOCOL_ERROR:') in text,
                f'missing native outcome in {name}')
        results.append(dict(name=name, exit=code, log=str(out / (name + '.log'))))

    with tempfile.TemporaryDirectory(prefix='fs-shadow-native-', dir='/tmp') as tmp:
        root = Path(tmp)
        path = root / 'healthy'
        server, slog = start('server', 'healthy-server', path)
        client, clog = start('client', 'healthy-client', path)
        finish(client, clog, 'healthy-client', 0)
        finish(server, slog, 'healthy-server', 0)
        require(not path.exists(), 'acknowledged clean finish retained its socket')
        bad = {
            'wrong-cycle': 'DATA 43 1 101', 'unknown-bit': 'DATA 42 x 101',
            'wrong-width': 'DATA 42 01 101', 'padding': 'DATA 42 1 201',
            'missing': 'DATA 42 1', 'extra': 'DATA 42 1 101 0',
            'noncanonical': 'DATA  42 1 101', 'bad-kind': 'NOPE 42 1 101',
            'bad-end': 'END 42 extra', 'oversize': 'D' * 1000,
            'cycle-overflow': 'DATA 18446744073709551616 1 101',
            'leading-cycle-zero': 'DATA 042 1 101', 'negative-cycle': 'DATA -1 1 101',
        }
        for name, packet in bad.items():
            path = root / name
            process, log = start('server', name, path)
            deadline = time.monotonic() + 5
            while not path.exists():
                require(time.monotonic() < deadline, 'native server did not bind')
                time.sleep(0.01)
            with socket.socket(socket.AF_UNIX) as peer:
                peer.settimeout(5)
                peer.connect(str(path))
                peer.sendall(f'HELLO {IDENTITY} 42\n'.encode())
                require(receive(peer) == 'READY', 'native handshake failed')
                peer.sendall((packet + '\n').encode())
            finish(process, log, name, 1)
        for name, hello in (('wrong-session', f'HELLO {"b" * 64} 42'),
                            ('wrong-origin', f'HELLO {IDENTITY} 43'),
                            ('early-eof', f'HELLO {IDENTITY} 42')):
            path = root / name
            process, log = start('server', name, path)
            deadline = time.monotonic() + 5
            while not path.exists():
                require(time.monotonic() < deadline, 'native server did not bind')
                time.sleep(0.01)
            with socket.socket(socket.AF_UNIX) as peer:
                peer.settimeout(5)
                peer.connect(str(path))
                peer.sendall((hello + '\n').encode())
                if name == 'early-eof':
                    require(receive(peer) == 'READY', 'native handshake failed')
            finish(process, log, name, 1)
        for name, acknowledgment in (('wrong-ack-cycle', 'ACK 43'), ('wrong-ack-kind', 'READY'),
                                     ('extra-ack', 'ACK 42 extra'), ('noncanonical-ack', 'ACK 042')):
            path = root / name
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(str(path))
                listener.listen(1)
                listener.settimeout(5)
                process, log = start('client', name, path)
                peer, _ = listener.accept()
                with peer:
                    peer.settimeout(5)
                    require(receive(peer) == f'HELLO {IDENTITY} 42', 'wrong native handshake')
                    peer.sendall(b'READY\n')
                    require(receive(peer) == 'DATA 42 1 101', 'wrong native sample')
                    peer.sendall((acknowledgment + '\n').encode())
                finish(process, log, name, 1)
        # Real elapsed-time timeout while the connected peer never supplies ACK.
        name = 'missing-ack-timeout'
        path = root / name
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path)); listener.listen(1); listener.settimeout(5)
            process, log = start('client', name, path)
            peer, _ = listener.accept()
            with peer:
                peer.settimeout(5)
                require(receive(peer) == f'HELLO {IDENTITY} 42', 'wrong native handshake')
                peer.sendall(b'READY\n')
                require(receive(peer) == 'DATA 42 1 101', 'wrong native sample')
                before = time.monotonic()
                finish(process, log, name, 1)
                elapsed = time.monotonic() - before
                require(29 <= elapsed <= 35, 'transport timeout was not bounded at 30 seconds')
        # Binding must preserve any preexisting destination, including regular
        # files; there is no unlink-before-bind shortcut.
        path = root / 'existing'
        path.write_bytes(b'preserve\n')
        process, log = start('server', 'existing-destination', path)
        finish(process, log, 'existing-destination', 1)
        require(path.read_bytes() == b'preserve\n', 'native setup replaced existing destination')
    summary = dict(results=results, sanitizer='ASan+UBSan', elapsed_timeout_seconds=elapsed)
    (out / 'summary.json').write_bytes(canonical(summary))
    (args.out / 'latest.json').write_bytes(canonical(dict(invocation=str(out), summary=str(out / 'summary.json'))))
    print(f'PASS: {len(results)} independent native transport cases with ASan/UBSan')


if __name__ == '__main__':
    main()
