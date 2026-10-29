"""Descriptor-relative secure file operations for the agent installer.

This module does not deploy agents or modify services.
"""

import os
import stat


def require_safe_name(name):
    """Accept only a single, ordinary filesystem component."""
    if (
        not isinstance(name, str)
        or not name
        or name in (".", "..")
        or "/" in name
        or "\x00" in name
    ):
        raise ValueError("Unsafe filename")

    return name


def require_safe_mode(mode):
    """Reject unsafe file creation permissions."""
    if (
        not isinstance(mode, int)
        or isinstance(mode, bool)
        or mode < 0
        or mode > 0o777
        or mode & 0o022
    ):
        raise ValueError("Unsafe file mode")

    return mode


def verify_regular_file(fd):
    """Verify an opened file without trusting its pathname."""
    info = os.fstat(fd)

    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Not a regular file")

    if info.st_uid != os.geteuid():
        raise RuntimeError("Unexpected file owner")

    if info.st_mode & 0o022:
        raise RuntimeError("Unsafe file permissions")

    if info.st_nlink != 1:
        raise RuntimeError("Unsafe file hardlink count")


def create_regular_file(directory_fd, name, *, mode=0o600):
    """Exclusively create a regular file beneath a trusted directory."""
    name = require_safe_name(name)
    mode = require_safe_mode(mode)

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    # Start private regardless of the caller's requested final mode.
    fd = os.open(
        name,
        flags,
        0o600,
        dir_fd=directory_fd,
    )

    try:
        verify_regular_file(fd)

        # Apply the final mode through the open descriptor.
        os.fchmod(fd, mode)

        verify_regular_file(fd)
        return fd

    except BaseException:
        os.close(fd)
        raise


def open_regular_file(directory_fd, name):
    """Open an existing regular file without following symlinks."""
    name = require_safe_name(name)

    flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | os.O_NONBLOCK
        | os.O_CLOEXEC
    )

    fd = os.open(
        name,
        flags,
        dir_fd=directory_fd,
    )

    try:
        verify_regular_file(fd)
        return fd

    except BaseException:
        os.close(fd)
        raise
