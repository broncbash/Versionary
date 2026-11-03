# Versionary — Developer Handoff

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
