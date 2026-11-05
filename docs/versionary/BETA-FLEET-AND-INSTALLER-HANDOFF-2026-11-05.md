# Versionary — Real-VM beta milestone and installer development handoff

Date: 2026-11-05. Branch: `feature/versionary-agent-rename` in `broncbash/arby-patch-command`.

## Confirmed live beta milestone

- Server: disposable Arch VM `192.168.122.75:8766`, isolated HTTPS beta, dashboard operational.
- Arch agent: disposable VM `192.168.122.132`; installed, registered, approved, enrolled, heartbeat `ok`, scan `success`, report `recorded`, 0 packages.
- Debian agent: Debian 13 VM `192.168.122.69`; installed, registered, approved, enrolled, heartbeat `ok`, scan `success`, report `recorded`, 0 packages.
- Server has `VERSIONARY_BETA_ENROLLMENT=true` and `VERSIONARY_BETA_REPORTING=true` in a systemd drop-in.
- All three VMs are powered off after the successful trials. Do not assume they are online.
- Agent systemd timers remain disabled. No automatic patch installation was tested or enabled.

## Observed installation problems

1. Debian lacked `curl` and Python `cryptography`; `apt-get install` resolved these.
2. Verified distribution, CA, and release scripts had to be transferred separately.
3. SSH heredoc with `ssh -t` could not prompt for `sudo` password.
4. Offline installer requires a private **root-owned** staging root; user-owned `mktemp` failed `Unsafe installation root`.
5. The actual system installer intentionally stops with `InstallationNotImplemented`; beta installation required manual staging and copy into `/`.
6. Registration, admin approval, enrollment, heartbeat, and reporting were separate manual operations.
7. The server CA was root-protected; non-root `curl --cacert` failed, while `sudo curl` succeeded.

## Development objective

One guided server installer and one guided agent installer, supporting interactive and scriptable operation. Detect Arch and Debian, offer dependency installation with explicit approval, verify distribution and CA, preserve existing credentials on reinstall, install and enable appropriate systemd units only after successful enrollment, and avoid hard-coded VM addresses. Retain manual admin approval and verified HTTPS; never enable unattended package upgrades.

## New prototype

`installer/versionary-beta-agent-bootstrap.sh` is a **disposable-VM-only prototype**, not a production-ready installer. It combines dependency checks, verified preflight, root-owned staging, installation, and registration. `complete` finishes enrollment, heartbeat, and one report after admin approval. It intentionally does not auto-enable the timer. It has not been run on a VM yet.

## Next acceptance gates

- Review and test prototype on freshly reinstalled Arch and Debian VMs.
- Add safe partial-install recovery and upgrade/reinstall handling; current prototype refuses existing destinations and may leave partial installation after copy failure.
- Add guided approval polling with timeout and clear errors; no secrets printed.
- Replace prototype with an atomic, supported real-system installer; remove the manual copy workaround.
- Implement server installer with certificate management, persistent state and systemd setup.
- Confirm unattended periodic observer-only reporting and clean rollback.

## Repository hygiene

No commit, push, merge, or PR update without explicit user approval. Preserve all existing untracked local files and work. Avoid live Proxmox CT 102/104. Do not represent this prototype as deployed or tested.
