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

## Persistent isolated beta staging (new)

The `installer/stage-beta.py` command creates an **inert installation**
inside an already-existing, administrator-selected test directory. It is
not a production installer and does not enable services, contact the
server, or enroll agents. The directory is retained after staging.

Example (only in a disposable test environment, with an explicit CA):

```sh
python3 installer/build-agent-package.py
mkdir -m 700 /tmp/arby-beta-root
python3 installer/stage-beta.py \
  --root /tmp/arby-beta-root \
  --server https://patch.example.test \
  --ca-cert /path/to/trusted-ca.crt
```

The command rejects `/`, missing roots, symlinked roots, and unsafe
ownership/permissions. It validates the package, HTTPS origin, and CA
certificate before staging, then performs a read-only installation audit.

**Important limitation:** staging is not an atomic transaction across all
files. If a later step fails, the test root may contain partial changes;
do not reuse a failed root as if it were a verified deployment. This is
an offline staging milestone, not a production deployment authorization.

## Integration validation checkpoint

The beta staging regression suite now includes a real package-to-filesystem
integration test. In a disposable root, it generates a test-only CA, stages
the validated distribution, verifies the agent release, config, CA and
systemd unit files, then stages the same package again and checks that all
those bytes and the active release target are unchanged.

This test does **not** start systemd, enroll an agent, or validate live
server communication. The complete end-to-end enrollment and reporting
trial remains a separate, explicitly approved beta milestone. CI runs
only at deliberate checkpoints to minimize GitHub Actions usage.

## Recheck a staged beta without modifying it

After staging, run the same command with `--verify-only`. This validates
the package and supplied CA, runs the read-only installation integrity audit,
and compares the persisted server configuration and installed CA against the
explicit inputs. It returns `status: verified` and `changes_made: false` on
success; any drift fails closed rather than repairing or replacing files.

```sh
python3 installer/stage-beta.py --verify-only \
  --root /tmp/arby-beta-root \
  --server https://patch.example.test \
  --ca-cert /path/to/trusted-ca.crt
```

This is still offline verification, not a live TLS connection or enrollment.

## Opt-in local smoke scan

After verifying the staged beta, `--verify-only --smoke-scan` executes
`python -B -m agent scan` from the staged release. This queries the **host's**
local package manager in read-only mode; it does not enroll, send reports,
start systemd, or contact PATCH COMMAND. The scan is explicitly optional
because it invokes the host's package-query command, unlike a pure
filesystem integrity check.

```sh
python3 installer/stage-beta.py --verify-only --smoke-scan \
  --root /tmp/arby-beta-root \
  --server https://patch.example.test \
  --ca-cert /path/to/trusted-ca.crt
```

The JSON output includes `scan_status`; a scan error fails the command.
This does **not** establish end-to-end server communication or authorize
production deployment. The test container must provide the appropriate
`checkupdates` or `apt` package scanner.
