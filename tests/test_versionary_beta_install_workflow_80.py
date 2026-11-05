"""Batch 80: beta installation workflow safety tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-beta-install-workflow.py"

spec = importlib.util.spec_from_file_location(
    "versionary_beta_workflow_80", SOURCE
)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class BetaWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(
            prefix="versionary-beta80-"
        )
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_rejects_real_root(self):
        with self.assertRaises(ValueError):
            workflow.validate_root("/")

    def test_rejects_relative_root(self):
        with self.assertRaises(ValueError):
            workflow.validate_root("relative")

    def test_rejects_symlink_root(self):
        link = self.root.parent / (self.root.name + "-link")
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            workflow.validate_root(link)

    def test_rejects_missing_authorization(self):
        with self.assertRaises(PermissionError):
            workflow.execute(
                self.root, "bundle", "server", "ca", None
            )

    def test_rejects_wrong_authorization(self):
        with self.assertRaises(PermissionError):
            workflow.execute(
                self.root, "bundle", "server", "ca", "yes"
            )

    def test_preview_never_installs(self):
        with patch.object(workflow, "load") as loader:
            loader.return_value.preflight.return_value = {}
            loader.return_value.inspect.return_value = {}
            result = workflow.prepare(
                self.root, "bundle", "server", "ca"
            )
        self.assertFalse(result["installation_performed"])
        self.assertFalse(result["real_system_installation_enabled"])

    def test_execute_requires_fresh_gate(self):
        with patch.object(
            workflow, "prepare",
            side_effect=RuntimeError("existing installation"),
        ):
            with self.assertRaises(RuntimeError):
                workflow.execute(
                    self.root, "bundle", "server", "ca",
                    workflow.AUTHORIZATION,
                )

    def test_execute_uses_isolated_installer(self):
        with (
            patch.object(
                workflow, "prepare",
                return_value={"status": "ready"},
            ),
            patch.object(workflow, "load") as loader,
        ):
            loader.return_value.run.return_value = {
                "status": "isolated"
            }
            result = workflow.execute(
                self.root, "bundle", "server", "ca",
                workflow.AUTHORIZATION,
            )

        self.assertEqual(
            result["installation_result"]["status"],
            "isolated",
        )
        self.assertFalse(result["production_approved"])

    def test_no_service_activation(self):
        with patch.object(workflow, "load") as loader:
            loader.return_value.preflight.return_value = {}
            loader.return_value.inspect.return_value = {}
            result = workflow.prepare(
                self.root, "bundle", "server", "ca"
            )
        self.assertFalse(result["services_activated"])
        self.assertFalse(result["enrollment_performed"])


if __name__ == "__main__":
    unittest.main()
