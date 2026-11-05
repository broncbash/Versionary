#!/usr/bin/env python3
"""Offline atomic publication of signed Versionary agent releases.

A successful publication creates an immutable-by-convention release
directory and atomically replaces the 'current' symlink.

This does not authorize production deployment or install an agent.
The publishing directory must be controlled by a trusted operator.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = (
    "versionary-agent.tar.gz",
    "release-manifest.json",
    "release-signature.json",
)

LIMITS = {
    FILES[0]: 100 * 1024 * 1024,
    FILES[1]: 1024 * 1024,
    FILES[2]: 16 * 1024,
}


class PublishError(Exception):
    pass


def load_tool(filename, name):
    path = ROOT / "installer" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PublishError("Verifier unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_bytes(path, limit):
    path = Path(path)
    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise PublishError("Input is not a regular file")
        if not 0 < info.st_size <= limit:
            raise PublishError("Invalid input size")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if not 0 < len(data) <= limit:
            raise PublishError("Input exceeds size limit")
        return data
    finally:
        os.close(fd)


def verified_inputs(package, manifest, signature, trusted_public):
    signing = load_tool("release-signing.py", "versionary_publish_signing")
    provenance = load_tool(
        "verify-release-provenance.py",
        "versionary_publish_manifest",
    )
    validator = load_tool(
        "validate-package.py",
        "versionary_publish_validator",
    )

    package_data = safe_bytes(package, LIMITS[FILES[0]])
    manifest_data = safe_bytes(manifest, LIMITS[FILES[1]])
    signature_data = safe_bytes(signature, LIMITS[FILES[2]])
    public_data = safe_bytes(trusted_public, 16 * 1024)

    with tempfile.TemporaryDirectory(prefix="versionary-verify-") as temp:
        base = Path(temp)
        paths = {}
        for filename, data in (
            (FILES[0], package_data),
            (FILES[1], manifest_data),
            (FILES[2], signature_data),
            ("trusted-public.pem", public_data),
        ):
            paths[filename] = base / filename
            paths[filename].write_bytes(data)

        signing.verify(
            paths[FILES[1]],
            paths[FILES[2]],
            paths["trusted-public.pem"],
        )

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise PublishError("Duplicate manifest field")
                result[key] = value
            return result

        metadata = provenance.validate_manifest(
            json.loads(manifest_data, object_pairs_hook=unique)
        )

        digest = hashlib.sha256(package_data).hexdigest()
        if digest != metadata["package"]["sha256"]:
            raise PublishError("Signed package checksum mismatch")

        if validator.validate(paths[FILES[0]]) != 13:
            raise PublishError("Invalid agent module count")

    return metadata, dict(zip(
        FILES,
        (package_data, manifest_data, signature_data),
    ))


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def require_private_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise PublishError("Publication root must be a real directory")
    if info.st_mode & 0o022:
        raise PublishError("Publication root must not be group/world writable")


def publish(destination, package, manifest, signature, trusted_public):
    metadata, contents = verified_inputs(
        package, manifest, signature, trusted_public
    )

    destination = Path(destination)
    if not destination.is_absolute():
        raise PublishError("Destination must be absolute")

    require_private_directory(destination)

    releases = destination / "releases"
    if not releases.exists() and not releases.is_symlink():
        releases.mkdir(mode=0o700)

    require_private_directory(releases)

    release_id = metadata["package"]["sha256"]
    final = releases / release_id

    lock_path = destination / ".publish.lock"
    lock_fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )

    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise PublishError("Invalid publication lock")

        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        if final.exists() or final.is_symlink():
            raise PublishError("Release already exists; refusing overwrite")

        staging = Path(tempfile.mkdtemp(
            prefix=".staging-",
            dir=releases,
        ))

        try:
            for filename, data in contents.items():
                target = staging / filename
                with target.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                target.chmod(0o444)

            fsync_directory(staging)

            os.rename(staging, final)
            fsync_directory(releases)

        finally:
            if staging.exists():
                shutil.rmtree(staging)

        pointer_temp = destination / (
            ".current-" + release_id[:16]
        )

        if pointer_temp.exists() or pointer_temp.is_symlink():
            raise PublishError("Temporary pointer already exists")

        os.symlink("releases/" + release_id, pointer_temp)

        try:
            os.replace(pointer_temp, destination / "current")
            fsync_directory(destination)
        finally:
            if pointer_temp.is_symlink():
                pointer_temp.unlink()

    finally:
        os.close(lock_fd)

    print("[PASS] Signed release published atomically")
    print("Release ID:", release_id)
    print("Version:", metadata["version"])
    print("Active pointer:", destination / "current")
    print("Production deployment remains disabled")
    return release_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--signature", required=True, type=Path)
    parser.add_argument("--trusted-public", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        publish(
            args.destination,
            args.package,
            args.manifest,
            args.signature,
            args.trusted_public,
        )
        return 0
    except (PublishError, OSError, ValueError, TypeError) as exc:
        print("[FAIL]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
