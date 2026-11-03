#!/usr/bin/env python3
"""Validate a Versionary release without installing it."""

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def fail(message):
    raise RuntimeError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def select_release(directory):
    candidates = []

    for manifest in directory.glob("versionary-rc2-*.json"):
        try:
            metadata = json.loads(manifest.read_text())
        except (OSError, ValueError):
            continue

        if not isinstance(metadata.get("files"), dict):
            continue

        archive_name = metadata.get("archive")

        if not isinstance(archive_name, str):
            continue

        if Path(archive_name).name != archive_name:
            continue

        archive = directory / archive_name

        if archive.is_file():
            candidates.append((manifest, archive, metadata))

    if not candidates:
        fail("No RC2 release with a per-file manifest found")

    return max(candidates, key=lambda item: item[0].name)


def extract_verified(archive, metadata, destination):
    if metadata.get("production_approved") is not False:
        fail("Production approval flag is invalid")

    if sha256(archive.read_bytes()) != metadata.get("sha256"):
        fail("Archive checksum mismatch")

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
                or name not in expected
                or name.startswith("/")
                or "\\" in name
            ):
                fail("Unsafe archive member: " + name)

            seen.add(name)

            stream = tar.extractfile(member)

            if stream is None:
                fail("Unreadable archive member: " + name)

            data = stream.read()

            if sha256(data) != expected[name]["sha256"]:
                fail("File checksum mismatch: " + name)

            if len(data) != expected[name]["size"]:
                fail("File size mismatch: " + name)

            path = destination.joinpath(*pure.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    if seen != set(expected):
        fail("Archive and manifest file lists differ")

    if len(seen) != metadata.get("file_count"):
        fail("Archive file count mismatch")

    return seen


def local_modules(root):
    modules = {}

    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        parts = relative.with_suffix("").parts

        if parts[-1] == "__init__":
            name = ".".join(parts[:-1])
        else:
            name = ".".join(parts)

        if name:
            modules[name] = path

    return modules


def check_import_closure(root, repo):
    packaged = local_modules(root)
    available = local_modules(repo)

    packaged_roots = {name.split(".")[0] for name in packaged}
    project_roots = {name.split(".")[0] for name in available}

    missing = set()

    for module_name, path in packaged.items():
        tree = ast.parse(path.read_text(), filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                names = [node.module] if node.module else []
            else:
                continue

            for imported in names:
                top = imported.split(".")[0]

                if top in project_roots and top not in packaged_roots:
                    missing.add((module_name, imported))

    if missing:
        for source, imported in sorted(missing):
            print(f"MISSING_INTERNAL_IMPORT={source} -> {imported}")

        fail(f"{len(missing)} missing internal import dependencies")

    return len(packaged)


def runtime_imports(root):
    script = """
import importlib

modules = (
    "report_validation",
    "arby_scanners.models",
    "agent_registry",
    "versionary_https_beta",
    "agent.credentials",
)

for module in modules:
    importlib.import_module(module)
    print("IMPORT_PASS=" + module)
"""

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )

    if result.returncode:
        print(result.stdout[-2000:])
        print(result.stderr[-3500:])
        fail("Runtime import validation failed")

    print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-dir",
        default=str(
            Path.home() / "Projects/versionary-release-candidates"
        ),
    )
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parent.parent),
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    release_dir = Path(args.release_dir).resolve()

    manifest, archive, metadata = select_release(release_dir)

    print("=== VERSIONARY RC2 DEPENDENCY VALIDATION ===", flush=True)
    print("ARCHIVE=" + str(archive))

    with tempfile.TemporaryDirectory(
        prefix="versionary-rc2-dependencies-"
    ) as temp:
        root = Path(temp)

        seen = extract_verified(archive, metadata, root)

        print("ARCHIVE_INTEGRITY=PASS")
        print("EXTRACTED_FILES=" + str(len(seen)))

        count = check_import_closure(root, repo)

        print("INTERNAL_IMPORT_CLOSURE=PASS")
        print("PACKAGED_PYTHON_MODULES=" + str(count))

        runtime_imports(root)

        print("RUNTIME_IMPORTS=PASS")
        print("PACKAGE_VALIDATION=PASS")
        print("PRODUCTION_APPROVED=NO")
        print("INSTALL_EXECUTED=NO")
        print("BETA_VM_MODIFIED=NO")
        print("GITHUB_MODIFIED=NO")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("PACKAGE_VALIDATION=FAIL", file=sys.stderr)
        print("REASON=" + str(exc), file=sys.stderr)
        sys.exit(1)
