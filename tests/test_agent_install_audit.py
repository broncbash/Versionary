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
PACKAGE = ROOT / "installer/dist/arby-patch-agent.tar.gz"
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
        release = self.root / "opt/arby-patch-agent/agent"
        (release / "config.py").write_text("tampered")
        result = audit.audit(self.root, PACKAGE)
        checks = {item["name"]: item["ok"] for item in result["checks"]}
        self.assertFalse(checks["release_contents_match_archive"])
        self.assertFalse(result["ready"])

    def test_cli_failure_json(self):
        process = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root),
                                  "--package", str(PACKAGE)], capture_output=True,
                                 text=True, check=False)
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertFalse(json.loads(process.stdout)["ready"])


if __name__ == "__main__":
    unittest.main()
