# Patch Command — Comprehensive Project Handoff

**Checkpoint date:** 2026-10-30  
**Repository:** `broncbash/arby-patch-command` (private)  
**Development branch:** `feature/runtime-visibility`  
**Integration target:** `develop` (draft PR #1); `main` remains baseline  
**Deployment status:** experimental development; **no production rollout authorized**

> **Provenance:** This is a total AI slop project: predominantly AI-generated code, tests and documentation, directed and checked by a human operator. Passing automated tests does not constitute an independent security audit or production endorsement.

## Mandatory handoff procedure

1. Inspect the **actual remote branch head, tree, and relevant source** before editing. This document is a snapshot, not authority over later commits.
2. Read `README.md`, `docs/USER-MANUAL.md`, and the relevant technical docs.
3. Develop substantial coordinated batches directly on the feature branch; avoid excessive interactive checkpoints.
4. Commit changes to the feature branch; **do not merge, deploy, restart services, or enable network gates without approval**.
5. Give one local copy/paste verification command and wait for the operator's actual results. Do not claim tests passed if only code was committed.
6. Update this handoff and manual when behavior changes.

## Current verified checkpoint

**Latest operator-verified result:** On 2026-10-30, the Arch/CachyOS desktop reported **686 tests passing in 7.685 seconds**, plus passing isolated beta HTTPS acceptance, TLS protocol check, and package integrity audit. No production installation, systemd service start, agent enrollment, or external network requests. Verified through commit `615b152`; subsequent independent-process recovery commits remain **unverified**.

**Latest unverified development:** Independent-process disposable recovery trial, `installer/restart-recovery-trial.py`, six new test methods, and documentation, through commit `3cc4f9f`. **Expected next count: 692, not yet confirmed.** The recovery trial terminates one worker and launches another in a parent-owned temporary directory; it is not a production installer or proof of crash/power-loss safety.

**Desktop maintenance interruption:** User paused development to install Arch/CachyOS updates. Immediately before maintenance, `ssh -T git@github.com` returned `Permission denied (publickey)` and `ssh-add -l` returned `Could not open a connection to your authentication agent.` Likely SSH agent/session issue, but cause is **not yet established**. Suggested first diagnostic: `eval "$(ssh-agent -s)"`, then inspect available keys and load the existing key if needed. Do not generate or replace keys prematurely. The GitHub connector remains available for repository work independently of the desktop SSH session.

**Local verification command:**

```bash
cd ~/Projects/arby-patch-command && git pull --ff-only && bash installer/local-check.sh --protocol-check
```

Full unittest log defaults to `/tmp/arby-tests.log`. Hosted CI is manual/checkpoint-oriented; avoid triggering GitHub Actions casually.

## Architecture and implementation

**Server:** FastAPI `main.py` with health endpoint, legacy local/SSH update scanner endpoints, agent-related routers, admin inventory and browser UI. Legacy endpoints are still present while the agent architecture matures.

**Persistence:** SQLite registry in `agent_registry.py` stores agents, states, reports, and credential hashes. Existing deployment uses a legacy data path; tests use disposable databases. Never overwrite a live database or copy secrets into Git.

**Agent:** Python package under `agent/`; identity, credential handling, registration/enrollment, heartbeat, scan and reporting modules. Targets Arch and Debian. Ed25519 challenge/response and trusted TLS are exercised in isolated protocol tests.

**Administrator surface:** `admin_agents_api.py` exposes read-only `/api/v1/admin/agents`, requiring admin auth. `dashboard_ui.py` provides `/admin/dashboard`, with online/attention counts, update totals, agent health, search/filter/sort. `settings_ui.py` provides `/admin/settings`, with staged settings and runtime visibility. Tokens are entered for API requests rather than intentionally persisted by the page.

**Health classification:** approved agents with a valid recent heartbeat (within 30 minutes) are online; stale/no-contact/unknown cases are distinct. Pending and revoked states are not reported as online. Invalid or future timestamps must not be treated as healthy.

**Settings:** `server_settings.py`, `server_settings_api.py`, `runtime_configuration.py`, `runtime_status_api.py` and installer CLI tools provide validation, staged persistence and fail-closed visibility. Settings alone never grant production activation. Legacy environment gates remain part of compatibility and must not be bypassed.

**Certificates:** `certificate_management.py`, `certificate_renewal.py`, `installer/manage-certificates.py` and generation helpers provide offline certificate handling. They do not imply live TLS termination, automatic CA rotation, or proxy reload.

**Installation:** `installer/build-agent-package.py`, `validate-package.py`, `install-files.py`, `install-ca.py`, `setup-config.py`, `install-systemd.py`, `stage-beta.py`, `audit-test-install.py`, `agent-preflight.py`, `deployment-readiness.py`, `beta-selftest.py`, and `beta-evaluate.py` support packaging, secure filesystem operations, inert staging and disposable verification. `installer/install-agent.sh --install` remains **disabled**.

**Security design:** restrictive private directories, non-following file operations, validated archive contents, atomic release and integrity mechanisms, staged certificate validation, explicit agent approval and credential revocation. These are engineering intentions with automated tests, **not** an independent security certification.

## Homelab deployment boundary

- Proxmox VE 9 mini PC; current live service on **CT104** (Arch Linux).
- **CT102** (Arch Linux) runs monitoring and has legacy integration.
- CT100 Debian DNS; CT101 Debian Docker; CT103 Arch Tailscale subnet router.
- The new feature branch is **not** presumed installed on any of these.
- **Never modify CT104 or CT102 without explicit operator approval.** Do not silently change other live containers either.
- No unattended package upgrades, automatic reboots, unsolicited agent enrollment, or automatic service restarts.

## Product and naming decisions

The public-facing product name is **Patch Command**, with restrained professional UI styling. Do not reintroduce the older branding or aesthetic terminology in visible UI, messages, or new code. Some old internal identifiers, paths, service unit names, environment variables and persisted settings values must remain until a deliberate compatibility migration is designed and tested. Use neutral language in new code where feasible.

The repository must **clearly disclose AI authorship**. The README includes the user's exact requested wording, alongside an explicit caution that independent review is required. Avoid pretending the project has been professionally audited.

## Development milestones completed

- Registry, agent approval/revocation, token/credential lifecycle, heartbeat and report storage.
- Feature-gated agent API and staged settings/runtime-status interfaces.
- Offline certificate import/inspection/renewal foundations.
- Package builder and archive validation, private-state-safe installer components, atomic release handling and filesystem hardening tests.
- Isolated beta staging, repeated-installation integrity audit, and disposable loopback TLS enrollment/reporting acceptance.
- Authenticated read-only agent inventory and professional fleet dashboard, including search/filter/sort and conservative health indicators.
- Offline beta evaluation wrapper and user-reported 655-test checkpoint.
- Fixed flaky shell-installation regression that depended on external package repository availability.

Historical docs such as `BUILD3-NOTES.md` describe earlier milestones; **do not treat their old branch names or outstanding-task lists as current**.

## Latest verified installation-safety checkpoint

On 2026-10-29 the operator confirmed **655 regression tests passed** and isolated HTTPS acceptance passed (TLS, package integrity). No production installation, systemd start, agent enrollment, or external network requests occurred. Last source commit included in this verification: `0cc1f8f`.

Recent verified features:
- Read-only beta installation planning: `installer/beta-install-plan.py`.
- Disposable install trial: `installer/disposable-install-trial.py`.
- Isolated code-release switch, durable recovery marker, and operator-controlled recovery: `installer/release-switch-trial.py`, `installer/release-recovery.py`, `installer/recover-isolated-release.py`.
- Read-only asset inventory: `installer/installation-inventory.py`.
- Private snapshot creation and verification: `installer/installation-snapshot.py`; configuration, public CA, and inactive systemd unit files only. **No snapshot restoration yet.** Private credentials and state are excluded.
- Tests: `tests/test_release_recovery.py`, `tests/test_recover_isolated_release.py`, `tests/test_installation_inventory.py`, `tests/test_installation_snapshot.py`.
- Docs: `docs/BETA-INSTALL-PLAN.md`, `docs/DISPOSABLE-INSTALL-TRIAL.md`, `docs/RELEASE-SWITCH-TRIAL.md`, `docs/INSTALLATION-INVENTORY.md`, `docs/INSTALLATION-SNAPSHOT.md`.

**Operator-verified checkpoint (2026-10-30):** 662 tests passed in 7.638s, isolated beta HTTPS acceptance passed, TLS protocol check passed, package integrity verified, no production installation, no systemd start, no agent enrollment, and no external network requests. The verified batch added in `installer/restore-installation-snapshot.py`, with regression tests in `tests/test_restore_installation_snapshot.py` and documentation in `docs/INSTALLATION-SNAPSHOT.md`. This is not an in-place rollback; verification covers the reported local regression and isolated beta acceptance only. **Next batch after verification:** review failure behavior and design coordinated release/configuration/CA/systemd rollback. Do not deploy, merge, or touch CT104/CT102 without explicit permission. Snapshots do not constitute complete backups or authenticated trust anchors.

## Outstanding work — prioritized

1. **Controlled beta installer:** implement a reviewed, explicit installation transaction, dependency preflight, durable backup/rollback, idempotent reinstall and safe service lifecycle. Do not simply enable the current `--install` switch.
2. **Approved end-to-end enrollment:** clean disposable Arch/Debian container trial with HTTPS trust, manual approval, authenticated heartbeat/reporting, and revocation, all with clear audit evidence.
3. **Production-safe server setup:** supported TLS termination, configuration/apply semantics, admin authentication hardening, secrets management, migration and rollback.
4. **Fleet operations:** safe agent discovery/onboarding design, approval UI, richer operational failure states and documentation.
5. **Compatibility cleanup:** staged migration away from legacy identifiers and paths, with backward-compatible upgrade tests.
6. **Independent security review:** threat model, privilege analysis, filesystem/SQLite race conditions, token exposure, CA trust lifecycle, authorization boundaries, dependency and supply-chain review.
7. **Release readiness:** clean installation on supported distributions, upgrade/uninstall procedures, recovery testing, reproducible packaging and user documentation.

## GitHub workflow ownership\n\nThe assistant manages development branches, commits, and pull request preparation. The operator does not need to manipulate branches or merges manually. **No merge to develop/main without explicit operator approval.** The operator runs the single local verification command and reports results.\n\n## Latest unverified development batch (2026-10-30)\n\nAfter the operator-verified 662-test checkpoint, additional commits hardened snapshot manifest mode/metadata validation, added three regression cases, and created `docs/COORDINATED-ROLLBACK-DESIGN.md`. These new commits are **not yet operator-tested**. The next implementation milestone is a read-only coordinated rollback planner and disposable fault injection, not a live installer.\n\n## Latest operator verification (2026-10-30)\n\nThe operator reported **665 tests passed in 7.660s**, `[Patch Command] PASS`, and isolated beta HTTPS acceptance `status: passed`, `tls_protocol_check: passed`, `integrity_audit: verified`, `production_installed: false`, `systemd_started: false`, `agent_enrolled: false`, `external_network_requests_made: false`. This covers the snapshot manifest hardening and syntax correction through commit `e194986`. The read-only coordinated rollback planner is the next development target.\n\n## Latest unverified development batch — read-only rollback planning

Following the operator-verified **665-test** checkpoint (through `e194986`), a read-only isolated rollback planner was added at `installer/rollback-plan.py`, with nine new regression tests at `tests/test_rollback_plan.py` and documentation at `docs/ROLLBACK-PLAN.md`. The planner compares allowlisted configuration, CA and systemd assets with a verified snapshot; reports create/replace/remove/unchanged and blockers; never applies changes or reads private credentials. **These changes have not yet been verified by the operator.** No production installation or service lifecycle is enabled. Future work: disposable coordinated fault-injection and review of filesystem races, followed by separately approved installer transaction design.

## Operator-verified rollback planner checkpoint (2026-10-30)\n\nOperator reports **674 tests passed in 7.702s**, `[Patch Command] PASS`, isolated beta HTTPS acceptance passed, TLS protocol check passed, integrity audit verified; production installation, systemd start, agent enrollment, and external network requests remained false. This verifies the read-only rollback planner batch through commit `b7debeb`. Next planned substantial batch: disposable rollback transaction fault-injection and recovery tests, without enabling live installation or touching homelab containers.\n\n## Unverified coordinated transaction modeling batch\n\nAdded `installer/transaction-simulation.py`, `tests/test_transaction_simulation.py`, and `docs/TRANSACTION-SIMULATION.md`. This is an **in-memory** state-machine/fault-injection model across release/config/CA/service/timer, **not** a durable filesystem transaction or rollback. Six new unittest methods (one with checkpoint subtests); no production changes. Operator verification pending. Next major work is a disposable filesystem transaction prototype with durable journal and crash recovery, subject to careful safety review.\n\n## Operator-verified transaction model checkpoint (2026-10-30)\n\nThe operator reported **680 tests passed in 7.693s**, isolated beta HTTPS acceptance passed, TLS protocol check passed, package integrity verified; no production installation, systemd start, agent enrollment or external network requests. This verifies the in-memory coordinated transaction simulation batch through commit `4892f91`. Next major development milestone: disposable filesystem transaction and recovery testing, with production gates unchanged.\n\n## Latest unverified filesystem transaction batch\n\nAfter the verified 680-test checkpoint, added `installer/disposable-filesystem-transaction.py`, six regression tests in `tests/test_disposable_filesystem_transaction.py`, and `docs/DISPOSABLE-FILESYSTEM-TRANSACTION.md`. This prototype creates its own temporary filesystem, stages five placeholder asset generations, journals per-file switches, and simulates rollback on injected failure. **It does not implement crash recovery across process restarts or production rollback.** Operator verification pending. No live systems touched, no merge.\n\n## Operator-verified filesystem transaction checkpoint (2026-10-30)

Operator reported **686 tests passed in 7.685s**, with isolated beta HTTPS acceptance, TLS protocol check, and integrity audit passing. No production installation, systemd start, agent enrollment, or external network requests. This verifies the disposable filesystem transaction trial through commit `615b152`. The next task is separately restarted recovery in a disposable root, including journal integrity and interruption tests. Production gates remain closed.

## Unverified independent-process recovery batch\n\nAdded `installer/restart-recovery-trial.py`, `tests/test_restart_recovery_trial.py` (six new test methods), and `docs/RESTART-RECOVERY-TRIAL.md`. A parent-owned disposable directory is used by a switch worker that exits at an injected checkpoint, followed by a separate recovery worker. Tampered journal and backup cases must refuse recovery. This is **not** a production crash-recovery implementation. Operator verification pending; no live changes or merges.\n\n## Next development session

Inspect `feature/runtime-visibility` first. The next milestone is **verify the 692-test checkpoint, then develop interrupted-recovery restart and durability/failure testing in disposable roots**, without touching live systems. Work without touching live systems. Work in substantial batches; provide one local regression command. Do not assume passing disposable tests means the operator approved deployment.

## Reference index

- `README.md` — overview, AI provenance and project entry point
- `docs/USER-MANUAL.md` — current operator manual
- `BETA-EVALUATION.md` — disposable beta workflow
- `docs/DEPLOYMENT-BETA-GATE.md` — explicit production blockers
- `docs/RUNTIME-VISIBILITY.md` — runtime gate behavior
- `docs/AGENT-INSTALL-PREFLIGHT.md` and `docs/AGENT-INSTALL-AUDIT.md` — installation checks
- `docs/RELEASE-READINESS.md` — release-related controls
- `BUILD3-NOTES.md` — historical certificate milestone notes

**Last rule:** GitHub commits are development authorization only. Never equate them with authorization to change live infrastructure.

## Return-to-project checklist (2026-10-30)

1. Read this file and inspect the actual remote branch head before modifying anything.
2. Help restore desktop GitHub SSH authentication if still broken; avoid rotating keys without evidence.
3. Run the single local verification command above once desktop maintenance and SSH access are restored. Expect 692 tests, but rely on actual output.
4. If passing, record the operator-verified checkpoint and proceed with substantial batches of isolated recovery tests.
5. Preserve the GitHub workflow: assistant commits on `feature/runtime-visibility`, no merge to `develop`/`main` without approval; no live CT104/CT102 changes or production deployment without explicit approval.

## Operator-verified independent-process recovery checkpoint (2026-10-30)

Operator reported **692 tests passed in 8.145s**, `[Patch Command] PASS`, and isolated beta HTTPS acceptance `status: passed`. Package built, test CA generated, repeated staging succeeded, integrity audit verified, and TLS protocol check passed. The disposable acceptance exercised local network requests (`network_requests_made: true`) but **no external network requests** (`external_network_requests_made: false`); no production installation, systemd start, or agent enrollment occurred. This verifies the independent-process restart recovery trial batch. Desktop GitHub access was restored following system updates and reboot. Next development: substantial disposable interrupted-recovery restart, durability, and failure-injection testing; no production gates lifted, no CT104/CT102 changes, no merge.

## Unverified expanded restart-recovery hardening batch (2026-10-30)

Following the operator-verified **692-test** checkpoint, hardened `installer/restart-recovery-trial.py` with per-file fsync, parent-directory fsync after atomic renames, strict journal validation, full backup and active-generation preflight, symlink/hardlink refusal, resumable interrupted recovery, and third-process idempotence verification. Added **11 test methods**, including a 5×5 switch/recovery interruption matrix, and `docs/RESTART-RECOVERY-HARDENING.md`. **Expected test count: 703, not yet operator-verified.** This is disposable experimental code only, not a production rollback mechanism. No live CTs modified, no merge, no deployment.

## Operator-verified expanded recovery hardening checkpoint (2026-10-30)

Operator reports **703 tests passed in 12.065s**, `[Patch Command] PASS`, and isolated beta HTTPS acceptance `status: passed`. Package built, test CA generated, repeat staging succeeded, integrity audit verified, and TLS protocol check passed. Network requests were confined to the isolated test (`network_requests_made: true`, `external_network_requests_made: false`); production installation, systemd startup, and agent enrollment remained false. This verifies the expanded restart-recovery hardening batch through commit `933fcca`. **Testing policy:** operator prefers local Arch desktop tests to avoid hosted GitHub testing fees; do not configure GitHub Actions or other hosted runners without approval. Continue larger batches before requesting local verification. No CT104/CT102 changes, deployment, or merge without permission.
