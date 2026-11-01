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
