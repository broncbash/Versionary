"""Safety contracts for the isolated HTTPS beta entry point."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "versionary_https_beta.py").read_text()


class IsolatedHTTPSBetaTests(unittest.TestCase):
    def test_source_compiles(self):
        ast.parse(SOURCE)

    def test_separate_state(self):
        self.assertIn('".versionary-https-beta"', SOURCE)
        self.assertNotIn('".versionary-local-beta"', SOURCE)

    def test_loopback_only(self):
        self.assertIn(
            "host=server_bind_address()",
            SOURCE,
        )
        self.assertIn(
            'os.environ.get("VERSIONARY_BIND_ADDRESS", "127.0.0.1")',
            SOURCE,
        )
        self.assertIn(
            'if value in ("0.0.0.0", "::"):',
            SOURCE,
        )
        self.assertIn(
            'VERSIONARY_ALLOW_NETWORK_BIND',
            SOURCE,
        )
        self.assertIn("port=server_port()", SOURCE)
        self.assertIn(
            'os.environ.get("VERSIONARY_HTTPS_PORT", "8766")',
            SOURCE,
        )

    def test_https_required(self):
        self.assertIn("ssl_certfile=", SOURCE)
        self.assertIn("ssl_keyfile=", SOURCE)

    def test_enrollment_and_reporting_present(self):
        self.assertIn("enrollment_v2_api", SOURCE)
        self.assertIn("agent_reporting_api", SOURCE)

    def test_no_production_installer(self):
        self.assertNotIn("subprocess.run", SOURCE)
        self.assertNotIn("systemctl", SOURCE)


if __name__ == "__main__":
    unittest.main()
