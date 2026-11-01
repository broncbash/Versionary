#!/usr/bin/env python3
"""Read-only, descriptor-based active-release content integrity verification.

Integrity is not authenticity, provenance, or rollback authorization.
This is not an atomic filesystem snapshot or a production authorization gate.
"""

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
from contextlib import ExitStack
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
POINTER_PATTERN = re.compile(r"releases/([0-9a-f]{64})/agent")


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked(fd, *, directory, label):
    info = os.fstat(fd)

    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RuntimeError(f"Unsafe ownership or permissions: {label}")

    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"Unsafe directory: {label}")
    else:
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RuntimeError(f"Unsafe release file: {label}")

    return info


def open_directory(stack, name, parent=None):
    try:
        if parent is None:
            fd = os.open(name, DIR_FLAGS)
        else:
            fd = os.open(name, DIR_FLAGS, dir_fd=parent)
    except OSError as exc:
        raise RuntimeError(
            f"Unsafe or inaccessible release directory: {name}"
        ) from exc

    stack.callback(os.close, fd)
    checked(fd, directory=True, label=str(name))
    return fd


def read_file(parent, name):
    try:
        fd = os.open(name, FILE_FLAGS, dir_fd=parent)
    except OSError as exc:
        raise RuntimeError(
            f"Unsafe or inaccessible release file: {name}"
        ) from exc

    try:
        before = checked(fd, directory=False, label=name)
        with os.fdopen(os.dup(fd), "rb") as stream:
            data = stream.read()
        after = checked(fd, directory=False, label=name)

        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise RuntimeError(f"Release file changed during read: {name}")

        return data
    finally:
        os.close(fd)


def check_cache(stack, release_fd):
    cache_fd = open_directory(stack, "__pycache__", release_fd)

    for name in os.listdir(cache_fd):
        if not name.endswith(".pyc") or name in (".", ".."):
            raise RuntimeError("Unexpected release bytecode entry")
        read_file(cache_fd, name)


def read_pointer(app_fd):
    info = os.stat("agent", dir_fd=app_fd, follow_symlinks=False)

    if not stat.S_ISLNK(info.st_mode):
        raise ValueError("Active release pointer is not a symlink")

    target = os.readlink("agent", dir_fd=app_fd)
    match = POINTER_PATTERN.fullmatch(target)

    if not match:
        raise ValueError("Unsafe active release target")

    return (match.group(1), info.st_dev, info.st_ino, target)


def verify_integrity(root):
    inspector = load(
        "active-release-inspection.py",
        "versionary_integrity_inspector",
    )
    atomic = load(
        "atomic-release.py",
        "versionary_integrity_atomic",
    )

    initial = inspector.inspect(root)

    response = {
        "product": "Versionary",
        "mode": "isolated-active-release-integrity",
        "active_release": initial["active_release"],
        "active_present": initial["active_present"],
        "integrity_verified": False,
        "authenticity_verified": False,
        "provenance_verified": False,
        "rollback_authorized": False,
        "changes_made": False,
        "production_approved": False,
    }

    root = Path(root).absolute()

    if root == Path("/"):
        raise ValueError("Live root forbidden")

    if not initial["active_present"]:
        response["status"] = "absent"
        return response

    with ExitStack() as stack:
        root_fd = open_directory(stack, root)
        opt_fd = open_directory(stack, "opt", root_fd)
        app_fd = open_directory(stack, "versionary-agent", opt_fd)

        pointer_before = read_pointer(app_fd)
        identifier = pointer_before[0]

        if identifier != initial["active_release"]:
            raise ValueError("Active release changed during inspection")

        releases_fd = open_directory(stack, "releases", app_fd)
        version_fd = open_directory(stack, identifier, releases_fd)
        release_fd = open_directory(stack, "agent", version_fd)

        release_before = os.fstat(release_fd)
        modules = {}

        for name in os.listdir(release_fd):
            if name == "__pycache__":
                check_cache(stack, release_fd)
                continue

            if (
                name in (".", "..")
                or not name.endswith(".py")
                or Path(name).name != name
            ):
                raise ValueError("Unexpected release entry")

            modules[name] = read_file(release_fd, name)

        if not modules:
            raise ValueError("Empty release")

        if atomic.release_id(modules) != identifier:
            raise ValueError("Active release integrity mismatch")

        release_after = os.fstat(release_fd)

        if (
            release_before.st_mtime_ns != release_after.st_mtime_ns
            or release_before.st_ctime_ns != release_after.st_ctime_ns
        ):
            raise RuntimeError("Release directory changed during inspection")

        if read_pointer(app_fd) != pointer_before:
            raise ValueError("Active release pointer changed during inspection")

        response["active_release"] = identifier
        response["integrity_verified"] = True
        response["status"] = "verified"
        response["module_count"] = len(modules)
        response["descriptor_based"] = True

    return response


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)

    try:
        result = verify_integrity(args.root)
    except (OSError, ValueError, RuntimeError) as exc:
        print(
            f"Release integrity verification refused: {exc}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
