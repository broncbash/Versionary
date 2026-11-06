# Versionary — Comprehensive Next-Session Prompt
## 2026-11-06 guided-installer remediation

The user abandoned a fresh Arch server VM after the manual beta1 installation sequence proved too cumbersome, despite INSTALL=PASS and dry-run success. **Do not ask them to resume that VM.** User authorized substantial installer and release improvements without repeated manual steps. On main, new standalone source wrappers `install-versionary.sh` and `install-versionary-agent.sh` now automate downloading four existing public beta1 release assets, verification, safe extraction, and the existing guided installation flows. The server wrapper detects IP and offers observer-only beta enrollment/reporting; the agent wrapper asks for the server URL and securely obtained CA, then waits for dashboard approval. README and quick-start link the new wrappers. **No new release assets have been built/published; the existing beta1 assets are unchanged. Fresh disposable-VM end-to-end acceptance of these wrappers remains outstanding.** The next priority is validating and improving the single-command experience and packaging a new prerelease after acceptance, not another manual multi-step beta1 walkthrough. No live homelab deployment or production authorization.


## 2026-11-06 repository identity update

The user renamed the GitHub repository to `broncbash/Versionary` and explicitly changed its visibility to **public**. Both changes were verified with the GitHub repository API. The existing beta `v0.1.0-beta.1` remains available with four release assets and identical filenames/digests. Public HTTPS GitHub release downloads no longer require GitHub CLI authentication; use the download instructions in `docs/versionary/QUICK-START.md`. This visibility change **does not** approve production deployment or authorize publication of secrets. Keep existing local checkout path `~/Projects/arby-patch-command` as a factual historical/local path until the user actually moves it. Update `git remote origin` separately on the local checkout as desired; GitHub may redirect old remote URLs, but the canonical remote is `https://github.com/broncbash/Versionary.git`. Historical checkpoint entries below may describe the former private repository; the latest verified status supersedes them. Do not change the published tag or asset bytes.

**Authoritative handoff: 2026-11-05, after GitHub v0.1.0-beta.1 publication.**

> Resume development of Versionary from this handoff and the connected GitHub repository `broncbash/Versionary`. Do not assume historical sections of other docs are current; read their newest checkpoint. Work in focused, meaningful batches, one short pasteable command at a time when local execution is required. Use GitHub integration directly for approved repository documentation changes. Do not restart from scratch, repeat already-accepted tests without reason, or make unauthorized changes.

## 1. Mission and product identity
Versionary is a portable, professional Linux fleet update visibility and eventual patch-management application. It replaces the old ARBY PATCH COMMAND project name; Some local checkout paths and internal identifiers still carry legacy names. **The GitHub repository was renamed with user authorization on 2026-11-06; do not rename local paths or break compatibility without checking first.**

Architecture: Python FastAPI HTTPS server, SQLite agent registry and reporting, secure agent identities and enrollment, dashboard, Linux Python agents with Arch/pacman and Debian/apt scanning. Current beta is **observer-only**: discover/update inventories, show health, manually approve/revoke agents, heartbeat/report. **No automatic patch installs or reboots.**

Product vision: friendly interactive and unattended/scriptable server and agent installers; professional dashboard with Settings and GUI/CLI administrative parity; user-owned or generated certificates and CA trust; safe upgrades/rollback, backup/restore, optional secure discovery, eventual explicit manual patch application. Never hard-code homelab IPs, fingerprints, or developer paths.

## 2. Published milestone — do not re-publish
- Repository: https://github.com/broncbash/Versionary (PUBLIC).
- Main branch after authorized PR #2 merge: `9a3587b5edfbbd0088ecb46d802117f62f01a551`.
- Development branch: `feature/versionary-agent-rename`; confirmed source commit `cd12d1f95a2d52d005a3623045e0efcf9084b5b3`.
- Published GitHub **prerelease**: https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.1
- Tag `v0.1.0-beta.1`, target merged main, 2026-11-05.
- Four uploaded assets:
  1. `versionary-v0.1.0-beta.1.tar.gz` (main release; 160 files), SHA256 `4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a`.
  2. `versionary-v0.1.0-beta.1-manifest.json`, SHA256 `9608eed0bddd4d828da2f936f5ac67821e58c8575c5337d58d8998be09685d50`.
  3. `versionary-v0.1.0-beta.1-agent.tar.gz`, SHA256 `936fc9c05e7b7f6d4b4c5aff4805d225da915311594af9e862797d024e76257b`.
  4. `SHA256SUMS`, SHA256 `b8ddf34bda69674df71eb366ed34368d8d80e1dbfa819fd8465822e2110d7bfc`.
