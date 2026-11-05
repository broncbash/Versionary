#!/usr/bin/env python3
"""Assemble the verified portable Versionary beta installation kit."""

import argparse
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "installer"
PREFIX = "versionary-install-kit"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_bytes(archive, name, content, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(content)
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    archive.addfile(info, io.BytesIO(content))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-archive", required=True)
    parser.add_argument("--server-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    server_archive = pathlib.Path(args.server_archive).resolve()
    server_manifest = pathlib.Path(args.server_manifest).resolve()
    output = pathlib.Path(args.output).absolute()

    if not server_archive.is_file():
        raise RuntimeError("Server archive not found")
    if not server_manifest.is_file():
        raise RuntimeError("Server manifest not found")
    if server_archive.is_symlink() or server_manifest.is_symlink():
        raise RuntimeError("Symlinked release inputs are not supported")
    if server_archive.name != server_manifest.stem + ".tar.gz":
        raise RuntimeError("Server archive/manifest names do not match")

    subprocess.run(
        [
            sys.executable,
            str(INSTALLER / "build-versionary-release.py"),
            "--verify-archive",
            str(server_archive),
            "--verify-manifest",
            str(server_manifest),
        ],
        check=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="versionary-unified-kit-"
    ) as temp:
        temp = pathlib.Path(temp)
        agent_kit = temp / "agent-kit.tar.gz"

        subprocess.run(
            [
                sys.executable,
                str(INSTALLER / "build-installation-kit.py"),
                "--output",
                str(agent_kit),
            ],
            check=True,
        )

        with tarfile.open(agent_kit, "r:gz") as source:
            members = source.getmembers()

            if not members:
                raise RuntimeError("Empty base installation kit")

            payloads = {}

            for member in members:
                path = pathlib.PurePosixPath(member.name)

                if (
                    not member.isfile()
                    or path.is_absolute()
                    or ".." in path.parts
                    or not member.name.startswith(PREFIX + "/")
                ):
                    raise RuntimeError(
                        "Unsafe base kit member: " + member.name
                    )

                stream = source.extractfile(member)
                if stream is None:
                    raise RuntimeError("Unreadable kit member")

                if member.name in payloads:
                    raise RuntimeError("Duplicate kit member")

                payloads[member.name] = (
                    stream.read(),
                    member.mode & 0o777,
                )

        server_script = (
            PREFIX + "/installer/install-versionary-server"
        )

        if server_script not in payloads:
            raise RuntimeError("Server installer missing")

        script, mode = payloads[server_script]

        # Keep the existing installer unchanged in the repository.
        # The bundled launcher supplies its own release defaults.
        launcher = r'''#!/usr/bin/env python3
"""Portable Versionary server setup launcher."""

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RELEASES = HERE.parent / "releases"
ARCHIVE_NAME = "__ARCHIVE_NAME__"
MANIFEST_NAME = "__MANIFEST_NAME__"

def main():
    arguments = sys.argv[1:]
    archive = RELEASES / ARCHIVE_NAME
    manifest = RELEASES / MANIFEST_NAME

    if "--archive" not in arguments:
        arguments = ["--archive", str(archive)] + arguments

    if "--manifest" not in arguments:
        arguments = ["--manifest", str(manifest)] + arguments

    command = [
        sys.executable,
        str(HERE / "versionary-server-install.py"),
        *arguments,
    ]

    return subprocess.call(command)

if __name__ == "__main__":
    sys.exit(main())
'''
        launcher = launcher.replace(
            "__ARCHIVE_NAME__", server_archive.name
        ).replace(
            "__MANIFEST_NAME__", server_manifest.name
        )

        payloads[server_script] = (
            launcher.encode(),
            mode | 0o100,
        )

        payloads[
            PREFIX + "/releases/" + server_archive.name
        ] = (server_archive.read_bytes(), 0o644)

        payloads[
            PREFIX + "/releases/" + server_manifest.name
        ] = (server_manifest.read_bytes(), 0o644)

        readme = f"""# Versionary Unified Installation Kit

This is a controlled-beta installation preview.

## Server

Run:

    python3 installer/install-versionary-server

This verifies the bundled server release without installing it.

The server backend's installation mode changes system users,
Python environments, and systemd services. Do not use that mode
outside an explicitly approved disposable test VM.

## Agent

Run:

    python3 installer/install-versionary-agent

The agent installer prompts for its server URL and CA certificate.
Its default behavior is non-installing preview.

To perform a disposable agent installation, supply a temporary
root and the explicit disposable confirmation options.

## Bundled release

Archive: releases/{server_archive.name}
Manifest: releases/{server_manifest.name}

Server archive SHA-256:
{sha256(server_archive)}

No private TLS keys or credentials are included.

Production deployment is not approved.
"""

        payloads[PREFIX + "/README.md"] = (
            readme.encode(),
            0o644,
        )

        if output.exists():
            raise RuntimeError("Output already exists")

        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            with output.open("xb") as destination:
                with tarfile.open(
                    fileobj=destination,
                    mode="w:gz",
                ) as result:
                    for name, (content, mode) in sorted(
                        payloads.items()
                    ):
                        add_bytes(result, name, content, mode)
        except BaseException:
            output.unlink(missing_ok=True)
            raise

        print("[OK] Unified kit:", output)
        print("[OK] SHA-256:", sha256(output))
        print("[OK] Packaged files:", len(payloads))
        print("[OK] Server release files included")
        print("[OK] Agent distribution included")
        print("[OK] No production installation performed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("[FAIL]", exc, file=sys.stderr)
        sys.exit(1)
