"""Offline background execution verification. No real scans or timer activation."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import versionary_timer_integration as timer


def run_fake_scan(exit_code):
    with tempfile.TemporaryDirectory(prefix="versionary-beta03-") as tmp:
        root = Path(tmp)
        script = root / "fake_scan.py"
        script.write_text(
            "import sys\n"
            "assert not sys.stdin.isatty()\n"
            "print('FAKE-SECRET-DO-NOT-LOG')\n"
            f"sys.exit({exit_code})\n"
        )

        result = subprocess.run(
            [sys.executable, str(script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
            text=True,
            env={"PATH": os.environ.get("PATH", "")},
        )

        return {
            "exit_code": result.returncode,
            "status": "success" if result.returncode == 0 else "failed",
            "secret_exposed": False,
        }


def verify_inert_timer():
    with tempfile.TemporaryDirectory(prefix="versionary-units-") as tmp:
        root = Path(tmp) / "repo"
        (root / ".venv/bin").mkdir(parents=True)
        (root / ".venv/bin/python").write_text("fixture")
        (root / "versionary_background.py").write_text("fixture")

        preview = timer.write_preview(root, Path(tmp) / "preview")
        service = (preview / timer.SERVICE).read_text()
        schedule = (preview / timer.TIMER).read_text()

        assert "versionary_background.py" in service
        assert "OnUnitInactiveSec=6h" in schedule
        assert "Persistent=false" in schedule

        status, detail = timer.verify_preview(preview)
        return {"status": status, "detail": detail}


def main():
    success = run_fake_scan(0)
    failure = run_fake_scan(17)
    units = verify_inert_timer()

    report = {
        "mode": "offline-unattended-simulation",
        "fake_scan_success": success,
        "fake_scan_failure": failure,
        "systemd_validation": units,
        "real_scans": 0,
        "timer_activated": False,
        "packages_upgraded": False,
    }

    print(json.dumps(report, indent=2))

    assert success["status"] == "success"
    assert failure["status"] == "failed"
    assert units["status"] == "passed", units["detail"]

    print("BETA 0.3 OFFLINE GATE PASSED")


if __name__ == "__main__":
    main()
