# Patch Command

> **This is a total AI slop project.** The application, tests, documentation, and much of the development process have been produced with AI assistance under human direction. This disclosure is intentional, not a quality certification. **Do not assume the code is secure, correct, maintained, or production-ready because it has tests.** Independently review and validate it before trusting it with infrastructure.

**Status: experimental development / observer-only. Not approved for production rollout.**

Patch Command is an experimental, self-hosted Linux patch-visibility platform. Its goal is to display update availability and agent health across a small fleet without automatically installing updates or rebooting machines.

## What exists today

- FastAPI server with legacy read-only local and SSH-based package-update endpoints.
- SQLite-backed agent registry, approval/revocation, authenticated heartbeat and scan-reporting components.
- Staged agent enrollment/reporting workflows, disabled by default on live systems.
- Read-only agent inventory API and fleet dashboard at `/admin/dashboard`.
- Staged administrator settings at `/admin/settings`; saved settings are **not** a deployment or automatic activation.
- Agent package builder, isolated installation, integrity audit, read-only preflight, disposable HTTPS protocol acceptance, and beta evaluation.
- Arch Linux and Debian agent targeting. Production agent installation is intentionally **disabled**.

The user interface uses the name **Patch Command**. Some internal paths, identifiers, environment variables and service names still use legacy names for compatibility. Do not rename these casually.

## Start here

- [User manual](docs/USER-MANUAL.md) — supported operations, commands, limitations, and troubleshooting.
- [Current project handoff](PROJECT-STATUS.md) — current development checkpoint, architecture, safety constraints, and next milestones.
- [Beta evaluation](BETA-EVALUATION.md) — isolated candidate evaluation.
- [Deployment gate](docs/DEPLOYMENT-BETA-GATE.md) — conditions before any real deployment.
- [Runtime visibility](docs/RUNTIME-VISIBILITY.md) — feature-gate behavior.
- [Isolated release recovery](docs/RELEASE-SWITCH-TRIAL.md) — interrupted code-release trial inspection and explicit recovery.
- [Installation snapshots](docs/INSTALLATION-SNAPSHOT.md) — experimental private asset snapshots, verification, and current restoration limitations.
- [Independent-process recovery trial](docs/RESTART-RECOVERY-TRIAL.md) — disposable fault-injection and recovery across worker processes; not a production rollback engine.

## Local development verification

From a checkout with a working `.venv` and installed project dependencies:

```bash
bash installer/local-check.sh --protocol-check
```

This builds the agent package, runs the Python regression suite, and then runs disposable HTTPS acceptance. The latest **user-reported** checkpoint on 2026-10-30 was **686 tests passed**, plus passing isolated HTTPS acceptance. The subsequent independent-process recovery batch adds six test methods (**692 expected, not yet verified**). These results apply only to the respective checkouts.

To evaluate the beta candidate separately:

```bash
.venv/bin/python installer/beta-evaluate.py --protocol-check
```

Neither command deploys an agent to production. The disposable protocol test uses local loopback network requests.

## Safety and trust

- No unattended package upgrades or automatic reboots are part of the approved operating model.
- Never enable enrollment/reporting gates or expose the service publicly without a separate security review.
- Do not place credentials, private keys, or live database copies in Git.
- No production installation, agent enrollment, systemd activation, or service migration is authorized by a passing test.
- Back up and document rollback before any explicitly approved deployment.

## Repository workflow

Development occurs on feature branches, with review toward `develop`; `main` remains the stable baseline. Hosted CI is intended for deliberate checkpoints rather than automatic runs on every feature push. Local tests are the primary rapid feedback loop.

**AI provenance:** This is a human-directed, AI-authored experimental project. Treat its outputs and documentation as unverified until independently checked. Contributions and audits are welcome, but no warranty or fitness for operational use is implied.

## Versionary naming and latest local checkpoint (2026-10-30)

**Versionary** is the selected future product name; legacy Patch Command identifiers remain for compatibility pending a planned migration. The user-reported **local desktop** checkpoint is **974 unittest cases, OK (1 skipped)**, with six real loopback-HTTPS tests passing and a passing disposable `installer/beta-selftest.py --protocol-check` run. **These local changes and counts are not guaranteed present in this remote branch**. Do not infer deployment readiness from them.

**Start the next session with [the detailed Versionary handoff](docs/VERSIONARY-SESSION-HANDOFF-2026-10-30.md).** Before syncing, compare the local working tree and remote feature branch; preserve local uncommitted code, credentials and state. The older historical checkpoints elsewhere in this README refer to earlier remote development.
