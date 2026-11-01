# Versionary Beta 0.9 — Isolated End-to-End Acceptance

**Scope:** development-only in-process FastAPI TestClient with a disposable SQLite database. No network sockets, operating-system installation, service activation, or homelab changes.

Run: `.venv/bin/python -m unittest tests.test_beta09_end_to_end_acceptance -v`

Acceptance covers actual server registration, manual administrator approval, credential issuance through the existing registry API, authenticated heartbeat and empty success report, authenticated inventory, read-only dashboard response, reporting disable gate, and permanent revocation.

**Not covered:** a separately installed agent process talking to a TLS server, certificate trust or SAN validation over the wire, installer UX, systemd timer, enrollment v2 cryptographic exchange, full nonempty package scanning, production rollout, upgrade/uninstall. These remain beta acceptance gaps; this batch does not assert production readiness.

Credentials and SQLite state are disposable; no secrets are committed. The tests use existing legacy agent API feature switches only inside the test process. Runtime deployment remains disabled.
