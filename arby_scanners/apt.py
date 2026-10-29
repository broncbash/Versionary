import re

from arby_scanners.models import PackageUpdate, ScanResult


APT_PATTERN = re.compile(
    r"^([^/\s]+)/(\S+)\s+(\S+)\s+\S+\s+"
    r"\[upgradable from: (.+)\]$"
)


def parse_apt_updates(
    output: str,
    node: str,
    returncode: int = 0,
    stderr: str = "",
) -> ScanResult:
    """Parse read-only apt list --upgradable output."""

    if returncode != 0:
        return ScanResult(
            node=node,
            status="error",
            count=None,
            error=stderr.strip()
            or f"APT scanner exited with code {returncode}",
        )

    packages = []

    for line in output.splitlines():
        match = APT_PATTERN.match(line.strip())

        if match:
            name, repository, available, installed = match.groups()

            packages.append(
                PackageUpdate(
                    name=name,
                    installed=installed,
                    available=available,
                    repository=repository,
                )
            )

    return ScanResult(
        node=node,
        status="success",
        count=len(packages),
        packages=packages,
    )
