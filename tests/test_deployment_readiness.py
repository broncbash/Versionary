"""Offline deployment readiness gate regression tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "installer/deployment-readiness.py"
spec = importlib.util.spec_from_file_location("arby_deployment_readiness", SCRIPT)
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class DeploymentReadinessTests(unittest.TestCase):
    def test_preflight_ready_does_not_enable_production(self):
        fake = {"ready": True, "checks": [{"name": "supported_os", "ok": True}]}
        with patch.object(readiness, "load_preflight") as loader:
            loader.return_value.inspect.return_value = fake
            result = readiness.report(server="https://example.test", ca_cert="/tmp/ca.crt")
        self.assertTrue(result["ready_for_isolated_test"])
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(result["changes_made"])
        self.assertFalse(result["network_requests_made"])
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "production_installer")["ok"])

    def test_preflight_failure_keeps_all_gates_closed(self):
        fake = {"ready": False, "checks": [{"name": "ca_certificate", "ok": False}]}
        with patch.object(readiness, "load_preflight") as loader:
            loader.return_value.inspect.return_value = fake
            result = readiness.report(server="https://example.test", ca_cert="/tmp/missing.crt")
        self.assertFalse(result["ready_for_isolated_test"])
        self.assertFalse(result["ready_for_production"])
        self.assertFalse(next(c for c in result["checks"] if c["name"] == "end_to_end_enrollment")["ok"])

    def test_report_passes_explicit_inputs_to_preflight(self):
        fake = {"ready": False, "checks": []}
        with patch.object(readiness, "load_preflight") as loader:
            loader.return_value.inspect.return_value = fake
            readiness.report(server="https://example.test", ca_cert="/tmp/ca.crt",
                             package=Path("/tmp/pkg.tar.gz"), os_release="/tmp/os-release")
            loader.return_value.inspect.assert_called_once_with(
                server="https://example.test", ca_cert="/tmp/ca.crt",
                package=Path("/tmp/pkg.tar.gz"), os_release="/tmp/os-release")

    def test_cli_outputs_machine_readable_report(self):
        fake = {"ready": False, "checks": []}
        with patch.object(readiness, "load_preflight") as loader:
            loader.return_value.inspect.return_value = fake
            import contextlib
            import io
            import json
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = readiness.main(["--server", "https://example.test",
                                       "--ca-cert", "/tmp/missing.crt"])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(out.getvalue())["ready_for_production"])


if __name__ == "__main__":
    unittest.main()
