"""Offline recovery fault matrix contract and reporting tests."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "installer/recovery-fault-matrix.py"
spec = importlib.util.spec_from_file_location("recovery_fault_matrix", SOURCE)
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


class RecoveryFaultMatrixTests(unittest.TestCase):
    def test_default_case_count_and_uniqueness(self):
        cases = matrix.cases(("release", "config", "ca", "service", "timer"))
        self.assertEqual(len(cases), 37)
        self.assertEqual(len(set(cases)), len(cases))

    def test_exhaustive_case_count_and_uniqueness(self):
        cases = matrix.cases(("release", "config", "ca", "service", "timer"), True)
        self.assertEqual(len(cases), 65)
        self.assertEqual(len(set(cases)), len(cases))

    def test_switch_and_recovery_cross_product(self):
        cases = matrix.cases(("a", "b"))
        self.assertIn(("recovery", "a", "b", None), cases)
        self.assertIn(("recovery", "b", "a", None), cases)

    def test_first_disposable_case_runs(self):
        result = matrix.run(max_cases=1)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["cases"], 1)
        self.assertEqual(result["passed"], 1)

    def test_tamper_case_runs(self):
        trial = matrix.load_trial()
        outcome = matrix.evaluate(trial, ("tamper", "ca", None, "backup"))
        self.assertEqual(outcome, "refused")

    def test_recovery_case_runs(self):
        trial = matrix.load_trial()
        outcome = matrix.evaluate(trial, ("recovery", "config", "timer", None))
        self.assertEqual(outcome, "recovered")

    def test_invalid_max_cases(self):
        for invalid in (0, -1, True, 1.5, "2"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    matrix.run(max_cases=invalid)

    def test_mismatched_status_detected(self):
        class FakeTrial:
            def run(self, *args, **kwargs):
                return {"status": "recovered", "production_installed": False,
                        "systemd_started": False}
        with self.assertRaises(AssertionError):
            matrix.evaluate(FakeTrial(), ("tamper", "ca", None, "backup"))

    def test_side_effect_flag_detected(self):
        class FakeTrial:
            def run(self, *args, **kwargs):
                return {"status": "recovered", "production_installed": True,
                        "systemd_started": False}
        with self.assertRaises(AssertionError):
            matrix.evaluate(FakeTrial(), ("switch", "ca", None, None))

    def test_enrollment_flag_detected(self):
        class FakeTrial:
            def run(self, *args, **kwargs):
                return {"status": "recovered", "production_installed": False,
                        "systemd_started": False, "agent_enrolled": True}
        with self.assertRaises(AssertionError):
            matrix.evaluate(FakeTrial(), ("switch", "ca", None, None))

    def test_failures_are_reported_without_suppressing(self):
        with patch.object(matrix, "evaluate", side_effect=RuntimeError("injected")):
            report = matrix.run(max_cases=2)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failed"], 2)
        self.assertIn("injected", report["results"][0]["error"])

    def test_cli_summary(self):
        completed = subprocess.run([sys.executable, str(SOURCE), "--max-cases", "1",
                                    "--summary"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "passed")
        self.assertNotIn("results", report)

    def test_cli_invalid_limit_refused(self):
        completed = subprocess.run([sys.executable, str(SOURCE), "--max-cases", "0"],
                                   capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
