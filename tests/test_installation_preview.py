"""Security and compatibility tests for installation previews."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/installation-preview.py"

spec = importlib.util.spec_from_file_location("installation_preview", SCRIPT)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class InstallationPreviewTests(unittest.TestCase):

    def agent(self, **overrides):
        options = {
            "role": "agent",
            "server": "https://example.test:8443",
            "ca_cert": "/tmp/test-ca.pem",
        }
        options.update(overrides)
        return preview.create_preview(**options)

    def test_agent_preview(self):
        result = self.agent()
        self.assertEqual(result["role"], "agent")
        self.assertEqual(result["status"], "preview-only")

    def test_schema_version(self):
        self.assertEqual(self.agent()["schema_version"], 1)

    def test_portable_server(self):
        result = self.agent(server="https://patch.example.org")
        self.assertEqual(
            result["configuration"]["server"],
            "https://patch.example.org",
        )

    def test_private_state_directory(self):
        result = self.agent()
        state = next(
            item for item in result["artifacts"]
            if item["path"] == "/var/lib/arby-patch-agent"
        )
        self.assertEqual(state["permissions"], "0700")

    def test_systemd_units_inactive(self):
        result = self.agent()
        units = [
            item for item in result["artifacts"]
            if item["path"].endswith((".service", ".timer"))
        ]
        self.assertEqual(len(units), 2)
        self.assertTrue(
            all(item["activation"] == "disabled" for item in units)
        )

    def test_production_disabled(self):
        self.assertFalse(
            self.agent()["safety"]["production_installation_enabled"]
        )

    def test_enrollment_disabled(self):
        self.assertFalse(
            self.agent()["safety"]["agent_enrollment_enabled"]
        )

    def test_network_disabled(self):
        self.assertFalse(
            self.agent()["safety"]["network_requests_enabled"]
        )

    def test_no_changes(self):
        self.assertFalse(self.agent()["safety"]["changes_made"])

    def test_no_operations_enabled(self):
        self.assertTrue(
            all(not op["enabled"] for op in self.agent()["operations"])
        )

    def test_existing_ca_required(self):
        with self.assertRaises(preview.PreviewError):
            self.agent(ca_cert=None)

    def test_generated_test_ca_mode(self):
        result = self.agent(
            ca_cert=None,
            certificate_mode="generate-test-ca",
        )
        self.assertEqual(
            result["certificate"]["mode"], "generate-test-ca"
        )
        self.assertFalse(
            result["certificate"]["generation_permitted"]
        )

    def test_conflicting_ca_options_rejected(self):
        with self.assertRaises(preview.PreviewError):
            self.agent(certificate_mode="generate-test-ca")

    def test_live_target_rejected(self):
        with self.assertRaises(preview.PreviewError):
            self.agent(target="/")

    def test_unknown_role_rejected(self):
        with self.assertRaises(preview.PreviewError):
            preview.create_preview(role="database")

    def test_http_rejected(self):
        with self.assertRaises(ValueError):
            self.agent(server="http://example.test")

    def test_server_preview_not_implemented(self):
        result = preview.create_preview(role="server")
        self.assertEqual(result["status"], "not-implemented")
        self.assertEqual(result["artifacts"], [])

    def test_server_rejects_agent_options(self):
        with self.assertRaises(preview.PreviewError):
            preview.create_preview(
                role="server",
                server="https://example.test",
            )

    def test_no_private_keys_in_json(self):
        result = json.dumps(self.agent())
        self.assertNotIn("PRIVATE KEY-----", result)
        self.assertNotIn("enrollment_token", result)

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
        self.assertEqual(result["role"], "agent")

    def test_text_cli(self):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--role", "server"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0)
        self.assertIn("Production installation: DISABLED", process.stdout)

    def test_invalid_target_cli(self):
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--role", "agent",
                "--server", "https://example.test",
                "--ca-cert", "/tmp/test-ca.pem",
                "--target", "/",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 2)


if __name__ == "__main__":
    unittest.main()
