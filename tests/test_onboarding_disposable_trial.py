import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = (
    Path(__file__).resolve().parents[1]
    / "installer/onboarding-disposable-trial.py"
)

spec = importlib.util.spec_from_file_location(
    "onboarding_disposable_trial_test", PATH
)
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)


class FakeOnboarding:
    def __init__(self, ready=True):
        self.ready = ready

    def build_onboarding(self, **kwargs):
        return {
            "readiness": {
                "ready_for_isolated_test": self.ready,
                "ready_for_production": False,
            }
        }


class FakeTrial:
    calls = 0

    def trial(self, **kwargs):
        self.calls += 1
        return {
            "status": "passed",
            "staging": "verified",
            "temporary_workspace_cleaned": True,
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
            "external_network_requests_made": False,
        }


class DisposableCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.args = {
            "server": "https://patch.example.test",
            "ca_cert": "/tmp/test-ca.pem",
            "package": "/tmp/agent.tar.gz",
        }

    def test_confirmation_required(self):
        result = coordinator.execute(**self.args)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["execution"]["performed"])

    def test_missing_package_blocked(self):
        result = coordinator.execute(
            **{**self.args, "package": None},
            confirmation=coordinator.CONFIRMATION,
        )
        self.assertEqual(result["status"], "blocked")

    def test_missing_ca_blocked(self):
        result = coordinator.execute(
            **{**self.args, "ca_cert": None},
            confirmation=coordinator.CONFIRMATION,
        )
        self.assertEqual(result["status"], "blocked")

    def test_readiness_failure_prevents_trial(self):
        with patch.object(
            coordinator, "load",
            return_value=FakeOnboarding(ready=False),
        ) as loader:
            result = coordinator.execute(
                **self.args,
                confirmation=coordinator.CONFIRMATION,
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(loader.call_count, 1)

    def test_success(self):
        trial = FakeTrial()

        def modules(filename, name):
            if filename == "onboard.py":
                return FakeOnboarding()
            if filename == "disposable-install-trial.py":
                return trial
            raise AssertionError(filename)

        with patch.object(coordinator, "load", side_effect=modules):
            result = coordinator.execute(
                **self.args,
                confirmation=coordinator.CONFIRMATION,
            )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(trial.calls, 1)
        self.assertTrue(result["execution"]["temporary_workspace_cleaned"])
        self.assertFalse(result["execution"]["production_installed"])

    def test_unsafe_trial_evidence_rejected(self):
        class UnsafeTrial:
            def trial(self, **kwargs):
                return {
                    "status": "passed",
                    "staging": "verified",
                    "temporary_workspace_cleaned": False,
                    "production_installed": False,
                    "systemd_started": False,
                    "agent_enrolled": False,
                }

        def modules(filename, name):
            return (
                FakeOnboarding()
                if filename == "onboard.py"
                else UnsafeTrial()
            )

        with patch.object(coordinator, "load", side_effect=modules):
            with self.assertRaises(RuntimeError):
                coordinator.execute(
                    **self.args,
                    confirmation=coordinator.CONFIRMATION,
                )

    def test_cli_without_confirmation_refused(self):
        result = coordinator.main([
            "--server", "https://patch.example.test",
            "--ca-cert", "/tmp/test-ca.pem",
            "--package", "/tmp/agent.tar.gz",
        ])
        self.assertEqual(result, 1)

    def test_no_root_argument_supported(self):
        self.assertNotIn(
            "--root",
            coordinator.__doc__ or "",
        )


if __name__ == "__main__":
    unittest.main()
