"""End-to-end acceptance of the integrated Versionary HTTPS beta."""

import importlib.util
import json
import os
import socket
import ssl
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import uvicorn

import agent_registry
import versionary_https_beta as beta

from agent.credentials import load_credential
from agent.enrollment_client import register_v2, complete_v2
from agent.enrollment_http import post_json
from agent.heartbeat import send_heartbeat, HeartbeatError
from agent.reporting import send_report, ReportingError


class HTTPSBetaJourneyTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name)
        self.state = self.root / "https-beta"
        self.state.mkdir(mode=0o700)

        self.certs = self.state / "certs"
        self.db = self.state / "agents.db"
        self.auth = self.state / "admin-token"

        self.auth.write_text("disposable-journey-admin-token\n")
        self.auth.chmod(0o600)

        cert_source = (
            Path(__file__).resolve().parents[1]
            / "installer/generate-certificates.py"
        )

        spec = importlib.util.spec_from_file_location(
            "versionary_journey_certgen", cert_source
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generator.generate("127.0.0.1", self.certs)

        patches = [
            patch.object(beta, "STATE", self.state),
            patch.object(beta, "CERTS", self.certs),
            patch.object(beta, "DB", self.db),
            patch.object(beta, "AUTH", self.auth),
            patch.object(agent_registry, "DB_PATH", self.db),
            patch.dict(
                os.environ,
                {
                    "VERSIONARY_BETA_ENROLLMENT": "true",
                    "VERSIONARY_BETA_REPORTING": "true",
                    "NO_PROXY": "localhost,127.0.0.1",
                    "no_proxy": "localhost,127.0.0.1",
                },
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        app = beta.create_app()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)

        self.port = sock.getsockname()[1]

        self.server = uvicorn.Server(
            uvicorn.Config(
                app,
                log_level="error",
                lifespan="off",
                ssl_certfile=str(self.certs / "server.crt"),
                ssl_keyfile=str(self.certs / "server.key"),
            )
        )

        self.thread = threading.Thread(
            target=self.server.run,
            kwargs={"sockets": [sock]},
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

        for _ in range(150):
            if self.server.started:
                break

            if not self.thread.is_alive():
                self.fail("Disposable HTTPS server exited unexpectedly")

            time.sleep(0.02)

        self.assertTrue(self.server.started)

        self.server_url = f"https://127.0.0.1:{self.port}"
        self.ca = self.certs / "ca.crt"

        self.identity = {
            "agent_id": str(uuid4()),
            "hostname": "versionary-journey-test",
            "platform": "arch",
        }

        self.agent_state = self.root / "agent-state"
        self.agent_state.mkdir(mode=0o700)

        self.key = self.agent_state / "key.json"
        self.journal = self.agent_state / "journal.json"
        self.credential = self.agent_state / "credential.json"

    def stop_server(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)

    def request(self, path, method="GET", payload=None, admin=False):
        headers = {}

        if admin:
            headers["Authorization"] = (
                "Bearer disposable-journey-admin-token"
            )

        data = None

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self.server_url + path,
            data=data,
            headers=headers,
            method=method,
        )

        context = ssl.create_default_context(cafile=str(self.ca))

        try:
            with urllib.request.urlopen(
                request, context=context, timeout=5
            ) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            finally:
                exc.close()

    def enroll_post(self, path, payload):
        return post_json(
            path,
            payload,
            server=self.server_url,
            ca_cert=self.ca,
        )

    def test_complete_agent_lifecycle_over_https(self):
        """Register, approve, enroll, report, inspect and revoke."""

        # Registration requires explicit opt-in and verified TLS.
        registered = register_v2(
            self.identity,
            key_path=self.key,
            post=self.enroll_post,
        )

        self.assertEqual(registered["status"], "pending")

        agent_id = self.identity["agent_id"]
        approval = f"/api/v1/admin/agents/{agent_id}/approve"

        # An unauthenticated caller cannot approve the agent.
        status, _ = self.request(approval, method="POST")
        self.assertEqual(status, 401)

        # Administrator approval uses the real HTTPS API.
        status, result = self.request(
            approval,
            method="POST",
            admin=True,
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "approved")

        # Ed25519 challenge-response enrollment.
        enrolled = complete_v2(
            self.identity,
            key_path=self.key,
            journal_path=self.journal,
            credential_path=self.credential,
            post=self.enroll_post,
        )

        self.assertEqual(enrolled["status"], "enrolled")

        token = load_credential(self.credential)

        connection = {
            "server": self.server_url,
            "ca_cert": self.ca,
        }

        # Authenticated heartbeat.
        heartbeat = send_heartbeat(
            self.identity,
            token,
            **connection,
        )

        self.assertEqual(heartbeat["status"], "ok")

        # Submit a synthetic update report.
        report = {
            "status": "success",
            "packages": [
                {
                    "name": "versionary-test-package",
                    "installed": "1.0",
                    "available": "1.1",
                    "repository": "core",
                }
            ],
            "error": None,
        }

        recorded = send_report(
            self.identity,
            token,
            report,
            **connection,
        )

        self.assertEqual(recorded["status"], "recorded")

        # Verify administrator inventory sees the agent.
        status, inventory = self.request(
            "/api/v1/admin/agents",
            admin=True,
        )

        self.assertEqual(status, 200)

        agents = inventory["agents"]

        matching = [
            item for item in agents
            if item["id"] == agent_id
        ]

        self.assertEqual(len(matching), 1)
        self.assertEqual(inventory["count"], 1)
        self.assertEqual(matching[0]["hostname"], "versionary-journey-test")
        self.assertEqual(matching[0]["status"], "approved")
        self.assertEqual(matching[0]["updates"], 1)
        self.assertEqual(matching[0]["scan_status"], "success")

        # Verify that the report reached isolated storage.
        import sqlite3
        from contextlib import closing

        with closing(sqlite3.connect(self.db)) as db:
            row = db.execute(
                """
                SELECT count, packages_json
                FROM scan_reports
                WHERE agent_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (agent_id,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)
        self.assertEqual(
            json.loads(row[1])[0]["name"],
            "versionary-test-package",
        )

        # Revoke through the authenticated HTTPS API.
        revocation = f"/api/v1/admin/agents/{agent_id}/revoke"

        status, result = self.request(
            revocation,
            method="POST",
            admin=True,
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "revoked")

        # Previously issued credentials must stop working.
        with self.assertRaisesRegex(
            HeartbeatError, "authentication rejected"
        ):
            send_heartbeat(
                self.identity,
                token,
                **connection,
            )

        with self.assertRaisesRegex(
            ReportingError, "authentication rejected"
        ):
            send_report(
                self.identity,
                token,
                report,
                **connection,
            )


if __name__ == "__main__":
    unittest.main()
