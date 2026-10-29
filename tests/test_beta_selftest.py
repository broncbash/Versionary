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
        self.assertEqual(result["tls_protocol_check"], "not-requested")
        for key in ("production_installed", "systemd_started",
                    "agent_enrolled", "network_requests_made",
                    "artifacts_retained"):
            self.assertFalse(result[key])

    def test_real_tls_protocol_acceptance(self):
        result = beta.run(protocol_check=True)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["tls_protocol_check"], "passed")
        self.assertTrue(result["network_requests_made"])
        self.assertFalse(result["external_network_requests_made"])

    def test_protocol_failure_fails_closed(self):
        import subprocess
        with patch.object(beta.subprocess, "run", return_value=subprocess.CompletedProcess(
                ["python", "-m", "unittest"], 1, "", "simulated TLS failure")):
            with self.assertRaisesRegex(RuntimeError, "Real TLS protocol check failed"):
                beta.run(protocol_check=True)

    def test_failure_does_not_claim_success(self):
        with patch.object(beta, "load", side_effect=ValueError("test failure")):
            with self.assertRaisesRegex(ValueError, "test failure"):
                beta.run()


if __name__ == "__main__":
    unittest.main()
