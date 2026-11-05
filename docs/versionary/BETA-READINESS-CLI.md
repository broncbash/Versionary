# Versionary Beta Readiness CLI

## Purpose

`installer/versionary-beta-readiness.py` produces a
machine-readable, read-only readiness report.

It checks distribution integrity, CA validity, HTTPS
configuration, destination conflicts, existing content,
and isolated fresh-install state.

It does not install software, start services, enroll
agents, or approve production deployment.

## Isolated-root example

```bash
.venv/bin/python installer/versionary-beta-readiness.py \
  --root /path/to/existing/isolated-root \
  --distribution installer/dist/versionary-agent-distribution-26l.tar.gz \
  --server https://versionary.example.test \
  --ca-cert /path/to/ca.crt
```

The root must already exist.

## Explicit system audit

`--root / --audit-system` permits read-only inspection
of the current machine.

It never enables real-system installation.

Do not run a system audit against a live homelab
container or beta VM without approval.

## Exit codes

- 0: readiness checks passed for review
- 1: one or more readiness blockers
- 2: invalid invocation or unsafe root

Passing checks means ready for human review, not
authorized for installation.

## Known limitations

Read-only checks cannot prevent later filesystem
changes or guarantee atomic installation.

The real-system installer remains disabled.

The isolated installer is multi-stage and is not
globally atomic.

A disposable VM snapshot and explicit target-specific
approval are required before a real-system trial.

## Next steps

Finish installation implementation and rollback
design in offline development.

Validate against a new disposable VM only after
explicit authorization.
