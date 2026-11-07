## Published beta.2 — 2026-11-06 (authoritative release checkpoint)

**Published prerelease:** https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.2. Tag `v0.1.0-beta.2`, source commit `ae16714` on `main`, after documentation PR #15 was merged (`798648f`). The release is **published and downloadable**, but **fresh disposable-VM installation acceptance remains pending**; production deployment is **not approved**.

Four uploaded GitHub release assets: `versionary-v0.1.0-beta.2.tar.gz`, `versionary-v0.1.0-beta.2-manifest.json`, `versionary-v0.1.0-beta.2-agent.tar.gz`, and `SHA256SUMS`. The final server archive contains **159 files**, with SHA256 `3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b`. Archive/manifest verification and all three checksum entries passed. The local disposable-VM helper `installer/versionary-disposable-vm-install.py` was deliberately excluded from the shipped archive without deleting its untracked local copy. Release GitHub asset metadata confirms the server archive checksum and four uploaded assets.

Local regression checkpoint before packaging: **1,700 tests OK (1 skipped)**. Both root installer scripts on `main` now target `TAG=v0.1.0-beta.2` and pin the final SHA256. The server script accepts `--address`, `--port`, `--beta-fleet`, `--no-beta-fleet`, and `--yes`; the agent script accepts `--server`, `--ca-cert`, `--ca-fingerprint`, `--install-deps`, and `--enable-timer`. Use `--help` for current usage; inspect scripts before running.

**Next session:** fetch/pull remote `main` without disturbing local untracked files, then test the published root wrappers on **fresh disposable Arch server and Arch/Debian agent VMs**, independently verify the server CA fingerprint, approve agents via dashboard, and check HTTPS health, heartbeats, update reports, and optional observer-only timers. Do not deploy to Proxmox CT 102/104 or production hosts. Automatic patch installation and reboots remain disabled. The older beta.1 instructions and dated beta.2 publication-planning paragraphs in this repository are historical; this checkpoint overrides publication status and the old 160-file/old-checksum candidate.

---

# Versionary — Command Reference

## Authoritative CLI reference — released v0.1.0-beta.1 (2026-11-05)

The commands below were checked against source on the `v0.1.0-beta.1` tag. **Do not assume planned switches are implemented.** Run `--help` from the checked-out release for detailed diagnostics. Server/agent installation is for disposable beta systems only.

### Guided agent installer — `installer/versionary-agent-guided-install.sh`
```bash
sudo bash installer/versionary-agent-guided-install.sh \
  --distribution /absolute/path/versionary-v0.1.0-beta.1-agent.tar.gz \
  --ca-cert /absolute/path/ca.crt \
  --server https://SERVER_HOST:8766 \
  [--install-deps] [--enable-timer]
```
- `--distribution PATH` (required, unless prompted): verified offline agent tarball.
- `--ca-cert PATH` (required, unless prompted): trusted CA certificate from **your own** server.
- `--server HTTPS_URL` (required, unless prompted): server HTTPS origin.
- `--install-deps`: explicitly allow installation of missing **system dependencies** (not update/upgrade of managed packages).
- `--enable-timer`: opt in to daily **observer-only** reporting timer.
- `-h`, `--help`: help.
- No arguments with terminal: interactive prompts. Installer waits up to approximately 10 minutes for administrator approval, then enrolls and reports; existing identity/configuration are preserved. Timer is off by default.

### Two-stage agent bootstrap — `installer/versionary-beta-agent-bootstrap.sh`
```bash
sudo bash installer/versionary-beta-agent-bootstrap.sh install \
  --distribution FILE --ca-cert FILE --server HTTPS_URL [--install-deps]
sudo bash installer/versionary-beta-agent-bootstrap.sh complete
```
- `install`: stage/deploy new agent and register as pending; refuses unsafe/conflicting existing installation.
- `complete`: after dashboard approval, enroll, heartbeat, report.
- No automatic reporting timer.

### Agent CLI — `versionary_agent_cli.py`
```bash
python3 versionary_agent_cli.py [--state-dir DIR] setup --server HTTPS_URL --ca-cert FILE
python3 versionary_agent_cli.py [--state-dir DIR] setup --interactive
python3 versionary_agent_cli.py [--state-dir DIR] status
python3 versionary_agent_cli.py [--state-dir DIR] register
python3 versionary_agent_cli.py [--state-dir DIR] enroll
python3 versionary_agent_cli.py [--state-dir DIR] heartbeat
python3 versionary_agent_cli.py [--state-dir DIR] report
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system status
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system register
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system enroll
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system heartbeat
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system report
```
- Global `--state-dir DIR`: user-owned private state, default `~/.local/state/versionary-agent`.
- Global `--system`: installed config `/etc/versionary-agent/config.json`, state `/var/lib/versionary-agent`; **incompatible with `--state-dir`**. `setup` prohibited in system mode.
- `setup` options: `--server`, `--ca-cert`, `--interactive`; never silently overwrites existing config.
- Commands: `setup`, `status`, `register`, `enroll`, `heartbeat`, `report`. Registration requires administrator approval before enrollment. Report scans available package updates, **does not install them**.

