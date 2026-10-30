"""Disposable filesystem transaction checkpoints; no real installation paths."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "installer/disposable-filesystem-transaction.py"
spec = importlib.util.spec_from_file_location("filesystem_transaction_test", path)
transaction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transaction)


class DisposableFilesystemTransactionTests(unittest.TestCase):
    def test_successful_generation(self):
        result = transaction.run()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["journal_states"][-1], "verified")
        self.assertFalse(result["production_installed"])

    def test_failure_at_every_checkpoint(self):
        for checkpoint in transaction.STAGES:
            with self.subTest(checkpoint=checkpoint):
                result = transaction.run(checkpoint)
                self.assertEqual(result["status"], "recovered")
                self.assertEqual(result["journal_states"][-1], "recovered")
                self.assertFalse(result["temporary_artifacts_retained"])

    def test_invalid_checkpoint(self):
        with self.assertRaises(ValueError):
            transaction.run("unrecognized")

    def test_no_services_or_enrollment(self):
        result = transaction.run("timer")
        self.assertFalse(result["systemd_started"])
        self.assertFalse(result["agent_enrolled"])
        self.assertFalse(result["external_network_requests_made"])

    def test_all_components_covered(self):
        self.assertEqual(set(transaction.NAMES),
                         {"release", "config", "ca", "service", "timer"})

    def test_deterministic_checkpoint_order(self):
        expected = ["prepared", *transaction.NAMES, "verified"]
        self.assertEqual(transaction.run()["journal_states"], expected)


if __name__ == "__main__":
    unittest.main()
