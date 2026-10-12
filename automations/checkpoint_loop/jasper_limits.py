#!/usr/bin/env python3
"""Limit Jasper callers and descendants without changing their sandbox."""

import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import select
import socket
import struct
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
DEFAULT_SOCKET = HERE / "runs/jasper-limits.sock"
DEFAULT_BYTES = 475_000_000_000


def request(path, value):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(str(path))
        connection.sendall(json.dumps(value).encode() + b"\n")
        response = json.loads(connection.makefile("rb").readline(4096))
    if "error" in response:
        raise RuntimeError(response["error"])
    return response


def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except FileNotFoundError:
        return None


def cleanup_job(group):
    if group.exists():
        (group / "cgroup.kill").write_text("1")
    subprocess.run(["systemctl", "--user", "--no-ask-password", "stop", group.name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    return not group.exists()


def serve(path, memory_bytes, cgroup_name):
    if memory_bytes <= 0 or not re.fullmatch(r"[a-zA-Z0-9_-]+\.slice", cgroup_name):
        raise ValueError("invalid Jasper memory budget or cgroup name")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS",
                          f"unix:path={os.environ['XDG_RUNTIME_DIR']}/bus")
    subprocess.run(["systemctl", "--user", "--no-ask-password", "set-property", "--runtime",
                    cgroup_name, f"MemoryMax={memory_bytes}", "MemorySwapMax=0"],
                   check=True, timeout=10)
    subprocess.run(["systemctl", "--user", "--no-ask-password", "start", cgroup_name],
                   check=True, timeout=10)
    control_group = subprocess.run(["systemctl", "--user", "show", cgroup_name,
                                   "-p", "ControlGroup", "--value"],
                                  check=True, text=True, capture_output=True, timeout=10).stdout.strip()
    budget = Path("/sys/fs/cgroup") / control_group.lstrip("/")
    (budget / "memory.oom.group").write_text("1")
    for group in budget.iterdir():
        if group.is_dir() and group.name.startswith("checkpoint-jasper-job-"):
            cleanup_job(group)
    logger = logging.getLogger("jasper-limits")
    logger.setLevel(logging.INFO)
    logger.addHandler(RotatingFileHandler(path.with_suffix(".log"),
                                         maxBytes=1024 * 1024, backupCount=2))
    path.unlink(missing_ok=True)
    jobs = {}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(path))
        path.chmod(0o600)
        listener.listen(16)
        logger.info("Shared Jasper budget: %s bytes, swap disabled", memory_bytes)
        while True:
            if select.select([listener], [], [], 0.5)[0]:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(5)
                    group = None
                    try:
                        pid, uid, _ = struct.unpack("3i", connection.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                        if uid != os.getuid() or pid <= 0:
                            raise PermissionError("Jasper limit caller identity rejected")
                        value = json.loads(connection.makefile("rb").readline(4096))
                        if value["operation"] == "status":
                            response = {"memory_bytes": memory_bytes, "jobs": len(jobs),
                                        "cgroup": str(budget)}
                        elif value["operation"] == "attach":
                            timeout = value["timeout"]
                            if type(timeout) is not int or timeout < 0:
                                raise ValueError("Jasper runtime limit must be a nonnegative integer")
                            identity = process_identity(pid)
                            if identity is None:
                                raise RuntimeError("Jasper caller exited before attachment")
                            unit = "checkpoint-jasper-job-" + str(pid) + "-" + uuid.uuid4().hex + ".scope"
                            group = budget / unit
                            # The user manager can migrate a caller from an SSH
                            # service into its delegated resource subtree.
                            properties = ["PIDs", "au", "1", str(pid), "Slice", "s", cgroup_name]
                            if timeout:
                                properties += ["RuntimeMaxUSec", "t", str(timeout * 1_000_000)]
                            subprocess.run(["busctl", "--user", "call", "org.freedesktop.systemd1",
                                "/org/freedesktop/systemd1", "org.freedesktop.systemd1.Manager",
                                "StartTransientUnit", "ssa(sv)a(sa(sv))", unit, "fail",
                                str(3 if timeout else 2), *properties, "0"],
                                check=True, stdout=subprocess.DEVNULL, timeout=10)
                            for _ in range(60):
                                membership = Path(f"/proc/{pid}/cgroup").read_text()
                                if membership.strip().endswith("/" + unit):
                                    break
                                time.sleep(0.05)
                            else:
                                raise RuntimeError("Jasper caller did not enter its limited scope")
                            (group / "memory.oom.group").write_text("1")
                            # Host credentials resolve the caller's PID across bwrap.
                            # Only move this caller: no commands run outside its sandbox.
                            jobs[group] = (pid, identity, time.monotonic() + timeout
                                           if timeout else float("inf"))
                            response = {"memory_bytes": memory_bytes, "cgroup": str(group),
                                        "runtime_seconds": timeout}
                            logger.info("Attached pid=%s, runtime=%ss, group=%s",
                                        pid, timeout, group.name)
                        else:
                            raise ValueError("unknown Jasper limit operation")
                    except Exception as error:
                        if group is not None and group.exists():
                            cleanup_job(group)
                        response = {"error": str(error)}
                    try:
                        connection.sendall(json.dumps(response).encode() + b"\n")
                    except BrokenPipeError:
                        pass
            for group, (pid, identity, deadline) in list(jobs.items()):
                timed_out = time.monotonic() >= deadline
                if timed_out or process_identity(pid) != identity:
                    if timed_out:
                        logger.warning("Jasper runtime limit reached: %s", group.name)
                    if cleanup_job(group):
                        del jobs[group]


def ensure(path):
    try:
        return request(path, {"operation": "status"})
    except (FileNotFoundError, ConnectionRefusedError):
        path.parent.mkdir(parents=True, exist_ok=True)
        memory_gb = int(os.environ.get("CHECKPOINT_JASPER_MEMORY_GB", "475"))
        if memory_gb <= 0:
            raise ValueError("Jasper memory limit must be positive")
        with path.with_suffix(".startup.log").open("wb") as errors:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                              "--socket", str(path), "serve",
                              "--memory-bytes", str(memory_gb * 1_000_000_000)],
                             stdin=subprocess.DEVNULL, stdout=errors, stderr=errors,
                             start_new_session=True)
        for _ in range(50):
            try:
                return request(path, {"operation": "status"})
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.1)
        raise RuntimeError(f"Cannot enforce Jasper memory cap; see {path.with_suffix('.startup.log')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, default=Path(os.environ.get(
        "CHECKPOINT_JASPER_LIMIT_SOCKET", str(DEFAULT_SOCKET))))
    commands = parser.add_subparsers(dest="operation", required=True)
    server = commands.add_parser("serve")
    server.add_argument("--memory-bytes", type=int, default=DEFAULT_BYTES)
    server.add_argument("--cgroup-name", default="checkpoint-jasper.slice")
    commands.add_parser("ensure")
    run = commands.add_parser("run")
    run.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.operation == "serve":
        serve(args.socket, args.memory_bytes, args.cgroup_name)
    elif args.operation == "ensure":
        print(json.dumps(ensure(args.socket)))
    else:
        command = args.command
        if command[:1] == ["--"]:
            command = command[1:]
        if not command:
            parser.error("run requires a Jasper command")
        ensure(args.socket)
        timeout = int(os.environ.get("CHECKPOINT_JASPER_TIMEOUT_SECONDS", "0"))
        limits = request(args.socket, {"operation": "attach", "timeout": timeout})
        print(f"[jasper limits] shared={limits['memory_bytes']} bytes swap=0 "
              f"runtime={limits['runtime_seconds']}s", file=sys.stderr, flush=True)
        os.execv(command[0], command)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Cannot enforce Jasper limits; refusing an unlimited launch: {error}", file=sys.stderr)
        sys.exit(125)