### Portable agent setup — `installer/versionary-agent-setup.py`
```bash
python3 installer/versionary-agent-setup.py \
  --server HTTPS_URL --ca-cert FILE [--state-dir DIR] [--dry-run]
python3 installer/versionary-agent-setup.py --interactive [--state-dir DIR] [--dry-run]
```
Supported: `--server`, `--ca-cert`, `--state-dir`, `--interactive`, `--dry-run`. This is a config bootstrap, not a full agent installation.

### Disposable server installer — `installer/versionary-server-install.py`
```bash
sudo python3 installer/versionary-server-install.py \
  --archive /absolute/path/versionary-v0.1.0-beta.1.tar.gz \
  --manifest /absolute/path/versionary-v0.1.0-beta.1-manifest.json \
  --mode dry-run \
  --tls-identity SERVER_HOST --bind-address SERVER_BIND --port 8766
```
- Required: `--archive PATH`, `--manifest PATH`.
- `--mode dry-run|install`: default **dry-run**. `install` changes the target system; only approved disposable VM.
- `--confirm-disposable`: explicit disposable-system confirmation for install mode.
- `--app-dir PATH`: default `/opt/versionary`.
- `--state-dir PATH`: default `/var/lib/versionary`.
- `--tls-identity HOST_OR_IP`: default `127.0.0.1`; must match cert SAN and client URL.
- `--bind-address ADDRESS`: default `127.0.0.1`.
- `--port INTEGER`: default `8766`.
- Archive verification checks manifest SHA256 and safe archive contents. Renamed release archive/manifest pairing should be tested with dry-run on a disposable target.

### HTTPS beta server — `versionary_https_beta.py`
```bash
python3 versionary_https_beta.py init
python3 versionary_https_beta.py status
python3 versionary_https_beta.py serve
```
Positional commands: `init`, `status`, `serve`; no other CLI flags defined. Environment:
- `VERSIONARY_STATE_DIR`: private server state root; installed default `/var/lib/versionary`.
- `VERSIONARY_TLS_IDENTITY`: TLS hostname/IP identity.
- `VERSIONARY_BIND_ADDRESS`: listen address.
- `VERSIONARY_HTTPS_PORT`: HTTPS port, default `8766`.
- `VERSIONARY_BETA_ENROLLMENT=true`: opt in to enrollment.
- `VERSIONARY_BETA_REPORTING=true`: opt in to reporting.
- `VERSIONARY_DISTRIBUTION_ENABLED=false`: server-side agent distribution intentionally disabled.
- Service uses `versionary-server.service`; `/health` and `/admin/dashboard` are known routes.
- `init` generates private CA/server credentials and refuses overwriting existing certificates.

### Server settings CLI — `installer/settings-cli.py` (staged, not applied to live services)
```bash
python3 installer/settings-cli.py [--path FILE] show
python3 installer/settings-cli.py [--path FILE] runtime-status
python3 installer/settings-cli.py [--path FILE] set KEY VALUE
```
`KEY`: `public_url`, `enrollment_enabled`, `reporting_enabled`, `scan_interval_minutes`, `appearance`, `tls_mode`. This tool explicitly says settings are **staged, not applied**; do not treat `set` as enabling a live service.

### Planned, NOT implemented release switches
Future UX may include `--uninstall`, `--upgrade`, `--rollback`, `--auto-discover`, `--rotate-ca`, `--apply-updates`, `--reboot-policy`, and GUI equivalents. **These are design concepts, not accepted CLI flags.** Confirm actual spelling/behavior before implementation and update this reference when delivered.

### Security and boundaries
Verify `SHA256SUMS`, use only CA from the intended server, keep keys/tokens private, require dashboard approval, never silently enable timers, and never perform package upgrades or reboots in observer-only beta.

---

## Historical engineering documentation (preserved)

# Versionary — Command Reference

Status: Development CLI reference, 2026-10-31.

All commands below run from the repository root.

Python executable:
.venv/bin/python

## Portable setup

Script:
installer/versionary-agent-setup.py

Options:

--server URL
    HTTPS server origin. No path, query, or embedded credentials.

--ca-cert PATH
    Existing trusted CA certificate file.

--state-dir PATH
    Private agent state directory.
    Default: ~/.local/state/versionary-agent

--interactive
    Prompt for missing settings. Requires a terminal.

--dry-run
    Validate and preview without writing configuration.

-h, --help
    Display command help.

Example:

.venv/bin/python installer/versionary-agent-setup.py \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt \
  --dry-run

