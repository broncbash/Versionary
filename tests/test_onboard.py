"""Unified onboarding integration and safety tests."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/onboard.py"

spec = importlib.util.spec_from_file_location("onboard", SCRIPT)
onboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(onboard)


class OnboardingTests(unittest.TestCase):

    def agent(self, **overrides):
        options = {
            "role": "agent",
            "server": "https://example.test",
            "ca_cert": "/tmp/example-ca.pem",
        }
        options.update(overrides)
        return onboard.build_onboarding(**options)

    def test_agent_preview(self):
        self.assertEqual(self.agent()["status"], "preview-ready")

    def test_server_preview(self):
        result = onboard.build_onboarding(role="server")
        self.assertEqual(result["status"], "not-implemented")

    def test_existing_ca(self):
        result = self.agent()
        self.assertEqual(
            result["manifest"]["certificate"]["mode"],
            "existing-ca",
        )

    def test_generated_test_ca(self):
        result = self.agent(
            ca_cert=None,
            certificate_mode="generate-test-ca",
        )
        self.assertEqual(
            result["manifest"]["certificate"]["mode"],
            "generate-test-ca",
        )

    def test_invalid_http(self):
        with self.assertRaises(ValueError):
            self.agent(server="http://example.test")

    def test_missing_ca(self):
        with self.assertRaises(ValueError):
            self.agent(ca_cert=None)

    def test_live_target_rejected(self):
        with self.assertRaises(ValueError):
            self.agent(target="/")

    def test_no_execution(self):
        self.assertFalse(self.agent()["execution"]["performed"])

    def test_no_installation(self):
        self.assertFalse(
            self.agent()["execution"]["installation_enabled"]
        )

    def test_no_enrollment(self):
        self.assertFalse(
            self.agent()["execution"]["enrollment_enabled"]
        )

    def test_no_network(self):
        self.assertFalse(
            self.agent()["execution"]["network_requests_made"]
        )

    def test_no_changes(self):
        self.assertFalse(self.agent()["execution"]["changes_made"])

    def test_review_initially_pending(self):
        self.assertFalse(self.agent()["review"]["completed"])

    def test_acknowledgment(self):
        result = onboard.acknowledge(self.agent())
        self.assertTrue(result["review"]["completed"])
        self.assertFalse(result["execution"]["performed"])

    def test_server_acknowledgment_blocked(self):
        with self.assertRaises(ValueError):
            onboard.acknowledge(
                onboard.build_onboarding(role="server")
            )

    def test_interactive_agent(self):
        args = type("Args", (), {
            "role": None,
            "server": None,
            "ca_cert": None,
            "certificate_mode": None,
        })()

        with patch(
            "builtins.input",
            side_effect=[
                "",
                "https://example.test",
                "",
                "/tmp/example-ca.pem",
            ],
        ):
            result = onboard.collect_interactive(args)

        self.assertEqual(result.role, "agent")
        self.assertEqual(
            result.certificate_mode, "existing-ca"
        )

    def test_interactive_server(self):
        args = type("Args", (), {
            "role": None,
            "server": None,
            "ca_cert": None,
            "certificate_mode": None,
        })()

        with patch("builtins.input", return_value="server"):
            result = onboard.collect_interactive(args)

        self.assertEqual(result.role, "server")

    def test_text_render(self):
        text = onboard.render_text(self.agent())
        self.assertIn("Production installation: DISABLED", text)
        self.assertIn("Changes made: NONE", text)

    def test_json_cli(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--role", "agent",
                "--server", "https://example.test",
                "--certificate-mode", "generate-test-ca",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(process.returncode, 0)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "preview-ready")

    def test_acknowledge_cli(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--role", "agent",
                "--server", "https://example.test",
                "--certificate-mode", "generate-test-ca",
                "--acknowledge-preview",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(process.returncode, 0)
        result = json.loads(process.stdout)
        self.assertTrue(result["review"]["completed"])
        self.assertFalse(result["execution"]["performed"])

    def test_json_interactive_conflict(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--interactive",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 2)

    def test_no_role_cli(self):
        process = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 2)


if __name__ == "__main__":
    unittest.main()
