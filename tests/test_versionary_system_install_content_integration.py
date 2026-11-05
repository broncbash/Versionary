"""System beta coordinator content-validation integration tests."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-install.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_content_integration",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContentIntegrationTests(unittest.TestCase):

    def run_coordinator(self, content_error=None):
        calls = []

        class Preflight:
            @staticmethod
            def preflight(*args):
                calls.append("preflight")
                return {"production_approved": False}

        class Conflicts:
            @staticmethod
            def inspect(*args):
                calls.append("destinations")
                return {"directories": {}, "files": {}}

        class Content:
            @staticmethod
            def expected_payloads(*args):
                calls.append("payloads")
                return {"etc/versionary-agent/config.json": b"test"}

            @staticmethod
            def inspect_existing(*args):
                calls.append("content")
                if content_error is not None:
                    raise content_error
                return {"etc/versionary-agent/config.json": "absent"}

        with (
            patch.object(module.platform, "system", return_value="Linux"),
            patch.object(module.os, "geteuid", return_value=0),
            patch.object(module, "load_preflight", return_value=Preflight),
            patch.object(module, "load_conflicts", return_value=Conflicts),
            patch.object(module, "load_content", return_value=Content),
        ):
            if content_error is None:
                expected = module.InstallationNotImplemented
            else:
                expected = type(content_error)

            with self.assertRaises(expected):
                module.install(
                    module.AUTHORIZATION,
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )

        return calls

    def test_validation_sequence(self):
        self.assertEqual(
            self.run_coordinator(),
            ["preflight", "destinations", "payloads", "content"],
        )

    def test_content_conflict_stops_coordinator(self):
        self.assertEqual(
            self.run_coordinator(ValueError("Existing file differs")),
            ["preflight", "destinations", "payloads", "content"],
        )

    def test_invalid_authorization_stops_before_loading_helpers(self):
        with (
            patch.object(module, "load_preflight") as preflight,
            patch.object(module, "load_conflicts") as conflicts,
            patch.object(module, "load_content") as content,
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
        content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
