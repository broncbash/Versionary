#!/usr/bin/env python3
"""Install the Versionary administrative CLI from a verified distribution.

Isolated beta roots only. No network, service activation, enrollment,
package-manager operations, or production installation.
"""
import argparse
import hashlib
import importlib.util
import os
import stat
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER = HERE / "build-agent-distribution.py"
DEFAULT_BUNDLE = (
    HERE / "dist/versionary-agent-distribution-26l.tar.gz"
)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verified_cli(bundle):
    """Verify the entire bundle before returning the CLI payload."""
    bundle = Path(bundle)

    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError("Distribution must be a regular file")

    builder = load_module(BUILDER, "versionary_distribution_builder")
    builder.verify(bundle)

    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) != 3:
            raise ValueError("Unexpected distribution member count")

        payloads = {}
        for member in members:
            if not member.isfile():
                raise ValueError("Unsafe distribution entry")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable distribution entry")
            with stream:
                payloads[member.name] = stream.read(member.size + 1)
            if len(payloads[member.name]) != member.size:
                raise ValueError("Distribution member size mismatch")

    cli = payloads["versionary_agent_cli.py"]
    agent_archive = payloads["versionary-agent.tar.gz"]

    # Verify the embedded agent archive against its existing strict
    # module allowlist, not merely the bundle's checksum manifest.
    validator = load_module(
        HERE / "validate-package.py",
        "versionary_embedded_agent_validator",
    )

    with tempfile.TemporaryDirectory() as temporary:
        archive_path = Path(temporary) / "agent.tar.gz"
        archive_path.write_bytes(agent_archive)
        validator.validate(archive_path)

    if not cli or len(cli) > 256 * 1024:
        raise ValueError("Invalid administrative CLI payload")

    return cli


def require_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"Unsafe directory: {path}")
    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError(f"Unsafe directory ownership/mode: {path}")


def install(root, bundle=DEFAULT_BUNDLE):
    """Install only into an existing isolated agent application root."""
    root = Path(root).absolute()

    if root == Path("/"):
        raise ValueError("Production installation remains disabled")

    # Verify the distribution before touching the installation tree.
    data = verified_cli(bundle)

    require_directory(root)

    opt = root / "opt"
    app = opt / "versionary-agent"

    require_directory(opt)
    require_directory(app)

    target = app / "versionary_agent_cli.py"

    try:
        existing = target.lstat()
    except FileNotFoundError:
        existing = None

    if existing is not None:
        if (
            not stat.S_ISREG(existing.st_mode)
            or existing.st_uid != os.geteuid()
            or existing.st_nlink != 1
            or existing.st_mode & 0o022
        ):
            raise ValueError("Unsafe existing CLI")

        if target.read_bytes() != data:
            raise ValueError(
                "Existing CLI differs; explicit upgrade required"
            )

        print("[OK] Identical administrative CLI preserved")
        return target

    # Exclusive creation: never replace an existing file.
    fd = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o644,
    )

    created_inode = os.fstat(fd).st_ino

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        if hashlib.sha256(target.read_bytes()).digest() != (
            hashlib.sha256(data).digest()
        ):
            raise RuntimeError("Installed CLI checksum mismatch")

    except BaseException:
        # Never delete a different file substituted during failure.
        try:
            current = target.lstat()
            if current.st_ino == created_inode:
                target.unlink()
        except FileNotFoundError:
            pass
        raise

    print("[OK] Verified distribution CLI installed")
    print("[OK] No services enabled")
    print("[OK] No registration attempted")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", type=Path,
                        default=DEFAULT_BUNDLE)
    args = parser.parse_args()

    try:
        install(args.root, args.distribution)
        return 0
    except (
        OSError, ValueError, RuntimeError, KeyError,
        tarfile.TarError,
    ) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
