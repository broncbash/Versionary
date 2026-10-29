from arby_scanners.models import PackageUpdate, ScanResult


def parse_pacman_updates(
    output: str,
    node: str,
    returncode: int = 0,
    stderr: str = "",
) -> ScanResult:
    """Parse read-only checkupdates output."""

    if returncode not in (0, 2):
        return ScanResult(
            node=node,
            status="error",
            count=None,
            error=stderr.strip() or
                  f"checkupdates exited with code {returncode}",
        )

    packages = []

    if returncode == 0:
        for line in output.splitlines():
            parts = line.split()

            if len(parts) == 4 and parts[2] == "->":
                packages.append(
                    PackageUpdate(
                        name=parts[0],
                        installed=parts[1],
                        available=parts[3],
                    )
                )

    return ScanResult(
        node=node,
        status="success",
        count=len(packages),
        packages=packages,
    )
