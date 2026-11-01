# Versionary Beta 0.9 — CLI to HTTPS Acceptance

**Scope:** disposable, loopback-only integration; not production approval.

Run `python -m unittest tests.test_beta09_cli_https_acceptance -v` from the repository.

The acceptance suite uses a generated temporary CA and TLS leaf, a loopback-only
Uvicorn server, a temporary SQLite registry, and a separate Python process
running the actual `versionary_agent_cli.py` executable. It exercises setup,
registration, administrator approval, enrollment, authenticated heartbeat,
synthetic update report over verified HTTPS, authenticated admin inventory,
dashboard HTML, and revocation. It also checks missing CA rejection.

The suite deliberately **does not** scan installed packages, modify host services,
install or activate systemd units, enroll any real device, or reach external
network destinations. The test uses the existing beta TLS fixture for its
server, which mounts the enrollment and reporting routers; the admin inventory
and dashboard are exercised via an in-process TestClient sharing the isolated
registry. This is **not** a full deployed server/process-to-browser test.

Remaining release work includes a supported installer/service lifecycle,
operator-facing certificate workflow, complete user acceptance, and explicit
release approval. All production deployment gates remain closed.
