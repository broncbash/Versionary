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


    def test_recovery_interruption_at_every_asset(self):
        for checkpoint in trial.PARTS:
            with self.subTest(checkpoint=checkpoint):
                result = trial.run("ca", recover_stop_at=checkpoint)
                self.assertEqual(result["status"], "recovered")
                self.assertEqual(result["recovery_interrupted_at"], checkpoint)
                self.assertTrue(result["idempotent_recovery_verified"])

    def test_switch_interruption_cross_recovery_interruption(self):
        for switch in trial.PARTS:
            for recovery in trial.PARTS:
                with self.subTest(switch=switch, recovery=recovery):
                    result = trial.run(switch, recover_stop_at=recovery)
                    self.assertEqual(result["status"], "recovered")

    def test_active_generation_tampering_refused(self):
        self.assertEqual(trial.run("ca", "active")["status"], "refused")

    def test_symlinked_journal_refused(self):
        self.assertEqual(trial.run("ca", "journal_symlink")["status"], "refused")

    def test_symlinked_backup_refused(self):
        self.assertEqual(trial.run("ca", "backup_symlink")["status"], "refused")

    def test_symlinked_active_asset_refused(self):
        self.assertEqual(trial.run("ca", "active_symlink")["status"], "refused")

    def test_symlinked_restore_staging_refused(self):
        self.assertEqual(trial.run("ca", "restore_symlink")["status"], "refused")

    def test_unknown_recovery_checkpoint_refused(self):
        with self.assertRaises(ValueError):
            trial.run("ca", recover_stop_at="unknown")

    def test_invalid_journal_state_rejected(self):
        with self.assertRaises(ValueError):
            trial.journal(Path("/nonexistent"), "bogus")

    def test_digests_stable(self):
        self.assertEqual(trial.expected_prior()["ca"], trial.digest(b"old:ca"))

    def test_recovery_result_has_no_production_side_effects(self):
        result = trial.run("release", recover_stop_at="timer")
        self.assertFalse(result["production_installed"])
        self.assertFalse(result["systemd_started"])
        self.assertFalse(result["agent_enrolled"])
        self.assertFalse(result["external_network_requests_made"])


if __name__ == "__main__":
    unittest.main()
