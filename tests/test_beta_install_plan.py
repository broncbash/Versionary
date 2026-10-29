"""Read-only beta plan regression checks."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

file = Path(__file__).resolve().parents[1] / "installer/beta-install-plan.py"
spec = importlib.util.spec_from_file_location("beta_plan", file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BetaPlanTests(unittest.TestCase):
    def test_plan_does_not_claim_live_readiness(self):
        class Stub:
            @staticmethod
            def report(**kwargs):
                return {"ready_for_isolated_test": True, "checks": []}
        with patch.object(module, "load", return_value=Stub):
            result = module.plan(server="https://example.test", ca_cert="ca.pem")
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(result["changes_made"])
        self.assertFalse(result["network_requests_made"])
        self.assertEqual(result["status"], "isolated-test-ready")

    def test_failed_check_blocks_isolated_readiness(self):
        class Stub:
            @staticmethod
            def report(**kwargs):
                return {"ready_for_isolated_test": False, "checks": [
                    {"name": "ca_certificate", "ok": False, "detail": "missing"}
                ]}
        with patch.object(module, "load", return_value=Stub):
            result = module.plan(server="https://example.test", ca_cert="ca.pem")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("ca_certificate", result["failed_checks"])
