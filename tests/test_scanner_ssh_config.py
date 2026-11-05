"""Security and compatibility checks for configurable SSH scanner transport."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import remote_scanner
import arch_remote_scanner
from scanner_ssh_config import DEFAULTS, SSHConfigError, command_options, load


class ScannerSSHConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ssh.json"
        self.settings = {"identity_file": "/etc/patch/ssh/id_ed25519",
                         "known_hosts_file": "/etc/patch/ssh/known_hosts",
                         "username": "patch-scanner"}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.settings))
        self.path.chmod(0o600)

    def test_defaults_preserve_existing_ssh_transport(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load(), DEFAULTS)
            opts = command_options("pve.example.test")
            self.assertIn("StrictHostKeyChecking=yes", opts)
            self.assertIn("BatchMode=yes", opts)
            self.assertIn("IdentitiesOnly=yes", opts)
            self.assertEqual(opts[-1], "arby-scanner@pve.example.test")

    def test_custom_paths_and_user(self):
        with patch.dict(os.environ, {"ARBY_SCANNER_SSH_CONFIG_PATH": str(self.path)}):
            opts = command_options("node.example.test")
            self.assertIn("/etc/patch/ssh/id_ed25519", opts)
            self.assertIn("UserKnownHostsFile=/etc/patch/ssh/known_hosts", opts)
            self.assertEqual(opts[-1], "patch-scanner@node.example.test")

    def test_invalid_explicit_path_never_falls_back(self):
        self.path.unlink()
        with patch.dict(os.environ, {"ARBY_SCANNER_SSH_CONFIG_PATH": str(self.path)}):
            with self.assertRaises(SSHConfigError):
                load()

    def test_symlink_refused(self):
        other = Path(self.tmp.name) / "real.json"
        self.path.rename(other)
        self.path.symlink_to(other)
        with self.assertRaises(SSHConfigError):
            load(self.path)

    def test_public_permissions_refused(self):
        self.path.chmod(0o644)
        with self.assertRaises(SSHConfigError):
            load(self.path)

    def test_malformed_configuration_refused(self):
        for settings in ({"identity_file": "/tmp/id"}, [], {"extra": "value"},
                         {**self.settings, "username": "bad@host"},
                         {**self.settings, "identity_file": "../key"},
                         {**self.settings, "identity_file": "/tmp/../key"},
                         {**self.settings, "known_hosts_file": "/tmp/key\n-oNo"},
                         {**self.settings, "username": "-oProxyCommand"}):
            with self.subTest(settings=settings):
                self.path.write_text(json.dumps(settings))
                with self.assertRaises(SSHConfigError):
                    load(self.path)

    def test_both_scanners_use_configured_ssh_without_executing_network(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.dict(os.environ, {"ARBY_SCANNER_SSH_CONFIG_PATH": str(self.path)}):
            for module, fn in ((remote_scanner, remote_scanner.scan_apt_updates),
                               (arch_remote_scanner, arch_remote_scanner.scan_arch_updates)):
                with self.subTest(module=module.__name__), patch.object(
                        module.subprocess, "run", return_value=fake) as run:
                    result = fn(node="TEST", host="test.example.net")
                    self.assertEqual(result["status"], "success")
                    args = run.call_args.args[0]
                    self.assertEqual(args[0], "/usr/bin/ssh")
                    self.assertIn("StrictHostKeyChecking=yes", args)
                    self.assertIn("UserKnownHostsFile=/etc/patch/ssh/known_hosts", args)
                    self.assertEqual(args[-1], "patch-scanner@test.example.net")

    def test_invalid_configuration_blocks_ssh_in_both_scanners(self):
        self.path.unlink()
        with patch.dict(os.environ, {"ARBY_SCANNER_SSH_CONFIG_PATH": str(self.path)}):
            with patch.object(subprocess, "run") as run:
                for fn in (remote_scanner.scan_apt_updates,
                           arch_remote_scanner.scan_arch_updates):
                    with self.subTest(fn=fn.__name__):
                        result = fn(node="TEST", host="test.example.net")
                        self.assertEqual(result["status"], "error")
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
