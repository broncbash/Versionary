#!/usr/bin/env python3
"""Install validated agent configuration without replacing existing settings."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.config import validate_config

def install_config(root, server, ca_cert="/etc/arby-patch-agent/ca.crt"):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Invalid installation root")
    data = validate_config({"server": server, "ca_cert": ca_cert})
    directory = root / "etc/arby-patch-agent"
    if directory.is_symlink():
        raise ValueError("Symlinked configuration directory")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "config.json"
    payload = (json.dumps(data, indent=2) + "\n").encode()
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except FileExistsError:
        if target.is_symlink() or not target.is_file():
            raise ValueError("Unsafe existing configuration")
        if target.read_bytes() != payload:
            raise ValueError("Configuration differs; explicit reconfiguration required")
        return data
    with os.fdopen(fd, "wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", default="/etc/arby-patch-agent/ca.crt")
    args = parser.parse_args()
    try:
        data = install_config(args.root, args.server, args.ca_cert)
        print("[OK] Configured server:", data["server"])
    except (OSError, ValueError, RuntimeError) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
