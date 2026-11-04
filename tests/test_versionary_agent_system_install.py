"""Tests for Versionary's system installation authorization boundary."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-install.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_install",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemInstallAuthorizationTests(unittest.TestCase):

    def test_rejects_missing_authorization(self):
        with self.assertRaises(ValueError):
            module.validate_authorization(
                "",
                "/",
                effective_uid=0,
            )

    def test_rejects_incorrect_authorization(self):
        with self.assertRaises(ValueError):
            module.validate_authorization(
                "yes",
                "/",
                effective_uid=0,
            )

    def test_rejects_nonroot(self):
        with self.assertRaises(PermissionError):
            module.validate_authorization(
                module.AUTHORIZATION,
                "/",
                effective_uid=1000,
            )

    def test_rejects_relative_root(self):
        with self.assertRaises(ValueError):
            module.validate_authorization(
                module.AUTHORIZATION,
                ".",
                effective_uid=0,
            )

    def test_rejects_alternate_root(self):
        with self.assertRaises(ValueError):
            module.validate_authorization(
                module.AUTHORIZATION,
                "/tmp/versionary",
                effective_uid=0,
            )

    def test_accepts_exact_authorization_contract(self):
        with patch.object(
            module.platform,
            "system",
            return_value="Linux",
        ):
            result = module.validate_authorization(
                module.AUTHORIZATION,
                "/",
                effective_uid=0,
            )

        self.assertEqual(result, Path("/"))

    def test_installation_still_disabled(self):
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
        ):
            with self.assertRaises(
                module.InstallationNotImplemented
            ):
                with (
                    patch.object(module, "load_preflight") as loader,
                    patch.object(module, "load_content") as content,
                ):
                    content.return_value.expected_payloads.return_value = {}
                    loader.return_value.preflight.return_value = {
                        "production_approved": False,
                    }
                    module.install(
                        module.AUTHORIZATION,
                        "/",
                        "distribution",
                        "https://example.test",
                        "ca",
                    )
                    loader.assert_called_once()

    def test_rejects_non_linux(self):
        with patch.object(
            module.platform,
            "system",
            return_value="Windows",
        ):
            with self.assertRaises(ValueError):
                module.validate_authorization(
                    module.AUTHORIZATION,
                    "/",
                    effective_uid=0,
                )


if __name__ == "__main__":
    unittest.main()
