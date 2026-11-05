#!/usr/bin/env python3
"""Local, non-deploying Versionary release acceptance workflow."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"

def run(label, command, log=None):
    print(f"\n=== {label} ===", flush=True)
    if log is None:
        subprocess.run(command, cwd=ROOT, check=True)
        return

    with log.open("w") as stream:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )

    lines = log.read_text(errors="replace").splitlines()
    for line in lines[-12:]:
        print(line)

    if result.returncode:
        raise RuntimeError(f"{label} failed; see {log}")

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def verify_kit(path, server_archive, server_manifest):
    expected = {
        f"versionary-install-kit/releases/{server_archive.name}",
        f"versionary-install-kit/releases/{server_manifest.name}",
        "versionary-install-kit/installer/install-versionary-server",
        "versionary-install-kit/installer/install-versionary-agent",
        "versionary-install-kit/README.md",
    }

    seen = set()

    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = member.name

            if (
                not member.isfile()
                or name in seen
                or not name.startswith("versionary-install-kit/")
                or "\\" in name
                or any(
                    part in ("", ".", "..")
                    for part in name.split("/")
                )
            ):
                raise RuntimeError(
                    f"Unsafe or duplicate kit entry: {name}"
                )

            seen.add(name)

            if name.endswith((".key", ".pem", ".crt", ".db")):
                raise RuntimeError(
                    f"Unexpected sensitive kit entry: {name}"
                )

            if name == (
                "versionary-install-kit/releases/"
                + server_archive.name
            ):
                content = archive.extractfile(member).read()
                if hashlib.sha256(content).hexdigest() != digest(
                    server_archive
                ):
                    raise RuntimeError("Server archive mismatch")

            if name == (
                "versionary-install-kit/releases/"
                + server_manifest.name
            ):
                content = archive.extractfile(member).read()
                if content != server_manifest.read_bytes():
                    raise RuntimeError("Server manifest mismatch")

    missing = expected - seen
    if missing:
        raise RuntimeError(
            "Missing kit entries: " + ", ".join(sorted(missing))
        )

    print(f"[OK] Unified kit verified: {len(seen)} files")

def check_safety_gates():
    agent = (
        INSTALLER / "versionary-agent-system-install.py"
    ).read_text()

    entry = (
        INSTALLER / "install-versionary-agent"
    ).read_text()

    transaction = (
        INSTALLER / "versionary-agent-system-transaction.py"
    ).read_text()

    required = [
        ("InstallationNotImplemented", agent),
        ("raise InstallationNotImplemented(", agent),
        ("Production installation: DISABLED", entry),
        ("--execute-disposable", entry),
        ("root == Path(\"/\")", transaction),
    ]

    for marker, source in required:
        if marker not in source:
            raise RuntimeError(
                f"Installation safety gate changed: {marker}"
            )

    for path in INSTALLER.glob("*.py"):
        if "backup" not in path.name:
            ast.parse(path.read_text(), filename=str(path))

    print("[OK] Existing installation safety gates retained")
    print("[OK] Installer Python syntax valid")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional existing or new output directory",
    )
    args = parser.parse_args()

    if args.output_dir:
        output = args.output_dir.expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise RuntimeError("Output directory must be empty")
    else:
        output = Path(tempfile.mkdtemp(
            prefix="versionary-rc-",
            dir="/tmp",
        ))

    print("=== VERSIONARY RELEASE ACCEPTANCE ===")
    print("Output:", output)
    print("Production installation: DISABLED")
    print("GitHub publishing: DISABLED")

    check_safety_gates()

    run("GIT INTEGRITY", [
        "git", "diff", "--check"
    ])

    run("BUILD SERVER RELEASE", [
        sys.executable,
        str(INSTALLER / "build-versionary-release.py"),
        "--output", str(output),
    ], output / "server-build.log")

    manifests = sorted(output.glob("versionary-rc2-*.json"))
    if len(manifests) != 1:
        raise RuntimeError("Expected exactly one server manifest")

    manifest = manifests[0]
    metadata = json.loads(manifest.read_text())
    archive = output / metadata["archive"]

    if metadata.get("production_approved") is not False:
        raise RuntimeError("Production flag must be false")

    run("VERIFY SERVER ARCHIVE", [
        sys.executable,
        str(INSTALLER / "build-versionary-release.py"),
        "--verify-archive", str(archive),
        "--verify-manifest", str(manifest),
    ], output / "server-verify.log")

    kit = output / "versionary-beta-installation-kit.tar.gz"

    run("BUILD UNIFIED INSTALLATION KIT", [
        sys.executable,
        str(INSTALLER / "build-unified-installation-kit.py"),
        "--server-archive", str(archive),
        "--server-manifest", str(manifest),
        "--output", str(kit),
    ], output / "kit-build.log")

    verify_kit(kit, archive, manifest)

    run("FULL REGRESSION", [
        sys.executable, "-B", "-m", "unittest",
        "discover", "-s", "tests",
        "-p", "test_*.py", "-q",
    ], output / "regression.log")

    checksums = output / "SHA256SUMS"
    checksums.write_text("".join(
        f"{digest(path)}  {path.name}\n"
        for path in (archive, manifest, kit)
    ))

    result = {
        "status": "local_acceptance_passed",
        "production_approved": False,
        "deployment_permitted": False,
        "github_published": False,
        "server_archive": archive.name,
        "server_manifest": manifest.name,
        "unified_kit": kit.name,
        "checksums": "SHA256SUMS",
        "limitations": [
            "Publisher authenticity not established",
            "Real-system installer not integrated",
            "Crash-safe recovery not established",
            "No fresh VM upgrade acceptance performed",
        ],
    }

    (output / "acceptance.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )

    print("\n=== ACCEPTANCE SUMMARY ===")
    print("[PASS] Server release archive")
    print("[PASS] Unified installation kit")
    print("[PASS] Existing installer safety gates")
    print("[PASS] Full local regression")
    print("[PASS] SHA-256 checksums")
    print("[INFO] Output:", output)
    print("[INFO] Production approved: NO")
    print("[INFO] Installation performed: NO")
    print("[INFO] GitHub release published: NO")
    print("=== RELEASE ACCEPTANCE COMPLETE ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
