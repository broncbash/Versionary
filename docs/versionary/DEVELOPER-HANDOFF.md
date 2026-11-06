# Versionary — Developer Handoff

## Current developer handoff — 2026-11-05, after beta publication

This supersedes earlier "do not merge/publish" statements that applied before explicit authorization.

- GitHub `broncbash/arby-patch-command` (private); `main` contains merged PR #2 at `9a3587b5edfbbd0088ecb46d802117f62f01a551`; development branch `feature/versionary-agent-rename` at `cd12d1f95a2d52d005a3623045e0efcf9084b5b3`.
- GitHub prerelease `v0.1.0-beta.1`: https://github.com/broncbash/arby-patch-command/releases/tag/v0.1.0-beta.1 . Published four assets; 160-file main archive. SHA256 main `4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a`; agent `936fc9c05e7b7f6d4b4c5aff4805d225da915311594af9e862797d024e76257b`.
- Local desktop CachyOS checkout `~/Projects/arby-patch-command`; release candidates `~/Projects/versionary-release-candidates`. Prefer one concise, full heredoc/paste block per step, verify results, no endless test loops, no hosted CI.
- Disposable VM lab: Arch server `192.168.122.75` HTTPS `:8766`, agent clone `192.168.122.180`; original Arch `192.168.122.132` and Debian `192.168.122.69` were powered off. VM addresses are **lab-only**, never product defaults.
- Guided agent installer executed successfully on Arch clone with registration, dashboard approval, enrollment, heartbeat, report; no patch installs; timer disabled. Improved approval-waiting message syntax checked but not re-run in VM.
- Source map: `versionary_https_beta.py`, `versionary_agent_cli.py`, `agent/`, `agent_registry.py`, `agent_reporting_api.py`, `installer/versionary-server-install.py`, `installer/versionary-agent-guided-install.sh`, `installer/versionary-beta-agent-bootstrap.sh`, `installer/build-versionary-release.py`.
- Implemented CLI reference is `docs/versionary/COMMAND-REFERENCE.md`; do not invent switches. Planned roadmap is `docs/versionary/ROADMAP.md`.
- Protect all untracked backups and local state: `.versionary-local-beta/`, `.versionary-timer-preview/`, `.versionary-https-beta/`, `return-prompt.md`, backups, certificates, credentials, SQLite databases and release archives. Never `git add -A` or clean/reset indiscriminately.
- No live Proxmox CT 102 or CT 104 changes without approval; no production deployment, no automatic patch installation/reboot. No commit/push/merge/tag/release/public visibility change without explicit approval.
- Next focus: improve friendly server/agent first-run installers, CA trust UX, real downloaded-asset verification, Arch/Debian clean-install coverage, dashboard admin ergonomics, reporting diagnostics, and secure upgrade/rollback planning. Avoid repeating passed tests without a relevant change.
- Keep GitHub documentation authoritative and update handoff with each substantial milestone. GitHub can be managed directly with connected GitHub integration when authorized; never force user to paste huge code solely for repository edits.

---

## Historical engineering documentation (preserved)

# Versionary — Developer Handoff

## Current developer handoff — 2026-11-04

This is the authoritative current checkpoint. Earlier sections
document historical implementation steps and are not current
instructions when they conflict with this section.

Repository: `broncbash/arby-patch-command`
Branch: `feature/versionary-agent-rename`
Last confirmed pushed commit before Batch 70: `f290fb3`
Draft PR: https://github.com/broncbash/arby-patch-command/pull/2

Latest local validation: 1,577 tests, one skipped.

Batch 70 local pending work:
- `tests/test_versionary_upgrade_sync_failure_70.py`
- `docs/versionary/RELEASE-CANDIDATE-STATUS.md`
- Current documentation reconciliation in core documents.

Next: verify full regression, review exact staged inventory,
commit and push only intended files, then continue isolated
upgrade recovery hardening.

Assistant responsibilities:
- Manage GitHub branch and draft PR integration.
- Maintain documentation alongside significant code changes.
- Verify documentation accuracy before each milestone push.
- Provide complete paste-ready terminal batches.
- Avoid hosted CI and unnecessary user GitHub operations.
- Preserve all untracked local artifacts and secrets.
- Never merge, publish a release, or deploy to live systems
  without explicit authorization.

