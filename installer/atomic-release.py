"""Atomic release staging for ARBY PATCH AGENT.

This module does not install services or activate agents.
"""

import hashlib
import os
import re
import stat
import tempfile
import importlib.util
from pathlib import Path

LOCK_HELPER_PATH = (
    Path(__file__).resolve().parent
    / "secure-install-lock.py"
)

lock_spec = importlib.util.spec_from_file_location(
    "arby_secure_install_lock",
    LOCK_HELPER_PATH,
)
secure_install_lock = importlib.util.module_from_spec(
    lock_spec
)
lock_spec.loader.exec_module(secure_install_lock)



def require_safe_path(path, *, directory=True):
    """Require correct ownership, type, and safe permissions."""
    path = Path(path)
    info = path.lstat()

    expected_uid = os.geteuid()

    if info.st_uid != expected_uid:
        raise RuntimeError(f"Unexpected owner: {path}")

    if info.st_mode & 0o022:
        raise RuntimeError(f"Unsafe permissions: {path}")

    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"Unsafe directory: {path}")
    else:
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"Unsafe regular file: {path}")

        if info.st_nlink != 1:
            raise RuntimeError(f"Hardlinked file: {path}")


def sync_directory(path):
    """Persist directory metadata to disk."""
    fd = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


from contextlib import contextmanager
import fcntl


@contextmanager
def install_lock(app):
    """Hold an exclusive installer lock across staging and activation."""
    app = Path(app)
    require_safe_path(app)

    lock_path = app / ".install.lock"

    fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )

    try:
        info = os.fstat(fd)

        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("Installer lock is not a regular file")

        if info.st_uid != os.geteuid():
            raise RuntimeError("Installer lock has unsafe ownership")

        if info.st_mode & 0o077:
            raise RuntimeError("Installer lock has unsafe permissions")

        if info.st_nlink != 1:
            raise RuntimeError("Installer lock has unsafe link count")

        fcntl.flock(fd, fcntl.LOCK_EX)

        def verify_lock_identity():
            descriptor = os.fstat(fd)

            try:
                pathname = lock_path.lstat()
            except FileNotFoundError as error:
                raise RuntimeError(
                    "Installer lock pathname disappeared"
                ) from error

            if (
                descriptor.st_dev != pathname.st_dev
                or descriptor.st_ino != pathname.st_ino
                or not stat.S_ISREG(pathname.st_mode)
                or pathname.st_nlink != 1
            ):
                raise RuntimeError(
                    "Installer lock pathname was replaced"
                )

        try:
            verify_lock_identity()
            try:
                yield
            finally:
                verify_lock_identity()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)

def release_id(modules):
    """Derive a deterministic ID from all module contents."""
    digest = hashlib.sha256()

    for name in sorted(modules):
        data = modules[name]
        digest.update(len(name.encode()).to_bytes(4, "big"))
        digest.update(name.encode())
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)

    return digest.hexdigest()


def stage_release(app, modules):
    """Stage an immutable release without activating it."""
    app = Path(app)
    releases = app / "releases"
    identifier = release_id(modules)
    target = releases / identifier

    require_safe_path(app)

    if releases.is_symlink():
        raise RuntimeError("Symlinked releases directory")

    releases.mkdir(exist_ok=True)
    require_safe_path(releases)

    if target.is_symlink():
        raise RuntimeError("Symlinked release destination")

    if target.exists():
        if not target.is_dir():
            raise RuntimeError("Invalid release destination")

        require_safe_path(target)

        existing = target / "agent"
        require_safe_path(existing)

        actual = {}

        for entry in existing.iterdir():
            info = entry.lstat()

            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError(
                    "Unexpected non-regular release entry"
                )

            if entry.name not in modules:
                raise RuntimeError(
                    "Unexpected release module"
                )

            if info.st_nlink != 1:
                raise RuntimeError(
                    "Hardlinked release module"
                )

            require_safe_path(entry, directory=False)
            actual[entry.name] = entry.read_bytes()

        if actual != modules:
            raise RuntimeError("Existing release content differs")

        return identifier

    with tempfile.TemporaryDirectory(
        prefix=".stage-",
        dir=releases,
    ) as temporary:
        staged = Path(temporary)
        agent = staged / "agent"
        agent.mkdir(mode=0o755)

        for name, data in modules.items():
            if Path(name).name != name or not name.endswith(".py"):
                raise ValueError("Unsafe module name")

            destination = agent / name

            with destination.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())

            destination.chmod(0o644)

        os.chmod(agent, 0o755)
        os.chmod(staged, 0o755)

        sync_directory(agent)
        sync_directory(staged)

        os.rename(staged, target)
        sync_directory(releases)

    return identifier



def validate_release_identifier(identifier):
    """Accept only canonical SHA-256 release identifiers."""
    if not isinstance(identifier, str):
        raise ValueError("Release identifier must be a string")

    if re.fullmatch(r"[0-9a-f]{64}", identifier) is None:
        raise ValueError("Invalid release identifier")

    return identifier


def activate_release(app, identifier):
    """Atomically switch the active agent symlink."""
    identifier = validate_release_identifier(identifier)

    app = Path(app)
    active = app / "agent"
    target = app / "releases" / identifier / "agent"

    require_safe_path(app)
    require_safe_path(app / "releases")
    require_safe_path(app / "releases" / identifier)
    require_safe_path(target)

    modules = {}

    for entry in target.iterdir():
        require_safe_path(entry, directory=False)

        if not entry.name.endswith(".py"):
            raise RuntimeError("Unexpected release entry")

        modules[entry.name] = entry.read_bytes()

    if not modules:
        raise RuntimeError("Empty release")

    if release_id(modules) != identifier:
        raise RuntimeError("Release integrity verification failed")

    if active.exists() and not active.is_symlink():
        raise RuntimeError("Legacy agent directory requires migration")

    import secrets

    # Create the symlink exclusively, without a file-to-symlink gap.
    for _ in range(10):
        temporary = app / f".agent-next-{secrets.token_hex(16)}"

        try:
            os.symlink(
                f"releases/{identifier}/agent",
                temporary,
            )
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError("Unable to reserve activation path")

    try:
        sync_directory(app)
        os.replace(temporary, active)
        sync_directory(app)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def install_release(app, modules):
    """Stage and activate a release under one exclusive installer lock."""
    app = Path(app)
    require_safe_path(app)

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    app_fd = os.open(app, flags)

    try:
        require_safe_path(app)

        with secure_install_lock.install_lock_fd(app_fd):
            identifier = stage_release(app, modules)
            activate_release(app, identifier)
            return identifier
    finally:
        os.close(app_fd)
