"""Batch 79: read-only fresh-system installation gate."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "installer/versionary-agent-beta-system-fresh-gate.py"
)

spec = importlib.util.spec_from_file_location(
    "versionary_beta_system_fresh_gate_79", SOURCE
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class FreshSystemGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-fresh79-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def create(self, relative, contents=b"x"):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
        return target

    def test_empty_root_passes_without_writing(self):
        before = set(self.root.rglob("*"))
        result = gate.inspect(self.root)
        self.assertEqual(
            result["status"], "fresh_install_destinations_clear"
        )
        self.assertFalse(result["installation_performed"])
        self.assertFalse(result["real_system_installation_enabled"])
        self.assertEqual(before, set(self.root.rglob("*")))

    def test_rejects_relative_root(self):
        with self.assertRaises(ValueError):
            gate.inspect("relative-root")

    def test_rejects_missing_root(self):
        with self.assertRaises(FileNotFoundError):
            gate.inspect(self.root / "missing")

    def test_rejects_symlinked_root(self):
        link = self.root.parent / (self.root.name + "-link")
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)
        with self.assertRaises(RuntimeError):
            gate.inspect(link)

    def test_rejects_existing_agent_release(self):
        self.create("opt/versionary-agent/agent/__main__.py")
        with self.assertRaisesRegex(RuntimeError, "Nonempty"):
            gate.inspect(self.root)

    def test_rejects_private_identity(self):
        self.create("var/lib/versionary-agent/identity.json")
        with self.assertRaisesRegex(RuntimeError, "Nonempty"):
            gate.inspect(self.root)

    def test_rejects_existing_configuration(self):
        self.create("etc/versionary-agent/config.json")
        with self.assertRaisesRegex(RuntimeError, "Existing"):
            gate.inspect(self.root)

    def test_rejects_existing_service(self):
        self.create(
            "etc/systemd/system/versionary-agent.service"
        )
        with self.assertRaisesRegex(RuntimeError, "Existing"):
            gate.inspect(self.root)

    def test_rejects_existing_timer(self):
        self.create(
            "etc/systemd/system/versionary-agent.timer"
        )
        with self.assertRaisesRegex(RuntimeError, "Existing"):
            gate.inspect(self.root)

    def test_rejects_install_journal(self):
        self.create(".versionary-install-journal.json")
        with self.assertRaisesRegex(RuntimeError, "journal"):
            gate.inspect(self.root)

    def test_rejects_upgrade_journal(self):
        self.create(".versionary-upgrade-transaction")
        with self.assertRaisesRegex(RuntimeError, "journal"):
            gate.inspect(self.root)

    def test_rejects_symlinked_application(self):
        (self.root / "opt").mkdir()
        (self.root / "opt/versionary-agent").symlink_to(
            self.root, target_is_directory=True
        )
        with self.assertRaisesRegex(RuntimeError, "Unsafe"):
            gate.inspect(self.root)

    def test_rejects_nonempty_state_directory(self):
        self.create("var/lib/versionary-agent/credential.json")
        with self.assertRaisesRegex(RuntimeError, "Nonempty"):
            gate.inspect(self.root)

    def test_rejects_unsafe_root_permissions(self):
        with patch.object(gate.os, "geteuid", return_value=0):
            if self.root.stat().st_uid != 0:
                with self.assertRaises(RuntimeError):
                    gate.inspect(self.root)

    def test_empty_application_and_state_allowed(self):
        (self.root / "opt/versionary-agent").mkdir(
            parents=True, mode=0o700
        )
        (self.root / "var/lib/versionary-agent").mkdir(
            parents=True, mode=0o700
        )
        result = gate.inspect(self.root)
        self.assertEqual(result["application_directory"], "existing")
        self.assertEqual(result["state_directory"], "existing")

if __name__ == "__main__":
    unittest.main()
