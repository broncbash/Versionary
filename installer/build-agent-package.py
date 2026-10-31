#!/usr/bin/env python3
"""Build a deterministic agent distribution from tracked source modules.

This script never installs, starts or registers an agent. The generated archive
is intentionally ignored by Git and validated before use.
"""
import argparse
import io
import tarfile
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("agent_package_validator", ROOT / "installer/validate-package.py")
validator = module_from_spec(spec)
spec.loader.exec_module(validator)


def build(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz", compresslevel=9) as archive:
        for name in sorted(validator.EXPECTED):
            source = ROOT / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Required agent source missing or unsafe: {name}")
            data = source.read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    validator.validate(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "installer/dist/versionary-agent.tar.gz")
    args = parser.parse_args()
    print(f"[OK] Built and validated {build(args.output)}")


if __name__ == "__main__":
    main()
