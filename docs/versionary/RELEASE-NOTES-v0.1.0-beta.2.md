# Versionary v0.1.0-beta.2 — release notes (prepared, not yet published)

**Status:** Publication pending. Do not treat this document as confirmation that a GitHub release or tag exists. This is an experimental, observer-only release for **fresh disposable Arch/Debian virtual machines**, not production.

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
- Archive/manifest verifier: PASS; **160 files**.
- **Fresh-VM end-to-end installation for beta.2 has not yet been performed.** The operator plans to test after publication.

## Planned release assets (upload all four)

- `versionary-v0.1.0-beta.2.tar.gz`
- `versionary-v0.1.0-beta.2-manifest.json`
- `versionary-v0.1.0-beta.2-agent.tar.gz`
- `SHA256SUMS`

The pinned server archive SHA256 from the locally verified candidate is:

`f7d73fa56dd0b064d9d09c35b415d6573947b5cd8c38161f5930d513ea768f7e`

**Critical:** Release publication must use the exact locally verified assets, and the two root-level installer wrappers must be committed on `main` with `TAG=v0.1.0-beta.2` and the matching `PIN` before users fetch the wrapper URLs. The release archives live on the operator's workstation and cannot be uploaded through the current GitHub connector.

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
