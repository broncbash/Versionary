"""Tests for the one-command disposable beta lifecycle."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "installer/beta-selftest.py"
spec = importlib.util.spec_from_file_location("beta_selftest_tests", SCRIPT)
beta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beta)


class BetaSelftestTests(unittest.TestCase):
    def test_full_disposable_lifecycle(self):
        result = beta.run()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["initial_stage"], "staged")
        self.assertEqual(result["repeat_stage"], "staged")
        self.assertEqual(result["integrity_audit"], "verified")
        self.assertEqual(result["scan_status"], "not-requested")
        for key in ("production_installed", "systemd_started",
                    "agent_enrolled", "network_requests_made",
                    "artifacts_retained"):
            self.assertFalse(result[key])

    def test_failure_does_not_claim_success(self):
        with patch.object(beta, "load", side_effect=ValueError("test failure")):
            with self.assertRaisesRegex(ValueError, "test failure"):
                beta.run()


if __name__ == "__main__":
    unittest.main()
