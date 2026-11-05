"""Failure-injection and cleanup tests for disposable workflows."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


trial = load(
    "disposable-install-trial.py",
    "recovery_matrix_trial",
)

transaction = load(
    "disposable-filesystem-transaction.py",
    "recovery_matrix_transaction",
)


class DisposableRecoveryTests(unittest.TestCase):

    def run_injected(self, fail_phase):
        observed = []
        calls = []

        original_tempdir = tempfile.TemporaryDirectory

        def tracked_tempdir(*args, **kwargs):
            context = original_tempdir(*args, **kwargs)

            class Tracked:
                def __enter__(self):
                    path = Path(context.__enter__())
                    observed.append(path)
                    return str(path)

                def __exit__(self, *exc):
                    return context.__exit__(*exc)

            return Tracked()

        class InjectedStage:
            def stage(self, *, root, verify_only=False, **kwargs):
                calls.append("verify" if verify_only else "stage")

                root = Path(root)
                self_test_file = root / "injected-test-asset"
                self_test_file.write_text("disposable-only")

                if fail_phase == "stage" and not verify_only:
                    raise RuntimeError("Injected staging failure")

                if fail_phase == "verify" and verify_only:
                    raise RuntimeError("Injected verification failure")

                if verify_only:
                    return {
                        "status": "verified",
                        "changes_made": False,
                    }

                return {"status": "staged"}

        with (
            patch.object(trial, "load", return_value=InjectedStage()),
            patch.object(
                trial.tempfile,
                "TemporaryDirectory",
                side_effect=tracked_tempdir,
            ),
        ):
            if fail_phase is None:
                result = trial.trial(
                    server="https://patch.example.test",
                    ca_cert="/unused/test-ca.pem",
                    package="/unused/agent.tar.gz",
                )
                self.assertEqual(result["status"], "passed")
                self.assertTrue(result["temporary_workspace_cleaned"])
            else:
                with self.assertRaisesRegex(
                    RuntimeError, "Injected"
                ):
                    trial.trial(
                        server="https://patch.example.test",
                        ca_cert="/unused/test-ca.pem",
                        package="/unused/agent.tar.gz",
                    )

        self.assertEqual(len(observed), 1)
        self.assertFalse(
            observed[0].exists(),
            "Temporary workspace survived trial completion",
        )

        return calls

    def test_success_cleans_workspace(self):
        self.assertEqual(
            self.run_injected(None),
            ["stage", "verify"],
        )

    def test_staging_failure_cleans_workspace(self):
        self.assertEqual(
            self.run_injected("stage"),
            ["stage"],
        )

    def test_verification_failure_cleans_workspace(self):
        self.assertEqual(
            self.run_injected("verify"),
            ["stage", "verify"],
        )


class TransactionRecoveryMatrixTests(unittest.TestCase):

    def test_every_failure_checkpoint_recovers(self):
        for checkpoint in transaction.STAGES:
            with self.subTest(checkpoint=checkpoint):
                result = transaction.run(
                    fail_after=checkpoint
                )

                self.assertEqual(
                    result["status"], "recovered"
                )
                self.assertEqual(
                    result["journal_states"][-1],
                    "recovered",
                )
                self.assertFalse(
                    result["temporary_artifacts_retained"]
                )
                self.assertFalse(
                    result["production_installed"]
                )
                self.assertFalse(
                    result["systemd_started"]
                )
                self.assertFalse(
                    result["agent_enrolled"]
                )

    def test_successful_transaction(self):
        result = transaction.run()

        self.assertEqual(result["status"], "verified")
        self.assertEqual(
            result["journal_states"][-1],
            "verified",
        )
        self.assertFalse(
            result["temporary_artifacts_retained"]
        )

    def test_unknown_checkpoint_rejected(self):
        with self.assertRaises(ValueError):
            transaction.run(
                fail_after="production"
            )


if __name__ == "__main__":
    unittest.main()