Safety: real-system agent installation remains disabled;
isolated upgrade is not guaranteed crash-safe or race-safe.

---


## Resume point

Date: 2026-10-31
Branch: feature/versionary-agent-rename
Last confirmed commit: 681e8b4
Selected regression: 68/68 passing

Latest completed work:
Portable agent setup foundation, with interactive, unattended,
and dry-run modes. Changes committed and pushed.

## Local checkout

~/Projects/arby-patch-command

Python environment:
.venv/bin/python

Preferred development workflow:
- Large, coherent batches.
- Full copy/paste heredoc commands.
- Minimal back-and-forth.
- Local tests before commits.
- Stage only intended files.
- Commit and push feature branch after verification.
- No hosted CI requirement.
- Do not use `set -e` in terminal command batches.

## Key files

versionary_agent_cli.py
    Manual agent lifecycle CLI.

installer/versionary-agent-setup.py
    Portable configuration bootstrap.

agent/config.py
    Server origin and configuration validation.

agent/credentials.py
    Private credential storage and directory validation.

agent/enrollment_client.py
    Agent enrollment protocol client.

agent/enrollment_http.py
    CA-verified HTTPS request transport.

agent/identity.py
    Persistent agent identity.

agent/heartbeat.py
    Heartbeat client.

agent/reporting.py
    Update report client.

agent/versionary_agent.py
    Platform detection and package scanning.

versionary_https_beta.py
    Disposable isolated HTTPS beta.

tests/test_versionary_agent_setup.py
    Portable setup tests.

tests/test_versionary_agent_cli.py
    Offline agent CLI tests.

tests/test_versionary_agent_cli_hardening.py
    Security regression tests.

tests/test_versionary_agent_cli_https.py
    Real disposable HTTPS lifecycle.

## Agent CLI architecture

State directory defaults to:

~/.local/state/versionary-agent

Expected private files may include:

config.json
identity.json
enrollment-key.json
enrollment-pending.json
credential.json

Security expectations:
- State directory: owned by current user, mode 0700.
- Configuration/identity/credential files: private 0600.
- Reject symlink substitution for protected state.
- Reject unsafe existing configuration.
- Do not overwrite existing credentials or trust anchors.
- Require HTTPS and a configured CA certificate.

## Manual development checks

Compile:

.venv/bin/python -m py_compile \
  versionary_agent_cli.py \
  installer/versionary-agent-setup.py

Installer tests:

.venv/bin/python -m unittest \
  tests.test_versionary_agent_setup -v

Selected regression:

.venv/bin/python -m unittest \
  tests.test_versionary_agent_setup \
  tests.test_versionary_agent_cli \
  tests.test_versionary_agent_cli_hardening \
  tests.test_versionary_agent_cli_https \
  tests.test_versionary_https_beta \
  tests.test_versionary_https_beta_security \
  tests.test_versionary_https_beta_integration \
  tests.test_versionary_https_beta_gates \
  tests.test_versionary_https_beta_admin \
  tests.test_versionary_https_beta_journey \
  tests.test_beta_tls_journey \
  tests.test_beta_agent_server_journey -q

Check repository:

git status -sb
git diff --check
git log -1 --oneline

## Environment restrictions

Development is on the user's desktop.

Do not modify CT104, CT102, CT103, or any other production
homelab container without approval.

CT103 previously received read-only preflight approval only.
That does not authorize installing an agent.

Do not touch the four protected untracked items listed in
PROJECT-STATUS.md.

Do not overwrite or expose secrets from .versionary-https-beta/.

## Git workflow

Work on feature/versionary-agent-rename.

Do not merge, tag, delete branches, or rename the repository
without explicit approval.

Never use blanket `git add .` when protected untracked
local files are present.

## Next engineering batch

1. Inspect existing installer and packaging conventions.
2. Design portable agent distribution without root assumptions.
3. Add secure, non-destructive upgrade planning.
4. Add optional service/timer plan, disabled by default.
5. Add offline tests for install, upgrade, and rollback.
6. Run selected and broader regression suites.
7. Commit only verified, intended files.

