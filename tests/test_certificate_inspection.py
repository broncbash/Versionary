import tempfile
import unittest
from pathlib import Path
from certificate_management import inspect_certificate, CertificateError
from tests.test_certificate_management import pair


class CertificateInspectionTests(unittest.TestCase):
    def inspect(self, expired=False, **kwargs):
        cert, _ = pair(expired=expired)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cert.pem'
            path.write_bytes(cert)
            return inspect_certificate(path, **kwargs)

    def test_valid_certificate(self):
        info = self.inspect(hostname='example.test')
        self.assertEqual(info['status'], 'expiring_soon')
        self.assertTrue(info['hostname_matches'])
        self.assertEqual(len(info['sha256']), 64)

    def test_expired_certificate(self):
        self.assertEqual(self.inspect(expired=True)['status'], 'expired')

    def test_hostname_mismatch(self):
        self.assertFalse(self.inspect(hostname='other.test')['hostname_matches'])

    def test_warning_threshold(self):
        self.assertEqual(self.inspect(warning_days=0)['status'], 'valid')

    def test_reject_invalid_threshold(self):
        with self.assertRaises(CertificateError):
            self.inspect(warning_days=-1)

    def test_no_hostname_does_not_assume_match(self):
        self.assertIsNone(self.inspect()['hostname_matches'])

    def test_reject_symlink(self):
        cert, _ = pair()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'cert.pem'
            target.write_bytes(cert)
            link = Path(folder) / 'link.pem'
            link.symlink_to(target)
            with self.assertRaises(CertificateError):
                inspect_certificate(link)
