# Versionary beta onboarding and update-count verification

## What the switches mean

- **Enable beta enrollment**: allow agents to request registration. Each new agent remains pending until an administrator approves it in the dashboard. No automatic approvals.
- **Enable observer-only reporting**: allow approved agents to send heartbeats and read-only update scan results. This does not install updates, run commands, reboot machines, or schedule unattended upgrades.
- **Enable daily timer (agent)**: opt into daily scan/report attempts. The agent never installs patches.
- **Install missing dependencies**: permit the system package manager to install scanner prerequisites; this is separate from Versionary patch management. On Arch, prerequisite installation may update existing system packages because pacman must avoid partial upgrades.

## CA onboarding (next packaged server release)

The server exposes only its PUBLIC CA certificate at `/api/v1/bootstrap/ca`. This is not an authenticated identity proof. On the SERVER console run:

```bash
sudo openssl x509 -in /var/lib/versionary/certs/ca.crt -noout -fingerprint -sha256
```

On the AGENT, the guided installer can discover a server and request the SHA256 fingerprint. Enter the fingerprint obtained independently from the server console (or a previously trusted channel). It downloads the public CA, verifies the fingerprint, then checks HTTPS with that CA. Never copy `ca.key` or `server.key`, and never accept a fingerprint obtained solely from the unverified discovery response.

For the **currently published beta.1 server**, the CA endpoint is not available. Use `--ca-cert /path/to/verified/ca.crt` until a new server release is built and installed. The GitHub source changes do not hot-update installed VMs.

## Verify reported update counts

The dashboard's zero count is not proof that package metadata is fresh. Versionary's Arch scanner uses `checkupdates` (pacman-contrib) and Debian uses `apt list --upgradable` against locally known package indexes. To compare manually:

```bash
# Arch agent
checkupdates; rc=$?; test "$rc" -eq 0 -o "$rc" -eq 2
# Debian agent
apt list --upgradable
```

Run the local read-only scanner to compare with the dashboard:

```bash
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system scan
```

The CLI's actual scan subcommand and syntax should be confirmed against `--help` before using it; if absent, use `python3 /opt/versionary-agent/agent/versionary_agent.py --scan` after checking the installed file path. Refreshing APT metadata with `apt update` changes local package indexes but does not install package upgrades. Versionary does not do this automatically.

## Remaining release gates

- Syntax and unit tests for installer changes, including a minimal Debian VM without sudo/curl and a clean Arch VM.
- End-to-end CA bootstrap with a genuine independently verified fingerprint; reject mismatches and hostile discovery responders.
- Build a new immutable release with the updated server CA endpoint and scanner diagnostics; beta.1 assets remain unchanged.
- Verify dashboard update counts match agent scans with controlled available updates.
- Provide browser trust instructions or a local certificate installation helper without bypassing HTTPS validation.
