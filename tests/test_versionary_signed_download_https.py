"""Disposable HTTPS integration tests for signed Versionary downloads.

No live installation, registration, systemd activation, or persistent keys.
The signed test manifest uses a synthetic Git identity; full Git provenance
verification is a separate release-publishing gate.
"""

import datetime
import hashlib
import importlib.util
import ipaddress
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI

from versionary_agent_distribution import router

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


download = load("download-agent-preview.py", "versionary_https_downloader")
builder = load("build-agent-package.py", "versionary_https_builder")
signing = load("release-signing.py", "versionary_https_signing")


class SignedDownloadHTTPSTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="versionary-https-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = builder.build(self.root / "versionary-agent.tar.gz")

        digest = hashlib.sha256(self.package.read_bytes()).hexdigest()
        manifest = {
            "schema_version": 1,
            "product": "Versionary",
            "component": "agent",
            "version": "0.0.0-beta.1",
            "git_commit": "a" * 40,
            "package": {
                "filename": "versionary-agent.tar.gz",
                "sha256": digest,
                "modules": 13,
            },
            "production_approved": False,
            "deployable": False,
        }
        self.manifest = self.root / "release-manifest.json"
        self.manifest.write_text(json.dumps(manifest, indent=2) + "\n")

        release_key = ed25519.Ed25519PrivateKey.generate()
        private = self.root / "release-private.pem"
        public = self.root / "release-public.pem"
        private.write_bytes(release_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        public.write_bytes(release_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        self.public = public
        signing.sign(
            self.manifest,
            private,
            self.root / "release-signature.json",
        )

        tls_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Versionary Test CA")
        ])
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(tls_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1"))
                ]),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .sign(tls_key, hashes.SHA256())
        )

        self.cert = self.root / "tls.crt"
        self.key = self.root / "tls.key"
        self.cert.write_bytes(certificate.public_bytes(
            serialization.Encoding.PEM
        ))
        self.key.write_bytes(tls_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))

        self.app = FastAPI()
        self.app.include_router(router)

        self.environment = patch.dict(os.environ, {
            "VERSIONARY_DISTRIBUTION_ENABLED": "true",
            "VERSIONARY_DISTRIBUTION_DIR": str(self.root),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]

        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=port,
            ssl_certfile=str(self.cert),
            ssl_keyfile=str(self.key),
            log_level="error",
            lifespan="off",
        )
        self.server = uvicorn.Server(config)
        self.server.install_signal_handlers = lambda: None
        self.thread = threading.Thread(
            target=self.server.run,
            kwargs={"sockets": [listener]},
            daemon=True,
        )
        self.thread.start()

        deadline = time.monotonic() + 10
        while not self.server.started and time.monotonic() < deadline:
            time.sleep(0.02)

        if not self.server.started:
            self.server.should_exit = True
            self.thread.join(timeout=5)
            listener.close()
            self.fail("Disposable HTTPS server did not start")

        self.addCleanup(self.stop_server)
        self.origin = f"https://127.0.0.1:{port}"

    def stop_server(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def test_signed_download_succeeds(self):
        manifest = download.preview(
            self.origin, self.public, self.cert
        )
        self.assertEqual(manifest["package"]["modules"], 13)
        self.assertIs(manifest["deployable"], False)

    def test_tampered_package_rejected(self):
        original = self.package.read_bytes()
        self.package.write_bytes(original + b"tampered")
        with self.assertRaises(download.DownloadError):
            download.preview(self.origin, self.public, self.cert)

    def test_wrong_trusted_key_rejected(self):
        other = ed25519.Ed25519PrivateKey.generate()
        wrong = self.root / "wrong-public.pem"
        wrong.write_bytes(other.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        with self.assertRaises(Exception):
            download.preview(self.origin, wrong, self.cert)


if __name__ == "__main__":
    unittest.main()
