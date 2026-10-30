"""Disposable tests: no real package scan, network, or systemd."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import versionary_background as bg


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'state'
        self.state.mkdir(mode=0o700)
        (self.state / 'agent.json').write_text('{"id":"fixed-id"}')
        (self.state / 'admin-token').write_text('secret')
        self.entry = Path(self.temp.name) / 'versionary_local_beta.py'
        self.entry.write_text('# test only')
        self.python = Path('/usr/bin/python3')

    def run_fake(self, result):
        fake = Mock(return_value=subprocess.CompletedProcess([], result, 'SECRET', 'SECRET'))
        output = bg.run_scan(execute=fake, state=self.state, entry=self.entry, python=self.python)
        self.assertEqual(fake.call_count, 1)
        args, kwargs = fake.call_args
        self.assertEqual(args[0], [str(self.python), str(self.entry), 'scan'])
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(kwargs['timeout'], 240)
        self.assertNotIn('SECRET', str(output))
        self.assertEqual((self.state / 'background-scan.lock').stat().st_mode & 0o777, 0o600)
        return output

    def test_success_isolated_and_secret_free(self):
        self.assertEqual(self.run_fake(0)['status'], 'success')

    def test_failure_does_not_claim_success(self):
        self.assertEqual(self.run_fake(1)['status'], 'failed')

    def test_timeout_is_reported_without_details(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], 240)
        self.assertEqual(bg.run_scan(execute=timeout, state=self.state,
                                     entry=self.entry, python=self.python)['status'], 'timeout')

    def test_missing_identity_blocks_execution(self):
        (self.state / 'agent.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Initialize'):
            bg.run_scan(execute=Mock(), state=self.state, entry=self.entry, python=self.python)

    def test_insecure_directory_blocks_execution(self):
        os.chmod(self.state, 0o755)
        with self.assertRaisesRegex(RuntimeError, 'not private'):
            bg.run_scan(execute=Mock(), state=self.state, entry=self.entry, python=self.python)

    def test_lock_contention_skips_second_scan(self):
        import fcntl
        lock = self.state / 'background-scan.lock'
        with lock.open('w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fake = Mock()
            outcome = bg.run_scan(execute=fake, state=self.state, entry=self.entry, python=self.python)
            self.assertEqual(outcome['status'], 'already-running')
            fake.assert_not_called()

    def test_source_has_no_activation_or_upgrade_commands(self):
        source = Path(bg.__file__).read_text()
        self.assertNotIn('systemctl', source)
        self.assertNotIn('pacman -Syu', source)


if __name__ == '__main__':
    unittest.main()