- Checksums and GitHub asset digests verified. **Follow-up:** validate renamed release archive/manifest together with server installer's `--mode dry-run` before recommending general installation. The archive builder originally produced `versionary-rc2-20261105-152857-347494.tar.gz` and matching JSON; renamed files were checksum verified, but no recorded paired server-installer dry-run after rename.
- Repository became PUBLIC on 2026-11-06 by explicit user action, so beta assets can be downloaded without authentication. No production approval.
- Release notes explain limitations; do not expose private CA, tokens, keys or lab data.

## 3. Source and local working environment
- CachyOS/Arch desktop checkout: `~/Projects/arby-patch-command`.
- Release candidates: `~/Projects/versionary-release-candidates`.
- Local release staging: `~/Projects/versionary-release-candidates/v0.1.0-beta.1/`.
- User uses Konsole, zsh, nvim, KDE Klipper (not wl-copy). Prefers complete copy-paste heredocs, minimal chatter, meaningful development batches, no hosted CI.
- Preserve all local untracked work, backup files, certificates, keys, SQLite DBs and staging directories. Known examples: `.versionary-local-beta/`, `.versionary-timer-preview/`, `.versionary-https-beta/`, `return-prompt.md`, `dashboard_ui.py.pre-tab-login`, `installer/setup-config.py.pre-batch8`, dated `*.backup-*` and `*.pre-*` files. Never run `git clean -fd`, broad reset, or `git add -A`.
- **No commit, push, merge, tag, release, repository visibility change or live deployment without explicit user approval.** Prior approval was for the documentation synchronization described below, not a blanket grant for future work.
- Do not modify Proxmox CT 102 (monitoring), CT 104 (Versionary/Patch Command) or any live homelab machine without approval. Prefer disposable virt-manager VMs.
- No hosted CI. Keep beta/production security gates explicit and disabled by default.

## 4. Disposable VM beta lab (historical last-known state, verify before connecting)
- Arch server VM `Arch-Ver-Server`, `192.168.122.75`; isolated HTTPS server `https://192.168.122.75:8766`, dashboard `/admin/dashboard`; service `versionary-server.service`; private CA typically `/var/lib/versionary/certs/ca.crt`.
- Arch clone `Arch-Ver-Installer-Test`, `192.168.122.180`, used for guided installer acceptance. Original Arch agent `192.168.122.132` and Debian `192.168.122.69` were powered off at last checkpoint. Addresses are lab-only.
- Server `VERSIONARY_BETA_ENROLLMENT=true`, `VERSIONARY_BETA_REPORTING=true`, `VERSIONARY_DISTRIBUTION_ENABLED=false` in tested beta setup; production flag false. Keep private server credentials private.
- Guided agent installer was **executed** on Arch clone with offline distribution and CA; passed preflight, installed 13 modules, registered pending, waited for dashboard approval, enrolled, heartbeat and report recorded. No system package upgrades, reporting timer disabled. Follow-up patch changed repetitive enrollment errors to a waiting message; syntax checked but not VM re-tested.
- Debian agent fleet acceptance was demonstrated earlier; do not imply the new guided installer was fully live-accepted on Debian.
- Agent test identity example `9c94f1dc-3729-448f-9214-f3804a0e8a09` (lab-only; no need to reuse).
- Avoid touching VMs unnecessarily. Ask approval before potentially destructive install/recovery experiments.

