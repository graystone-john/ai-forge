#!/usr/bin/env python3
"""Runs on Daedalus over SSH. Requests idle exit; never force-kills."""
from pathlib import Path
import os
import pwd
import sys
import time
import uuid

if os.geteuid() != 0:
    raise SystemExit("Run as root.")

uid = pwd.getpwnam("daedalus").pw_uid
directory = Path("/run/ai-forge-hermes-exit")

def processes():
    result = {}
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            raw = (path / "stat").read_text()
            fields = raw[raw.rfind(")") + 2:].split()
            if fields[0] == "Z":
                continue
            result[int(path.name)] = {
                "start": fields[19],
                "parent": int(fields[1]),
                "uid": path.stat().st_uid,
                "cmd": (path / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                    errors="replace"
                ),
                "exe": (path / "exe").resolve().name,
            }
        except (OSError, ValueError, IndexError):
            continue
    return result

initial = processes()
candidates = [
    pid for pid, info in initial.items()
    if info["uid"] == uid
    and info["exe"] == "node"
    and ("tui" in info["cmd"])
    and ("entry.js" in info["cmd"] or "entry.tsx" in info["cmd"])
]

if not candidates:
    print("No active Hermes TUI; no disconnect needed.")
    sys.exit(0)
if len(candidates) != 1:
    raise SystemExit("Multiple Hermes TUIs are open. Restore stopped before reboot.")

pid = candidates[0]
prefix = directory / f'{pid}-{initial[pid]["start"]}'
registration = Path(str(prefix) + ".json")
if not registration.is_file():
    raise SystemExit(
        "This Hermes session lacks the exit handshake. "
        "Exit it and start a new session; no reboot performed."
    )

import json
registered = json.loads(registration.read_text())
if registered != {"pid": pid, "start": initial[pid]["start"], "protocol": 1}:
    raise SystemExit("Invalid Hermes session registration.")

# Track the TUI and its current descendants, including its Python gateway.
tracked = {pid: initial[pid]["start"]}
while True:
    additions = {
        child: info["start"] for child, info in initial.items()
        if info["parent"] in tracked and child not in tracked
    }
    if not additions:
        break
    tracked.update(additions)

if "--check" in sys.argv[1:]:
    print(f"Handshake ready: TUI PID {pid}; tracking {len(tracked)} processes.")
    sys.exit(0)

request = Path(str(prefix) + ".request")
ready = Path(str(prefix) + ".ready")
token = uuid.uuid4().hex
ready.unlink(missing_ok=True)
request.write_text(token)
request.chmod(0o644)

print(f"Waiting for Hermes PID {pid} to finish its response and exit.", flush=True)
deadline = time.monotonic() + 60
acknowledged = False
try:
    while time.monotonic() < deadline:
        if ready.exists() and ready.read_text().strip() == token:
            acknowledged = True
        current = processes()

        # Include descendants created while the response is finishing.
        while True:
            additions = {
                child: info["start"] for child, info in current.items()
                if info["parent"] in tracked
                and info["parent"] in current
                and current[info["parent"]]["start"] == tracked[info["parent"]]
                and child not in tracked
            }
            if not additions:
                break
            tracked.update(additions)

        alive = [
            child for child, start in tracked.items()
            if child in current and current[child]["start"] == start
        ]
        if not alive:
            if not acknowledged:
                raise SystemExit("Hermes exited without acknowledging the handoff.")
            print("Hermes TUI and gateway exited; reboot may proceed.")
            break
        time.sleep(0.2)
    else:
        raise SystemExit("Hermes shutdown timed out. No reboot performed.")
finally:
    request.unlink(missing_ok=True)
    ready.unlink(missing_ok=True)
