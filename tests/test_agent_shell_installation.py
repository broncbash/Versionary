"""End-to-end smoke test for the agent shell installer."""

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/install-agent.sh"


class AgentShellInstallationTests(unittest.TestCase):

    def test_isolated_installation_and_scan(self):
        result = subprocess.run(
            ["bash", str(INSTALLER), "--test-install"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + "\n" + result.stderr,
        )

        self.assertIn(
            "[OK] Agent release activated",
            result.stdout,
        )

        self.assertIn(
            "[OK] Private state directory verified",
            result.stdout,
        )

        self.assertIn(
            "[OK] Installed agent executed successfully",
            result.stdout,
        )

        self.assertIn(
            "[OK] Identical reinstallation preserved release, CA, config and units",
            result.stdout,
        )

    def test_isolated_smoke_test_does_not_depend_on_live_repositories(self):
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("python3 -m agent --help", source)
        self.assertNotIn("python3 -m agent scan", source)

    def test_production_installation_remains_disabled(self):
        # Must not invoke --install: that could require root
        # and may become active in a future release.
        source = INSTALLER.read_text(encoding="utf-8")

        self.assertIn(
            "Production installation is not enabled yet.",
            source,
        )


if __name__ == "__main__":
    unittest.main()