## 5. Current implementation
Server: `versionary_https_beta.py`, `versionary_https_beta_admin.py`, `versionary_browser_sessions.py`, `dashboard_ui.py`, `agent_registry.py`, `agent_reporting_api.py`, `agent_enrollment_api.py`, `enrollment_v2_api.py`, admin agent APIs. FastAPI/SQLite, Ed25519 challenge/proof, approval/revocation, agent credential authentication, browser sessions and dashboard, private TLS state.
Agent: `versionary_agent_cli.py`, `agent/` package (config, identity, enrollment, credentials, heartbeat, reporting, scanner). Manual CLI and optional systemd reporting timer. Arch and Debian-family scanner support.
Installer/release: `installer/versionary-server-install.py`, `installer/versionary-agent-guided-install.sh`, `installer/versionary-beta-agent-bootstrap.sh`, `installer/install-agent-offline.py`, `installer/versionary-agent-system-preflight.py`, `installer/versionary-agent-setup.py`, `installer/build-versionary-release.py`, `installer/build-agent-distribution.py`, certificate and recovery modules.
Historical full regression checkpoints include 1,577 tests with one skipped on Nov 4, and later test runs in preceding work. **Do not claim a fresh full-suite run for the published tag without running one.** Security and transaction hardening prototypes exist but production acceptance remains blocked.

## 6. Implemented command-line switches — authoritative at beta tag
See `docs/versionary/COMMAND-REFERENCE.md` for exact syntax and defaults; verify source before modifying.

**Guided agent installer:**
```bash
sudo bash installer/versionary-agent-guided-install.sh \
 --distribution /path/versionary-v0.1.0-beta.1-agent.tar.gz \
 --ca-cert /path/ca.crt --server https://HOST:8766 \
 [--install-deps] [--enable-timer]
```
No args prompts interactively. `-h`/`--help` supported. Waits up to 10 minutes for approval. `--install-deps` may install missing system dependencies, **not** update managed packages; `--enable-timer` opts in to daily observer-only reporting. Neither is default.

**Two-stage bootstrap:**
```bash
sudo bash installer/versionary-beta-agent-bootstrap.sh install --distribution FILE --ca-cert FILE --server HTTPS_URL [--install-deps]
sudo bash installer/versionary-beta-agent-bootstrap.sh complete
```
Install stages/deploys and registers pending; complete enrolls, heartbeats, reports after approval.

**Agent CLI:** `python3 versionary_agent_cli.py [--state-dir DIR] setup --server HTTPS_URL --ca-cert FILE`, or `setup --interactive`; commands `status`, `register`, `enroll`, `heartbeat`, `report`. Global `--system` selects installed `/etc/versionary-agent/config.json` and `/var/lib/versionary-agent`, mutually exclusive with `--state-dir`; `setup` forbidden in system mode. Typical `sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system report`.

**Portable setup:** `python3 installer/versionary-agent-setup.py --server HTTPS_URL --ca-cert FILE [--state-dir DIR] [--interactive] [--dry-run]`.

**Disposable server installer:**
```bash
sudo python3 installer/versionary-server-install.py \
 --archive FILE --manifest FILE --mode dry-run \
 [--confirm-disposable] [--app-dir /opt/versionary] \
 [--state-dir /var/lib/versionary] [--tls-identity HOST_OR_IP] \
 [--bind-address ADDRESS] [--port 8766]
```
`--mode` choices `dry-run` (default), `install`. Install requires disposable confirmation and changes system; no live host installation without approval.

**HTTPS server runtime:** `python3 versionary_https_beta.py init|serve|status`; environment `VERSIONARY_STATE_DIR`, `VERSIONARY_TLS_IDENTITY`, `VERSIONARY_BIND_ADDRESS`, `VERSIONARY_HTTPS_PORT`, `VERSIONARY_BETA_ENROLLMENT`, `VERSIONARY_BETA_REPORTING`, `VERSIONARY_DISTRIBUTION_ENABLED`. `init` refuses overwriting existing certificates.

**Staged server settings CLI:** `python3 installer/settings-cli.py [--path FILE] show|runtime-status|set KEY VALUE`; keys `public_url`, `enrollment_enabled`, `reporting_enabled`, `scan_interval_minutes`, `appearance`, `tls_mode`. **Staged settings are not applied to running service.**

