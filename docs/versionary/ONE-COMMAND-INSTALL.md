# One-command Versionary beta server install

**Controlled beta only. Use a new disposable systemd VM on a trusted private network.** The existing v0.1.0-beta.1 release assets are used unchanged; the guided wrapper performs downloads, pinned SHA-256 verification, manifest checks, dry-run, install, and service setup.

On a fresh Arch/Debian VM with curl, Python 3 (venv/pip), sudo and systemd:

```bash
curl -fL -o install-versionary.sh https://raw.githubusercontent.com/broncbash/Versionary/main/install-versionary.sh
bash install-versionary.sh
```

The installer detects one active IPv4 address or prompts for the desired server IP, confirms disposable installation, and offers optional beta enrollment/reporting. It prints the dashboard URL and locations of the CA and administrator token (never the token itself).

Noninteractive disposable-VM usage:

```bash
bash install-versionary.sh --address 192.168.122.83 --beta-fleet --yes
```

`--yes` authorizes installation on a **fresh disposable VM**, not production. `--beta-fleet` only enables agent enrollment and observer-only reports. No package updates or unattended reboots are enabled. No production deployment is approved.

The wrapper refuses existing/partial installations rather than overwriting state. If installation fails, inspect service logs and preserved state; never blindly delete or reinstall. The CA must be securely transferred to agent hosts, and agent approval is still manual. The agent guided installer remains `installer/versionary-agent-guided-install.sh` inside the verified release tree; the agent experience still needs a similarly streamlined wrapper.

This script is a **source-level installer improvement**, not a newly built or republished GitHub release. It has not yet completed a fresh-VM end-to-end acceptance run.
