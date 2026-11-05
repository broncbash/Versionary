"""Offline contract tests for installer/disposable-install-trial.py.

No real installer, services, network, or credentials are used.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'installer' / 'disposable-install-trial.py'


def module():
    spec = importlib.util.spec_from_file_location('versionary_disposable_trial_contract', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class FakeStaging:
    def __init__(self, fail=None):
        self.fail = fail
        self.calls = []
        self.roots = []

    def stage(self, *, root, verify_only=False, **kwargs):
        self.calls.append((verify_only, kwargs))
        self.roots.append(root)
        if self.fail == ('verify' if verify_only else 'stage'):
            raise RuntimeError('simulated failure')
        if not verify_only:
            (root / 'marker').write_text('disposable only')
            return {'status': 'staged'}
        return {'status': 'verified', 'changes_made': False}


class DisposableTrialContract(unittest.TestCase):
    def test_stage_then_verify_and_cleanup(self):
        trial = module()
        fake = FakeStaging()
        with patch.object(trial, 'load', return_value=fake):
            report = trial.trial(server='https://example.invalid', ca_cert='/fake/ca.pem', package='/fake/package.tar.gz')
        self.assertEqual([c[0] for c in fake.calls], [False, True])
        self.assertTrue(all(not p.exists() for p in fake.roots))
        self.assertEqual(report['status'], 'passed')
        self.assertFalse(report['production_installed'])
        self.assertFalse(report['systemd_started'])
        self.assertFalse(report['agent_enrolled'])

    def test_cleanup_on_stage_failure(self):
        trial = module()
        fake = FakeStaging('stage')
        with patch.object(trial, 'load', return_value=fake):
            with self.assertRaises(RuntimeError):
                trial.trial(server='https://example.invalid', ca_cert='/fake/ca.pem')
        self.assertTrue(fake.roots)
        self.assertTrue(all(not p.exists() for p in fake.roots))

    def test_cleanup_on_verify_failure(self):
        trial = module()
        fake = FakeStaging('verify')
        with patch.object(trial, 'load', return_value=fake):
            with self.assertRaises(RuntimeError):
                trial.trial(server='https://example.invalid', ca_cert='/fake/ca.pem')
        self.assertTrue(all(not p.exists() for p in fake.roots))

    def test_no_change_to_unrelated_file(self):
        trial = module()
        fake = FakeStaging()
        with tempfile.TemporaryDirectory() as d:
            sentinel = Path(d) / 'sentinel'
            sentinel.write_text('unchanged')
            with patch.object(trial, 'load', return_value=fake):
                trial.trial(server='https://example.invalid', ca_cert='/fake/ca.pem')
            self.assertEqual(sentinel.read_text(), 'unchanged')


if __name__ == '__main__':
    unittest.main()
