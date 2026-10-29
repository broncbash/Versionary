"""Descriptor-based directory traversal for ARBY PATCH AGENT."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def secure_directory(root, relative, *, create=False, mode=0o755):
    """Open a directory beneath root without following symlinks.

    Existing components must belong to the effective user and must
    not be writable by group or others.

    Missing components are created only when create=True.
    The final directory descriptor remains open for the caller.
    """
    if (
        not isinstance(mode, int)
        or isinstance(mode, bool)
        or mode < 0
        or mode > 0o777
        or mode & 0o022
    ):
        raise ValueError("Unsafe directory creation mode")

    root = Path(root)
    relative = Path(relative)

    if relative.is_absolute() or not relative.parts:
        raise ValueError("Expected a nonempty relative directory path")

    if any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError("Unsafe relative directory path")

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    fd = os.open(root, flags)

    try:
        def check(descriptor):
            info = os.fstat(descriptor)

            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError("Unsafe directory type")

            if info.st_uid != os.geteuid():
                raise RuntimeError("Unexpected directory owner")

            if info.st_mode & 0o022:
                raise RuntimeError("Unsafe directory permissions")

        check(fd)

        for part in relative.parts:
            if part in ("", ".", ".."):
                raise ValueError("Unsafe path component")

            created = False

            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                    created = True
                except FileExistsError:
                    pass

            next_fd = os.open(part, flags, dir_fd=fd)

            try:
                check(next_fd)

                if created:
                    os.fchmod(next_fd, mode)
                    check(next_fd)

            except BaseException:
                os.close(next_fd)
                raise

            os.close(fd)
            fd = next_fd

        yield fd

    finally:
        os.close(fd)
