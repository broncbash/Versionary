"""Read-only installation audit regression tests."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/audit-test-install.py"
PACKAGE = ROOT / "installer/dist/versionary-agent.tar.gz"
INSTALL = ROOT / "installer/install-files.py"
spec = importlib.util.spec_from_file_location("agent_install_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AgentInstallAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_empty_root_fails_without_changes(self):
        before = sorted(self.root.iterdir())
        result = audit.audit(self.root, PACKAGE)
        self.assertFalse(result["ready"])
        self.assertFalse(result["changes_made"])
        self.assertEqual(before, sorted(self.root.iterdir()))

    def test_production_root_refused(self):
        result = audit.audit("/", PACKAGE)
        self.assertFalse(result["ready"])
        self.assertFalse(result["changes_made"])

    def test_isolated_install_missing_config_and_units_fails(self):
        process = subprocess.run([sys.executable, str(INSTALL), str(PACKAGE),
                                  "--root", str(self.root)], capture_output=True,
                                 text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = audit.audit(self.root, PACKAGE)
        self.assertFalse(result["ready"])
        checks = {item["name"]: item["ok"] for item in result["checks"]}
        self.assertTrue(checks["active_release_matches_archive"])
        self.assertTrue(checks["release_contents_match_archive"])
        self.assertTrue(checks["private_state"])
        self.assertFalse(checks["agent_config"])

    def test_tampered_release_detected(self):
        process = subprocess.run([sys.executable, str(INSTALL), str(PACKAGE),
                                  "--root", str(self.root)], capture_output=True,
                                 text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        release = self.root / "opt/versionary-agent/agent"
        (release / "config.py").write_text("tampered")
        result = audit.audit(self.root, PACKAGE)
        checks = {item["name"]: item["ok"] for item in result["checks"]}
        self.assertFalse(checks["release_contents_match_archive"])
        self.assertFalse(result["ready"])

    def _installed_release(self):
        process = subprocess.run([sys.executable, str(INSTALL), str(PACKAGE),
                                  "--root", str(self.root)], capture_output=True,
                                 text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        return self.root / "opt/versionary-agent/agent"

    def _source_integrity_ok(self):
        result = audit.audit(self.root, PACKAGE)
        return {item["name"]: item["ok"] for item in result["checks"]}[
            "release_contents_match_archive"]

    def test_symlinked_source_rejected(self):
        release = self._installed_release()
        source = release / "config.py"
        copy = self.root / "config-copy.py"
        copy.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(copy)
        self.assertFalse(self._source_integrity_ok())

    def test_hardlinked_source_rejected(self):
        import os
        release = self._installed_release()
        source = release / "config.py"
        os.link(source, self.root / "hardlink.py")
        self.assertFalse(self._source_integrity_ok())

    def test_symlinked_bytecode_cache_rejected(self):
        release = self._installed_release()
        cache = release / "__pycache__"
        cache.symlink_to(self.root)
        self.assertFalse(self._source_integrity_ok())

    def test_unexpected_cache_entry_rejected(self):
        release = self._installed_release()
        cache = release / "__pycache__"
        cache.mkdir()
        (cache / "unexpected.txt").write_text("not bytecode")
        self.assertFalse(self._source_integrity_ok())

    def test_regular_bytecode_cache_accepted(self):
        release = self._installed_release()
        cache = release / "__pycache__"
        cache.mkdir()
        (cache / "config.cpython-314.pyc").write_bytes(b"test bytecode")
        self.assertTrue(self._source_integrity_ok())

    def _install_full_test_root(self):
        # Build an isolated file layout for adversarial file-type checks.
        # The full shell installer is covered separately by smoke tests.
        self._installed_release()
        config_dir = self.root / "etc/versionary-agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text('{"server":"https://example.test"}')
        (config_dir / "ca.crt").write_text("-----BEGIN CERTIFICATE-----\\nTEST\\n")
        units_dir = self.root / "etc/systemd/system"
        units_dir.mkdir(parents=True, exist_ok=True)
        for name in ("versionary-agent.service", "versionary-agent.timer"):
            (units_dir / name).write_text("[Unit]\\nDescription=Test\\n")
            (units_dir / name).chmod(0o644)
        return config_dir, units_dir

    def test_symlinked_config_rejected(self):
        config_dir, _ = self._install_full_test_root()
        config = config_dir / "config.json"
        original = self.root / "config-copy.json"
        original.write_bytes(config.read_bytes())
        config.unlink()
        config.symlink_to(original)
        checks = {item["name"]: item["ok"] for item in audit.audit(self.root, PACKAGE)["checks"]}
        self.assertFalse(checks["agent_config"])

    def test_hardlinked_ca_rejected(self):
        import os
        config_dir, _ = self._install_full_test_root()
        os.link(config_dir / "ca.crt", self.root / "ca-hardlink.crt")
        checks = {item["name"]: item["ok"] for item in audit.audit(self.root, PACKAGE)["checks"]}
        self.assertFalse(checks["trusted_ca"])

    def test_symlinked_systemd_unit_rejected(self):
        _, units = self._install_full_test_root()
        service = units / "versionary-agent.service"
        original = self.root / "service-copy"
        original.write_bytes(service.read_bytes())
        service.unlink()
        service.symlink_to(original)
        checks = {item["name"]: item["ok"] for item in audit.audit(self.root, PACKAGE)["checks"]}
        self.assertFalse(checks["versionary-agent.service"])

    def test_hardlinked_systemd_unit_rejected(self):
        import os
        _, units = self._install_full_test_root()
        os.link(units / "versionary-agent.timer", self.root / "timer-hardlink")
        checks = {item["name"]: item["ok"] for item in audit.audit(self.root, PACKAGE)["checks"]}
        self.assertFalse(checks["versionary-agent.timer"])

    def test_cli_failure_json(self):
        process = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root),
                                  "--package", str(PACKAGE)], capture_output=True,
                                 text=True, check=False)
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertFalse(json.loads(process.stdout)["ready"])


if __name__ == "__main__":
    unittest.main()
