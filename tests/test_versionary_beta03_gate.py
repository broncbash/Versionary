import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

import versionary_beta03_gate as gate
import versionary_timer_integration as timer


class Beta03Tests(unittest.TestCase):

    def test_success(self):
        self.assertEqual(gate.run_fake_scan(0)["status"], "success")

    def test_failure(self):
        self.assertEqual(gate.run_fake_scan(17)["status"], "failed")

    def test_exit_code_preserved(self):
        self.assertEqual(gate.run_fake_scan(23)["exit_code"], 23)

    def test_noninteractive_execution(self):
        self.assertEqual(gate.run_fake_scan(0)["exit_code"], 0)

    def test_timer_is_inert(self):
        with patch.object(
            timer, "verify_preview",
            return_value=("passed", "verified"),
        ):
            result = gate.verify_inert_timer()
        self.assertEqual(result["status"], "passed")

    def test_missing_validator(self):
        with patch.object(
            timer.subprocess,
            "run",
            side_effect=FileNotFoundError,
        ):
            result = gate.verify_inert_timer()
        self.assertEqual(result["status"], "unavailable")

    def test_unsafe_paths(self):
        with self.assertRaisesRegex(ValueError, "Unsupported character"):
            timer.units(Path("/tmp/bad%path"))


if __name__ == "__main__":
    unittest.main()
