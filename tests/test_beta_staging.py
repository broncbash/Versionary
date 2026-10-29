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
            with self.assertRaisesRegex(ValueError, "beta CA"):
                beta.stage(root=test_root, server="https://patch.example.test",
                           ca_cert=ca, package=package, verify_only=True)
            self.assertEqual(installed_ca.read_text(), "TAMPERED")

    def test_smoke_scan_requires_verify_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "requires --verify-only"):
                beta.stage(root=tmp, server="https://example.test",
                           ca_cert="/missing", package="/missing",
                           smoke_scan=True)

    def test_smoke_scan_runs_staged_agent_and_checks_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ca = root / "trusted.crt"
            ca.write_bytes(b"certificate-placeholder")
            package = root / "package.tar.gz"
            package.write_bytes(b"archive-placeholder")
            config = root / "etc/arby-patch-agent/config.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "server": "https://example.test",
                "ca_cert": "/etc/arby-patch-agent/ca.crt",
            }))
            installed_ca = root / "etc/arby-patch-agent/ca.crt"
            installed_ca.write_bytes(ca.read_bytes())
            class Module:
                pass
            config_module = Module()
            config_module.validate_config = lambda data: data
            ca_module = Module()
            ca_module.validate_ca = lambda data: "fingerprint"
            package_module = Module()
            package_module.validate = lambda path: 13
            audit_module = Module()
            audit_module.audit = lambda root, package: {"ready": True}
            mapping = {"setup-config.py": config_module,
                       "install-ca.py": ca_module,
                       "validate-package.py": package_module,
                       "audit-test-install.py": audit_module}
            completed = subprocess.CompletedProcess(
                ["agent", "scan"], 0,
                stdout=json.dumps({"status": "success", "packages": [], "error": None}),
                stderr="")
            with patch.object(beta, "module", side_effect=lambda name, alias: mapping[name]):
                with patch.object(beta.subprocess, "run", return_value=completed) as run:
                    result = beta.stage(root=root, server="https://example.test",
                                        ca_cert=ca, package=package,
                                        verify_only=True, smoke_scan=True)
            self.assertEqual(result["scan_status"], "success")
            self.assertFalse(result["network_requests_made"])
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.kwargs["cwd"],
                             str(root / "opt/arby-patch-agent"))
            self.assertIn("-B", run.call_args.args[0])

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
