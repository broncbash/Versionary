"""Offline regression tests for the installed Versionary CLI mode."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import versionary_agent_cli as cli


class AgentSystemModeTests(unittest.TestCase):

    def test_system_mode_uses_installed_state(self):
        with patch.object(cli, "SYSTEM_STATE", Path("/var/lib/versionary-agent")):
            with patch.object(cli, "read_system_config",
                              return_value=("https://example.test", Path("/tmp/ca.crt"))):
                with patch.object(cli, "load_identity", return_value=None):
                    with patch.object(cli, "load_credential",
                                      side_effect=FileNotFoundError):
                        with patch.object(cli, "state_paths",
                                          wraps=cli.state_paths) as paths:
                            with contextlib.redirect_stdout(io.StringIO()):
                                result = cli.main(["--system", "status"])

        self.assertEqual(result, 0)
        self.assertEqual(
            paths.call_args.args[0],
            "/var/lib/versionary-agent",
        )

    def test_system_mode_rejects_alternate_state(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli.main([
                    "--system",
                    "--state-dir", "/tmp/other",
                    "status",
                ])
        self.assertEqual(error.exception.code, 2)

    def test_system_mode_refuses_setup(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            result = cli.main([
                "--system",
                "setup",
                "--server", "https://example.test",
                "--ca-cert", "/tmp/ca.crt",
            ])

        self.assertEqual(result, 1)
        self.assertIn("disabled in system mode", errors.getvalue())

    def test_portable_mode_keeps_default_state(self):
        with patch.object(cli, "read_config",
                          return_value=("https://example.test", Path("/tmp/ca.crt"))):
            with patch.object(cli, "load_identity", return_value=None):
                with patch.object(cli, "load_credential",
                                  side_effect=FileNotFoundError):
                    with patch.object(cli, "state_paths",
                                      wraps=cli.state_paths) as paths:
                        with contextlib.redirect_stdout(io.StringIO()):
                            result = cli.main(["status"])

        self.assertEqual(result, 0)
        self.assertEqual(
            paths.call_args.args[0],
            str(cli.DEFAULT_STATE),
        )

    def test_system_configuration_uses_installed_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            state.mkdir(mode=0o700)
            paths = cli.state_paths(state)

            with patch.object(cli, "validate_directory"):
                with patch.object(cli, "load_config", return_value={
                    "server": "https://example.test",
                    "ca_cert": "/etc/versionary-agent/ca.crt",
                }) as config:
                    with patch.object(Path, "is_file", return_value=True):
                        result = cli.read_system_config(paths)

            self.assertEqual(result[0], "https://example.test")
            self.assertEqual(
                result[1],
                Path("/etc/versionary-agent/ca.crt"),
            )
            config.assert_called_once_with(cli.SYSTEM_CONFIG)

    def test_system_status_does_not_create_identity(self):
        with patch.object(cli, "read_system_config",
                          return_value=("https://example.test", Path("/tmp/ca.crt"))):
            with patch.object(cli, "load_identity", return_value=None):
                with patch.object(cli, "load_credential",
                                  side_effect=FileNotFoundError):
                    with patch.object(cli, "get_or_create_identity") as create:
                        with contextlib.redirect_stdout(io.StringIO()):
                            result = cli.main(["--system", "status"])

        self.assertEqual(result, 0)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
