#!/usr/bin/env python3
"""Build a verified Versionary disposable-beta release archive."""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tarfile
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent

# Only these root-level files and source directories are eligible.

def SENSITIVE_ROOT_NAME(name):
    lower = name.lower()
    return any(
        marker in lower
        for marker in (
            "secret", "password", "private_key",
            "token_store", "credential_store",
        )
    )

ROOT_FILES = {
    path.name
    for path in ROOT.glob("*.py")
    if path.is_file()
    and not path.is_symlink()
    and not path.name.startswith(".")
    and not path.name.startswith("test_")
    and not path.name.endswith("_test.py")
    and ".backup-" not in path.name
    and not SENSITIVE_ROOT_NAME(path.name)
} | {"requirements-baseline.txt"}

SOURCE_DIRS = {
    "agent",
    "installer",
    "arby_scanners",
}

# These files are mandatory for the RC2 server installation.
REQUIRED = {
    "versionary_https_beta.py",
    "agent_registry.py",
    "requirements-baseline.txt",
    "agent/credentials.py",
    "arby_scanners/models.py",
    "installer/generate-certificates.py",
    "installer/versionary-server-install.py",
    "installer/build-versionary-release.py",
    "installer/versionary-beta-agent-bootstrap.sh",
    "installer/versionary-agent-guided-install.sh",
    "installer/systemd/versionary-agent.service",
    "installer/systemd/versionary-agent.timer",
}

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules",
    "dist", "build", ".tox", ".nox",
}

EXCLUDED_SUFFIXES = {
    ".pyc", ".pyo", ".p12", ".pfx", ".pem", ".key",
    ".crt", ".db", ".sqlite", ".sqlite3", ".log",
    ".tar", ".gz", ".zip", ".bak", ".swp",
}

EXCLUDED_NAMES = {
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", "authorized_keys",
    "known_hosts", "agents.db", "server.key",
    "ca.key", "admin-token", "admin.token",
}

SENSITIVE_PATTERN = re.compile(
    r"(^|[-_.])(secret|password|private[-_]?key|credential[-_]?store|"
    r"token[-_]?store|backup|bak)([-_.]|$)",
    re.IGNORECASE,
)

MAX_FILE_SIZE = 8 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def eligible(path):
    relative = path.relative_to(ROOT)
    parts = relative.parts

    if len(parts) == 1:
        if relative.as_posix() not in ROOT_FILES:
            return False
    elif parts[0] not in SOURCE_DIRS:
        return False

    if any(part in EXCLUDED_DIRS for part in parts):
        return False

    # Local disposable-VM helper is not part of the public release.
    if relative.as_posix() == "installer/versionary-disposable-vm-install.py":
        return False

    if any(part.startswith(".") for part in parts):
        return False

    if path.name.lower() in EXCLUDED_NAMES:
        return False

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    if ".backup-" in path.name.lower():
        return False

    if SENSITIVE_PATTERN.search(path.name):
        # Agent credential source code is legitimate application code.
        if relative.as_posix() != "agent/credentials.py":
            return False

    return (
        relative.as_posix() in {
            "installer/versionary-beta-agent-bootstrap.sh",
            "installer/versionary-agent-guided-install.sh",
        }
        or path.suffix == ".py"
        or relative.as_posix() in ROOT_FILES
        or relative.as_posix() in {
            "installer/systemd/versionary-agent.service",
            "installer/systemd/versionary-agent.timer",
        }
    )


def collect():
    selected = {}

    for name in sorted(ROOT_FILES):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Required root file missing: {name}")
        selected[name] = path

    for directory in sorted(SOURCE_DIRS):
        base = ROOT / directory

        if not base.is_dir() or base.is_symlink():
            raise RuntimeError(f"Source directory missing: {directory}")

        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                continue
            if not path.is_file() or not eligible(path):
                continue

            relative = path.relative_to(ROOT).as_posix()
            selected[relative] = path

    missing = REQUIRED - selected.keys()
    if missing:
        raise RuntimeError(
            "Missing mandatory release files: " + ", ".join(sorted(missing))
        )

    for name, path in selected.items():
        if path.stat().st_size > MAX_FILE_SIZE:
            raise RuntimeError(f"File exceeds size limit: {name}")

    return dict(sorted(selected.items()))


