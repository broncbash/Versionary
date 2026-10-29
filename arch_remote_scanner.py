import re
import subprocess
from datetime import datetime, timezone

SSH_KEY = "/opt/arby-patch-command/keys/scanner_ed25519"
KNOWN_HOSTS = "/opt/arby-patch-command/keys/known_hosts"

PACKAGE_PATTERN = re.compile(r"^(\S+)\s+(\S+)\s+->\s+(\S+)$")


def scan_arch_updates(node, host):
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        result = subprocess.run(
            [
                "/usr/bin/ssh",
                "-T",
                "-i", SSH_KEY,
                "-o", "StrictHostKeyChecking=yes",
                "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5",
                "-o", "IdentitiesOnly=yes",
                f"arby-scanner@{host}",
            ],
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
            match = PACKAGE_PATTERN.match(line.strip())

            if match:
                name, installed, available = match.groups()

                packages.append({
                    "name": name,
                    "installed": installed,
                    "available": available,
                    "repository": None,
                })

        return {
            "node": node,
            "status": "success",
            "timestamp": timestamp,
            "count": len(packages),
            "packages": packages,
            "error": None,
        }

    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return {
            "node": node,
            "status": "error",
            "timestamp": timestamp,
            "count": None,
            "packages": [],
            "error": str(exc),
        }
