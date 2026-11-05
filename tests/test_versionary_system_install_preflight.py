"""Integration tests for system-install authorization and preflight."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-install.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_install_preflight_tests",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemInstallPreflightTests(unittest.TestCase):

    def test_invalid_authorization_never_loads_preflight(self):
        with patch.object(module, "load_preflight") as loader:
            with self.assertRaises(ValueError):
                module.install(
                    "incorrect",
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )

        loader.assert_not_called()

    def test_missing_inputs_rejected(self):
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
            patch.object(module, "load_preflight") as loader,
        ):
            with self.assertRaises(ValueError):
                module.install(
                    module.AUTHORIZATION,
                    "/",
                )

        loader.assert_not_called()

    def test_valid_inputs_reach_preflight(self):
        calls = []

        class FakePreflight:
            @staticmethod
            def preflight(distribution, server, ca_cert):
                calls.append((distribution, server, ca_cert))

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
            patch.object(module, "load_content") as content,
        ):
            content.return_value.expected_payloads.return_value = {}
            with self.assertRaises(
                module.InstallationNotImplemented
            ):
                module.install(
                    module.AUTHORIZATION,
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )

        self.assertEqual(
            calls,
            [(
                "distribution",
                "https://example.test",
                "ca",
            )],
        )

    def test_preflight_failure_stops_installation(self):
        class FailingPreflight:
            @staticmethod
            def preflight(*args):
                raise ValueError("Preflight rejected payload")

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
                return_value=FailingPreflight,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Preflight rejected payload",
            ):
                module.install(
                    module.AUTHORIZATION,
                    "/",
                    "distribution",
                    "https://example.test",
                    "ca",
                )


if __name__ == "__main__":
    unittest.main()
