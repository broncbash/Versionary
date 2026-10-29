"""Read-only integrity and idempotency audit of an isolated agent install.

Never invokes systemctl, connects to a server, changes permissions, or
modifies installation files. Intended for test roots, not production.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "installer/validate-package.py"
spec = importlib.util.spec_from_file_location("audit_agent_validator", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def audit(root, package):
    root = Path(root).absolute()
    package = Path(package)
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    try:
        info = root.lstat()
        safe_root = stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o022
    except OSError:
        safe_root = False
    check("safe_isolated_root", safe_root and root != Path("/"))
    if not safe_root or root == Path("/"):
        return {"ready": False, "changes_made": False, "checks": checks}

    app = root / "opt/arby-patch-agent"
    active = app / "agent"
    state = root / "var/lib/arby-patch-agent"
    config = root / "etc/arby-patch-agent/config.json"
    ca = root / "etc/arby-patch-agent/ca.crt"
    units = [root / "etc/systemd/system" / name for name in
             ("arby-patch-agent.service", "arby-patch-agent.timer")]
    try:
        modules = validator.load_modules(package)
        digest = hashlib.sha256()
        for name in sorted(modules):
            data = modules[name]
            digest.update(len(name.encode()).to_bytes(4, "big"))
            digest.update(name.encode())
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        identifier = digest.hexdigest()
        check("validated_archive", True)
    except (OSError, ValueError, Exception):
        identifier = None
        modules = {}
        check("validated_archive", False)

    try:
        link = active.lstat()
        link_target = os.readlink(active)
        valid_link = (stat.S_ISLNK(link.st_mode) and identifier is not None and
                      link_target == f"releases/{identifier}/agent")
        check("active_release_matches_archive", valid_link)
    except OSError:
        check("active_release_matches_archive", False)

    try:
        release = app / "releases" / identifier / "agent"
        actual = {p.name: p.read_bytes() for p in release.iterdir()
                  if p.is_file() and not p.is_symlink()}
        check("release_contents_match_archive", actual == modules and bool(modules) and
              set(p.name for p in release.iterdir()) == set(modules))
    except (OSError, TypeError):
        check("release_contents_match_archive", False)

    try:
        info = state.lstat()
        check("private_state", stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
              and info.st_uid == os.geteuid())
    except OSError:
        check("private_state", False)

    for name, path in (("agent_config", config), ("trusted_ca", ca)):
        try:
            info = path.lstat()
            check(name, stat.S_ISREG(info.st_mode) and info.st_size > 0)
        except OSError:
            check(name, False)
    for unit in units:
        try:
            info = unit.lstat()
            check(unit.name, stat.S_ISREG(info.st_mode) and
                  stat.S_IMODE(info.st_mode) == 0o644)
        except OSError:
            check(unit.name, False)
    return {"ready": all(c["ok"] for c in checks), "changes_made": False, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--package", required=True)
    args = parser.parse_args(argv)
    result = audit(args.root, args.package)
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
