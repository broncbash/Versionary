"""Descriptor-relative installation lock.

Does not deploy agents, install services, or modify production.
"""

import fcntl
import os
import stat
from contextlib import contextmanager


LOCK_NAME = ".install.lock"


def verify_lock(fd):
    """Validate the opened lock file."""
    info = os.fstat(fd)

    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Installer lock is not a regular file")

    if info.st_uid != os.geteuid():
        raise RuntimeError("Installer lock has unsafe ownership")

    if info.st_mode & 0o077:
        raise RuntimeError("Installer lock has unsafe permissions")

    if info.st_nlink != 1:
        raise RuntimeError("Installer lock has unsafe hardlink count")

    return info


def verify_lock_identity(directory_fd, lock_fd):
    """Ensure the lock pathname still refers to our locked inode."""
    descriptor = verify_lock(lock_fd)

    try:
        pathname = os.stat(
            LOCK_NAME,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Installer lock pathname disappeared"
        ) from error

    if (
        not stat.S_ISREG(pathname.st_mode)
        or pathname.st_dev != descriptor.st_dev
        or pathname.st_ino != descriptor.st_ino
        or pathname.st_nlink != 1
    ):
        raise RuntimeError(
            "Installer lock pathname was replaced"
        )


@contextmanager
def install_lock_fd(directory_fd):
    """Hold an exclusive lock relative to a trusted directory fd."""
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
        | os.O_NONBLOCK
    )

    fd = os.open(
        LOCK_NAME,
        flags,
        0o600,
        dir_fd=directory_fd,
    )

    try:
        verify_lock(fd)

        fcntl.flock(fd, fcntl.LOCK_EX)

        try:
            verify_lock_identity(directory_fd, fd)

            try:
                yield
            finally:
                verify_lock_identity(directory_fd, fd)

        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)

    finally:
        os.close(fd)
