"""Local runner presentation and deployment safety regression checks."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallerPresentationTests(unittest.TestCase):
    def test_local_runner_uses_product_name(self):
        runner = (ROOT / "installer/local-check.sh").read_text()
        self.assertIn("[Patch Command] PASS", runner)
        self.assertIn("PATCH_COMMAND_TEST_LOG", runner)
        self.assertIn("ARBY_TEST_LOG", runner)  # Existing override stays supported.

    def test_installer_help_is_safe_and_clear(self):
        result = subprocess.run(
            ["bash", str(ROOT / "installer/install-agent.sh"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Production installation remains disabled.", result.stdout)
        self.assertNotIn("ARBY PATCH AGENT", result.stdout)

    def test_install_mode_does_not_enable_deployment(self):
        installer = (ROOT / "installer/install-agent.sh").read_text()
        self.assertIn('if [[ "$MODE" == "install" ]]', installer)
        self.assertIn("Production installation is not enabled yet.", installer)
        self.assertIn('exit 1', installer)


if __name__ == "__main__":
    unittest.main()
