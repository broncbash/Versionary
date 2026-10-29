import re
import subprocess
from scanner_ssh_config import command_options, SSHConfigError
from datetime import datetime, timezone
from pathlib import Path

SSH_KEY = Path("/opt/arby-patch-command/keys/scanner_ed25519")

APT_PATTERN = re.compile(
    r"^([^/\s]+)/(\S+)\s+(\S+)\s+\S+\s+"
    r"\[upgradable from: (.+)\]$"
)


def scan_apt_updates(node="PVE CORE", host="192.168.86.5"):
    """Retrieve available updates from PVE CORE over restricted SSH."""

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        result = subprocess.run(
            ["/usr/bin/ssh", *command_options(host)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or f"SSH exited with code {result.returncode}"
            )

        packages = []

        for line in result.stdout.splitlines():
            match = APT_PATTERN.match(line.strip())

            if match:
                name, repository, available, installed = match.groups()

                packages.append({
                    "name": name,
                    "installed": installed,
                    "available": available,
                    "repository": repository,
                })

        return {
            "node": node,
            "status": "success",
            "timestamp": timestamp,
            "count": len(packages),
            "packages": packages,
            "error": None,
        }

    except (OSError, RuntimeError, SSHConfigError, subprocess.TimeoutExpired) as exc:
        return {
            "node": node,
            "status": "error",
            "timestamp": timestamp,
            "count": None,
            "packages": [],
            "error": str(exc),
        }
def scan_proxmox_updates():
    from scanner_inventory import target
    config = target("proxmox")
    return scan_apt_updates(config["node"], config["host"])
