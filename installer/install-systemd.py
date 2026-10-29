#!/usr/bin/env python3
"""Install trusted agent systemd units without enabling services."""

import argparse
import importlib.util
import os
import stat
import sys
from contextlib import ExitStack
from pathlib import Path


HERE = Path(__file__).resolve().parent

UNITS = (
    "arby-patch-agent.service",
    "arby-patch-agent.timer",
)


def load_helper(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


directories = load_helper(
    "secure-directories.py", "arby_secure_directories"
)
files = load_helper(
    "secure-files.py", "arby_secure_files"
)


def install_units(root, source_dir=None):
    root = Path(root).absolute()
    source_dir = Path(source_dir or HERE / "systemd")

    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("Invalid installation root")

    root_info = root.stat()

    if root_info.st_uid != os.geteuid():
        raise RuntimeError("Unexpected installation root owner")

    if root_info.st_mode & 0o022:
        raise RuntimeError("Unsafe installation root permissions")

    if root == Path("/") and os.geteuid() != 0:
        raise RuntimeError("Production installation requires root")

    # Validate every source before modifying the destination.
    payloads = {}

    for name in UNITS:
        source = source_dir / name
        info = source.lstat()

        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"Invalid unit source: {name}")

        if info.st_mode & 0o022:
            raise RuntimeError(f"Unsafe unit source: {name}")

        if info.st_size > 65536:
            raise RuntimeError(f"Unit source too large: {name}")

        payloads[name] = source.read_bytes()

    with ExitStack() as stack:
        directory_fd = stack.enter_context(
            directories.secure_directory(
                root,
                "etc/systemd/system",
                create=True,
                mode=0o755,
            )
        )

        # Preflight every destination before creating any unit.
        for name, payload in payloads.items():
            try:
                fd = files.open_regular_file(
                    directory_fd, name
                )
            except FileNotFoundError:
                continue

            with os.fdopen(fd, "rb") as stream:
                existing = stream.read(65537)

            if existing != payload:
                raise RuntimeError(
                    f"Existing systemd unit differs: {name}"
                )

        # Install only after all existing units pass preflight.
        # Track new inodes so failures cannot remove preexisting units.
        created_units = []

        try:
            for name, payload in payloads.items():
                try:
                    fd = files.create_regular_file(
                        directory_fd, name, mode=0o644
                    )
                except FileExistsError:
                    fd = files.open_regular_file(
                        directory_fd, name
                    )

                    with os.fdopen(fd, "rb") as stream:
                        existing = stream.read(65537)

                    if existing != payload:
                        raise RuntimeError(
                            f"Existing systemd unit differs: {name}"
                        )

                    print(f"[OK] Existing unit preserved: {name}")
                    continue

                created_info = os.fstat(fd)
                created_units.append(
                    (name, created_info.st_dev, created_info.st_ino)
                )

                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())

                print(f"[OK] Installed systemd unit: {name}")

            os.fsync(directory_fd)

        except BaseException:
            for name, device, inode in reversed(created_units):
                try:
                    current = os.stat(
                        name,
                        dir_fd=directory_fd,
                        follow_symlinks=False,
                    )

                    if (
                        current.st_dev == device
                        and current.st_ino == inode
                    ):
                        os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass

            raise

    print("[OK] No systemd units enabled or started")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-dir")
    args = parser.parse_args()

    try:
        install_units(args.root, args.source_dir)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
