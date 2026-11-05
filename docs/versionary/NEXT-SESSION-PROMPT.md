# VERSIONARY — COMPLETE NEXT-SESSION HANDOFF

Updated: 2026-11-01
Repository: broncbash/arby-patch-command
Local checkout: ~/Projects/arby-patch-command
Branch: feature/versionary-agent-rename
Last confirmed pushed commit: 62f9f5e

## FIRST ACTIONS

Continue Versionary Beta 0.9 development.

Before changing anything:
1. Check git branch, status, and latest commits.
2. Read all docs/versionary/*.md documentation.
3. Inspect the current implementation and tests.
4. Preserve all existing local state and credentials.
5. Identify the next coherent development batch.

Do not assume this handoff is newer than the repository.

## PROJECT

Versionary is a standalone Linux patch-visibility platform,
formerly ARBY PATCH COMMAND.

The current product is observer-only.

It supports agent registration, approval, revocation,
authenticated heartbeat, update reporting, and fleet monitoring.

Do not introduce automatic package installation, unattended
upgrades, reboots, or production deployment without approval.

## VERIFIED BETA 0.9 MILESTONE

A persistent local HTTPS server runs on the development desktop.

Dashboard:
https://localhost:8769/admin/dashboard

A real CachyOS desktop agent was successfully:
- Registered
- Approved
- Activated
- Authenticated
- Heartbeated
- Used to report actual available updates

The dashboard displayed 24 real package updates.

On this system:
- pacman -Qu returned zero updates.
- checkupdates returned 24 updates.

The installed local scanner was corrected to use checkupdates.
Scanner errors must never be silently reported as zero updates.

The launcher works through:
~/.local/bin/versionary-beta09

The launcher invokes the project's Python virtual environment.

The dashboard supports:
- Fleet overview
- Agent approval and revocation
- Update totals
- Filtering and sorting
- Tab-scoped administrator token persistence
- Log out

The user verified refresh persistence and logout.

IMPORTANT: Browser sessionStorage is not a secure replacement
for server-side administrator sessions.

## IMPORTANT FILES

dashboard_ui.py
installer/versionary-beta09-local.py
installer/versionary-beta09-wrapper.sh
installer/versionary-local-real-agent-trial.py

docs/versionary/PROJECT-STATUS.md
docs/versionary/DEVELOPER-HANDOFF.md
docs/versionary/ROADMAP.md
docs/versionary/USER-GUIDE.md
docs/versionary/COMMAND-REFERENCE.md

Review these files rather than relying only on this summary.

## USER'S TERMINAL AND CODE DELIVERY PREFERENCES

The user works primarily on an Arch/CachyOS desktop,
using Konsole and a Klipper clipboard workflow.

CRITICAL:
- Prefer complete, directly pasteable shell heredocs.
- Use cat > file <<'EOF' ... EOF for full-file delivery.
- Use equivalent complete heredocs for Python scripts.
- Make each batch easy to paste through Konsole/Klipper.
- Avoid piecemeal edits and manual line-by-line changes.
- Avoid ZIP downloads and files in ~/Downloads by default.
- Do not create downloadable artifacts unless necessary
  or explicitly requested.
- Prefer one coherent batch over many tiny instructions.
- Avoid excessive chatter and repeated confirmation questions.
- Provide clear success/failure verification.
- Avoid set -e in commands pasted directly into an
  interactive shell; use it only inside standalone scripts
  when appropriate.
- The user prefers nvim over nano.
- The user is not a programmer.

Do not confuse the user's Klipper clipboard workflow with
the Versionary launcher wrapper. Preserve both.

## SAFETY AND LOCAL STATE

Never delete, overwrite, reset, or commit:
- ~/.local/state/versionary-beta09
- Existing SQLite database
- Agent credentials and tokens
- HTTPS private keys or certificates
- Existing approved agent identity

Protect untracked local development artifacts, including:
- .versionary-local-beta/
- .versionary-timer-preview/
- dashboard_ui.py.pre-tab-login
- installer/setup-config.py.pre-batch8
- return-prompt.md

Check for additional untracked files before staging.

Never modify live Proxmox containers or other homelab
systems without explicit approval.

No hosted CI.
No surprise package updates.
No automatic reboots.
No unapproved deployment.

## NEXT DEVELOPMENT PRIORITIES

1. Inspect repository and verify current checkpoint.
2. Replace the development-only, path-specific launcher
   with a properly portable installer and runtime layout.
3. Integrate accurate checkupdates-based Arch/CachyOS
   detection into the distributable installation.
4. Implement real server-side administrator authentication:
   - HttpOnly cookies
   - Secure and SameSite attributes
   - Session expiration
   - Logout and server-side invalidation
   - CSRF protection
   - Appropriate security regression tests
5. Validate server and agent restart persistence.
6. Validate installation, upgrades, rollback, and backups.
7. Continue portable server/agent packaging and GUI/CLI
   configuration parity.
8. Update documentation after each major milestone.

Support user-supplied and automatically managed TLS
certificates, with correct hostname/IP SAN handling,
without hard-coded homelab-specific addresses.

## TESTING AND GIT WORKFLOW

Use local tests only.

Prefer targeted tests followed by broader verification
when appropriate.

Never claim tests passed unless they actually ran.

Keep large development batches coherent and reviewable.

Do not commit or push without the user's approval.

Stage only intended files; exclude local secrets, state,
backups, and temporary artifacts.

After approved commits, update the documentation and
next-session handoff with the new commit identifier.

## COMMUNICATION STYLE

Be concise, practical, and proactive.

The user enjoys occasional Star Trek/Spaceballs humor,
but working code takes priority over speeches.

Avoid unnecessary back-and-forth.

Deliver usable, complete solutions.

## START HERE

Check the current repository, read the Versionary
documentation, verify the latest code, and proceed
with the next safe local development batch.

Do not repeat registration or enrollment unless required.