## Important distinction

The existing setup script configures the agent connection.

It does not:
- Install system packages.
- Install a background service.
- Register or enroll the agent.
- Enable reporting.
- Contact the server.

Maintain that separation.

## KDE Klipper Clipboard Workflow

The developer uses CachyOS/Arch Linux, KDE Plasma, and Konsole.

For future Versionary development sessions, use KDE Klipper to copy
terminal diagnostic output automatically into the clipboard.

Verified command:

    qdbus6 org.kde.klipper /klipper org.kde.klipper.klipper.setClipboardContents "$(cat "$LOG")"

Recommended workflow:

1. Create a temporary log using mktemp.
2. Capture command output and errors into that log.
3. Include exit statuses for important verification commands.
4. Copy the completed log using the Klipper D-Bus command above.
5. Tell the user to press Ctrl+V in ChatGPT.
6. Preserve the log path as a backup.

Security and usability rules:

- Never copy passwords, tokens, private keys, or enrollment secrets.
- Prefer complete, copy-paste-ready terminal commands.
- Do not use set -e or exit 1 in pasted Konsole command blocks.
- Do not overwrite protected local development artifacts.
- Do not modify CT104, CT102, or disposable beta machines without approval.
- Keep changes local until testing and review are complete.

This workflow was verified on 2026-11-01.

## Mission 5C — Developer Handoff (2026-11-01)

Branch: feature/versionary-agent-rename
Previous pushed baseline: 203412d

Mission 5C implementation:

- installer/active-release-integrity.py (new)
- installer/rollback-plan.py (updated)
- tests/test_active_release_integrity.py (new)
- tests/test_rollback_integrity_integration.py (new)
- tests/test_rollback_release_awareness.py (fixture updated)

Verification:

- 49 focused security tests passed.
- Full suite: 1,275 tests, zero failures/errors, one skipped.
- Compilation and git diff --check passed.

Security rules:

- Integrity verification is not signature authentication.
- Signature authentication is not rollback authorization.
- All rollback planning remains read-only.
- Production installation and deployment remain prohibited.
- Pathname-based integrity reads are not yet race-resistant.
- Do not modify CT104, CT102, or disposable beta systems without approval.

Developer workflow:

- Use local development and full heredoc commands.
- Use KDE Klipper D-Bus clipboard transfer for terminal logs.
- Preserve protected untracked files and local beta artifacts.
- Do not use hosted CI.
- Commit and push only after staged validation.

## Mission 5D handoff — Descriptor-based active-release integrity

Implementation: `installer/active-release-integrity.py`.

Tests: `tests/test_active_release_descriptor_security.py`, plus existing integrity and rollback integration tests.

Local verification: compilation passed; 39 focused tests passed; full regression ran 1,282 tests with one skip and zero failures; diff validation passed.

The verifier uses directory-relative descriptors, no-follow opens, `fstat` checks, content-addressed hashing, and active-pointer identity checks. It remains read-only.

Security boundaries: these checks reduce pathname substitution risks but do not establish a race-free atomic snapshot. In-place modification, ABA-style pointer changes, and adversarial mutation beyond the checked metadata remain outside the guarantee. No release authenticity, provenance, rollback authorization, production installation, or service activation is established by this verifier.

Protected untracked local artifacts must remain untouched. No CT104, CT102, or production modifications without explicit approval.

## Mission 5E handoff — Release concurrency hardening

Implementation: `installer/active-release-integrity.py`.

New tests: `tests/test_active_release_concurrency.py`.

Local validation: compilation passed; 44 focused tests passed; full regression ran 1,287 tests with one skip and zero failures; diff validation passed.

The verifier now captures module metadata before reading, compares it after reading, and rechecks it after content hashing. It also compares release-directory pathname identities with opened descriptors and detects persistent changes to release-directory entries.

These defenses reduce observable race windows but are not a transaction, atomic snapshot, or immutable-release guarantee. Metadata checks do not establish continuous immutability. The verifier does not authorize deployment, rollback, service activation, or production use.

