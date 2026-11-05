# Disposable installation trial

Run after building the agent package:

```bash
.venv/bin/python installer/disposable-install-trial.py \
  --server https://example.test --ca-cert /path/to/trusted-ca.crt
```

This creates a new temporary private directory, stages an agent candidate, audits it using the existing read-only verification path, and deletes the temporary workspace whether staging succeeds or raises an error. The CA file must be a valid certificate; the server origin must be HTTPS. No external server is contacted.

**Rollback scope is only the temporary test workspace.** This is **not** production rollback and cannot undo changes to a live host. It does not start systemd, enroll agents, install to `/`, or enable the production installer. A successful trial is not permission to deploy.

The project still needs reviewed production transactions, backup and restore procedures, service lifecycle handling, and explicit authorization before any live rollout.
