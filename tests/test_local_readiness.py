"""Local-only readiness coordinator regression tests."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "installer/local-readiness.py"
spec = importlib.util.spec_from_file_location("local_readiness", SOURCE)
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)

FLAGS = {"production_installed": False, "systemd_started": False,
         "agent_enrolled": False, "external_network_requests_made": False}
BETA = {"status": "passed", "mode": "disposable-isolated-beta",
        "package_built": True, "test_ca_generated": True,
        "initial_stage": "staged", "repeat_stage": "staged",
        "integrity_audit": "verified", "tls_protocol_check": "passed",
        "network_requests_made": True, **FLAGS}
MATRIX = {"status": "passed", "mode": "offline-disposable-recovery-fault-matrix",
          "exhaustive": True, "cases": 65, "passed": 65, "failed": 0, **FLAGS}


class ReadinessTests(unittest.TestCase):
    def fake(self, command):
        if "unittest" in command:
            return subprocess.CompletedProcess(command, 0, "", "Ran 732 tests in 1.0s\n\nOK\n")
        if "--protocol-check" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(BETA), "")
        if "--exhaustive" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(MATRIX), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    def test_success(self):
        result = readiness.verify(self.fake)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["regression_tests"], 732)
        self.assertFalse(result["deployment_permitted"])

    def test_package_failure_stops(self):
        def failing(command):
            return subprocess.CompletedProcess(command, 3, "", "")
        result = readiness.verify(failing)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["completed_steps"], ["package"])

    def test_test_failure_stops(self):
        def failing(command):
            if "unittest" in command:
                return subprocess.CompletedProcess(command, 1, "", "")
            return self.fake(command)
        self.assertEqual(readiness.verify(failing)["status"], "failed")

    def test_missing_test_marker_fails(self):
        def invalid(command):
            result = self.fake(command)
            if "unittest" in command:
                return subprocess.CompletedProcess(command, 0, "", "")
            return result
        self.assertEqual(readiness.verify(invalid)["status"], "failed")

    def test_partial_matrix_fails(self):
        def invalid(command):
            result = self.fake(command)
            if "--exhaustive" in command:
                return subprocess.CompletedProcess(command, 0,
                                                   json.dumps({**MATRIX, "cases": 37}), "")
            return result
        self.assertEqual(readiness.verify(invalid)["status"], "failed")

    def test_invalid_beta_json_fails(self):
        def invalid(command):
            if "--protocol-check" in command:
                return subprocess.CompletedProcess(command, 0, "{", "")
            return self.fake(command)
        self.assertEqual(readiness.verify(invalid)["status"], "failed")

    def test_timeout_fails(self):
        def timed_out(command):
            raise subprocess.TimeoutExpired(command, 300)
        self.assertEqual(readiness.verify(timed_out)["status"], "failed")

    def test_no_deployment_authority_on_failure(self):
        result = readiness.verify(lambda cmd: subprocess.CompletedProcess(cmd, 1, "", ""))
        self.assertIs(result["production_approved"], False)
        self.assertIs(result["deployment_permitted"], False)
        self.assertIs(result["hosted_ci_used"], False)


if __name__ == "__main__":
    unittest.main()
