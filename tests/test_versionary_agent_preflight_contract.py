"""Contract tests for Versionary's non-installing system preflight."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-preflight.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_preflight_contract",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemPreflightContractTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.root = Path(self.temporary.name)
        self.distribution = self.root / "agent.tar.gz"
        self.ca = self.root / "ca.crt"

        self.distribution.write_bytes(b"test distribution")
        self.ca.write_bytes(b"test certificate")

        self.distribution.chmod(0o600)
        self.ca.chmod(0o600)

    def test_rejects_invalid_server_before_ca_validation(self):
        calls = []

        class FakeCLI:
            @staticmethod
            def verified_cli(path):
                calls.append("distribution")

        class FakeConfig:
            @staticmethod
            def validate_server(server):
                calls.append("server")
                raise ValueError("Invalid server URL")

        class FakeCA:
            @staticmethod
            def validate_ca(data):
                calls.append("ca")

        helpers = {
            "install-agent-cli.py": FakeCLI,
            "../agent/config.py": FakeConfig,
            "install-ca.py": FakeCA,
        }

        with (
            patch.object(
                module,
                "validate_platform",
                return_value="test",
            ),
            patch.object(
                module,
                "load_helper",
                side_effect=lambda name, alias: helpers[name],
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "Invalid server URL"
            ):
                module.preflight(
                    self.distribution,
                    "http://insecure.example",
                    self.ca,
                )

        self.assertEqual(
            calls,
            ["distribution", "server"],
        )

    def test_valid_inputs_reach_all_validators(self):
        calls = []

        class FakeCLI:
            @staticmethod
            def verified_cli(path):
                calls.append("distribution")

        class FakeConfig:
            @staticmethod
            def validate_server(server):
                calls.append("server")

        class FakeCA:
            @staticmethod
            def validate_ca(data):
                calls.append("ca")

        helpers = {
            "install-agent-cli.py": FakeCLI,
            "../agent/config.py": FakeConfig,
            "install-ca.py": FakeCA,
        }

        with (
            patch.object(
                module,
                "validate_platform",
                return_value="test",
            ),
            patch.object(
                module,
                "load_helper",
                side_effect=lambda name, alias: helpers[name],
            ),
        ):
            result = module.preflight(
                self.distribution,
                "https://example.test",
                self.ca,
            )

        self.assertEqual(
            calls,
            ["distribution", "server", "ca"],
        )
        self.assertIs(result["production_approved"], False)

    def test_rejects_unsafe_distribution_before_loading_helpers(self):
        self.distribution.chmod(0o666)

        with patch.object(module, "load_helper") as loader:
            with self.assertRaises(ValueError):
                module.preflight(
                    self.distribution,
                    "https://example.test",
                    self.ca,
                )

        loader.assert_not_called()

    def test_rejects_symlinked_ca_before_loading_helpers(self):
        link = self.root / "linked-ca.crt"
        link.symlink_to(self.ca)

        with patch.object(module, "load_helper") as loader:
            with self.assertRaises(ValueError):
                module.preflight(
                    self.distribution,
                    "https://example.test",
                    link,
                )

        loader.assert_not_called()

    def test_no_privileged_installation_calls(self):
        source = SOURCE.read_text()

        forbidden = (
            "os.chown(",
            "os.chmod(",
            "systemctl",
            "install_release(",
            "install_units(",
            "install_config(",
            "install_ca(",
            "subprocess.run(",
            "subprocess.call(",
        )

        for expression in forbidden:
            with self.subTest(expression=expression):
                self.assertNotIn(expression, source)


if __name__ == "__main__":
    unittest.main()
