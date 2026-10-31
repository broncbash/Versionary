#!/usr/bin/env python3
"""VERSIONARY AGENT v0.1 — read-only Linux update scanner."""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys


APT_PATTERN = re.compile(
    r"^([^/\s]+)/(\S+)\s+(\S+)\s+\S+\s+"
    r"\[upgradable from: (.+)\]$"
)


def detect_platform():
    """Detect the host package-management platform."""

    values = {}

    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    values[key] = value.strip('"')
    except OSError:
        pass

    distro = values.get("ID", "").lower()
    family = values.get("ID_LIKE", "").lower().split()

    if distro == "arch" or "arch" in family:
        return "arch"

    if distro in ("debian", "ubuntu") or "debian" in family:
        return "debian"

    raise RuntimeError(
        f"Unsupported Linux distribution: {distro or 'unknown'}"
    )


def run_command(command):
    """Execute an update-query command without a shell."""

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(str(exc)) from exc


def scan_arch():
    """Query Arch updates without modifying the live Pacman database."""

    if not shutil.which("checkupdates"):
        raise RuntimeError(
            "checkupdates not found; install pacman-contrib"
        )

    result = run_command(["checkupdates"])

    if result.returncode == 2:
        return []

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or f"checkupdates exited with code {result.returncode}"
        )

    packages = []

    for line in result.stdout.splitlines():
        parts = line.split()

        if len(parts) != 4 or parts[2] != "->":
            raise RuntimeError(
                f"Unexpected checkupdates output: {line[:200]}"
            )

        packages.append({
            "name": parts[0],
            "installed": parts[1],
            "available": parts[3],
        })

    return packages


def scan_debian():
    """Query locally known APT upgrades without installing packages."""

    if not shutil.which("apt"):
        raise RuntimeError("apt command not found")

    result = run_command(["apt", "list", "--upgradable"])

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or f"apt exited with code {result.returncode}"
        )

    packages = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if not line or line.startswith("Listing"):
            continue

        match = APT_PATTERN.match(line)

        if not match:
            raise RuntimeError(
                f"Unexpected APT output: {line[:200]}"
            )

        name, repository, available, installed = match.groups()

        packages.append({
            "name": name,
            "installed": installed,
            "available": available,
            "repository": repository,
        })

    return packages


def scan():
    """Return a Versionary-compatible scan report."""

    platform = detect_platform()

    try:
        packages = (
            scan_arch()
            if platform == "arch"
            else scan_debian()
        )

        return {
            "status": "success",
            "packages": packages,
            "error": None,
        }

    except RuntimeError as exc:
        return {
            "status": "error",
            "packages": [],
            "error": str(exc)[:4096],
        }


def main():
    parser = argparse.ArgumentParser(
        description="VERSIONARY AGENT — observer-only scanner"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan locally and print JSON",
    )

    args = parser.parse_args()

    if not args.scan:
        parser.print_help()
        return 0

    try:
        report = scan()
    except RuntimeError as exc:
        report = {
            "status": "error",
            "packages": [],
            "error": str(exc)[:4096],
        }

    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
