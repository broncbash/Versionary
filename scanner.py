import subprocess
from datetime import datetime, timezone


def scan_arch_updates():
    """Read-only Arch Linux package update scanner."""

    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        result = subprocess.run(
            ["/usr/bin/checkupdates"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode not in (0, 2):
            return {
                "status": "error",
                "timestamp": timestamp,
                "count": None,
                "packages": [],
                "error": result.stderr.strip() or
                         f"Scanner exited with code {result.returncode}",
            }

        packages = []

        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split()

                if len(parts) >= 4 and parts[2] == "->":
                    packages.append({
                        "name": parts[0],
                        "installed": parts[1],
                        "available": parts[3],
                    })

        return {
            "status": "success",
            "timestamp": timestamp,
            "count": len(packages),
            "packages": packages,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "timestamp": timestamp,
            "count": None,
            "packages": [],
            "error": "Scanner timed out after 120 seconds",
        }

    except OSError as exc:
        return {
            "status": "error",
            "timestamp": timestamp,
            "count": None,
            "packages": [],
            "error": str(exc),
        }
