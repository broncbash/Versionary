# Versionary v0.1.0-beta.2 — published prerelease

**Status:** Published on GitHub: https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.2. This is an experimental, observer-only release for **fresh disposable Arch/Debian virtual machines**, not production.

## Changes since beta.1

- Guided server and agent bootstrap scripts prepared for the beta.2 release, with interactive dependency handling and improved root/sudo/su execution.
- Agent LAN server discovery is offered when no server URL is provided.
- Agent CA bootstrap can download the public CA over HTTPS with an **independently obtained and verified SHA-256 fingerprint**. Do not trust a fingerprint delivered over the same untrusted connection.
- Server public CA bootstrap endpoint, dashboard root redirect, and administrator-token newline handling are incorporated into the beta.2 candidate source.
- Verified beta.2 server archive and agent package were assembled locally on 2026-11-06.

## Verification reported by release operator

- Python regression: **1,700 tests, OK (1 skipped)**, on an isolated Python 3.14 environment with baseline requirements plus `httpx2`.
- Both root shell installers: `bash -n` PASS; `git diff --check` PASS.
- SHA256SUMS: server archive, manifest and agent package PASS.
- Archive/manifest verifier: PASS; **159 files**.
- **Fresh-VM end-to-end installation for beta.2 has not yet been performed.** The operator plans to test after publication.

## Published release assets (all four uploaded)

- `versionary-v0.1.0-beta.2.tar.gz`
- `versionary-v0.1.0-beta.2-manifest.json`
- `versionary-v0.1.0-beta.2-agent.tar.gz`
- `SHA256SUMS`

The final published server archive SHA256 is:

`3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b`

**Published confirmation:** The verified four release assets were uploaded successfully. Root wrappers on `main` were committed at `ae16714` and use `TAG=v0.1.0-beta.2` with the matching SHA256 pin. The original 160-file candidate was rebuilt to exclude an untracked disposable-VM helper; the final archive has 159 files.

## Disposable VM smoke test (after publication)

1. On a **fresh** server VM, fetch `install-versionary.sh` from `main`, inspect it, and run it interactively.
2. Confirm archive verification, HTTPS health, generated CA identity, and dashboard login.
3. On fresh Arch and Debian agent VMs, fetch `install-versionary-agent.sh`, independently verify the server CA fingerprint, and run the guided install.
4. Approve pending agents in the dashboard, verify authenticated heartbeat and read-only update reports; optionally enable the observer-only timer.
5. Record any installer failure without deleting state or retrying blindly.

## Safety and limitations

- No production approval; do not install on live homelab CTs or production systems.
- No automatic patch installation, unattended upgrades or reboots by Versionary.
- Installer dependency bootstrap may invoke the OS package manager, including `pacman -Syu` on Arch, **only after explicit operator authorization**. This may upgrade the VM's packages; use disposable targets.
- Enrollment/reporting gates are opt-in; server-side distribution stays disabled.
- Generated CA trust requires independent verification; never use `curl -k` as a trust substitute.
- Installer upgrade, uninstall, rollback, certificate rotation and full GUI/CLI configuration parity are **future work**, not guaranteed beta.2 commands.
- Local untracked project files and VM credentials must not be bundled into release assets.

## Published beta.2 — 2026-11-06 (authoritative release checkpoint)

**Published prerelease:** https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.2. Tag `v0.1.0-beta.2`, source commit `ae16714` on `main`, after documentation PR #15 was merged (`798648f`). The release is **published and downloadable**, but **fresh disposable-VM installation acceptance remains pending**; production deployment is **not approved**.

Four uploaded GitHub release assets: `versionary-v0.1.0-beta.2.tar.gz`, `versionary-v0.1.0-beta.2-manifest.json`, `versionary-v0.1.0-beta.2-agent.tar.gz`, and `SHA256SUMS`. The final server archive contains **159 files**, with SHA256 `3b42b8dfaddf58fa004e1e626314599bf10aa2f8b9c3932b046ded92ecc2fb3b`. Archive/manifest verification and all three checksum entries passed. The local disposable-VM helper `installer/versionary-disposable-vm-install.py` was deliberately excluded from the shipped archive without deleting its untracked local copy. Release GitHub asset metadata confirms the server archive checksum and four uploaded assets.

Local regression checkpoint before packaging: **1,700 tests OK (1 skipped)**. Both root installer scripts on `main` now target `TAG=v0.1.0-beta.2` and pin the final SHA256. The server script accepts `--address`, `--port`, `--beta-fleet`, `--no-beta-fleet`, and `--yes`; the agent script accepts `--server`, `--ca-cert`, `--ca-fingerprint`, `--install-deps`, and `--enable-timer`. Use `--help` for current usage; inspect scripts before running.

**Next session:** fetch/pull remote `main` without disturbing local untracked files, then test the published root wrappers on **fresh disposable Arch server and Arch/Debian agent VMs**, independently verify the server CA fingerprint, approve agents via dashboard, and check HTTPS health, heartbeats, update reports, and optional observer-only timers. Do not deploy to Proxmox CT 102/104 or production hosts. Automatic patch installation and reboots remain disabled. The older beta.1 instructions and dated beta.2 publication-planning paragraphs in this repository are historical; this checkpoint overrides publication status and the old 160-file/old-checksum candidate.
