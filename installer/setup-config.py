#!/usr/bin/env python3
"""Install validated agent configuration with atomic no-clobber publication."""

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.config import validate_config


def sync_directory(directory):
    fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def check_existing(target, payload):
    info = target.lstat()

    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Unsafe existing configuration")

    if info.st_uid != os.geteuid() or info.st_nlink != 1:
        raise ValueError("Unsafe existing configuration")

    if info.st_mode & 0o022:
        raise ValueError("Unsafe existing configuration")

    if target.read_bytes() != payload:
        raise ValueError(
            "Configuration differs; explicit reconfiguration required"
        )


def install_config(root, server, ca_cert="/etc/versionary-agent/ca.crt"):
    root = Path(root).absolute()

    if root.is_symlink() or not root.is_dir():
        raise ValueError("Invalid installation root")

    data = validate_config({
        "server": server,
        "ca_cert": ca_cert,
    })

    directory = root / "etc/versionary-agent"

    if directory.is_symlink():
        raise ValueError("Symlinked configuration directory")

    directory.mkdir(parents=True, exist_ok=True)

    target = directory / "config.json"
    payload = (json.dumps(data, indent=2) + "\n").encode()

    if os.path.lexists(target):
        check_existing(target, payload)
        return data

    fd, temporary = tempfile.mkstemp(
        prefix=".config-install-",
        dir=directory,
    )

    try:
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())

        os.chmod(temporary, 0o644)

        try:
            os.link(
                temporary,
                target,
                follow_symlinks=False,
            )
        except FileExistsError:
            check_existing(target, payload)
        else:
            sync_directory(directory)

    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument(
        "--ca-cert",
        default="/etc/versionary-agent/ca.crt",
    )
    args = parser.parse_args()

    try:
        data = install_config(
            args.root,
            args.server,
            args.ca_cert,
        )
        print("[OK] Configured server:", data["server"])
    except (OSError, ValueError, RuntimeError) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
