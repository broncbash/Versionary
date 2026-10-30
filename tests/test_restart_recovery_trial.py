"""Independent-process disposable recovery exercise."""
import importlib.util
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "installer/restart-recovery-trial.py"
spec = importlib.util.spec_from_file_location("restart_recovery_trial", source)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class RestartRecoveryTrialTests(unittest.TestCase):
    def test_each_worker_termination_checkpoint(self):
        for checkpoint in trial.PARTS:
            with self.subTest(checkpoint=checkpoint):
                result = trial.run(checkpoint)
                self.assertEqual(result["status"], "recovered")
                self.assertFalse(result["production_installed"])

    def test_journal_tampering_refused(self):
        result = trial.run("ca", "journal")
        self.assertEqual(result["status"], "refused")

    def test_backup_tampering_refused(self):
        result = trial.run("ca", "backup")
        self.assertEqual(result["status"], "refused")

    def test_unknown_checkpoint_refused(self):
        with self.assertRaises(ValueError):
            trial.run("unknown")

    def test_unknown_tamper_refused(self):
        with self.assertRaises(ValueError):
            trial.run("ca", "unknown")

    def test_no_live_services(self):
        result = trial.run("timer")
        self.assertFalse(result["systemd_started"])
        self.assertFalse(result["agent_enrolled"])
        self.assertFalse(result["external_network_requests_made"])


if __name__ == "__main__":
    unittest.main()
