import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'versionary_release.py'
spec = importlib.util.spec_from_file_location('versionary_release', SOURCE)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        for name in release.REQUIRED:
            (self.root / name).write_text('pass\n')

    def test_preflight(self):
        self.assertTrue(all(c['ok'] for c in release.preflight(self.root)))

    def test_missing_required_fails(self):
        (self.root / release.REQUIRED[0]).unlink()
        self.assertEqual(release.main(['--root', str(self.root), '--json']), 1)

    def test_excludes_runtime_and_secrets(self):
        private = self.root / '.versionary-local-beta'
        private.mkdir()
        (private / 'admin-token').write_text('TOPSECRET')
        (self.root / '.env').write_text('TOPSECRET')
        (self.root / 'notes.md').write_text('safe')
        names = [p.name for p in release.collect(self.root)]
        self.assertIn('notes.md', names)
        self.assertNotIn('admin-token', names)
        self.assertNotIn('.env', names)

    def test_excludes_symlink(self):
        outside = Path(self.temp.name) / 'outside.py'
        outside.write_text('private')
        (self.root / 'link.py').symlink_to(outside)
        self.assertNotIn('link.py', [p.name for p in release.collect(self.root)])

    def test_rejects_output_inside_repo(self):
        with self.assertRaises(SystemExit):
            release.main(['--root', str(self.root), '--output', str(self.root / 'release.tar.gz')])

    def test_archive_and_no_overwrite(self):
        out = Path(self.temp.name) / 'release.tar.gz'
        self.assertEqual(release.main(['--root', str(self.root), '--output', str(out)]), 0)
        self.assertTrue(out.is_file())
        with self.assertRaises(SystemExit):
            release.main(['--root', str(self.root), '--output', str(out)])

    def test_manifest_hash(self):
        m = release.manifest(self.root, release.collect(self.root))
        self.assertFalse(m['deployable'])
        self.assertEqual(len(m['files']), len(release.REQUIRED))

if __name__ == '__main__':
    unittest.main()
