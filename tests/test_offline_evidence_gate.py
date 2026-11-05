"""Fail-closed offline evidence gate tests."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "installer/offline-evidence-gate.py"
spec = importlib.util.spec_from_file_location("offline_evidence_gate", SOURCE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

FLAGS = {flag: False for flag in gate.REQUIRED_FLAGS}
BETA = dict(status="passed", mode="disposable-isolated-beta", package_built=True,
            test_ca_generated=True, initial_stage="staged", repeat_stage="staged",
            integrity_audit="verified", tls_protocol_check="passed",
            network_requests_made=True, **FLAGS)
MATRIX = dict(status="passed", mode="offline-disposable-recovery-fault-matrix",
              exhaustive=True, cases=65, passed=65, failed=0, **FLAGS)


class OfflineEvidenceGateTests(unittest.TestCase):
    def test_valid_disposable_evidence(self):
        report = gate.inspect(BETA, MATRIX, 716)
        self.assertEqual(report["status"], "passed")
        self.assertIs(report["deployment_permitted"], False)

    def test_missing_fields_fail_closed(self):
        for field in gate.REQUIRED_BETA:
            with self.subTest(field=field):
                beta = dict(BETA)
                del beta[field]
                self.assertEqual(gate.inspect(beta, MATRIX, 716)["status"], "failed")

    def test_missing_matrix_fields_fail_closed(self):
        for field in gate.REQUIRED_MATRIX:
            with self.subTest(field=field):
                matrix = dict(MATRIX)
                del matrix[field]
                self.assertEqual(gate.inspect(BETA, matrix, 716)["status"], "failed")

    def test_beta_false_safety_flags(self):
        for flag in gate.REQUIRED_FLAGS:
            with self.subTest(flag=flag):
                beta = dict(BETA, **{flag: True})
                self.assertEqual(gate.inspect(beta, MATRIX, 716)["status"], "failed")

    def test_matrix_false_safety_flags(self):
        for flag in gate.REQUIRED_FLAGS:
            with self.subTest(flag=flag):
                matrix = dict(MATRIX, **{flag: True})
                self.assertEqual(gate.inspect(BETA, matrix, 716)["status"], "failed")

    def test_reject_partial_matrix(self):
        for field, value in (("exhaustive", False), ("cases", 37),
                             ("passed", 64), ("failed", 1), ("status", "failed")):
            with self.subTest(field=field):
                matrix = dict(MATRIX, **{field: value})
                self.assertEqual(gate.inspect(BETA, matrix, 716)["status"], "failed")

    def test_reject_bool_integer_counts(self):
        for field in ("cases", "passed", "failed"):
            with self.subTest(field=field):
                matrix = dict(MATRIX, **{field: True})
                self.assertEqual(gate.inspect(BETA, matrix, 716)["status"], "failed")

    def test_reject_low_test_count(self):
        for count in (0, 715, True, -1):
            with self.subTest(count=count):
                self.assertEqual(gate.inspect(BETA, MATRIX, count)["status"], "failed")

    def test_reject_wrong_beta_stage(self):
        beta = dict(BETA, integrity_audit="unverified")
        self.assertEqual(gate.inspect(beta, MATRIX, 716)["status"], "failed")

    def test_reject_no_loopback_evidence(self):
        beta = dict(BETA, network_requests_made=False)
        self.assertEqual(gate.inspect(beta, MATRIX, 716)["status"], "failed")

    def test_reject_non_object(self):
        with self.assertRaises(ValueError):
            gate.inspect([], MATRIX, 716)

    def test_json_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"status":"passed","status":"failed"}')
            with self.assertRaises(ValueError):
                gate.load_json(path)

    def test_json_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original"
            original.write_text("{}")
            link = Path(directory) / "link"
            link.symlink_to(original)
            with self.assertRaises(OSError):
                gate.load_json(link)

    def test_json_oversized_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large"
            path.write_bytes(b" " * (1048576 + 1))
            with self.assertRaises(ValueError):
                gate.load_json(path)

    def test_cli_valid_report_and_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            beta = Path(directory) / "beta.json"
            matrix = Path(directory) / "matrix.json"
            beta.write_text(json.dumps(BETA))
            matrix.write_text(json.dumps(MATRIX))
            proc = subprocess.run([sys.executable, str(SOURCE), "--beta-json", str(beta),
                                   "--matrix-json", str(matrix), "--tests", "716"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(json.loads(proc.stdout)["production_approved"])

    def test_cli_missing_evidence_exits_nonzero(self):
        proc = subprocess.run([sys.executable, str(SOURCE), "--beta-json", "/missing/beta",
                               "--matrix-json", "/missing/matrix", "--tests", "716"],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