The next development phase should define a filesystem-independent immutable-release contract before choosing optional Btrfs-specific enhancements.

Protected untracked artifacts remain untouched. No CT104, CT102, or production changes without explicit approval.

## Beta 0.9 localhost acceptance checkpoint — 2026-11-01

### Live local Beta 0.9 trial
- Checkout: `~/Projects/arby-patch-command`; branch expected `feature/versionary-agent-rename`.
- Dashboard: `https://localhost:8769/admin/dashboard` (local self-signed certificate; browser exception used for testing only).
- Launcher: `~/.local/bin/versionary-beta09` (shell wrapper invokes checkout `.venv/bin/python` and `installer/versionary-beta09-local.py`). This is development-only and NOT portable.
- `versionary-beta09 status` showed state directory present and agent present.
- `versionary-beta09 report` successfully reported 24 actual CachyOS repo updates after changing scanner from `pacman -Qu` to `checkupdates` (0=updates, 2=no updates; other codes must be errors).
- `dashboard_ui.py` locally patched: tab-scoped `sessionStorage` token restore on reload and `Log out` clears it; user confirmed both after server restart. This is not an HttpOnly server-side session.
- Preserve persistent state at `~/.local/state/versionary-beta09`, especially SQLite DB, certificates, admin token, and approved agent credentials. Do not print or commit secrets.
- Preserve existing untracked `.versionary-local-beta/`, `.versionary-timer-preview/`, `installer/setup-config.py.pre-batch8`, `return-prompt.md`, and any other local trial files. Inspect before staging.
- Local backup files include `~/.local/bin/versionary-beta09.pre-batch-usability`, `dashboard_ui.py.pre-tab-login`, and possibly scanner backups. Do not commit backups.
- No live CT104/CT102/CT103 changes without explicit approval. No hosted CI. No production deployment.

### Next engineering batch
1. Inspect actual working tree, last commit, and git diff; never assume previous commit hashes are current.
2. Convert checkout-specific launcher into relocatable, tested package/install logic; include `checkupdates` and honest error handling.
3. Implement server-managed administrator sessions, secure cookies, CSRF protection, expiry and invalidation; add targeted regression tests and migration plan.
4. Validate real desktop restart persistence and avoid damaging existing local trial state.
5. Refresh documentation, run appropriate local tests, commit and push only with user approval.

---

<!-- VERSIONARY_RC2_ACCEPTANCE_20261102 -->
## RC2 real installation handoff

The 2026-11-02 real installation and reboot acceptance passed.

Read:
- RC2-REAL-INSTALL-ACCEPTANCE.md
- RC2-ACCEPTANCE-OPERATIONS.md
- NEXT-SESSION-RC2-HANDOFF.md

Do not confuse the working local repository with the GitHub remote:
many development files remain modified or untracked.

The known-good acceptance VM is 192.168.122.92.
Preserve it while testing destructive recovery elsewhere.

Production approval: NO.

## 2026-11-03 — Real multi-distribution beta handoff

Development branch: feature/versionary-agent-rename

Working disposable beta environment:
- Server: Arch Linux, 192.168.122.202, HTTPS port 8766.
- Arch agent: 192.168.122.96.
- Debian 13 agent: 192.168.122.6.
- Dashboard: /admin/dashboard.

Verified lifecycle on both agents:
registration, administrator approval, secure enrollment, heartbeat,
package scan, authenticated report, and dashboard visibility.

Debian installation observations:
- Agent archive required the separate versionary_agent_cli.py module.
- Debian required python3-cryptography, python3-bcrypt, and
  python3-cffi-backend.
- Agent module defaults use /etc/versionary-agent and
  /var/lib/versionary-agent, while portable setup supports a user
  state directory. The mismatch caused permission errors.
- System-directory configuration was used to complete beta acceptance.
- These are portability and installer-usability issues to address,
  not evidence that unattended agent installation is complete.

Pending development:
- Automate agent setup, dependencies, service installation, and reporting.
- Complete disposable installer failure-recovery acceptance.
- Preserve all known-good VMs, backups, and local beta state.
- Do not trigger hosted CI or approve production deployment.


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


