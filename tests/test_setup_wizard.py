"""Tests for the unified read-only installation wizard."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/setup-wizard.py"

spec = importlib.util.spec_from_file_location("setup_wizard", SCRIPT)
wizard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wizard)


class SetupWizardTests(unittest.TestCase):

    def test_server_role_is_not_deployable(self):
        result = wizard.build_plan("server")
        self.assertEqual(result["status"], "not-yet-supported")
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(result["changes_made"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            wizard.build_plan("unknown")

    def test_http_rejected(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("http://example.test")

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://user:pass@example.test")

    def test_path_rejected(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test/admin")

    def test_query_rejected(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test/?token=secret")

    def test_valid_https_origin(self):
        self.assertEqual(
            wizard.validate_server("https://example.test:8443/"),
            "https://example.test:8443",
        )

    def test_agent_requires_ca(self):
        with self.assertRaises(ValueError):
            wizard.build_plan("agent", server="https://example.test")

    def test_agent_reuses_existing_planner(self):
        fake = {
            "product": "Patch Command",
            "mode": "read-only-planning",
            "status": "blocked",
            "ready_for_isolated_test": False,
            "ready_for_production": False,
            "changes_made": False,
            "network_requests_made": False,
            "failed_checks": [],
            "checks": [],
        }

        class ExistingPlanner:
            @staticmethod
            def plan(**kwargs):
                return dict(fake)

        with patch.object(wizard, "load_module", return_value=ExistingPlanner):
            result = wizard.build_plan(
                "agent",
                server="https://example.test",
                ca_cert="/tmp/example-ca.pem",
            )

        self.assertEqual(result["role"], "agent")
        self.assertFalse(result["production_install_enabled"])
        self.assertFalse(result["enrollment_enabled"])

    def test_server_json_cli(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--role",
                "server",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 1)
        result = json.loads(process.stdout)
        self.assertEqual(result["role"], "server")
        self.assertFalse(result["changes_made"])

    def test_install_flag_is_blocked(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--role",
                "server",
                "--install",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("disabled", process.stderr.lower())

    def test_text_output_identifies_safety(self):
        result = wizard.build_plan("server")
        output = wizard.render_text(result)
        self.assertIn("Production installation: DISABLED", output)
        self.assertIn("Changes made: NO", output)


if __name__ == "__main__":
    unittest.main()


class SetupWizardHardeningTests(unittest.TestCase):

    def test_rejects_empty_hostname(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://")

    def test_rejects_userinfo_without_password(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://user@example.test")

    def test_rejects_invalid_port(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test:invalid")

    def test_rejects_zero_port(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test:0")

    def test_rejects_whitespace(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test /")

    def test_rejects_backslash(self):
        with self.assertRaises(ValueError):
            wizard.validate_server("https://example.test\\admin")

    def test_real_agent_planner_is_called(self):
        with patch.object(wizard, "load_module", wraps=wizard.load_module) as loader:
            result = wizard.build_plan(
                "agent",
                server="https://example.test",
                ca_cert="/nonexistent/example-ca.pem",
            )

        loader.assert_called_once()
        self.assertEqual(result["role"], "agent")
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(result["changes_made"])
        self.assertFalse(result["network_requests_made"])
        self.assertFalse(result["ready_for_isolated_test"])
        self.assertIn("failed_checks", result)
