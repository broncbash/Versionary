"""Isolated release switch and rollback tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_switch_trial", ROOT / "installer/release-switch-trial.py")
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class ReleaseSwitchTrialTests(unittest.TestCase):
    def test_rejects_filesystem_root(self):
        with self.assertRaises(ValueError):
            trial.require_test_root("/")

    def test_rejects_missing_active_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "opt/versionary-agent"
            app.mkdir(parents=True)
            with self.assertRaises(ValueError):
                trial.active_identifier(app)

    def test_switch_restores_original_release(self):
        atomic = trial.load("atomic-release.py", "test_release_switch_atomic")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "opt/versionary-agent"
            app.mkdir(parents=True)
            original = atomic.install_release(app, {"__main__.py": b"print('original')\n"})
            class Validator:
                @staticmethod
                def load_modules(path):
                    return {"__main__.py": b"print('candidate')\n"}
            real_load = trial.load
            def mocked_load(filename, name):
                if filename == "validate-package.py":
                    return Validator
                return real_load(filename, name)
            with patch.object(trial, "load", side_effect=mocked_load):
                result = trial.switch_and_restore(root=root, package=root / "unused.tar.gz")
            self.assertEqual(result["status"], "restored")
            self.assertEqual(result["active_release"], original)
            self.assertEqual(trial.active_identifier(app), original)
            self.assertNotEqual(result["candidate_release"], original)
            self.assertFalse(result["production_installed"])

    def test_rejects_malformed_active_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / "agent").symlink_to("../../etc")
            with self.assertRaises(ValueError):
                trial.active_identifier(app)
