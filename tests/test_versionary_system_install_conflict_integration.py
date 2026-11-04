"""Verify the system coordinator enforces destination inspection."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-install.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_conflict_integration",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoordinatorConflictIntegrationTests(unittest.TestCase):

    def execute(self, conflict_error=None):
        calls = []

        class FakePreflight:
            @staticmethod
            def preflight(*args):
                calls.append("preflight")
                return {"production_approved": False}

        class FakeConflicts:
            @staticmethod
            def inspect(root):
                calls.append("conflicts")
                if conflict_error is not None:
                    raise conflict_error
                return {"directories": {}, "files": {}}

        with (
            patch.object(
                module.platform,
                "system",
                return_value="Linux",
            ),
            patch.object(
                module.os,
                "geteuid",
                return_value=0,
            ),
            patch.object(
                module,
                "load_preflight",
                return_value=FakePreflight,
            ),
            patch.object(
                module,
                "load_conflicts",
                return_value=FakeConflicts,
            ),
            patch.object(module, "load_content") as content,
        ):
            content.return_value.expected_payloads.return_value = {}
            with self.assertRaises(
                type(conflict_error)
                if conflict_error is not None
                else module.InstallationNotImplemented
            ):
                module.install(
                    module.AUTHORIZATION,
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )

        return calls

    def test_validated_payload_then_destination_inspection(self):
        self.assertEqual(
            self.execute(),
            ["preflight", "conflicts"],
        )

    def test_conflicting_destination_stops_installation(self):
        self.assertEqual(
            self.execute(ValueError("Unsafe destination")),
            ["preflight", "conflicts"],
        )

    def test_invalid_authorization_skips_all_inspection(self):
        with (
            patch.object(module, "load_preflight") as preflight,
            patch.object(module, "load_conflicts") as conflicts,
        ):
            with self.assertRaises(ValueError):
                module.install(
                    "incorrect",
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )

        preflight.assert_not_called()
        conflicts.assert_not_called()


if __name__ == "__main__":
    unittest.main()
