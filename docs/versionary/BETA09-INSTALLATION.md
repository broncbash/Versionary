# Versionary Beta 0.9 — Distribution and Installation

**Status:** development acceptance only. Production deployment is not approved.

## Build and validate the agent distribution

From the repository checkout:

```bash
.venv/bin/python installer/build-agent-package.py --output /tmp/versionary-agent-beta09.tar.gz
.venv/bin/python installer/validate-package.py /tmp/versionary-agent-beta09.tar.gz
```

The archive contains 13 agent Python modules. It does not bundle Python,
cryptography, operating-system dependencies, or a standalone installer.

## Install into a disposable root only

```bash
ROOT=$(mktemp -d /tmp/versionary-install.XXXXXX)
.venv/bin/python installer/install-files.py /tmp/versionary-agent-beta09.tar.gz --root "$ROOT"
```

This creates `$ROOT/opt/versionary-agent`, a content-addressed active release,
and `$ROOT/var/lib/versionary-agent` with private permissions. It does **not**
enroll the agent, contact a server, install systemd units, or enable scheduling.

## Acceptance tests

```bash
.venv/bin/python -m unittest tests.test_beta09_distribution_acceptance -v
```

These tests use disposable directories and cover deterministic packaging,
archive validation, isolated installation, state preservation, rejection of
corrupt archives, and offline agent CLI startup.

## Configuration and enrollment

The separate `installer/versionary-agent-setup.py` creates unprivileged
configuration. See `USER-GUIDE.md`. Enrollment requires trusted HTTPS and
explicit administrator approval. Packaging never enrolls automatically.

## Limitations

- No production deployment authorization or automatic patching/reboot
- No automatic service or timer activation
- No completed production upgrade/uninstall lifecycle
- No immutable-runtime guarantee
- SHA-256 release identity is not publisher authentication
- Offline acceptance does not prove production deployment safety

Release-candidate acceptance remains a separate decision.
