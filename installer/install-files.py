#!/usr/bin/env python3
"""Install ARBY PATCH AGENT files into an isolated root."""

import argparse
import importlib.util
import os
import stat
import sys
import tarfile
from pathlib import Path


VALIDATOR_PATH = (
    Path(__file__).resolve().parent
    / "validate-package.py"
)

spec = importlib.util.spec_from_file_location(
    "arby_package_validator",
    VALIDATOR_PATH,
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

ATOMIC_RELEASE_PATH = (
    Path(__file__).resolve().parent
    / "atomic-release.py"
)

atomic_spec = importlib.util.spec_from_file_location(
    "arby_atomic_release", ATOMIC_RELEASE_PATH
)
atomic_release = importlib.util.module_from_spec(atomic_spec)
atomic_spec.loader.exec_module(atomic_release)

from contextlib import ExitStack

DIRECTORY_HELPER_PATH = (
    Path(__file__).resolve().parent
    / "secure-directories.py"
)

directory_spec = importlib.util.spec_from_file_location(
    "arby_secure_directories",
    DIRECTORY_HELPER_PATH,
)
secure_directories = importlib.util.module_from_spec(
    directory_spec
)
directory_spec.loader.exec_module(secure_directories)


MODULES = {
    "__main__.py",
    "config.py",
    "arby_patch_agent.py",
    "credentials.py",
    "enrollment_client.py",
    "enrollment_crypto.py",
    "enrollment_http.py",
    "enrollment_journal.py",
    "enrollment_keys.py",
    "heartbeat.py",
    "identity.py",
    "registration.py",
    "reporting.py",
}


def require_safe_directory(path, root):
    """Reject symlinks and non-directory path components."""

    relative = path.relative_to(root)
    current = root

    for part in relative.parts:
        current = current / part

        if current.is_symlink():
            raise RuntimeError(
                f"Symlinked installation path: {current}"
            )

        if current.exists() and not current.is_dir():
            raise RuntimeError(
                f"Not a directory: {current}"
            )


def require_secure_install_root(root):
    """Require a trusted, real installation-root directory."""
    root = Path(root)

    try:
        info = root.lstat()
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Installation root does not exist: {root}"
        ) from error

    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(
            f"Installation root is not a real directory: {root}"
        )

    if info.st_uid != os.geteuid():
        raise RuntimeError(
            f"Unexpected installation root owner: {root}"
        )

    if info.st_mode & 0o022:
        raise RuntimeError(
            f"Unsafe installation root permissions: {root}"
        )


def require_secure_ancestors(path, root):
    """Validate existing directory components beneath the install root."""
    path = Path(path).absolute()
    root = Path(root).absolute()

    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            "Installation path escapes the installation root"
        ) from error

    current = root
    expected_uid = os.geteuid()

    for part in relative.parts[:-1]:
        current = current / part

        try:
            info = current.lstat()
        except FileNotFoundError:
            continue

        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(
                f"Unsafe installation ancestor: {current}"
            )

        if info.st_uid != expected_uid:
            raise RuntimeError(
                f"Unexpected ancestor owner: {current}"
            )

        if info.st_mode & 0o022:
            raise RuntimeError(
                f"Writable installation ancestor: {current}"
            )


def require_production_root(root):
    """Require root privileges when installing into the real filesystem."""
    root = Path(root).absolute()

    if root == Path("/") and os.geteuid() != 0:
        raise PermissionError(
            "Production installation requires root privileges"
        )


def require_secure_app_directory(app):
    """Reject an application directory with unsafe ownership or modes."""
    app = Path(app)
    info = app.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(
            f"Application path is not a real directory: {app}"
        )

    if info.st_uid != os.geteuid():
        raise RuntimeError(
            f"Unexpected application directory owner: {app}"
        )

    if info.st_mode & 0o022:
        raise RuntimeError(
            f"Unsafe application directory permissions: {app}"
        )


def install(archive_path, root):
    """Install validated modules using an atomic release transaction."""
    modules = validator.load_modules(archive_path)

    if set(modules) != MODULES:
        raise ValueError("Validated module set does not match installer")

    root = Path(root).absolute()
    require_production_root(root)
    require_secure_install_root(root)

    app = root / "opt/arby-patch-agent"
    state = root / "var/lib/arby-patch-agent"
    config = root / "etc/arby-patch-agent"

    for directory in (app, state, config):
        require_safe_directory(directory, root)
        require_secure_ancestors(directory, root)

    agent_dir = app / "agent"

    if agent_dir.is_symlink():
        pass
    elif agent_dir.exists():
        raise RuntimeError(
            "Legacy agent directory requires explicit migration"
        )

    with ExitStack() as stack:
        stack.enter_context(
            secure_directories.secure_directory(
                root,
                "opt/arby-patch-agent",
                create=True,
                mode=0o755,
            )
        )

        stack.enter_context(
            secure_directories.secure_directory(
                root,
                "var/lib/arby-patch-agent",
                create=True,
                mode=0o700,
            )
        )

        stack.enter_context(
            secure_directories.secure_directory(
                root,
                "etc/arby-patch-agent",
                create=True,
                mode=0o755,
            )
        )

        state_info = state.stat(follow_symlinks=False)

        if stat.S_IMODE(state_info.st_mode) != 0o700:
            raise RuntimeError(
                "Agent state directory must have permissions 0700"
            )

        identifier = atomic_release.install_release(
            app, modules
        )

    print(f"[OK] Installed {len(modules)} agent modules")
    print(f"[OK] Release: {identifier}")
    print(f"[OK] Application: {app}")
    print(f"[OK] Persistent state preserved: {state}")
    print(f"[OK] Configuration directory: {config}")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    try:
        install(args.archive, args.root)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        print(f"[ERROR] Installation failed: {exc}",
              file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
