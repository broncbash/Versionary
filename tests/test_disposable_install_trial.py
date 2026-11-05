"""Disposable trial must clean its private workspace on failure."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

file = Path(__file__).resolve().parents[1] / "installer/disposable-install-trial.py"
spec = importlib.util.spec_from_file_location("disposable_trial", file)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class DisposableTrialTests(unittest.TestCase):
    def test_success_stages_and_verifies(self):
        roots = []
        class Stage:
            @staticmethod
            def stage(*, root, verify_only=False, **kwargs):
                roots.append(root)
                return {"status": "verified", "changes_made": False} if verify_only else {"status": "staged"}
        with patch.object(trial, "load", return_value=Stage):
            result = trial.trial(server="https://example.test", ca_cert="ca.pem")
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["production_installed"])
        self.assertFalse(result["systemd_started"])
        self.assertEqual(len(roots), 2)
        self.assertFalse(roots[0].exists())

    def test_failure_cleans_workspace(self):
        roots = []
        class Stage:
            @staticmethod
            def stage(*, root, **kwargs):
                roots.append(root)
                raise ValueError("deliberate failure")
        with patch.object(trial, "load", return_value=Stage):
            with self.assertRaises(ValueError):
                trial.trial(server="https://example.test", ca_cert="ca.pem")
        self.assertFalse(roots[0].exists())

    def test_cli_rejects_live_install(self):
        with self.assertRaises(SystemExit) as caught:
            trial.main(["--install"])
        self.assertEqual(caught.exception.code, 2)
