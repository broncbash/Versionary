#!/usr/bin/env python3
"""Validate the VERSIONARY AGENT distribution archive."""

import sys
import tarfile
from pathlib import Path, PurePosixPath

EXPECTED = {
    "agent/__main__.py",
    "agent/config.py",
    "agent/versionary_agent.py",
    "agent/credentials.py",
    "agent/enrollment_client.py",
    "agent/enrollment_crypto.py",
    "agent/enrollment_http.py",
    "agent/enrollment_journal.py",
    "agent/enrollment_keys.py",
    "agent/heartbeat.py",
    "agent/identity.py",
    "agent/registration.py",
    "agent/reporting.py",
}

MAX_MODULE_SIZE = 256 * 1024
MAX_TOTAL_SIZE = 1024 * 1024


def load_modules(path):
    """Validate and return agent module bytes from one archive opening."""
    seen = set()
    total = 0
    modules = {}

    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = member.name
            parts = PurePosixPath(name)

            if (
                parts.is_absolute()
                or ".." in parts.parts
                or name not in EXPECTED
                or name in seen
            ):
                raise ValueError("Unexpected or unsafe archive entry")

            if not member.isfile():
                raise ValueError("Archive contains a non-regular file")

            if (
                member.size < 0
                or member.size > MAX_MODULE_SIZE
            ):
                raise ValueError("Invalid module size")

            total += member.size

            if total > MAX_TOTAL_SIZE:
                raise ValueError("Archive exceeds size limit")

            source = archive.extractfile(member)

            if source is None:
                raise ValueError("Cannot read archive member")

            with source:
                data = source.read(member.size + 1)

            if len(data) != member.size:
                raise ValueError("Incomplete archive member")

            seen.add(name)
            modules[parts.name] = data

    if seen != EXPECTED:
        raise ValueError("Missing required agent modules")

    return modules


def validate(path):
    """Preserve the existing validation interface."""
    return len(load_modules(path))


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected one archive path")

        count = validate(Path(sys.argv[1]))
        print(f"[OK] Validated {count} agent modules")

    except (ValueError, OSError, tarfile.TarError) as exc:
        print(f"[ERROR] Package validation failed: {exc}",
              file=sys.stderr)
        sys.exit(1)
