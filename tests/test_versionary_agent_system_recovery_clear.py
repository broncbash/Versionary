import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "installer/versionary-agent-system-recovery.py"
)
spec = importlib.util.spec_from_file_location("recovery_clear", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RecoveryClearTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.payloads = {"etc/versionary-agent/config.json": b"config"}

    def fail_install(self):
        with self.assertRaises(RuntimeError):
            mod.install_isolated(
                self.root, self.payloads, fail_after=0
            )

    def test_failed_install_can_be_cleared(self):
        self.fail_install()
        result = mod.review_and_clear(self.root, self.payloads)
        self.assertEqual(result["status"], "cleared")
        self.assertEqual(result["files_removed"], 0)
        self.assertEqual(mod.inspect_pending(self.root)["status"], "clear")

    def test_retry_after_clear(self):
        self.fail_install()
        mod.review_and_clear(self.root, self.payloads)
        result = mod.install_isolated(self.root, self.payloads)
        self.assertEqual(result["created"], 1)

    def test_wrong_payload_refused(self):
        self.fail_install()
        with self.assertRaises(ValueError):
            mod.review_and_clear(
                self.root,
                {"etc/versionary-agent/config.json": b"other"},
            )

    def test_existing_file_not_deleted(self):
        self.fail_install()
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"config")
        with self.assertRaises(RuntimeError):
            mod.review_and_clear(self.root, self.payloads)
        self.assertEqual(target.read_bytes(), b"config")

    def test_symlinked_journal_refused(self):
        self.fail_install()
        journal = self.root / ".versionary-install-journal.json"
        backup = self.root / "saved-journal"
        journal.rename(backup)
        journal.symlink_to(backup)
        with self.assertRaises(ValueError):
            mod.review_and_clear(self.root, self.payloads)

    def test_no_pending_journal_refused(self):
        with self.assertRaises(FileNotFoundError):
            mod.review_and_clear(self.root, self.payloads)


if __name__ == "__main__":
    unittest.main()
