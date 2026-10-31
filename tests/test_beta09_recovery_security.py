"""Beta 0.9 disposable recovery security tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "installer/recovery-engine.py"
spec = importlib.util.spec_from_file_location("beta09_recovery", SOURCE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class RecoverySecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = engine.initialize(self.temp.name)
        old = {name: ("old:" + name).encode() for name in engine.ASSETS}
        new = {name: ("new:" + name).encode() for name in engine.ASSETS}
        engine.prepare(self.root, old, new)

    def test_boolean_journal_version_rejected(self):
        path = self.root / "journal.json"
        data = json.loads(path.read_text())
        data["version"] = True
        path.write_text(json.dumps(data))
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_world_readable_root_rejected(self):
        self.root.chmod(0o755)
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_world_readable_asset_directory_rejected(self):
        (self.root / "backup").chmod(0o755)
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_symlinked_asset_directory_rejected(self):
        backup = self.root / "backup"
        backup.rename(self.root / "backup-original")
        backup.symlink_to(
            self.root / "backup-original",
            target_is_directory=True
        )
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_valid_disposable_recovery_still_works(self):
        engine.apply(self.root)
        self.assertEqual(
            engine.recover(self.root)["state"],
            "recovered"
        )


if __name__ == "__main__":
    unittest.main()
