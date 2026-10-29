# Deployment beta gate

The portable agent's **production installer is still disabled**. This
checkpoint command reports prerequisites without installing, enrolling,
starting systemd units, modifying certificates, or contacting the server.

Run from the repository checkout after building the agent package:

```sh
python3 installer/build-agent-package.py
python3 installer/deployment-readiness.py \
  --server https://patch.example.test \
  --ca-cert /path/to/trusted-ca.crt
```

The JSON report distinguishes `ready_for_isolated_test` from
`ready_for_production`. Production readiness is **always false** until
a reviewed deployment workflow and approved end-to-end enrollment test
exist. Exit code 0 means only that the read-only prerequisites for an
isolated test are met; it is **not** permission to deploy.

## First controlled beta acceptance criteria

1. A disposable fresh Arch or Debian test container passes preflight.
2. The isolated installation and repeat-installation integrity audit pass.
3. A separate approved beta installer safely installs without touching CT104.
4. A test agent enrolls with explicit approval and trusted TLS.
5. Agent scan results appear on the server dashboard, with failure states.
6. No unattended upgrades, automatic reboots, or unapproved enrollment.
7. Reinstall and failed-install recovery preserve state, CA, and config.

## Cost policy

Feature-branch and draft PR pushes do not trigger hosted CI. Group work into
large development batches and schedule full Python 3.13/3.14 CI at intentional
integration checkpoints. Account billing caps must be configured by the owner.
