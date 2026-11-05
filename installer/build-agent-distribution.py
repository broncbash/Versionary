#!/usr/bin/env python3
"""Build and verify a portable Versionary agent distribution.

Development artifact only. Does not install, enroll, or start services.
"""
import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_ARCHIVE = ROOT / "installer/dist/versionary-agent.tar.gz"
CLI = ROOT / "versionary_agent_cli.py"
DEFAULT_OUTPUT = ROOT / "installer/dist/versionary-agent-distribution.tar.gz"

FILES = {
    "versionary-agent.tar.gz": AGENT_ARCHIVE,
    "versionary_agent_cli.py": CLI,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_agent_archive(path):
    import importlib.util

    source = ROOT / "installer/validate-package.py"
    spec = importlib.util.spec_from_file_location(
        "versionary_distribution_validator", source
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(path)


def add_file(archive, name, data):
    entry = tarfile.TarInfo(name)
    entry.size = len(data)
    entry.mode = 0o644
    entry.uid = entry.gid = 0
    entry.uname = entry.gname = ""
    entry.mtime = 0
    archive.addfile(entry, io.BytesIO(data))


def build(output):
    output = Path(output).absolute()

    if output.is_symlink():
        raise ValueError("Output must not be a symlink")

    if output in (p.absolute() for p in FILES.values()):
        raise ValueError("Output would overwrite source")

    validate_agent_archive(AGENT_ARCHIVE)

    payload = {}
    for name, path in FILES.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or unsafe source: {name}")
        payload[name] = path.read_bytes()

    metadata = {
        "product": "Versionary Agent",
        "distribution": "isolated-beta",
        "production_approved": False,
        "files": {
            name: {
                "sha256": digest(data),
                "size": len(data),
            }
            for name, data in sorted(payload.items())
        },
    }

    payload["manifest.json"] = (
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    ).encode()

    output.parent.mkdir(parents=True, exist_ok=True)

    created = False
    try:
        with output.open("xb") as raw:
            created = True
            with gzip.GzipFile(
                filename="",
                fileobj=raw,
                mode="wb",
                mtime=0,
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed,
                    mode="w",
                ) as archive:
                    for name, data in sorted(payload.items()):
                        add_file(archive, name, data)

        verify(output)
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise

    return output


def verify(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid distribution file")

    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        expected = set(FILES) | {"manifest.json"}
        names = [member.name for member in members]

        if set(names) != expected or len(names) != len(expected):
            raise ValueError("Unexpected distribution contents")

        payload = {}
        for member in members:
            if not member.isfile() or member.size > 4 * 1024 * 1024:
                raise ValueError("Unsafe distribution member")

            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable distribution member")

            payload[member.name] = stream.read()

    metadata = json.loads(payload["manifest.json"])

    if metadata.get("production_approved") is not False:
        raise ValueError("Production approval must remain false")

    if set(metadata.get("files", {})) != set(FILES):
        raise ValueError("Invalid distribution manifest")

    for name in FILES:
        actual = payload[name]
        expected = metadata["files"][name]

        if expected["sha256"] != digest(actual):
            raise ValueError(f"Checksum mismatch: {name}")

        if expected["size"] != len(actual):
            raise ValueError(f"Size mismatch: {name}")

    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()

    if args.verify:
        metadata = verify(args.verify)
        print("[OK] Distribution integrity verified")
        print("Production approved:", metadata["production_approved"])
        return

    output = args.output or DEFAULT_OUTPUT

    if output.exists() or output.is_symlink():
        raise SystemExit(
            f"Output already exists; refusing overwrite: {output}"
        )

    result = build(output)
    print("[OK] Agent distribution built:", result)
    print("[OK] Administrative CLI included")
    print("[OK] Existing agent archive preserved")
    print("[OK] Production deployment remains disabled")


if __name__ == "__main__":
    main()