## Unified kit handoff — November 4, 2026

Repository: broncbash/arby-patch-command
Branch: feature/versionary-agent-rename
Last confirmed commit: e0a825a

Relevant files:
- installer/build-installation-kit.py
- installer/build-unified-installation-kit.py
- installer/install-versionary-server
- installer/install-versionary-agent
- installer/install-agent-offline.py
- docs/versionary/INSTALLATION-GUIDE.md

Batch 32 acceptance passed:
- Server release verified: 137 files
- Server installer dry run passed
- Agent installed into disposable filesystem
- No enrollment or service activation

Constraints:
- Preserve all existing untracked data and local changes
- No CT 102 or CT 104 modifications without approval
- No production deployment without approval
- No Git staging, commits, pushes, or merges without approval
- No hosted CI
- Use local regression tests and paste-ready terminal batches
- Maintain documentation and coordinate GitHub integration

Next: Complete regression checkpoint and prepare Git review.


## 2026-11-04 — Disposable VM acceptance and portability checkpoint

Current desktop checkout:
~/Projects/arby-patch-command

Branch: feature/versionary-agent-rename
Latest confirmed pushed commit before this checkpoint: 47556cf
Local changes are not yet committed or pushed.

Use .venv/bin/python for all regression runs. Running the suite
with /usr/bin/python3 causes import failures because system Python
lacks FastAPI and other project dependencies.

Verified full-suite command:

    .venv/bin/python -m unittest discover -s tests -p 'test_*.py'

Batch 43D result: 1,446 tests, one skipped, zero failures/errors.

Current local fixes:
- atomic-release.py creates new release directories with secure
  permissions even under Debian's umask 0002.
- install-versionary-agent reports missing cryptography with
  distro-specific package guidance.
- Each fix has three passing regression tests.

Disposable VM lab:
- Arch Server: 192.168.122.249
- Arch Agent: 192.168.122.81
- Debian 13 Agent: 192.168.122.34

Server HTTPS is operational. Agent preflight and disposable-root
installations succeeded. Live agent enrollment and service
activation have not been performed in this lab.

Next engineering work:
1. Review existing real-system disposable-VM agent deployment
   tooling before implementing anything new.
2. Define explicit safety gates and reversible installation.
3. Validate enrollment, approval, heartbeat, and reporting.
4. Rebuild the unified kit to incorporate the local fixes.
5. Run targeted and full regression suites.
6. Update documentation and prepare a reviewed GitHub change set.

Preserve all untracked files and backups. Do not modify live
homelab containers without approval. Do not commit, push, merge,
or use hosted CI without explicit authorization.


## Verified Three-VM Beta — 2026-11-04

The disposable beta environment passed real-system installation,
enrollment, approval, heartbeat, reporting, and dashboard verification.

Server: Arch Linux, 192.168.122.249:8766.
Agents: Arch Linux 192.168.122.81 and Debian 13 192.168.122.34.

Agent IDs:
- Arch: 541e1a5f-f742-40da-9908-52c655b4ddf2
- Debian: 6b6ba671-56fb-40ab-a9d1-465dbb61b8fb

Both agents are approved, online, and reporting successfully.
Both systemd reporting timers are enabled for 06:00 daily.

The server and agents are disposable beta systems, not production.
Do not deploy to live homelab containers without explicit approval.
Do not enable automatic package installation.

Local development branch: feature/versionary-agent-rename.
Last synchronized commit before documentation integration: 47556cf.
Regression: 1,534 tests passed, one skipped.

Preserve all local untracked artifacts and backup files.
No hosted CI. No commits, pushes, or merges without user approval.


## Batch 72 — Journal integrity checkpoint

Batch 72: finalization_assessment now checks the exact journal filename inventory before reading manifest snapshots. It remains advisory and never authorizes cleanup.

## Batch 73 — Controlled beta acceptance

Batch 73 introduces BETA-ACCEPTANCE-PLAN.md. Use its seven evidence-based gates to prioritize development. Do not equate unit-test success with completed disposable-system acceptance.
