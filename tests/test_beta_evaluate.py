"""Regression coverage for the non-deploying beta evaluation entry point."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "installer/beta-evaluate.py"
spec = importlib.util.spec_from_file_location("patch_command_beta_evaluate", SCRIPT)
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class BetaEvaluateTests(unittest.TestCase):
    def test_evaluation_reports_safe_disposable_result(self):
        fake = {
            "status": "passed", "production_installed": False,
            "systemd_started": False, "agent_enrolled": False,
        }
        class Selftest:
            def run(self, **kwargs):
                self.kwargs = kwargs
                return fake
        stub = Selftest()
        with patch.object(evaluate, "load", return_value=stub):
            result = evaluate.evaluate(protocol_check=True)
        self.assertEqual(stub.kwargs, {"protocol_check": True, "smoke_scan": False})
        self.assertEqual(result["product"], "Patch Command")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["host_modified"])
        self.assertEqual(result["verification"], fake)

    def test_refuses_install_or_service_activation(self):
        for key in ("production_installed", "systemd_started"):
            with self.subTest(key=key):
                fake = {"status": "passed", "production_installed": False, "systemd_started": False}
                fake[key] = True
                class Selftest:
                    def run(self, **kwargs):
                        return fake
                with patch.object(evaluate, "load", return_value=Selftest()):
                    with self.assertRaises(RuntimeError):
                        evaluate.evaluate()

    def test_refuses_failed_verification(self):
        class Selftest:
            def run(self, **kwargs):
                return {"status": "failed", "production_installed": False, "systemd_started": False}
        with patch.object(evaluate, "load", return_value=Selftest()):
            with self.assertRaises(RuntimeError):
                evaluate.evaluate()

    def test_command_line_rejects_install_argument(self):
        with self.assertRaises(SystemExit) as caught:
            evaluate.main(["--install"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
