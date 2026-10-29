# Patch Command — Beta Evaluation

The beta evaluation workflow verifies packaging, filesystem staging, integrity,
and optionally the real enrollment/reporting protocol over disposable loopback
HTTPS. It does **not** install the agent on the host, modify production services,
enable systemd units, or enroll a live machine.

## Local evaluation

From a development checkout with the Python virtual environment installed:

```bash
.venv/bin/python installer/beta-evaluate.py --protocol-check
```

The JSON result includes `production_ready: false` by design. Passing this
check means the isolated candidate is working, **not** that production
deployment has been authorized or completed.

The standard regression checkpoint remains:

```bash
bash installer/local-check.sh --protocol-check
```

## Installation prerequisites and current limits

- The agent supports Arch Linux and Debian with Python 3.11+, systemd, an
  appropriate read-only package scanner, and a trusted HTTPS server CA.
- The candidate package must pass archive validation.
- `installer/agent-preflight.py` and `installer/deployment-readiness.py`
  provide read-only checks of target prerequisites.
- Production installation remains deliberately disabled. Do not bypass that
  restriction or enable enrollment/reporting on a live server to test a beta.
- Live deployment requires a separate implementation review, explicit target
  approval, a rollback plan, and a scoped acceptance test.

Existing filesystem paths and service identifiers retain their legacy names
for compatibility until a separate migration is designed.
