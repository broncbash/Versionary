#!/usr/bin/env python3
"""Versionary offline isolated-root installer coordinator.

Development-only. Never installs into /, starts services,
enrolls agents, or enables timers.
"""
import argparse
import importlib.util
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BUNDLE = (
    HERE / "dist/versionary-agent-distribution-26l.tar.gz"
)


def helper(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# One module instance keeps exception classes consistent.
CONFIG = helper(
    "../agent/config.py",
    "versionary_offline_config",
)


def check_root(root):
    root = Path(root).absolute()

    if root == Path("/"):
        raise ValueError("Production installation is disabled")

    info = root.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Root must be a real directory")

    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError("Unsafe installation root")

    return root


def run_helper(script, *arguments):
    subprocess.run(
        [sys.executable, str(HERE / script), *map(str, arguments)],
        check=True,
    )


def install(root, bundle, server, ca_cert):
    root = check_root(root)
    bundle = Path(bundle)
    ca_cert = Path(ca_cert)

    cli = helper(
        "install-agent-cli.py",
        "versionary_verified_cli",
    )

    # Validate the complete distribution before installation.
    cli.verified_cli(bundle)

    # Validate configuration and CA before installing agent files.
    CONFIG.validate_server(server)

    if ca_cert.is_symlink() or not ca_cert.is_file():
        raise ValueError("CA must be a regular file")

    if ca_cert.stat().st_size > 1024 * 1024:
        raise ValueError("CA file exceeds size limit")

    # Validate X.509 CA semantics before any installation helper runs.
    # Reuse the CA installer's existing certificate trust checks.
    ca_installer = helper(
        "install-ca.py",
        "versionary_offline_ca_preflight",
    )
    ca_installer.validate_ca(ca_cert.read_bytes())

    print("[OK] Distribution and inputs validated", flush=True)

    with tempfile.TemporaryDirectory() as temporary:
        archive_path = Path(temporary) / "agent.tar.gz"

        with tarfile.open(bundle, "r:gz") as archive:
            member = archive.getmember("versionary-agent.tar.gz")
            stream = archive.extractfile(member)

            if stream is None:
                raise ValueError("Missing embedded agent archive")

            with stream:
                archive_path.write_bytes(stream.read())

        run_helper(
            "install-files.py",
            archive_path,
            "--root", root,
        )

        cli.install(root, bundle)

        run_helper(
            "install-ca.py",
            ca_cert,
            "--root", root,
        )

        run_helper(
            "setup-config.py",
            "--root", root,
            "--server", server,
        )

        run_helper(
            "install-systemd.py",
            "--root", root,
        )

    print("[OK] Offline installation stages completed")
    print("[OK] No registration or enrollment performed")
    print("[OK] No services or timers activated")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--distribution",
        default=str(DEFAULT_BUNDLE),
    )
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    args = parser.parse_args()

    try:
        install(
            args.root,
            args.distribution,
            args.server,
            args.ca_cert,
        )
        return 0
    except (
        OSError,
        ValueError,
        RuntimeError,
        CONFIG.ConfigurationError,
        subprocess.CalledProcessError,
        tarfile.TarError,
    ) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
