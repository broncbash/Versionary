"""Crash and corruption tests for disposable-only recovery engine."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'installer/recovery-engine.py'
spec = importlib.util.spec_from_file_location('disposable_recovery_engine', SOURCE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

class RecoveryMatrix(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = engine.initialize(self.temp.name)
        self.old = {n: ('old-' + n).encode() for n in engine.ASSETS}
        self.new = {n: ('new-' + n).encode() for n in engine.ASSETS}
        engine.prepare(self.root, self.old, self.new)

    def check(self, values):
        for n in engine.ASSETS:
            self.assertEqual((self.root / 'live' / n).read_bytes(), values[n])

    def test_complete_apply(self):
        self.assertEqual(engine.apply(self.root)['state'], 'verified')
        self.check(self.new)

    def test_complete_rollback(self):
        engine.apply(self.root)
        self.assertEqual(engine.recover(self.root)['state'], 'recovered')
        self.check(self.old)

    def test_idempotent_rollback(self):
        engine.apply(self.root)
        engine.recover(self.root)
        self.assertEqual(engine.recover(self.root)['state'], 'recovered')

    def test_apply_twice_refused(self):
        engine.apply(self.root)
        with self.assertRaises(engine.RecoveryError):
            engine.apply(self.root)

    def test_unmarked_root_refused(self):
        (self.root / '.disposable-recovery-test').unlink()
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_root_symlink_refused(self):
        link = self.root.parent / ('link-' + self.root.name)
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)
        with self.assertRaises(engine.RecoveryError):
            engine.recover(link)

    def test_corrupt_journal_refused(self):
        (self.root / 'journal.json').write_text('{bad')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_corrupt_backup_refused(self):
        (self.root / 'backup' / 'ca').write_bytes(b'corrupt')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_corrupt_candidate_refused(self):
        (self.root / 'candidate' / 'ca').write_bytes(b'corrupt')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_unknown_live_content_refused_without_rollback(self):
        engine.apply(self.root)
        (self.root / 'live' / 'ca').write_bytes(b'unknown')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)
        self.assertEqual((self.root / 'live' / 'release').read_bytes(), self.new['release'])

    def test_live_symlink_refused(self):
        path = self.root / 'live' / 'ca'
        path.unlink()
        path.symlink_to(self.root / 'backup' / 'ca')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_live_hardlink_refused(self):
        path = self.root / 'live' / 'ca'
        path.unlink()
        os.link(self.root / 'backup' / 'ca', path)
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)

    def test_prepare_again_refused(self):
        with self.assertRaises(engine.RecoveryError):
            engine.prepare(self.root, self.old, self.new)

    def test_incomplete_assets_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = engine.initialize(folder)
            with self.assertRaises(engine.RecoveryError):
                engine.prepare(root, {'ca': b'a'}, self.new)

    def test_all_interruption_points(self):
        for stage in (*engine.ASSETS, 'verified'):
            for position in ('before', 'after'):
                with self.subTest(stage=stage, position=position):
                    with tempfile.TemporaryDirectory() as folder:
                        root = engine.initialize(folder)
                        engine.prepare(root, self.old, self.new)
                        with self.assertRaises(engine.Interrupted):
                            engine.apply(root, fail_at=position + ':' + stage)
                        self.assertEqual(engine.recover(root)['state'], 'recovered')
                        for n in engine.ASSETS:
                            self.assertEqual((root / 'live' / n).read_bytes(), self.old[n])

    def test_all_rollback_interruption_points(self):
        for name in engine.ASSETS:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as folder:
                    root = engine.initialize(folder)
                    engine.prepare(root, self.old, self.new)
                    engine.apply(root)
                    with self.assertRaises(engine.Interrupted):
                        engine.recover(root, fail_after=name)
                    self.assertEqual(engine.recover(root)['state'], 'recovered')
                    for n in engine.ASSETS:
                        self.assertEqual((root / 'live' / n).read_bytes(), self.old[n])

if __name__ == '__main__':
    unittest.main()
