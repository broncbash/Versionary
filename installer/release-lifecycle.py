#!/usr/bin/env python3
"""Offline, verified Versionary release activation and rollback.

Does not install agents, start services, or authorize deployment.
"""

import argparse
import fcntl
import importlib.util
import os
import re
import stat
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
RELEASE_ID = re.compile(r"[0-9a-f]{64}\Z")


class LifecycleError(Exception):
    pass


def load_publisher():
    path = HERE / "publish-agent-release.py"
    spec = importlib.util.spec_from_file_location(
        "versionary_lifecycle_publisher", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_root(root):
    root = Path(root)

    if not root.is_absolute():
        raise LifecycleError("Publication root must be absolute")

    info = root.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise LifecycleError("Publication root must be a real directory")

    if info.st_mode & 0o022:
        raise LifecycleError("Unsafe publication root permissions")

    releases = root / "releases"
    info = releases.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise LifecycleError("Releases must be a real directory")

    if info.st_mode & 0o022:
        raise LifecycleError("Unsafe releases directory permissions")

    return root, releases


def validate_release_id(release_id):
    if not RELEASE_ID.fullmatch(release_id):
        raise LifecycleError("Invalid release ID")


def verify_release(root, release_id, trusted_public):
    validate_release_id(release_id)

    root, releases = validate_root(root)
    directory = releases / release_id

    info = directory.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise LifecycleError("Release must be a real directory")

    if info.st_mode & 0o022:
        raise LifecycleError("Unsafe release directory permissions")

    publisher = load_publisher()

    metadata, contents = publisher.verified_inputs(
        directory / "versionary-agent.tar.gz",
        directory / "release-manifest.json",
        directory / "release-signature.json",
        trusted_public,
    )

    import hashlib

    digest = hashlib.sha256(
        contents["versionary-agent.tar.gz"]
    ).hexdigest()

    if digest != release_id:
        raise LifecycleError("Release directory ID mismatch")

    return metadata


def active_release(root):
    root, _ = validate_root(root)
    pointer = root / "current"

    if not pointer.is_symlink():
        if pointer.exists():
            raise LifecycleError("Current pointer is not a symlink")
        return None

    target = os.readlink(pointer)
    prefix = "releases/"

    if not target.startswith(prefix):
        raise LifecycleError("Unsafe current pointer target")

    release_id = target[len(prefix):]
    validate_release_id(release_id)

    return release_id


def activate(root, release_id, trusted_public):
    """Verify a stored release and atomically activate it.

    The publication lock is held during verification and pointer
    replacement, preventing cooperating publishers and activators
    from switching the pointer concurrently.
    """
    validate_release_id(release_id)
    root, _ = validate_root(root)

    lock_path = root / ".publish.lock"

    fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )

    try:
        info = os.fstat(fd)

        if not stat.S_ISREG(info.st_mode):
            raise LifecycleError("Invalid publication lock")

        fcntl.flock(fd, fcntl.LOCK_EX)

        metadata = verify_release(
            root, release_id, trusted_public
        )

        previous = active_release(root)

        if previous == release_id:
            return previous

        pointer = root / "current"

        if pointer.exists() and not pointer.is_symlink():
            raise LifecycleError("Unsafe current pointer")

        temporary = root / (
            ".activate-" + release_id[:16]
        )

        if temporary.exists() or temporary.is_symlink():
            raise LifecycleError("Temporary activation pointer exists")

        os.symlink(
            "releases/" + release_id,
            temporary,
        )

        try:
            os.replace(temporary, pointer)

            directory_fd = os.open(
                root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        finally:
            if temporary.is_symlink():
                temporary.unlink()

        print("[PASS] Verified release activated")
        print("Release:", release_id)
        print("Previous:", previous or "none")
        print("Version:", metadata["version"])
        print("Production deployment remains disabled")

        return previous

    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "command",
        choices=("status", "verify", "activate"),
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--release-id")
    parser.add_argument("--trusted-public", type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            print("Active release:", active_release(args.root) or "none")
            return 0

        if not args.release_id or not args.trusted_public:
            parser.error(
                "verify/activate require --release-id "
                "and --trusted-public"
            )

        if args.command == "verify":
            metadata = verify_release(
                args.root,
                args.release_id,
                args.trusted_public,
            )
            print("[PASS] Stored release verified")
            print("Version:", metadata["version"])
            return 0

        activate(
            args.root,
            args.release_id,
            args.trusted_public,
        )
        return 0

    except (LifecycleError, OSError, ValueError, TypeError) as exc:
        print("[FAIL]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
