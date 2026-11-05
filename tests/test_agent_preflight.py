"""Agent preflight is read-only and never activates production installation."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/agent-preflight.py"
spec = importlib.util.spec_from_file_location("agent_preflight", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AgentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.os_release = self.root / "os-release"
        self.os_release.write_text('NAME="Arch Linux"\nID=arch\n')
        self.ca = self.root / "ca.crt"
        self.ca.write_text("-----BEGIN CERTIFICATE-----\nplaceholder\n-----END CERTIFICATE-----\n")

    def inspect(self, **kwargs):
        return module.inspect(os_release=str(self.os_release), **kwargs)

    def test_no_server_or_ca_fails_closed(self):
        result = self.inspect()
        self.assertFalse(result["ready"])
        self.assertFalse(result["production_install_enabled"])
        self.assertFalse(result["changes_made"])
        self.assertEqual(result["mode"], "read-only")

    def test_invalid_http_url_rejected(self):
        result = self.inspect(server="http://example.test", ca_cert=str(self.ca))
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "https_server")["ok"])

    def test_invalid_ca_symlink_rejected(self):
        link = self.root / "link.crt"
        link.symlink_to(self.ca)
        result = self.inspect(server="https://example.test", ca_cert=str(link))
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "ca_certificate")["ok"])

    def test_unsupported_distribution_rejected(self):
        self.os_release.write_text("ID=fedora\n")
        result = self.inspect(server="https://example.test", ca_cert=str(self.ca))
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "supported_os")["ok"])

    def test_malformed_archive_rejected(self):
        bad = self.root / "bad.tar.gz"
        bad.write_bytes(b"not an archive")
        result = self.inspect(server="https://example.test", ca_cert=str(self.ca),
                              package=str(bad))
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "agent_package")["ok"])

    def test_cli_json_and_nonzero_exit_when_unready(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--os-release",
                                 str(self.os_release)], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["ready"])
        self.assertFalse(data["changes_made"])

    def test_no_shell_or_network_execution(self):
        with patch.object(module.shutil, "which", return_value="/usr/bin/mock"), patch.object(
                module.validator, "validate", return_value=13), patch.object(
                module, "_has_crypto", return_value=True), patch.object(
                subprocess, "run", side_effect=AssertionError("command execution")):
            archive = self.root / "agent.tar.gz"
            archive.write_bytes(b"placeholder")
            result = self.inspect(server="https://example.test",
                                  ca_cert=str(self.ca), package=str(archive))
        self.assertTrue(result["ready"])
        self.assertFalse(result["changes_made"])


if __name__ == "__main__":
    unittest.main()
