"""Test-only inherited mask policy for restricted native HTIF executions.

Block before exec and VCS worker creation. The lifecycle provider still checks
the calling thread mask, pending signals and handlers. This supplies no signal-caused
exit continuation or production signal coordinator.
"""
import os
import signal
import sys


def main():
    if len(sys.argv) < 3 or sys.argv[1] != '--':
        raise SystemExit('expected -- executable [arguments]')
    signals = {signal.SIGINT, signal.SIGTERM, signal.SIGABRT}
    signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    if not signals.issubset(signal.pthread_sigmask(signal.SIG_BLOCK, set())) or signal.sigpending() & signals:
        raise SystemExit('invalid inherited HTIF signal policy')
    print('TEST_HTIF_SIGNAL_POLICY blocked=SIGINT,SIGTERM,SIGABRT pending=0 before_exec=1', flush=True)
    os.execv(sys.argv[2], sys.argv[2:])


if __name__ == '__main__':
    main()
