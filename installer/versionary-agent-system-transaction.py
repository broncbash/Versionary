#!/usr/bin/env python3
"""Isolated Versionary installation transaction engine.

This module is not authorized for real-system installation.
It handles ordinary exceptions, not process crashes or power loss.
"""

import os
import stat
import tempfile
from pathlib import Path


class InstallationConflict(ValueError):
    pass


class InstallationRollbackError(RuntimeError):
    pass


def _relative(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Nonempty relative path required")

    path = Path(value)

    if (
        path.is_absolute()
        or any(part in (".", "..") for part in value.split("/"))
        or str(path) != value
    ):
        raise ValueError(f"Unsafe relative path: {value}")

    return path


def _existing_file(path, expected):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False

    if not stat.S_ISREG(info.st_mode):
        raise InstallationConflict(f"Unsafe destination: {path}")

    if info.st_nlink != 1:
        raise InstallationConflict(f"Hardlinked destination: {path}")

    if info.st_mode & 0o022:
        raise InstallationConflict(f"Writable destination: {path}")

    if info.st_size != len(expected) or path.read_bytes() != expected:
        raise InstallationConflict(f"Different destination: {path}")

    return True


def _check_parent_chain(root, relative):
    current = root

    for component in relative.parts[:-1]:
        current = current / component

        try:
            info = current.lstat()
        except FileNotFoundError:
            continue

        if not stat.S_ISDIR(info.st_mode):
            raise InstallationConflict(
                f"Unsafe parent directory: {current}"
            )

        if info.st_mode & 0o022:
            raise InstallationConflict(
                f"Writable parent directory: {current}"
            )


def _ensure_parent(root, target, created_dirs):
    missing = []
    cursor = target.parent

    while cursor != root:
        try:
            info = cursor.lstat()
        except FileNotFoundError:
            missing.append(cursor)
            cursor = cursor.parent
            continue

        if not stat.S_ISDIR(info.st_mode):
            raise InstallationConflict(
                f"Unsafe parent directory: {cursor}"
            )

        if info.st_mode & 0o022:
            raise InstallationConflict(
                f"Writable parent directory: {cursor}"
            )

        break

    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        created_dirs.append(directory)


def install_payloads(
    root,
    payloads,
    modes=None,
    fail_after=None,
    fail_staging_after=None,
):
    """Install payloads into an isolated root with exception rollback."""

    root = Path(root)

    if not root.is_absolute() or root == Path("/"):
        raise ValueError("An isolated absolute root is required")

    if root.is_symlink() or not root.is_dir():
        raise ValueError("Unsafe isolated root")

    modes = modes or {}
    validated = {}

    for relative, content in payloads.items():
        path = _relative(relative)

        if not isinstance(content, bytes):
            raise TypeError("Payloads must contain bytes")

        _check_parent_chain(root, path)

        target = root / path
        validated[relative] = (
            target,
            content,
            _existing_file(target, content),
        )

    staged = {}
    created_files = []
    created_dirs = []
    staging_count = 0

    try:
        # Stage all new files before publishing any of them.
        for relative, (target, content, exists) in validated.items():
            if exists:
                continue

            _ensure_parent(root, target, created_dirs)

            if (
                fail_staging_after is not None
                and staging_count >= fail_staging_after
            ):
                raise RuntimeError("Injected staging failure")

            fd, name = tempfile.mkstemp(
                prefix=".versionary-stage-",
                dir=target.parent,
            )
            stage = Path(name)
            staged[relative] = stage

            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.chmod(stage, modes.get(relative, 0o600))
            staging_count += 1

        # Publish with exclusive creation: never overwrite a new file.
        for relative, (target, content, exists) in validated.items():
            if exists:
                continue

            if fail_after is not None and len(created_files) >= fail_after:
                raise RuntimeError("Injected installation failure")

            stage = staged[relative]

            try:
                os.link(stage, target, follow_symlinks=False)
            except FileExistsError as exc:
                raise InstallationConflict(
                    f"Destination appeared during installation: {target}"
                ) from exc

            created_files.append(target)
            stage.unlink()
            del staged[relative]

        return {
            "created": len(created_files),
            "preserved": sum(
                exists for _, _, exists in validated.values()
            ),
        }

    except Exception:
        errors = []

        for target in reversed(created_files):
            try:
                target.unlink()
            except OSError as exc:
                errors.append(f"{target}: {exc}")

        for stage in staged.values():
            try:
                stage.unlink(missing_ok=True)
            except OSError as exc:
                errors.append(f"{stage}: {exc}")

        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                # Nonempty directories may contain external files.
                pass

        if errors:
            raise InstallationRollbackError(
                "Rollback incomplete: " + "; ".join(errors)
            )

        raise
