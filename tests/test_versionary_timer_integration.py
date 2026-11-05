"""Timer preview tests: no systemd state, no real scans."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import versionary_timer_integration as timer


class TimerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        (self.root / '.venv/bin').mkdir(parents=True)
        (self.root / '.venv/bin/python').write_text('test executable')
        (self.root / 'versionary_background.py').write_text('test runner')
        self.out = Path(self.tmp.name) / 'preview'

    def test_service_invokes_locking_background_runner(self):
        service = timer.units(self.root)[timer.SERVICE]
        self.assertIn('versionary_background.py', service)
        self.assertNotIn('versionary_local_beta.py', service)
        self.assertIn('NoNewPrivileges=yes', service)
        self.assertIn('UMask=0077', service)

    def test_timer_uses_six_hour_user_session_cadence(self):
        content = timer.units(self.root)[timer.TIMER]
        self.assertIn('OnStartupSec=10min', content)
        self.assertIn('OnUnitInactiveSec=6h', content)
        self.assertIn('Persistent=false', content)
        self.assertNotIn('OnBootSec=', content)

    def test_preview_is_private_and_inert(self):
        path = timer.write_preview(self.root, self.out)
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        for name in (timer.SERVICE, timer.TIMER):
            self.assertEqual((path / name).stat().st_mode & 0o777, 0o600)
        source = Path(timer.__file__).read_text()
        self.assertNotIn('systemctl ', source)
        self.assertNotIn('pacman -Syu', source)

    def test_existing_preview_never_overwritten(self):
        timer.write_preview(self.root, self.out)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            timer.write_preview(self.root, self.out)

    def test_symlink_preview_rejected(self):
        target = Path(self.tmp.name) / 'elsewhere'
        target.mkdir()
        self.out.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            timer.write_preview(self.root, self.out)

    def test_unsafe_paths_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported character'):
            timer.units(self.root / 'bad%path')

    def test_validator_reports_failure_not_success(self):
        class Result:
            returncode = 1
            stderr = 'invalid unit'
            stdout = ''
        with patch.object(timer.subprocess, 'run', return_value=Result()):
            self.assertEqual(timer.verify_preview(self.out)[0], 'failed')

    def test_validator_handles_missing_binary(self):
        with patch.object(timer.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertEqual(timer.verify_preview(self.out)[0], 'unavailable')


if __name__ == '__main__':
    unittest.main()