**Future concepts, NOT current flags:** `--uninstall`, `--upgrade`, `--rollback`, `--auto-discover`, `--rotate-ca`, `--apply-updates`, `--reboot-policy`. Decide final names/semantics before implementing; never advertise as existing.

## 7. Product roadmap / planned features
**Immediate:** polish one-command/interactive first-run experience; stable release packaging and downloadable-asset verification; dependency detection, friendly errors, clean Arch/Debian installs, secure approval onboarding, diagnostics and reporting schedule UI. 
**Near-term:** GUI Settings > Security > Certificates with user-provided TLS cert/key OR easy CA/server cert generation/renewal, hostname/IP SAN checks, safe trust installation/rotation; equivalent CLI options. Configurable network binding, service installation, admin sessions and credentials, certificate lifecycle. Agent inventory/search/filters, scan history, stale/failed agent status, package counts, scheduled observer-only reporting and manual scans. Optional secure agent discovery with explicit approval and no silent trust/enrollment.
**Safety/operability:** transactional install/upgrade/rollback/recovery, backups, identity/credential preservation, safe uninstall, signed release provenance, filesystem race/durability hardening, cross-distro matrix, secure defaults, production acceptance gate.
**Later:** explicit administrator-triggered package update execution and progress, per-agent policy, maintenance windows, reboot handling, with no unattended upgrades/reboots by default. GUI/CLI parity, user-friendly standalone packaging, branding, accessibility and responsive dashboard.
**Deferred decisions:** final supported OS/version matrix, discovery protocol, backend migration policy, distribution channel, update/reboot authorization model, public release-distribution process (repository rename and public visibility completed 2026-11-06).

## 8. GitHub documentation and ongoing handoffs
- Authoritative docs: `docs/versionary/PROJECT-STATUS.md`, `ROADMAP.md`, `COMMAND-REFERENCE.md`, `USER-GUIDE.md`, `DEVELOPER-HANDOFF.md`, and **this file**.
- On 2026-11-05 user explicitly approved syncing docs to GitHub. A docs branch `docs/versionary-beta-2026-11-05` was created and the five companion docs updated with a new authoritative checkpoint while retaining historical text. Verify whether this next-session prompt and a PR/merge are completed before claiming documentation is on `main`. **Do not merge automatically absent explicit approval for that action.**
- User had repeated problems downloading generated ZIP; use GitHub integration for approved updates rather than relying on sandbox downloads.
- After meaningful milestones, update status/roadmap/CLI reference/handoff in same authorized batch, preserving prior engineering history. Do not commit local state/secrets.
- Do not confuse docs branch or development branch with published release tag. Do not mutate released tag or assets without explicit authorization.

## 9. Recommended first actions next session
1. Read this handoff, current GitHub branch/main, docs status and release metadata; check any open docs PR.
2. If docs changes still awaiting review/merge, summarize and request authorization rather than silently merging.
3. Ask user which immediate priority to tackle only if not already specified; suggest **real downloadable beta install/verification and simplified first-run experience**.
4. Before changing code, inspect relevant source and existing tests; make a focused implementation plan and carry out a meaningful batch.
5. Use approved disposable VMs for any real installation, not live Proxmox/LXC. Keep outputs short and actionable.
6. Never re-run broad tests needlessly, and never invent a passing result.
7. Preserve all untracked files; do not commit/push without authorization.
8. Keep documentation current and report precise changed files, verified checks, commit/PR state, and next action.

## 10. Working relationship
User appreciates occasional Star Trek jokes (Captain / Lt. Uhura / Darth Helmet), but wants fast, grounded engineering, not endless ceremony. Avoid repetitive clarification when requirements are established. Prefer full pasteable heredocs for local code, nvim not nano, and direct GitHub operations where permitted. Keep all risky actions opt-in and be transparent about what has and has not been executed.

**Resume at the actual GitHub checkpoint, not an imagined one. This document is a starting map; verify changing state before acting.**
