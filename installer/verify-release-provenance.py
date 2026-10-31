#!/usr/bin/env python3
"""Verify Versionary agent releases against an isolated Git checkout."""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
VERSION_RE = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:alpha|beta|rc)\.(?:0|[1-9]\d*))?\Z"
)
PACKAGE_NAME = "versionary-agent.tar.gz"


class ProvenanceError(Exception):
    pass


def git(*args, cwd=ROOT):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise ProvenanceError(
            f"Git command failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest(data):
    if not isinstance(data, dict):
        raise ProvenanceError("Manifest must be an object")

    expected = {
        "schema_version", "product", "component", "version",
        "git_commit", "package", "production_approved", "deployable",
    }
    if set(data) != expected:
        raise ProvenanceError("Unexpected manifest fields")

    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ProvenanceError("Unsupported manifest schema")

    if data["product"] != "Versionary" or data["component"] != "agent":
        raise ProvenanceError("Incorrect release identity")

    if not isinstance(data["version"], str) or not VERSION_RE.fullmatch(data["version"]):
        raise ProvenanceError("Invalid release version")

    if not isinstance(data["git_commit"], str) or not COMMIT_RE.fullmatch(data["git_commit"]):
        raise ProvenanceError("Invalid Git commit identity")

    if data["production_approved"] is not False or data["deployable"] is not False:
        raise ProvenanceError("Production authorization forbidden")

    package = data["package"]
    if not isinstance(package, dict) or set(package) != {
        "filename", "sha256", "modules"
    }:
        raise ProvenanceError("Invalid package metadata")

    if package["filename"] != PACKAGE_NAME:
        raise ProvenanceError("Unexpected package filename")

    if not isinstance(package["sha256"], str) or not DIGEST_RE.fullmatch(package["sha256"]):
        raise ProvenanceError("Invalid package checksum")

    if type(package["modules"]) is not int or package["modules"] != 13:
        raise ProvenanceError("Unexpected agent module count")

    return data


def load_release_module(checkout):
    path = checkout / "installer/release-metadata.py"
    spec = importlib.util.spec_from_file_location(
        "versionary_provenance_release_metadata", path
    )
    if spec is None or spec.loader is None:
        raise ProvenanceError("Cannot load release metadata verifier")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(manifest_path, package_path):
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProvenanceError("Manifest must be a regular file")

    if package_path.is_symlink() or not package_path.is_file():
        raise ProvenanceError("Package must be a regular file")

    manifest = validate_manifest(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )

    if sha256(package_path) != manifest["package"]["sha256"]:
        raise ProvenanceError("Release package checksum mismatch")

    commit = manifest["git_commit"]

    if git("rev-parse", "--verify", f"{commit}^{{commit}}") != commit:
        raise ProvenanceError("Manifest commit does not resolve exactly")

    failure = None
    cleanup_failure = None

    with tempfile.TemporaryDirectory(
        prefix="versionary-provenance-"
    ) as temporary:
        checkout = Path(temporary) / "checkout"
        rebuilt = Path(temporary) / PACKAGE_NAME
        added = False

        try:
            git("worktree", "add", "--detach", str(checkout), commit)
            added = True

            if git("rev-parse", "HEAD", cwd=checkout) != commit:
                raise ProvenanceError("Detached checkout commit mismatch")

            print("[OK] Exact Git commit checked out")

            result = subprocess.run(
                [
                    sys.executable,
                    "installer/build-agent-package.py",
                    "--output",
                    str(rebuilt),
                ],
                cwd=checkout,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )

            if result.returncode:
                raise ProvenanceError(
                    "Isolated package build failed: "
                    + result.stderr.strip()
                )

            if not rebuilt.is_file() or rebuilt.is_symlink():
                raise ProvenanceError("Rebuilt package missing")

            if sha256(rebuilt) != manifest["package"]["sha256"]:
                raise ProvenanceError("Rebuilt package checksum mismatch")

            if package_path.read_bytes() != rebuilt.read_bytes():
                raise ProvenanceError("Packages differ byte-for-byte")

            print("[OK] Byte-for-byte reproducibility confirmed")

            release = load_release_module(checkout)

            if not release.verify(manifest, rebuilt):
                raise ProvenanceError("Manifest verification failed")

            print("[OK] Manifest verified against rebuilt package")

        except Exception as exc:
            failure = exc

        finally:
            if added:
                try:
                    git(
                        "worktree",
                        "remove",
                        "--force",
                        str(checkout),
                    )
                except Exception as exc:
                    cleanup_failure = exc

    if failure is not None and cleanup_failure is not None:
        raise ProvenanceError(
            f"Verification failed: {failure}; "
            f"worktree cleanup also failed: {cleanup_failure}"
        )

    if cleanup_failure is not None:
        raise ProvenanceError(
            f"Worktree cleanup failed: {cleanup_failure}"
        )

    if failure is not None:
        raise ProvenanceError(str(failure))

    print("[OK] Temporary worktree removed")
    print("[PASS] Versionary release provenance verified")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        verify(args.manifest, args.package)
        return 0
    except (
        ProvenanceError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
