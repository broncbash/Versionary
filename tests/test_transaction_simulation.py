"""Fault matrix for non-mutating coordinated rollback model."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "installer/transaction-simulation.py"
spec = importlib.util.spec_from_file_location("transaction_simulation", path)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class TransactionSimulationTests(unittest.TestCase):
    def test_success(self):
        result = model.simulate()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(result["journal"]), 7)
        self.assertFalse(result["existing_files_modified"])
        self.assertFalse(result["production_installed"])

    def test_each_failure_checkpoint(self):
        for checkpoint in model.STEPS:
            with self.subTest(checkpoint=checkpoint):
                result = model.simulate(checkpoint)
                self.assertEqual(result["status"], "recovered")
                self.assertTrue(result["recovery_verified"])
                self.assertEqual(result["journal"][-1]["state"], "recovered")
                self.assertFalse(result["systemd_started"])
                self.assertFalse(result["agent_enrolled"])

    def test_invalid_checkpoint_refused(self):
        with self.assertRaises(ValueError):
            model.simulate("arbitrary")

    def test_deterministic_journal(self):
        self.assertEqual(model.simulate("ca"), model.simulate("ca"))

    def test_all_asset_steps_present(self):
        self.assertEqual(set(model.ASSETS), {"release", "config", "ca", "service", "timer"})

    def test_no_external_requests(self):
        self.assertFalse(model.simulate()["external_network_requests_made"])


if __name__ == "__main__":
    unittest.main()
