import unittest

from arby_scanners.apt import parse_apt_updates
from arby_scanners.pacman import parse_pacman_updates


class TestPacman(unittest.TestCase):

    def test_updates(self):
        result = parse_pacman_updates(
            "linux 6.1 -> 6.2\nvim 9.0 -> 9.1",
            "TEST",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.count, 2)
        self.assertEqual(result.packages[0].name, "linux")

    def test_no_updates(self):
        result = parse_pacman_updates("", "TEST", 2)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.count, 0)

    def test_error(self):
        result = parse_pacman_updates("", "TEST", 1, "Failure")
        self.assertEqual(result.status, "error")
        self.assertIsNone(result.count)


class TestAPT(unittest.TestCase):

    def test_updates(self):
        result = parse_apt_updates(
            "Listing...\n"
            "curl/stable 8.0 amd64 [upgradable from: 7.0]\n",
            "TEST",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.count, 1)
        self.assertEqual(result.packages[0].name, "curl")
        self.assertEqual(result.packages[0].repository, "stable")

    def test_no_updates(self):
        result = parse_apt_updates("Listing...\n", "TEST")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.count, 0)

    def test_error(self):
        result = parse_apt_updates("", "TEST", 1, "Failure")
        self.assertEqual(result.status, "error")
        self.assertIsNone(result.count)


if __name__ == "__main__":
    unittest.main()
