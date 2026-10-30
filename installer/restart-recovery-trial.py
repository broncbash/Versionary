#!/usr/bin/env python3
"""Restartable recovery experiment in a self-created disposable directory.

The parent owns the temporary root. Worker processes only receive that root
through this internal harness, never through a public installation interface.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PARTS = ("release", "config", "ca", "service", "timer")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def journal(root, state):
    data = json.dumps({"version": 1, "state": state,
                       "prior": {name: digest(("old:" + name).encode()) for name in PARTS}},
                      sort_keys=True).encode()
    pending = root / "journal.pending"
    write(pending, data)
    os.replace(pending, root / "journal.json")


def worker(root, operation, stop_at=None):
    if operation not in ("switch", "recover"):
        raise ValueError("Invalid worker operation")
    if operation == "switch":
        journal(root, "prepared")
        for name in PARTS:
            pending = root / "active" / (name + ".pending")
            write(pending, ("new:" + name).encode())
            os.replace(pending, root / "active" / name)
            journal(root, name)
            if name == stop_at:
                os._exit(77)
        journal(root, "verified")
        return
    saved = json.loads((root / "journal.json").read_text())
    if (saved.get("version") != 1 or saved.get("state") not in ("prepared", *PARTS, "verified")
            or saved.get("prior") != {name: digest(("old:" + name).encode()) for name in PARTS}):
        raise ValueError("Untrusted or malformed journal")
    for name in PARTS:
        prior = (root / "prior" / name).read_bytes()
        if digest(prior) != saved["prior"][name]:
            raise ValueError("Prior generation corrupted")
    for name in PARTS:
        pending = root / "active" / (name + ".restore")
        write(pending, (root / "prior" / name).read_bytes())
        os.replace(pending, root / "active" / name)
    journal(root, "recovered")


def run(stop_at="ca", tamper=None):
    if stop_at not in PARTS:
        raise ValueError("Unknown stop checkpoint")
    if tamper not in (None, "journal", "backup"):
        raise ValueError("Unknown tamper mode")
    with tempfile.TemporaryDirectory(prefix="patch-command-restart-trial-") as temp:
        root = Path(temp)
        for name in ("active", "prior"):
            (root / name).mkdir(mode=0o700)
        for name in PARTS:
            data = ("old:" + name).encode()
            write(root / "active" / name, data)
            write(root / "prior" / name, data)
        command = [sys.executable, str(Path(__file__).resolve()), "_worker", str(root)]
        switched = subprocess.run(command + ["switch", stop_at], capture_output=True, text=True)
        if switched.returncode != 77:
            raise RuntimeError("Expected independent worker termination")
        if tamper == "journal":
            (root / "journal.json").write_text('{"version":0}')
        if tamper == "backup":
            (root / "prior" / "ca").write_text("tampered")
        recovered = subprocess.run(command + ["recover"], capture_output=True, text=True)
        if tamper:
            if recovered.returncode == 0:
                raise RuntimeError("Tampered recovery was accepted")
            return {"status": "refused", "tamper": tamper, "checkpoint": stop_at,
                    "production_installed": False, "systemd_started": False}
        if recovered.returncode != 0:
            raise RuntimeError("Recovery worker failed: " + recovered.stderr)
        if any((root / "active" / name).read_bytes() != ("old:" + name).encode()
               for name in PARTS):
            raise RuntimeError("Restored generation mismatch")
        if json.loads((root / "journal.json").read_text())["state"] != "recovered":
            raise RuntimeError("Recovery journal not finalized")
        return {"status": "recovered", "mode": "disposable-independent-process-recovery",
                "checkpoint": stop_at, "production_installed": False,
                "systemd_started": False, "agent_enrolled": False,
                "external_network_requests_made": False}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "_worker":
        if len(sys.argv) not in (4, 5):
            raise SystemExit(2)
        worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else None)
    else:
        import argparse
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--stop-at", choices=PARTS, default="ca")
        parser.add_argument("--tamper", choices=("journal", "backup"))
        args = parser.parse_args()
        print(json.dumps(run(args.stop_at, args.tamper), indent=2))


if __name__ == "__main__":
    main()
