#!/usr/bin/env python3
"""Verify Versionary release authenticity and reproducibility.

Trust must come from either an independently supplied public key or
an independently provisioned trust-policy file.

Successful verification never authorizes production deployment.
"""

import argparse
import importlib.util
import json
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


def signing_identity(signature_path):
    """Extract an untrusted key ID solely for policy lookup."""
    signing = load_tool(
        "release-signing.py",
        "versionary_trust_identity_signing",
    )

    raw = signing.read_regular(signature_path, signing.MAX_SIGNATURE)

    def reject_duplicates(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise TrustedReleaseError(
                    f"Duplicate signature field: {name}"
                )
            result[name] = value
        return result

    try:
        envelope = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (ValueError, UnicodeError) as exc:
        raise TrustedReleaseError("Invalid signature envelope") from exc

    if not isinstance(envelope, dict):
        raise TrustedReleaseError("Signature envelope must be an object")

    identity = envelope.get("key_id")

    if (
        not isinstance(identity, str)
        or not signing.KEY_ID_RE.fullmatch(identity)
    ):
        raise TrustedReleaseError("Invalid signature key identity")

    return identity


def verify(
    manifest,
    signature,
    trusted_public=None,
    package=None,
    trust_policy=None,
):
    if (trusted_public is None) == (trust_policy is None):
        raise TrustedReleaseError(
            "Specify exactly one trusted-public key or trust policy"
        )

    if package is None:
        raise TrustedReleaseError("Release package is required")

    signing = load_tool(
        "release-signing.py",
        "versionary_trusted_release_signing",
    )

    provenance = load_tool(
        "verify-release-provenance.py",
        "versionary_trusted_release_provenance",
    )

    if trust_policy is not None:
        policy = load_tool(
            "release-trust-policy.py",
            "versionary_trusted_release_policy",
        )

        identity = signing_identity(signature)

        try:
            trusted_key = policy.trusted_key(trust_policy, identity)
        except Exception as exc:
            raise TrustedReleaseError(
                f"Release trust policy rejected signing key: {exc}"
            ) from exc

        import tempfile
        from cryptography.hazmat.primitives import serialization

        with tempfile.TemporaryDirectory(
            prefix="versionary-trusted-key-"
        ) as temporary:
            public_path = Path(temporary) / "trusted.pem"
            public_path.write_bytes(
                trusted_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

            try:
                verified_identity = signing.verify(
                    manifest, signature, public_path
                )
            except Exception as exc:
                raise TrustedReleaseError(
                    f"Release authentication failed: {exc}"
                ) from exc

    else:
        try:
            verified_identity = signing.verify(
                manifest, signature, trusted_public
            )
        except Exception as exc:
            raise TrustedReleaseError(
                f"Release authentication failed: {exc}"
            ) from exc

    print("[OK] Trusted Ed25519 release signature verified")
    print(f"[OK] Trusted key identity: {verified_identity}")

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
    parser.add_argument("--package", required=True, type=Path)

    trust = parser.add_mutually_exclusive_group(required=True)
    trust.add_argument("--trusted-public", type=Path)
    trust.add_argument("--trust-policy", type=Path)

    args = parser.parse_args(argv)

    try:
        verify(
            manifest=args.manifest,
            signature=args.signature,
            trusted_public=args.trusted_public,
            package=args.package,
            trust_policy=args.trust_policy,
        )
        return 0

    except (TrustedReleaseError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
