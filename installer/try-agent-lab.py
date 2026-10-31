#!/usr/bin/env python3
"""Hands-on isolated agent lab. Never deploys, enrolls, or starts services."""
import argparse
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workspace_guard(path):
    path = Path(path).absolute()
    if path == Path("/") or path.is_symlink():
        raise ValueError("Unsafe lab workspace")
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("Workspace must be an owner-controlled private directory (0700)")
    if any(path.iterdir()):
        raise ValueError("Workspace must be empty; refusing to overwrite")
    return path


def lab(workspace):
    workspace = workspace_guard(workspace)
    package = load("build-agent-package.py", "lab_builder").build(workspace / "agent.tar.gz")
    certs = load("generate-certificates.py", "lab_certs")
    certs.generate("127.0.0.1", workspace / "certificates")
    root = workspace / "isolated-root"
    root.mkdir(mode=0o700)
    stage = load("stage-beta.py", "lab_stage")
    args = dict(root=root, server="https://127.0.0.1:8443",
                ca_cert=workspace / "certificates/ca.crt", package=package)
    installed = stage.stage(**args)
    verified = stage.stage(**args, verify_only=True)
    inventory = load("installation-inventory.py", "lab_inventory").inspect(root)
    if installed["status"] != "staged" or verified["status"] != "verified":
        raise ValueError("Lab staging failed")
    return {"status": "ready", "mode": "offline-isolated-agent-lab",
            "workspace": str(workspace), "staged_root": str(root),
            "package": str(package), "inventory": inventory,
            "production_installed": False, "systemd_started": False,
            "agent_enrolled": False, "external_network_requests_made": False,
            "production_approved": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path,
                        help="Existing EMPTY private (0700) directory; retained for inspection")
    args = parser.parse_args(argv)
    try:
        if args.workspace:
            report = lab(args.workspace)
        else:
            with tempfile.TemporaryDirectory(prefix="versionary-lab-") as directory:
                report = lab(directory)
                report["workspace_retained"] = False
        if args.workspace:
            report["workspace_retained"] = True
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, "Lab refused: " + str(error) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
