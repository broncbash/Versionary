#!/usr/bin/env python3
"""Offline Versionary agent release manifest generation and verification."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "installer/release-version.txt"
VERSION_PATTERN = re.compile(r"0|[1-9]\d*")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")


def release_version():
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(
        r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-(?:alpha|beta|rc)\.(0|[1-9]\d*))?",
        version,
    ):
        raise ValueError("Invalid release version")
    return version


def git(*args):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise ValueError(f"Git verification failed: {' '.join(args)}")
    return result.stdout.strip()


def committed_identity():
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Tracked source contains uncommitted changes")

    commit = git("rev-parse", "--verify", "HEAD^{commit}")
    if not SHA_PATTERN.fullmatch(commit):
        raise ValueError("Invalid Git commit identity")

    return commit


def package_digest(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Package must be a regular non-symlink file")

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def package_modules(path):
    import importlib.util

    validator_path = ROOT / "installer/validate-package.py"
    spec = importlib.util.spec_from_file_location(
        "versionary_release_package_validator", validator_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(path)


def generate(package):
    version = release_version()
    commit = committed_identity()
    count = package_modules(package)
    digest = package_digest(package)

    return {
        "schema_version": 1,
        "product": "Versionary",
        "component": "agent",
        "version": version,
        "git_commit": commit,
        "package": {
            "filename": Path(package).name,
            "sha256": digest,
            "modules": count,
        },
        "production_approved": False,
        "deployable": False,
    }


def verify(manifest, package):
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")

    if set(manifest) != {
        "schema_version", "product", "component", "version",
        "git_commit", "package", "production_approved", "deployable",
    }:
        raise ValueError("Unexpected manifest fields")

    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("Unsupported manifest schema")

    if manifest["product"] != "Versionary" or manifest["component"] != "agent":
        raise ValueError("Incorrect product identity")

    if manifest["production_approved"] is not False or manifest["deployable"] is not False:
        raise ValueError("Production authorization is forbidden")

    expected = generate(package)

    if manifest != expected:
        raise ValueError("Release manifest does not match committed source and package")

    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.output and args.verify:
            raise ValueError("Choose generation or verification")

        if args.verify:
            manifest = json.loads(args.verify.read_text(encoding="utf-8"))
            verify(manifest, args.package)
            print("[OK] Versionary release manifest verified")
            return 0

        manifest = generate(args.package)
        rendered = json.dumps(manifest, indent=2) + "\n"

        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("Refusing to overwrite existing manifest")
            args.output.write_text(rendered, encoding="utf-8")
            print(f"[OK] Release manifest written: {args.output}")
        else:
            print(rendered, end="")

        return 0

    except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
