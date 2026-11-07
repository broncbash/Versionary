## Published beta.2 — 2026-11-06 (authoritative release checkpoint)

**Published prerelease:** https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.2. Tag `v0.1.0-beta.2`, source commit `ae16714` on `main`, after documentation PR #15 was merged (`798648f`). The release is **published and downloadable**, but **fresh disposable-VM installation acceptance remains pending**; production deployment is **not approved**.

Four uploaded GitHub release assets: `versionary-v0.1.0-beta.2.tar.gz`, `versionary-v0.1.0-beta.2-manifest.json`, `versionary-v0.1.0-beta.2-agent.tar.gz`, and `SHA256SUMS`. The final server archive contains **159 files**, with SHA256 `3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b`. Archive/manifest verification and all three checksum entries passed. The local disposable-VM helper `installer/versionary-disposable-vm-install.py` was deliberately excluded from the shipped archive without deleting its untracked local copy. Release GitHub asset metadata confirms the server archive checksum and four uploaded assets.

Local regression checkpoint before packaging: **1,700 tests OK (1 skipped)**. Both root installer scripts on `main` now target `TAG=v0.1.0-beta.2` and pin the final SHA256. The server script accepts `--address`, `--port`, `--beta-fleet`, `--no-beta-fleet`, and `--yes`; the agent script accepts `--server`, `--ca-cert`, `--ca-fingerprint`, `--install-deps`, and `--enable-timer`. Use `--help` for current usage; inspect scripts before running.

**Next session:** fetch/pull remote `main` without disturbing local untracked files, then test the published root wrappers on **fresh disposable Arch server and Arch/Debian agent VMs**, independently verify the server CA fingerprint, approve agents via dashboard, and check HTTPS health, heartbeats, update reports, and optional observer-only timers. Do not deploy to Proxmox CT 102/104 or production hosts. Automatic patch installation and reboots remain disabled. The older beta.1 instructions and dated beta.2 publication-planning paragraphs in this repository are historical; this checkpoint overrides publication status and the old 160-file/old-checksum candidate.

---

# Versionary — Agent User Guide

## Current user guide — controlled GitHub beta v0.1.0-beta.1 (2026-11-05)

Download from https://github.com/broncbash/arby-patch-command/releases/tag/v0.1.0-beta.1 (currently **private**, so GitHub access is required). Assets: `versionary-v0.1.0-beta.1.tar.gz`, `versionary-v0.1.0-beta.1-manifest.json`, `versionary-v0.1.0-beta.1-agent.tar.gz`, `SHA256SUMS`.

1. Download all assets to the same directory and verify with `sha256sum -c SHA256SUMS`.
2. Use an **approved disposable VM**, not a production server. Extract the main archive; review `installer/versionary-server-install.py --help`; first run server installer with `--mode dry-run`, the main archive and manifest, and intended TLS identity/bind/port.
3. Only after explicit approval, install the isolated HTTPS server. Keep its private `/var/lib/versionary` state, certificates and admin token secure. Dashboard is `https://SERVER:8766/admin/dashboard`. Do not expose beta to public internet.
4. Obtain **the server's CA certificate** securely (normally `/var/lib/versionary/certs/ca.crt`); it is not bundled in release. Verify its fingerprint through a trusted channel.
5. On a disposable agent VM, from the extracted release directory run `sudo bash installer/versionary-agent-guided-install.sh --distribution /path/to/versionary-v0.1.0-beta.1-agent.tar.gz --ca-cert /path/to/ca.crt --server https://SERVER:8766`. Add `--install-deps` only if you authorize system dependency installation; `--enable-timer` only if you want daily observer-only reporting.
6. Approve the pending agent in the dashboard. Guided installer waits for approval, enrolls, heartbeats and sends first scan report. It does **not** install package updates.
7. Inspect installed agent with `sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system status`; manually report with `--system report`.
8. Keep reporting timer disabled unless explicitly opted in. No unattended updates or automatic reboots are included.
9. See `COMMAND-REFERENCE.md` for exact implemented server/agent switches, defaults, and planned-but-not-implemented options.

**Known limitations:** controlled beta, private repository, no production approval, limited real-VM guided installer acceptance (Arch), more clean-install and recovery testing needed. The installer waiting-message patch was not separately VM re-tested. Do not interpret a successful beta test as production readiness.

---

## Historical engineering documentation (preserved)

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

## Batch 73 — Controlled beta acceptance

Controlled beta installation is not yet approved. The acceptance requirements and known limitations are tracked in BETA-ACCEPTANCE-PLAN.md.

---

## Beta.2 guided installer notes (pending publication)

The beta.2 candidate has passed 1,700 local tests (one skipped) and 160-file archive verification; fresh-VM acceptance and publication are still pending. When released, download and inspect the root `install-versionary.sh` (server) or `install-versionary-agent.sh` (agent) from `main`, and use **fresh disposable VMs only**. The agent wrapper supports `--server`, `--ca-cert`, `--ca-fingerprint`, `--install-deps`, `--enable-timer`; confirm current `--help` output. Never accept an unverified CA fingerprint from the same untrusted server connection. Enrollment requires administrator approval; timers remain opt-in; Versionary does not install patches or reboot hosts. Package-manager dependency installation, especially `pacman -Syu` on Arch, can upgrade VM packages. See [beta.2 release notes](RELEASE-NOTES-v0.1.0-beta.2.md).
