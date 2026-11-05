"""Durable isolated installation recovery integration tests."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCE = (
    BASE / "installer/versionary-agent-durable-install.py"
)

spec = importlib.util.spec_from_file_location(
    "versionary_durable88", SOURCE
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DurableInstallTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory(
            prefix="versionary-durable88-"
        )
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.payloads = {
            "etc/versionary-agent/config.json": b'{"test":true}\n',
            "opt/versionary-agent/cli.py": b"print('ok')\n",
            "etc/systemd/system/versionary-agent.service":
                b"[Unit]\nDescription=Test\n",
        }

    def test_rejects_real_root(self):
        with self.assertRaises(ValueError):
            module.validate_root("/")

    def test_rejects_relative_root(self):
        with self.assertRaises(ValueError):
            module.validate_root("relative")

    def test_rejects_symlink_root(self):
        link = self.root.parent / (
            self.root.name + "-link"
        )
        link.symlink_to(
            self.root, target_is_directory=True
        )
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            module.validate_root(link)

    def test_clear_root(self):
        result = module.inspect(self.root)
        self.assertEqual(result["status"], "clear")

    def test_complete_install(self):
        result = module.install_isolated(
            self.root, self.payloads
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["created"], 3)
        self.assertFalse(
            (self.root / module.JOURNAL).exists()
        )
        self.assertFalse(
            result["real_system_installation_enabled"]
        )

    def test_failure_leaves_recovery_journal(self):
        with self.assertRaises(RuntimeError):
            module.install_isolated(
                self.root, self.payloads, fail_after=1
            )
        self.assertTrue(
            (self.root / module.JOURNAL).exists()
        )
        self.assertEqual(
            module.inspect(self.root)["status"],
            "recovery_required",
        )

    def test_pending_blocks_second_install(self):
        module.write_intent(
            self.root, self.payloads
        )
        with self.assertRaises(module.RecoveryRequired):
            module.install_isolated(
                self.root, self.payloads
            )

    def test_partial_install_cannot_finalize(self):
        module.write_intent(
            self.root, self.payloads
        )
        with self.assertRaises(module.RecoveryRequired):
            module.finalize(
                self.root, self.payloads
            )
        self.assertTrue(
            (self.root / module.JOURNAL).exists()
        )

    def test_manifest_mismatch_cannot_finalize(self):
        module.write_intent(
            self.root, self.payloads
        )
        with self.assertRaises(ValueError):
            module.finalize(
                self.root, {"other": b"different"}
            )

    def test_existing_files_preserved_on_failure(self):
        target = (
            self.root /
            "etc/versionary-agent/config.json"
        )
        target.parent.mkdir(parents=True)
        target.write_bytes(
            self.payloads[
                "etc/versionary-agent/config.json"
            ]
        )
        with self.assertRaises(RuntimeError):
            module.install_isolated(
                self.root, self.payloads, fail_after=0
            )
        self.assertEqual(
            target.read_bytes(),
            self.payloads[
                "etc/versionary-agent/config.json"
            ],
        )

    def test_corrupt_journal_refused(self):
        path = self.root / module.JOURNAL
        path.write_text("not-json")
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_malformed_journal_refused(self):
        path = self.root / module.JOURNAL
        path.write_text(json.dumps({
            "version": 1,
            "phase": "installing",
            "files": {
                "../escape": {
                    "state": "planned",
                    "size": 1,
                    "sha256": "0" * 64,
                }
            },
        }))
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_unrelated_file_preserved(self):
        unrelated = self.root / "keep.txt"
        unrelated.write_text("preserve")
        module.install_isolated(
            self.root, self.payloads
        )
        self.assertEqual(
            unrelated.read_text(), "preserve"
        )

    def test_cli_does_not_expose_install(self):
        source = SOURCE.read_text()
        self.assertIn(
            "inspection-only", source
        )
        self.assertNotIn(
            "systemctl", source
        )


if __name__ == "__main__":
    unittest.main()
