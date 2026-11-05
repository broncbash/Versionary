"""Tests for the standalone VERSIONARY AGENT scanner."""

import subprocess
import unittest
from unittest.mock import patch

from agent.versionary_agent import (
    detect_platform,
    scan,
    scan_arch,
    scan_debian,
)


def command_result(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestPatchAgent(unittest.TestCase):

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/checkupdates")
    @patch("agent.versionary_agent.run_command")
    def test_arch_updates(self, run, _which):
        run.return_value = command_result(
            "linux 6.11 -> 6.12\n"
            "vim 9.0 -> 9.1\n"
        )

        packages = scan_arch()

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0]["name"], "linux")
        self.assertEqual(packages[0]["available"], "6.12")

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/checkupdates")
    @patch("agent.versionary_agent.run_command")
    def test_arch_no_updates(self, run, _which):
        run.return_value = command_result(returncode=2)
        self.assertEqual(scan_arch(), [])

    @patch("agent.versionary_agent.shutil.which",
           return_value=None)
    def test_arch_missing_checkupdates(self, _which):
        with self.assertRaises(RuntimeError):
            scan_arch()

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/checkupdates")
    @patch("agent.versionary_agent.run_command")
    def test_arch_unexpected_output(self, run, _which):
        run.return_value = command_result("invalid output")

        with self.assertRaises(RuntimeError):
            scan_arch()

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/apt")
    @patch("agent.versionary_agent.run_command")
    def test_debian_updates(self, run, _which):
        run.return_value = command_result(
            "Listing...\n"
            "curl/stable 8.0 amd64 "
            "[upgradable from: 7.0]\n"
        )

        packages = scan_debian()

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["name"], "curl")
        self.assertEqual(packages[0]["repository"], "stable")

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/apt")
    @patch("agent.versionary_agent.run_command")
    def test_debian_no_updates(self, run, _which):
        run.return_value = command_result("Listing...\n")
        self.assertEqual(scan_debian(), [])

    @patch("agent.versionary_agent.shutil.which",
           return_value="/usr/bin/apt")
    @patch("agent.versionary_agent.run_command")
    def test_debian_unexpected_output(self, run, _which):
        run.return_value = command_result("unexpected")

        with self.assertRaises(RuntimeError):
            scan_debian()

    @patch("agent.versionary_agent.detect_platform",
           return_value="arch")
    @patch("agent.versionary_agent.scan_arch")
    def test_successful_scan(self, arch, _platform):
        arch.return_value = [{
            "name": "linux",
            "installed": "6.11",
            "available": "6.12",
        }]

        report = scan()

        self.assertEqual(report["status"], "success")
        self.assertEqual(len(report["packages"]), 1)
        self.assertIsNone(report["error"])

    @patch("agent.versionary_agent.detect_platform",
           return_value="arch")
    @patch("agent.versionary_agent.scan_arch")
    def test_failed_scan(self, arch, _platform):
        arch.side_effect = RuntimeError("scanner failed")

        report = scan()

        self.assertEqual(report["status"], "error")
        self.assertEqual(report["packages"], [])
        self.assertEqual(report["error"], "scanner failed")

    def test_platform_detection(self):
        self.assertIn(detect_platform(), ("arch", "debian"))


if __name__ == "__main__":
    unittest.main()
