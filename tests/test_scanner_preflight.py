"""Isolated tests for scanner preflight CLI with no SSH or filesystem writes."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scanner_inventory import LEGACY_TARGETS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer" / "scanner-preflight.py"
spec = importlib.util.spec_from_file_location("scanner_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class ScannerPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.inventory = Path(self.tmp.name) / "inventory.json"
        self.ssh = Path(self.tmp.name) / "ssh.json"
        self.inventory.write_text(json.dumps({"version": 1, "targets": LEGACY_TARGETS}))
        self.ssh.write_text(json.dumps({
            "identity_file": "/etc/patch/private.key",
            "known_hosts_file": "/etc/patch/known_hosts",
            "username": "patch-scanner",
        }))
        self.inventory.chmod(0o600)
        self.ssh.chmod(0o600)

    def test_valid_preflight_does_not_touch_network(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("network call")):
            result = preflight.inspect(str(self.inventory), str(self.ssh))
        self.assertTrue(result["ready"])
        self.assertFalse(result["network_contacted"])
        self.assertEqual(len(result["targets"]), 5)
        self.assertTrue(result["ssh"]["strict_host_key_checking"])

    def test_diagnostics_redact_private_paths(self):
        result = preflight.inspect(str(self.inventory), str(self.ssh))
        serialized = json.dumps(result)
        self.assertNotIn("private.key", serialized)
        self.assertNotIn("known_hosts", serialized)
        self.assertNotIn(str(self.ssh), serialized)

    def test_invalid_inventory_fails_closed(self):
        self.inventory.unlink()
        result = preflight.inspect(str(self.inventory), str(self.ssh))
        self.assertFalse(result["ready"])
        self.assertEqual(result["targets"], {})
        self.assertFalse(result["inventory"]["valid"])

    def test_invalid_ssh_fails_closed(self):
        self.ssh.chmod(0o644)
        result = preflight.inspect(str(self.inventory), str(self.ssh))
        self.assertFalse(result["ready"])
        self.assertEqual(result["targets"], {})
        self.assertFalse(result["ssh"]["valid"])

    def test_cli_success_and_failure_exit_codes(self):
        env = {**os.environ, "ARBY_SCANNER_INVENTORY_PATH": str(self.inventory),
               "ARBY_SCANNER_SSH_CONFIG_PATH": str(self.ssh)}
        success = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                                 text=True, env=env, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertTrue(json.loads(success.stdout)["ready"])
        self.ssh.unlink()
        failure = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                                 text=True, env=env, check=False)
        self.assertEqual(failure.returncode, 1)
        self.assertFalse(json.loads(failure.stdout)["ready"])

    def test_explicit_paths_override_invalid_environment(self):
        with patch.dict(os.environ, {
            "ARBY_SCANNER_INVENTORY_PATH": "/missing/inventory.json",
            "ARBY_SCANNER_SSH_CONFIG_PATH": "/missing/ssh.json",
        }):
            result = preflight.inspect(str(self.inventory), str(self.ssh))
        self.assertTrue(result["ready"])


if __name__ == "__main__":
    unittest.main()
