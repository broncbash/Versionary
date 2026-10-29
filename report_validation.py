import json

from pydantic import ValidationError

from arby_scanners.models import PackageUpdate


MAX_PACKAGES = 5000
MAX_REPORT_BYTES = 2 * 1024 * 1024


def validate_packages(packages: list) -> list[dict] | None:
    """Validate and normalize package update data."""

    if not isinstance(packages, list):
        return None

    if len(packages) > MAX_PACKAGES:
        return None

    try:
        validated = [
            PackageUpdate.model_validate(package).model_dump(
                mode="json"
            )
            for package in packages
        ]

        payload = json.dumps(
            validated,
            allow_nan=False,
        )

        if len(payload.encode("utf-8")) > MAX_REPORT_BYTES:
            return None

        return validated

    except (ValidationError, TypeError, ValueError):
        return None