def build(destination):
    files = collect()

    destination.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    archive = destination / f"versionary-rc2-{stamp}.tar.gz"
    manifest = destination / f"versionary-rc2-{stamp}.json"

    entries = {}

    # Read source bytes before packaging so the archive and manifest
    # describe exactly the same content.
    for name, path in files.items():
        data = path.read_bytes()
        entries[name] = {
            "data": data,
            "sha256": sha256(data),
            "size": len(data),
        }

    try:
        with tarfile.open(archive, "w:gz") as tar:
            for name, item in entries.items():
                info = tarfile.TarInfo(name)
                info.size = item["size"]
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0

                tar.addfile(info, io.BytesIO(item["data"]))

        digest = sha256(archive.read_bytes())

        metadata = {
            "release": "Versionary RC2 disposable beta",
            "production_approved": False,
            "archive": archive.name,
            "sha256": digest,
            "file_count": len(entries),
            "files": {
                name: {
                    "sha256": item["sha256"],
                    "size": item["size"],
                }
                for name, item in entries.items()
            },
        }

        manifest.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )

        verify(archive, manifest)

    except BaseException:
        archive.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise

    return archive, manifest, digest, len(entries)


def verify(archive, manifest):
    metadata = json.loads(manifest.read_text())

    if metadata.get("production_approved") is not False:
        raise RuntimeError("Production approval must remain false")

    if metadata.get("archive") != archive.name:
        raise RuntimeError("Archive name mismatch")

    if sha256(archive.read_bytes()) != metadata["sha256"]:
        raise RuntimeError("Archive checksum mismatch")

    expected = metadata["files"]
    seen = set()

    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            name = member.name
            pure = PurePosixPath(name)

            if (
                not member.isfile()
                or pure.is_absolute()
                or ".." in pure.parts
                or name in seen
            ):
                raise RuntimeError(f"Unsafe archive member: {name}")

            seen.add(name)

            if name not in expected:
                raise RuntimeError(f"Unexpected archive member: {name}")

            stream = tar.extractfile(member)
            if stream is None:
                raise RuntimeError(f"Cannot read member: {name}")

            data = stream.read()

            if sha256(data) != expected[name]["sha256"]:
                raise RuntimeError(f"File checksum mismatch: {name}")

            if len(data) != expected[name]["size"]:
                raise RuntimeError(f"File size mismatch: {name}")

    if seen != set(expected):
        raise RuntimeError("Archive/manifest file list mismatch")

    if not REQUIRED <= seen:
        raise RuntimeError("Mandatory files missing from archive")

    if len(seen) != metadata["file_count"]:
        raise RuntimeError("File count mismatch")

    return len(seen)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(Path.home() / "Projects/versionary-release-candidates"),
    )
    parser.add_argument("--verify-archive")
    parser.add_argument("--verify-manifest")
    args = parser.parse_args()

    if bool(args.verify_archive) != bool(args.verify_manifest):
        parser.error("Both verification arguments are required together")

    if args.verify_archive:
        count = verify(
            Path(args.verify_archive),
            Path(args.verify_manifest),
        )
        print("ARCHIVE_VERIFICATION=PASS")
        print(f"FILES={count}")
        return

    archive, manifest, digest, count = build(Path(args.output))

    print("=== VERSIONARY RC2 VERIFIED RELEASE ===")
    print(f"ARCHIVE={archive}")
    print(f"MANIFEST={manifest}")
    print(f"FILES={count}")
    print(f"SHA256={digest}")
    print("ARCHIVE_VERIFICATION=PASS")
    print("PRODUCTION_APPROVED=NO")
    print("INSTALL_EXECUTED=NO")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"RELEASE_BUILD=FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
