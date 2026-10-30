"""Real subprocess integration tests. Fake scanners only; no real scans."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import versionary_background as background


class BackgroundIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='versionary-beta04-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)

        for name in ('agent.json', 'admin-token'):
            path = self.state / name
            path.write_text('FAKE-SECRET-DO-NOT-LOG')
            path.chmod(0o600)

        self.entry = self.root / 'fake_scan.py'

    def fake(self, code):
        self.entry.write_text(code)
        self.entry.chmod(0o600)

    def run_it(self):
        return background.run_scan(
            state=self.state,
            entry=self.entry,
            python=sys.executable,
        )

    def test_real_child_success_and_sanitized_output(self):
        self.fake("print('FAKE-SECRET-DO-NOT-LOG')\n")
        result = self.run_it()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['exit_code'], 0)
        self.assertNotIn('FAKE-SECRET', json.dumps(result))

    def test_real_child_failure_and_sanitized_stderr(self):
        self.fake(
            "import sys\n"
            "print('FAKE-SECRET-DO-NOT-LOG', file=sys.stderr)\n"
            "sys.exit(23)\n"
        )
        result = self.run_it()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['exit_code'], 23)
        self.assertNotIn('FAKE-SECRET', json.dumps(result))

    def test_noninteractive_child_has_no_stdin(self):
        self.fake(
            "import sys\n"
            "assert sys.stdin.read() == ''\n"
            "assert not sys.stdin.isatty()\n"
        )
        self.assertEqual(self.run_it()['status'], 'success')

    def test_real_lock_contention_and_recovery(self):
        import fcntl

        lock = self.state / 'background-scan.lock'
        lock.touch(mode=0o600)
        fd = os.open(lock, os.O_RDWR)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        self.fake('raise AssertionError("must not execute")\n')

        try:
            result = self.run_it()
            self.assertEqual(result['status'], 'already-running')
            self.assertFalse(result['scan_started'])
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)

        self.fake('print("lock released")\n')
        self.assertEqual(self.run_it()['status'], 'success')

    def test_lock_recovers_after_crashed_holder(self):
        lock = self.state / 'background-scan.lock'
        lock.touch(mode=0o600)

        holder = subprocess.Popen(
            [
                sys.executable,
                '-c',
                'import fcntl,os,sys; '
                'f=open(sys.argv[1],"r+"); '
                'fcntl.flock(f,fcntl.LOCK_EX); '
                'print("READY",flush=True); '
                'os._exit(17)',
                str(lock),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        self.addCleanup(
            lambda: holder.kill() if holder.poll() is None else None
        )

        output, _ = holder.communicate(timeout=5)
        self.assertEqual(output.strip(), 'READY')
        self.assertEqual(holder.returncode, 17)

        self.fake('print("recovered")\n')
        self.assertEqual(self.run_it()['status'], 'success')

    def test_state_directory_symlink_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.state, target_is_directory=True)

        with self.assertRaisesRegex(RuntimeError, 'state'):
            background.run_scan(
                state=alias,
                entry=self.entry,
                python=sys.executable,
            )

    def test_lock_symlink_rejected(self):
        (self.state / 'background-scan.lock').symlink_to(
            self.state / 'agent.json'
        )

        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            self.run_it()

    def test_insecure_state_permissions_rejected(self):
        self.state.chmod(0o755)

        with self.assertRaisesRegex(RuntimeError, 'private'):
            self.run_it()

    def test_missing_identity_rejected(self):
        (self.state / 'agent.json').unlink()

        with self.assertRaisesRegex(RuntimeError, 'Initialize'):
            self.run_it()

    def test_lock_file_permissions_are_private(self):
        self.fake('pass\n')
        self.assertEqual(self.run_it()['status'], 'success')
        self.assertEqual(
            (self.state / 'background-scan.lock').stat().st_mode & 0o777,
            0o600,
        )

    def test_launch_error_is_sanitized(self):
        self.fake('pass\n')

        result = background.run_scan(
            state=self.state,
            entry=self.entry,
            python=self.root / 'missing-python',
        )

        self.assertEqual(result['status'], 'launch-error')
        self.assertFalse(result['scan_started'])

    def test_timeout_is_sanitized_without_waiting(self):
        self.fake('pass\n')

        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(
                cmd=['FAKE-SECRET'],
                timeout=240,
                output=b'FAKE-SECRET',
            )

        result = background.run_scan(
            execute=timeout,
            state=self.state,
            entry=self.entry,
            python=sys.executable,
        )

        self.assertEqual(result['status'], 'timeout')
        self.assertNotIn('FAKE-SECRET', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
