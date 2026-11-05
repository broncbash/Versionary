import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from versionary_archive_audit import audit, check_name, main


class ArchiveAuditTests(unittest.TestCase):
    def test_normal_path(self):
        self.assertIsNone(check_name('versionary/README.md'))

    def test_traversal(self):
        self.assertIsNotNone(check_name('../outside'))

    def test_absolute(self):
        self.assertIsNotNone(check_name('/etc/passwd'))

    def test_private_directory(self):
        self.assertIsNotNone(check_name('app/.versionary-local-beta/admin-token'))

    def test_credential_suffix(self):
        self.assertIsNotNone(check_name('app/private.key'))

    def test_safe_tar(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'ok.tar.gz'
            with tarfile.open(p, 'w:gz') as t:
                data = b'hello'
                info = tarfile.TarInfo('app/README.md')
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
            self.assertEqual(audit(p)['status'], 'passed')
            self.assertEqual(main([str(p), '--json']), 0)

    def test_tar_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'link.tar'
            with tarfile.open(p, 'w') as t:
                info = tarfile.TarInfo('app/linked')
                info.type = tarfile.SYMTYPE
                info.linkname = '/etc/passwd'
                t.addfile(info)
            self.assertEqual(audit(p)['status'], 'failed')

    def test_zip_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'duplicate.zip'
            import warnings
            with zipfile.ZipFile(p, 'w') as z, warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('a.txt', 'first')
                z.writestr('a.txt', 'second')
            self.assertEqual(audit(p)['status'], 'failed')

    def test_zip_safe(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'safe.zip'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('app/README.md', 'ok')
            self.assertEqual(audit(p)['status'], 'passed')

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.zip'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('../../escape', 'bad')
            self.assertEqual(audit(p)['status'], 'failed')

    def test_missing_archive_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main([str(Path(d) / 'missing.zip')]), 1)


if __name__ == '__main__':
    unittest.main()
