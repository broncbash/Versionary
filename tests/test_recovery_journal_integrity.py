"""Batch 8C.2: journal corruption and interrupted rollback fail-closed tests.

All tests operate exclusively on fresh disposable temporary directories.
"""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'installer/recovery-engine.py'
spec = importlib.util.spec_from_file_location('recovery_integrity_under_test', SOURCE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

class JournalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = engine.initialize(self.temp.name)
        self.old = {name: ('old-' + name).encode() for name in engine.ASSETS}
        self.new = {name: ('new-' + name).encode() for name in engine.ASSETS}
        engine.prepare(self.root, self.old, self.new)

    def mutate_journal(self, callback):
        path = self.root / 'journal.json'
        payload = json.loads(path.read_text())
        callback(payload)
        path.write_text(json.dumps(payload))

    def assert_unchanged_on_recovery_failure(self):
        before = {name: (self.root / 'live' / name).read_bytes() for name in engine.ASSETS}
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root)
        self.assertEqual(before, {name: (self.root / 'live' / name).read_bytes() for name in engine.ASSETS})

    def test_reject_unknown_journal_field(self):
        self.mutate_journal(lambda j: j.update(unexpected=True))
        self.assert_unchanged_on_recovery_failure()

    def test_reject_list_manifest(self):
        self.mutate_journal(lambda j: j.update(previous=list(engine.ASSETS)))
        self.assert_unchanged_on_recovery_failure()

    def test_reject_null_manifest(self):
        self.mutate_journal(lambda j: j.update(candidate=None))
        self.assert_unchanged_on_recovery_failure()

    def test_reject_extra_manifest_asset(self):
        self.mutate_journal(lambda j: j['previous'].update(extra='0'*64))
        self.assert_unchanged_on_recovery_failure()

    def test_reject_unknown_journal_state(self):
        self.mutate_journal(lambda j: j.update(state='committed'))
        self.assert_unchanged_on_recovery_failure()

    def test_reject_journal_symlink(self):
        path = self.root / 'journal.json'
        data = path.read_bytes()
        path.unlink()
        outside = self.root / 'outside.json'
        outside.write_bytes(data)
        path.symlink_to(outside)
        self.assert_unchanged_on_recovery_failure()

    def test_reject_journal_hardlink(self):
        path = self.root / 'journal.json'
        outside = self.root / 'outside.json'
        os.link(path, outside)
        self.assert_unchanged_on_recovery_failure()

    def test_reject_stale_pending_on_recovery(self):
        engine.apply(self.root)
        pending = self.root / 'live' / 'ca.pending'
        pending.write_bytes(b'unknown-pending')
        with self.assertRaises(engine.RecoveryError):
            engine.recover(self.root, fail_after='ca')
        self.assertEqual(pending.read_bytes(), b'unknown-pending')

    def test_rollback_resumes_after_each_interruption(self):
        for name in engine.ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = engine.initialize(folder)
                engine.prepare(root, self.old, self.new)
                engine.apply(root)
                with self.assertRaises(engine.Interrupted):
                    engine.recover(root, fail_after=name)
                self.assertEqual(engine.recover(root)['state'], 'recovered')
                self.assertEqual(engine.recover(root)['state'], 'recovered')
                for asset in engine.ASSETS:
                    self.assertEqual((root / 'live' / asset).read_bytes(), self.old[asset])

if __name__ == '__main__':
    unittest.main()
