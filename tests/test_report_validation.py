import unittest

from report_validation import (
    MAX_PACKAGES,
    MAX_REPORT_BYTES,
    validate_packages,
)


class TestReportValidation(unittest.TestCase):

    def setUp(self):
        self.package = {
            "name": "linux",
            "installed": "6.11",
            "available": "6.12",
            "repository": "core",
        }

    def test_valid_package(self):
        self.assertEqual(
            validate_packages([self.package]),
            [self.package],
        )

    def test_empty_update_list(self):
        self.assertEqual(validate_packages([]), [])

    def test_missing_required_fields(self):
        self.assertIsNone(
            validate_packages([{"name": "linux"}])
        )

    def test_empty_package_name(self):
        package = {**self.package, "name": ""}
        self.assertIsNone(validate_packages([package]))

    def test_oversized_package_name(self):
        package = {**self.package, "name": "x" * 257}
        self.assertIsNone(validate_packages([package]))

    def test_too_many_packages(self):
        self.assertIsNone(
            validate_packages(
                [self.package] * (MAX_PACKAGES + 1)
            )
        )

    def test_invalid_package_type(self):
        self.assertIsNone(
            validate_packages(["not-a-package"])
        )

    def test_invalid_report_type(self):
        self.assertIsNone(
            validate_packages({"packages": []})
        )

    def test_oversized_serialized_report(self):
        package = {
            "name": "x" * 256,
            "installed": "1" * 128,
            "available": "2" * 128,
            "repository": "r" * 256,
        }

        self.assertIsNone(
            validate_packages([package] * MAX_PACKAGES)
        )


if __name__ == "__main__":
    unittest.main()
