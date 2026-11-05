import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "installer/onboarding-readiness.py"

spec = importlib.util.spec_from_file_location("readiness_adapter", PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class ReadinessAdapterTests(unittest.TestCase):

    def test_server_pending(self):
        result = adapter.evaluate(role="server")
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["ready_for_production"])

    def test_generated_ca_pending(self):
        result = adapter.evaluate(
            role="agent",
            server="https://example.test",
            certificate_mode="generate-test-ca",
        )
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["ready_for_isolated_test"])

    def test_missing_ca_pending(self):
        result = adapter.evaluate(
            role="agent", server="https://example.test"
        )
        self.assertEqual(result["status"], "pending")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            adapter.evaluate(role="database")

    def test_unknown_certificate_mode_rejected(self):
        with self.assertRaises(ValueError):
            adapter.evaluate(
                role="agent",
                server="https://example.test",
                ca_cert="/tmp/ca.pem",
                certificate_mode="unknown",
            )

    def test_real_planner_called(self):
        result = adapter.evaluate(
            role="agent",
            server="https://example.test",
            ca_cert="/nonexistent/ca.pem",
        )
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(result["changes_made"])
        self.assertIn("checks", result)

    def test_ready_isolated_not_production(self):
        fake = {
            "ready_for_isolated_test": True,
            "checks": [
                {"name": "python", "ok": True, "detail": "OK"},
                {
                    "name": "production_installer",
                    "ok": False,
                    "detail": "Production disabled",
                },
                {
                    "name": "end_to_end_enrollment",
                    "ok": False,
                    "detail": "Enrollment disabled",
                },
            ],
            "failed_checks": [
                "production_installer", "end_to_end_enrollment"
            ],
        }

        class FakePlanner:
            def plan(self, **kwargs):
                return fake

        with patch.object(adapter, "load_plan", return_value=FakePlanner()):
            result = adapter.evaluate(
                role="agent",
                server="https://example.test",
                ca_cert="/tmp/ca.pem",
            )

        self.assertTrue(result["ready_for_isolated_test"])
        self.assertFalse(result["ready_for_production"])
        self.assertEqual(result["blockers"], [])

    def test_preflight_failure_blocked(self):
        fake = {
            "ready_for_isolated_test": False,
            "checks": [
                {
                    "name": "certificate",
                    "ok": False,
                    "detail": "CA missing",
                }
            ],
            "failed_checks": ["certificate"],
        }

        class FakePlanner:
            def plan(self, **kwargs):
                return fake

        with patch.object(adapter, "load_plan", return_value=FakePlanner()):
            result = adapter.evaluate(
                role="agent",
                server="https://example.test",
                ca_cert="/tmp/ca.pem",
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blockers"], ["CA missing"])

    def test_no_network_or_changes(self):
        result = adapter.evaluate(role="server")
        self.assertFalse(result["network_requests_made"])
        self.assertFalse(result["changes_made"])


if __name__ == "__main__":
    unittest.main()
