"""Loopback-only real TLS beta protocol test; never touches homelab services."""
import importlib.util
import os
import socket
import ssl
import urllib.request
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import uvicorn
from cryptography import x509
from fastapi import FastAPI

import agent_registry
from agent.enrollment_client import register_v2, complete_v2
from agent.enrollment_http import post_json, EnrollmentHTTPError
from agent.credentials import load_credential
from enrollment_v2_api import router as enrollment_router


class BetaTLSJourney(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        cert_path = Path(__file__).resolve().parents[1] / "installer/generate-certificates.py"
        spec = importlib.util.spec_from_file_location("beta_cert_gen", cert_path)
        cert_gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cert_gen)
        self.certs = self.root / "certs"
        cert_gen.generate("127.0.0.1", self.certs)
        ca = x509.load_pem_x509_certificate((self.certs / "ca.crt").read_bytes())
        leaf = x509.load_pem_x509_certificate((self.certs / "server.crt").read_bytes())
        ca_ski = ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
        ca_aki = ca.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
        leaf_aki = leaf.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
        self.assertEqual(ca_aki.key_identifier, ca_ski.digest)
        self.assertEqual(leaf_aki.key_identifier, ca_ski.digest)
        self.state = self.root / "agent-state"
        self.state.mkdir(mode=0o700)
        self.db = self.root / "agents.db"
        db_patch = patch.object(agent_registry, "DB_PATH", self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        env_patch = patch.dict(os.environ, {
            "ARBY_ENROLLMENT_V2_ENABLED": "true",
            "NO_PROXY": "localhost,127.0.0.1",
            "no_proxy": "localhost,127.0.0.1",
        })
        env_patch.start()
        self.addCleanup(env_patch.stop)
        agent_registry.initialize_database()
        app = FastAPI()
        app.include_router(enrollment_router)
        # Socket is bound to loopback by the OS before starting the server.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)
        self.port = sock.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(
            app, log_level="error", lifespan="off",
            ssl_certfile=str(self.certs / "server.crt"),
            ssl_keyfile=str(self.certs / "server.key"),
        ))
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [sock]}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        for _ in range(150):
            if self.server.started:
                break
            if not self.thread.is_alive():
                self.fail("Loopback TLS server exited unexpectedly")
            time.sleep(0.02)
        self.assertTrue(self.server.started)
        self.server_url = f"https://127.0.0.1:{self.port}"
        self.identity = {"agent_id": str(uuid4()), "hostname": "beta-loopback",
                         "platform": "arch"}

    def stop_server(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)

    def assert_tls_ready(self):
        context = ssl.create_default_context(cafile=str(self.certs / "ca.crt"))
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as raw:
            with context.wrap_socket(raw, server_hostname="127.0.0.1") as conn:
                self.assertEqual(conn.version()[:3], "TLS")

    def post(self, path, payload):
        return post_json(path, payload, server=self.server_url,
                         ca_cert=self.certs / "ca.crt")

    def test_real_tls_register_approve_and_complete(self):
        self.assert_tls_ready()
        registered = register_v2(self.identity, key_path=self.state / "key.json",
                                 post=self.post)
        self.assertEqual(registered["status"], "pending")
        self.assertTrue(agent_registry.approve_agent(self.identity["agent_id"]))
        result = complete_v2(
            self.identity, key_path=self.state / "key.json",
            journal_path=self.state / "journal.json",
            credential_path=self.state / "credential.json", post=self.post)
        self.assertEqual(result["status"], "enrolled")
        token = load_credential(self.state / "credential.json")
        self.assertTrue(agent_registry.authenticate_agent(self.identity["agent_id"], token))

    def test_untrusted_ca_is_rejected_before_registration(self):
        other = self.root / "other"
        cert_path = Path(__file__).resolve().parents[1] / "installer/generate-certificates.py"
        spec = importlib.util.spec_from_file_location("other_beta_cert_gen", cert_path)
        cert_gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cert_gen)
        cert_gen.generate("127.0.0.1", other)
        with self.assertRaises(EnrollmentHTTPError):
            post_json("/api/v2/agents/register", {}, server=self.server_url,
                      ca_cert=other / "ca.crt")
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM agents").fetchone()[0], 0)

    def test_disabled_enrollment_rejects_verified_https(self):
        self.assert_tls_ready()
        with patch.dict(os.environ, {"ARBY_ENROLLMENT_V2_ENABLED": "false"}):
            with self.assertRaisesRegex(EnrollmentHTTPError, "disabled"):
                register_v2(self.identity, key_path=self.state / "key.json",
                            post=self.post)


if __name__ == "__main__":
    unittest.main()
