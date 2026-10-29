"""Regression tests for inert persistent beta staging."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "installer/stage-beta.py"
spec = importlib.util.spec_from_file_location("arby_beta_staging", SCRIPT)
beta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beta)


class BetaStagingTests(unittest.TestCase):
    def test_refuses_live_root(self):
        with self.assertRaises(ValueError):
            beta.stage(root="/", server="https://example.test",
                       ca_cert="/missing", package="/missing")

    def test_refuses_symlinked_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "real").mkdir()
            (base / "link").symlink_to(base / "real")
            with self.assertRaises(ValueError):
                beta.stage(root=base / "link", server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_refuses_missing_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                beta.stage(root=Path(tmp) / "not-created",
                           server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_refuses_group_writable_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "test"
            root.mkdir()
            root.chmod(0o775)
            with self.assertRaises(ValueError):
                beta.stage(root=root, server="https://example.test",
                           ca_cert="/missing", package="/missing")

    def test_rejects_bad_url_before_any_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(beta.subprocess, "run") as run:
                with self.assertRaises((ValueError, RuntimeError)):
                    beta.stage(root=root, server="http://insecure.test",
                               ca_cert="/missing", package="/missing")
                run.assert_not_called()

    def test_persistent_stage_and_repeat_preserve_files(self):
        """Exercise the actual staging pipeline without touching live paths."""
        root_dir = SCRIPT.parents[1]
        package = root_dir / "installer/dist/arby-patch-agent.tar.gz"
        if not package.is_file():
            self.skipTest("Build agent package first (CI builds it before tests)")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            test_root = base / "isolated-root"
            test_root.mkdir(mode=0o700)
            cert_dir = base / "certs"
            subprocess.run(
                [sys.executable, str(root_dir / "installer/generate-certificates.py"),
                 "--hostname", "patch.example.test", "--output", str(cert_dir)],
                check=True, capture_output=True, text=True, timeout=20)
            ca = cert_dir / "ca.crt"
            first = beta.stage(root=test_root, server="https://patch.example.test",
                               ca_cert=ca, package=package)
            self.assertEqual(first["status"], "staged")
            self.assertFalse(first["production_installed"])
            self.assertFalse(first["systemd_started"])
            self.assertFalse(first["agent_enrolled"])
            self.assertFalse(first["network_requests_made"])
            active = test_root / "opt/arby-patch-agent/agent"
            config = test_root / "etc/arby-patch-agent/config.json"
            installed_ca = test_root / "etc/arby-patch-agent/ca.crt"
            service = test_root / "etc/systemd/system/arby-patch-agent.service"
            timer = test_root / "etc/systemd/system/arby-patch-agent.timer"
            before = (os.readlink(active), *(p.read_bytes() for p in
                      (config, installed_ca, service, timer)))
            second = beta.stage(root=test_root, server="https://patch.example.test",
                                ca_cert=ca, package=package)
            after = (os.readlink(active), *(p.read_bytes() for p in
                     (config, installed_ca, service, timer)))
            self.assertEqual(second["status"], "staged")
            self.assertEqual(before, after)
            verified = beta.stage(root=test_root, server="https://patch.example.test",
                                  ca_cert=ca, package=package, verify_only=True)
            self.assertEqual(verified["status"], "verified")
            self.assertFalse(verified["changes_made"])
            self.assertEqual(
                (os.readlink(active), *(p.read_bytes() for p in
                 (config, installed_ca, service, timer))), before)
            with self.assertRaisesRegex(ValueError, "configuration"):
                beta.stage(root=test_root, server="https://other.example.test",
                           ca_cert=ca, package=package, verify_only=True)
            self.assertEqual(config.read_bytes(), before[1])
            installed_ca.write_text("TAMPERED")
            with self.assertRaisesRegex(ValueError, "integrity audit"):
                beta.stage(root=test_root, server="https://patch.example.test",
                           ca_cert=ca, package=package, verify_only=True)
            self.assertEqual(installed_ca.read_text(), "TAMPERED")

    def test_cli_failure_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", tmp,
                 "--server", "http://insecure.test", "--ca-cert", "/missing"],
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Beta staging failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
