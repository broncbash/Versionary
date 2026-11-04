# Versionary — Agent User Guide

## Current user-facing status — 2026-11-04

This section supersedes older statements about what has
or has not been packaged or tested. Historical beta
instructions below are retained for reference.

Versionary is an observer-focused Linux patch visibility
product in controlled beta development.

A unified installation kit exists, and disposable Arch and
Debian beta agents have demonstrated HTTPS reporting and
daily timers. These are controlled development milestones.

The isolated-root agent installer and upgrade engine are
prototypes. They are not approved real-system installers.
Upgrade recovery is not yet guaranteed safe against power
loss or concurrent filesystem modification.

Do not interpret historical source-checkout instructions as
a supported production installation procedure.

Automatic patch installation, unattended upgrades, and
reboots are not part of the current approved behavior.

Production installation and public release remain blocked
pending additional security and acceptance work.

---


Status: Development preview, not a production installation guide.

## What Versionary does

Versionary helps administrators see which Linux systems have
package updates available.

The current agent is observer-only. It does not install updates,
upgrade packages, or reboot machines.

## Requirements

For the current source-checkout workflow:

- Supported Linux development environment.
- Python and required project dependencies.
- Versionary source checkout.
- HTTPS Versionary server endpoint.
- Locally available trusted CA certificate.
- Administrator approval for enrollment.

The portable setup tool does not download or install dependencies.

## Preview configuration

From the repository checkout:

.venv/bin/python installer/versionary-agent-setup.py \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt \
  --dry-run

Replace the example server and CA path with real values.

Dry-run validates configuration inputs and previews paths.
It does not create the agent configuration.

## Unattended configuration

.venv/bin/python installer/versionary-agent-setup.py \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt

This creates private local configuration.

It does not register an agent or install a service.

## Interactive configuration

.venv/bin/python installer/versionary-agent-setup.py \
  --interactive

The installer prompts for missing settings.

## Check status

.venv/bin/python versionary_agent_cli.py status

Status shows the configured server, local identity state,
and whether a local credential is provisioned.

Local credential presence does not prove the server still
authorizes the agent.

## Register the agent

.venv/bin/python versionary_agent_cli.py register

Registration requests administrator approval.

It does not grant approval automatically.

## Administrator approval

An authorized administrator must review and approve the
pending agent on the Versionary server.

The exact administrative workflow remains part of the
development/beta interface and may change before release.

## Complete enrollment

After approval:

.venv/bin/python versionary_agent_cli.py enroll

This performs the enrollment protocol and provisions
the local agent credential.

## Send a heartbeat

.venv/bin/python versionary_agent_cli.py heartbeat

This contacts the configured server using the trusted CA
and the provisioned agent credential.

## Send an update report

.venv/bin/python versionary_agent_cli.py report

This scans the local system for package updates and sends
an inventory report.

It does not install those updates.

## Custom state directory

For each agent CLI operation, specify:

--state-dir /path/to/private/agent-state

The option appears before the command:

.venv/bin/python versionary_agent_cli.py \
  --state-dir /path/to/private/agent-state \
  status

For the setup script, the option can be passed alongside
other setup arguments.

## Safety and troubleshooting

If configuration already exists, setup refuses to overwrite it.

If the CA path is missing or a symlink, setup fails.

If the server URL is not a bare HTTPS origin, setup fails.

If identity or credential permissions are unsafe, the CLI
may refuse to load them.

Do not work around these protections by making credential
files world-readable.

Do not put agent tokens, private keys, or administrator
credentials into support tickets or terminal transcripts.

## Current limitations

- Source checkout required.
- No standalone package yet.
- No service or timer installer yet.
- No automatic enrollment or reporting schedule.
- No production release approval.

## Beta 0.9 localhost acceptance checkpoint — 2026-11-01

### Beta 0.9 localhost operator trial (development only)
From a configured desktop with the local trial already installed:

```bash
~/.local/bin/versionary-beta09 status
~/.local/bin/versionary-beta09 report
~/.local/bin/versionary-beta09 server
```

Open `https://localhost:8769/admin/dashboard` on the same machine. Enter the admin bearer token and choose **Refresh fleet**. The page can now restore access on reload within the same tab. Choose **Log out** to clear tab access. Closing the tab normally clears its `sessionStorage`; browser session restore behavior may vary. Avoid shared devices: the token is stored in browser-accessible tab storage, not an HttpOnly cookie. Do not mistake this trial for production authentication.

For Arch/CachyOS, update detection uses `checkupdates`, which queries refreshed package metadata without installing updates. A `pacman -Qu` count can differ. The reported count is a snapshot, not a command to install packages.

---

<!-- VERSIONARY_RC2_ACCEPTANCE_20261102 -->
## RC2 beta installation status

The RC2 installer has been tested successfully on a disposable
Arch Linux VM, including HTTPS and reboot persistence.

This is a development/beta acceptance milestone, not a declaration
of production readiness.

The installer creates a dedicated service account and protected state
directory. The generated CA certificate is stored within protected state.

See RC2-ACCEPTANCE-OPERATIONS.md for verified service and HTTPS
diagnostic commands.

Do not weaken certificate directory permissions or publish private
administrative credentials.

## Multi-distribution beta notes — 2026-11-03

Versionary's controlled HTTPS beta successfully monitored an Arch Linux
client and a Debian 13 client from one server dashboard.

The verified manual agent workflow is:
1. Configure the HTTPS server and trusted CA certificate.
2. Register the agent using register-v2.
3. Approve the pending agent in the administrator dashboard.
4. Complete enrollment using enroll-v2.
5. Run heartbeat, scan, and report.
6. Refresh the dashboard to confirm online status and scan results.

During this beta, Debian required additional Python dependencies and
system-level configuration. The portable agent installation experience
is not yet finalized. Automatic periodic reporting is still pending.

Successful beta operation does not constitute production approval.


## Agent Installer Checkpoint — Batch 26U

The consolidated offline agent installer has passed
permanent end-to-end regression testing.

Verified:
- 1,432 regression tests executed successfully (1 skipped).
- Seven permanent installer integration tests passed.
- Complete installation into an isolated filesystem.
- Idempotent reinstallation.
- Preservation of existing identity and credentials.
- Rejection of conflicting CLI and CA destinations.
- Recovery from a simulated interrupted installation.
- No automatic registration or service activation.

Current implementation:
- Verified agent distribution archive.
- Administrative CLI with system-mode support.
- Offline installation coordinator.
- Agent modules, CA, configuration, and systemd units.

Outstanding:
- Complete destination preflight.
- Publisher authenticity verification.
- Comprehensive rollback/recovery policy.
- Stable distribution artifact naming.
- Clean Arch and Debian installer validation.
- Controlled beta deployment acceptance.

Production deployment remains unauthorized.

See AGENT-INSTALLER-READINESS.md for details.


## Installation kit — controlled-beta preview

Versionary now has a unified installation kit containing
both server and agent installers.

See INSTALLATION-GUIDE.md for instructions.

Server installation has passed verified dry-run acceptance.
Agent installation has passed disposable-filesystem acceptance.

Real server installation, enrollment, and production deployment
remain separate approval-gated milestones.


## Batch 72 — Journal integrity checkpoint

Batch 72: recovery journal anomalies require investigation. Do not manually delete the journal or retry installation.
