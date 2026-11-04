#!/usr/bin/env python3
"""Build a portable Versionary installer preview kit."""

import argparse
import hashlib
import io
import os
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES = (
    "installer/install-versionary-server",
    "installer/install-versionary-agent",
    "installer/versionary-server-install.py",
    "installer/install-agent-offline.py",
    "installer/install-agent-cli.py",
    "installer/install-ca.py",
    "installer/install-files.py",
    "installer/setup-config.py",
    "installer/install-systemd.py",
    "installer/build-agent-distribution.py",
    "installer/validate-package.py",
    "installer/dist/versionary-agent-distribution-26l.tar.gz",
    "agent/config.py",
    'installer/atomic-release.py',
    'installer/secure-directories.py',
    'installer/secure-files.py',
    'installer/secure-install-lock.py',
)

SYSTEMD_RESOURCES = (
    'installer/systemd/versionary-agent.service',
    'installer/systemd/versionary-agent.timer',
)

README = """# Versionary Installation Kit — Preview

This is a development preview, NOT a production installer.

Requirements:
- Python 3
- Python cryptography package
- Supported Linux installation environment
- A trusted CA certificate for the intended server

Server installer help:

    python3 installer/install-versionary-server --help

Server verification example:

    python3 installer/install-versionary-server \\
      --archive /path/to/server-release.tar.gz \\
      --manifest /path/to/server-manifest.json \\
      --tls-identity versionary.example.test

The server release archive and manifest must be supplied separately.
Server production installation is disabled.

Agent installer help:

    python3 installer/install-versionary-agent --help

Agent verification example:

    python3 installer/install-versionary-agent \\
      --server https://versionary.example.test \\
      --ca-cert /path/to/trusted-ca.crt \\
      --dry-run

The bundled agent distribution is automatically discovered.
A CA certificate is intentionally NOT included in this kit.

Disposable agent installation requires an explicitly selected
isolated root and --execute-disposable --yes.

Production installation, service activation, and enrollment
are not enabled by this preview.
"""


def add_bytes(archive, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    archive.addfile(info, io.BytesIO(data))


def build(output):
    output = output.expanduser().resolve()

    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; refusing overwrite")

    missing = [name for name in FILES + SYSTEMD_RESOURCES if not (ROOT / name).is_file()]
    if missing:
        raise ValueError(
            "Missing required files: " + ", ".join(missing)
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output.open("xb") as stream:
            with tarfile.open(
                fileobj=stream, mode="w:gz"
            ) as archive:
                add_bytes(
                    archive,
                    "versionary-install-kit/README.md",
                    README.encode(),
                )

                for name in FILES + SYSTEMD_RESOURCES:
                    source = ROOT / name

                    if source.is_symlink():
                        raise ValueError(
                            "Refusing symlink: " + name
                        )

                    data = source.read_bytes()

                    mode = (
                        0o755
                        if name in (
                            "installer/install-versionary-server",
                            "installer/install-versionary-agent",
                        )
                        else 0o644
                    )

                    add_bytes(
                        archive,
                        "versionary-install-kit/" + name,
                        data,
                        mode,
                    )

        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        print("[OK] Kit:", output)
        print("[OK] SHA-256:", digest)
        print("[OK] Files:", len(FILES) + len(SYSTEMD_RESOURCES) + 1)
        print("[OK] No private CA, keys or credentials bundled")
        print("[OK] No production installation performed")

    except BaseException:
        output.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Build Versionary installation preview kit"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
