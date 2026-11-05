#!/usr/bin/env python3
"""Download and authenticate a Versionary agent release without installing it.

The trusted Ed25519 public key must be obtained independently of the
distribution server. This preview never extracts, executes, or installs
downloaded content.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import ssl
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_PACKAGE = 100 * 1024 * 1024
MAX_MANIFEST = 1024 * 1024
MAX_SIGNATURE = 16 * 1024


class DownloadError(Exception):
    pass


def load_tool(filename, name):
    path = ROOT / "installer" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DownloadError("Required verifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_origin(origin):
    parsed = urllib.parse.urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.hostname.endswith(".")
    ):
        raise DownloadError("Expected a bare HTTPS server origin")
    try:
        port = parsed.port
    except ValueError as exc:
        raise DownloadError("Invalid HTTPS port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise DownloadError("Invalid HTTPS port")
    return origin.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DownloadError("HTTP redirects are not permitted")


def fetch(origin, endpoint, destination, limit, context):
    url = origin + endpoint
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        NoRedirect(),
        urllib.request.ProxyHandler({}),
    )
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream"},
    )
    with opener.open(request, timeout=20) as response:
        if response.status != 200:
            raise DownloadError("Unexpected HTTP response")
        with destination.open("xb") as stream:
            total = 0
            while True:
                chunk = response.read(min(65536, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise DownloadError("Download exceeds size limit")
                stream.write(chunk)
    if total == 0:
        raise DownloadError("Empty download")


def verify_files(manifest_path, signature_path, package_path, trusted_public):
    signing = load_tool("release-signing.py", "versionary_download_signing")
    provenance = load_tool(
        "verify-release-provenance.py", "versionary_download_manifest"
    )
    validator = load_tool(
        "validate-package.py", "versionary_download_validator"
    )

    signing.verify(manifest_path, signature_path, trusted_public)

    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DownloadError("Duplicate manifest field")
            result[key] = value
        return result

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_fields,
    )
    provenance.validate_manifest(manifest)

    digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if digest != manifest["package"]["sha256"]:
        raise DownloadError("Package checksum does not match signed manifest")

    count = validator.validate(package_path)
    if count != manifest["package"]["modules"]:
        raise DownloadError("Unexpected agent module count")

    return manifest


def preview(origin, trusted_public, ca_cert=None):
    origin = validate_origin(origin)
    trusted_public = Path(trusted_public)

    if trusted_public.is_symlink() or not trusted_public.is_file():
        raise DownloadError("Trusted public key must be a regular file")

    if ca_cert is not None:
        ca_cert = Path(ca_cert)
        if ca_cert.is_symlink() or not ca_cert.is_file():
            raise DownloadError("CA certificate must be a regular file")

    context = ssl.create_default_context(
        cafile=str(ca_cert) if ca_cert is not None else None
    )

    endpoints = {
        "manifest": "/api/v1/distribution/agent/release-manifest",
        "signature": "/api/v1/distribution/agent/release-signature",
        "package": "/api/v1/distribution/agent/package",
    }

    with tempfile.TemporaryDirectory(prefix="versionary-download-") as temp:
        base = Path(temp)
        paths = {
            "manifest": base / "release-manifest.json",
            "signature": base / "release-signature.json",
            "package": base / "versionary-agent.tar.gz",
        }
        limits = {
            "manifest": MAX_MANIFEST,
            "signature": MAX_SIGNATURE,
            "package": MAX_PACKAGE,
        }

        for name in ("manifest", "signature", "package"):
            fetch(origin, endpoints[name], paths[name], limits[name], context)

        manifest = verify_files(
            paths["manifest"],
            paths["signature"],
            paths["package"],
            trusted_public,
        )

        print("[PASS] Trusted Ed25519 signature verified")
        print("[PASS] Package checksum and module validation passed")
        print("Version:", manifest["version"])
        print("Git commit:", manifest["git_commit"])
        print("Production approved: NO")
        print("Deployable: NO")
        print("No package extracted, installed, or executed")
        print("No agent registered and no services changed")
        return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--trusted-public", required=True)
    parser.add_argument("--ca-cert")
    args = parser.parse_args(argv)

    try:
        preview(args.server, args.trusted_public, args.ca_cert)
        return 0
    except (
        DownloadError,
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        urllib.error.URLError,
        ssl.SSLError,
    ) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
