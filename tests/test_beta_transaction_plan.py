"""Batch 8C.3A: verify read-only intent, no false recovery guarantees."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / 'installer'
spec = importlib.util.spec_from_file_location('beta_transaction_plan', HERE / 'beta-transaction-plan.py')
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


class BetaTransactionPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'package.tar.gz'
        self.package.write_bytes(b'fixture')
        self.modules = {'__main__.py': b'print(1)'}
        self.server = 'https://patch.example.test'
        self.ca = b'example CA'
        self.real_load = plan._load

        def fake_load(name, alias):
            if name == 'beta-preflight.py':
                return type('Preflight', (), {'inspect': lambda *args: {'changes_made': False}})()
            if name == 'validate-package.py':
                return type('Validator', (), {'load_modules': lambda *args: self.modules})()
            return self.real_load(name, alias)

        p = patch.object(plan, '_load', side_effect=fake_load)
        p.start()
        self.addCleanup(p.stop)

    def test_plan_is_read_only_and_deterministic(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        first = plan.build(self.root, self.server, self.ca, self.package)
        self.assertEqual(first, plan.build(self.root, self.server, self.ca, self.package))
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.assertFalse(first['changes_made'])
        self.assertFalse(first['recovery_available'])
        self.assertFalse(first['production_approved'])

    def test_five_named_assets(self):
        result = plan.build(self.root, self.server, self.ca, self.package)
        self.assertEqual([a['name'] for a in result['assets']],
                         ['release', 'config', 'ca', 'service', 'timer'])
        self.assertEqual([a['kind'] for a in result['assets']],
                         ['symlink', 'file', 'file', 'file', 'file'])
        self.assertTrue(all(len(a['sha256']) == 64 for a in result['assets']))

    def test_ca_change_changes_only_ca_digest(self):
        old = plan.build(self.root, self.server, self.ca, self.package)
        new = plan.build(self.root, self.server, b'new CA', self.package)
        changed = [a['name'] for a, b in zip(old['assets'], new['assets']) if a['sha256'] != b['sha256']]
        self.assertEqual(changed, ['ca'])

    def test_root_refused(self):
        with self.assertRaises(ValueError):
            plan.build('/', self.server, self.ca, self.package)

    def test_root_symlink_refused(self):
        with tempfile.TemporaryDirectory() as parent:
            link = Path(parent) / 'link'
            link.symlink_to(self.root, target_is_directory=True)
            with self.assertRaises(ValueError):
                plan.build(link, self.server, self.ca, self.package)

    def test_preflight_failure_propagates(self):
        with patch.object(plan, '_load', return_value=type('Reject', (), {'inspect': lambda *args: (_ for _ in ()).throw(ValueError('conflict'))})()):
            with self.assertRaisesRegex(ValueError, 'conflict'):
                plan.build(self.root, self.server, self.ca, self.package)


if __name__ == '__main__':
    unittest.main()
