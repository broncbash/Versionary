#!/usr/bin/env python3
"""Verify Versionary release authenticity and reproducibility.

This tool requires:
  1. A manifest signed by an explicitly trusted Ed25519 public key.
  2. A package reproducible from the manifest's exact Git commit.

A successful result does not authorize production deployment.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TrustedReleaseError(Exception):
    pass


def load_tool(name, module_name):
    path = ROOT / "installer" / name
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise TrustedReleaseError(f"Cannot load {name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(manifest, signature, trusted_public, package):
    signing = load_tool(
        "release-signing.py",
        "versionary_trusted_release_signing",
    )

    provenance = load_tool(
        "verify-release-provenance.py",
        "versionary_trusted_release_provenance",
    )

    try:
        identity = signing.verify(
            manifest,
            signature,
            trusted_public,
        )
    except Exception as exc:
        raise TrustedReleaseError(
            f"Release authentication failed: {exc}"
        ) from exc

    print("[OK] Trusted Ed25519 release signature verified")
    print(f"[OK] Trusted key identity: {identity}")

    try:
        provenance.verify(manifest, package)
    except Exception as exc:
        raise TrustedReleaseError(
            f"Release provenance failed: {exc}"
        ) from exc

    print("[PASS] Versionary trusted release verified")
    print("[INFO] Production deployment remains disabled")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--signature", required=True, type=Path)
    parser.add_argument("--trusted-public", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)

    args = parser.parse_args(argv)

    try:
        verify(
            args.manifest,
            args.signature,
            args.trusted_public,
            args.package,
        )
        return 0

    except (TrustedReleaseError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