## Agent CLI

Script:
versionary_agent_cli.py

Global option:

--state-dir PATH
    Private state directory.
    Must appear before the subcommand.

Subcommands:

setup
    Save HTTPS origin and CA path.
    Refuses to overwrite configuration.

status
    Show configured server, identity, and local credential state.

register
    Request registration using the enrollment protocol.

enroll
    Complete enrollment after administrator approval.

heartbeat
    Send an authenticated heartbeat.

report
    Scan package update availability and submit a report.

## Agent CLI setup options

setup --server URL --ca-cert PATH

setup --interactive

Example:

.venv/bin/python versionary_agent_cli.py \
  setup \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt

## Lifecycle command sequence

1. Configure:

.venv/bin/python versionary_agent_cli.py setup \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt

2. Inspect:

.venv/bin/python versionary_agent_cli.py status

3. Register:

.venv/bin/python versionary_agent_cli.py register

4. Obtain administrator approval on the server.

5. Enroll:

.venv/bin/python versionary_agent_cli.py enroll

6. Send heartbeat:

.venv/bin/python versionary_agent_cli.py heartbeat

7. Send report:

.venv/bin/python versionary_agent_cli.py report

## Return codes

0
    Command completed successfully.

1
    Handled operational/configuration error.
    The report command also returns 1 when local scan status
    is unsuccessful.

2
    Common argparse usage error, such as an unknown command
    or missing required command-line arguments.

## Important security notes

- Never paste live credentials or private keys into commands.
- A CA file must already exist before setup.
- The CA must be trusted for the intended server.
- HTTPS hostname/IP verification happens during connection.
- Registration and enrollment require a reachable server
  with the relevant feature gates enabled.
- Server-side approval is a separate administrative action.
- No command listed here installs patches or reboots machines.

## Not implemented yet

Do not assume the existence of commands named:

install
upgrade
uninstall
service enable
service start
certificate rotate

These are roadmap items, not current CLI functionality.

## Beta 0.9 localhost acceptance checkpoint — 2026-11-01

### Local Beta 0.9 trial commands (not the portable agent CLI)

```bash
~/.local/bin/versionary-beta09 --help
~/.local/bin/versionary-beta09 status
~/.local/bin/versionary-beta09 server
~/.local/bin/versionary-beta09 register
~/.local/bin/versionary-beta09 activate
~/.local/bin/versionary-beta09 report
```

These commands operate on the local trial's persistent state, separate from the portable agent CLI documented above. Do not rerun `register` or `activate` for an already approved/activated agent without a specific reason. `server` binds the local HTTPS trial endpoint at `https://localhost:8769/admin/dashboard`. Stop the existing foreground server with Ctrl+C before launching another. The local launcher currently depends on the developer checkout and `.venv`.

---

## Beta.2 root-wrapper command notes — pending publication

**The following describes locally validated root wrappers; it is not a claim that the beta.2 release is published.** The wrappers use `TAG=v0.1.0-beta.2` and `PIN=f7d73fa56dd0b064d9d09c35b415d6573947b5cd8c38161f5930d513ea768f7e` in the operator's local checkout.

- `bash install-versionary.sh`: guided server install, interactive dependency handling, release checksum validation, HTTPS server IP selection, dry-run, then disposable installation with optional observer-only beta gates.
- `bash install-versionary-agent.sh`: guided agent install, optional LAN discovery, CA fingerprint validation, release checksum validation, and delegated guided agent installer.
- Agent wrapper switches documented in local source: `--server`, `--ca-cert`, `--ca-fingerprint`, `--install-deps`, `--enable-timer`. Confirm `--help` against the downloaded wrapper before use.
- `--install-deps` authorizes package-manager changes on the VM. Arch bootstrap may use `pacman -Syu`, which can upgrade system packages. Do not use on production.
- The agent's `--enable-timer` remains optional; no unattended patching or reboot is implemented.
- The underlying `versionary_agent_cli.py` and server installer switches above remain the baseline reference unless a future release explicitly changes them.

See [beta.2 release notes](RELEASE-NOTES-v0.1.0-beta.2.md). Fresh-VM acceptance and publication remain pending.

## Versionary v0.1.0-beta.3 - Public beta installer update

The public agent installer now constructs and verifies the
complete agent distribution from verified release assets.

Server installer options:
- --address IP
- --port PORT
- --beta-fleet
- --no-beta-fleet
- --yes
- --help

Agent installer options:
- --server URL
- --ca-cert PATH
- --ca-fingerprint SHA256_HEX
- --install-deps
- --enable-timer
- --help

Agent enrollment requires administrator approval.
Agent reporting is observer-only: no automatic package
installation or reboots.

Production deployment remains disabled.

Release notes: RELEASE-NOTES-v0.1.0-beta.3.md
