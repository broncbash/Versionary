# Versionary — Quick Start (v0.1.0-beta.1)

**Goal:** bring up one isolated HTTPS Versionary server and one approved Linux agent, then see an update report in the dashboard. This guide is for **fresh, disposable VMs only**, not production. No package updates or reboots are performed by Versionary.

> **Beta caveat:** the published, renamed archive/manifest pair has not yet been independently re-tested together with the server installer in a new VM. Perform the dry-run below and stop on any verification error. The installer is not a general-purpose reinstall/upgrade tool.

## Recommended guided installation (new source wrappers, 2026-11-06)

For a fresh disposable server VM, **use this instead of the manual release extraction and multi-command setup documented below**:

```bash
curl -fL -o install-versionary.sh https://raw.githubusercontent.com/broncbash/Versionary/main/install-versionary.sh
bash install-versionary.sh
```

It downloads and verifies the existing beta1 release, determines the server IP, performs dry-run and installation, and optionally enables observer-only beta enrollment/reporting. The old detailed steps below remain for manual recovery and troubleshooting.

For a fresh agent VM, securely obtain the server CA certificate and verify its fingerprint independently, then:

```bash
curl -fL -o install-versionary-agent.sh https://raw.githubusercontent.com/broncbash/Versionary/main/install-versionary-agent.sh
bash install-versionary-agent.sh
```

Both wrappers are source-level improvements not yet part of a repackaged release, and **fresh-VM acceptance remains outstanding**. Do not use on production machines or an existing/partial Versionary installation. See [guided installation details](ONE-COMMAND-INSTALL.md).

## What you need

- Two fresh systemd Linux VMs on a trusted, reachable private network: one **server** and one **agent**. Server installation has been exercised on disposable Arch; previous fleet tests covered Arch and Debian agents, but the guided agent installer has been live-tested on Arch only.
- Root/sudo access to each VM, Python 3 and basic archive tools. Server needs working Python `venv`, `pip`, internet access for `requirements-baseline.txt`, `useradd`, `runuser`, and systemd. Agent needs Python cryptography, curl and the distro's scanner; `--install-deps` can authorize supported dependency installation.
- A **fixed reachable server IP**, substituted for `SERVER_IP` below. Use a private IP on the server VM itself, **not** `0.0.0.0`. Port 8766 must be reachable from the agent VM.
- Public GitHub release (no sign-in required to download): https://github.com/broncbash/Versionary/releases/tag/v0.1.0-beta.1 .
- Never copy server private keys, administrator token or agent credentials into chat, public files or release assets.

## 1. Download and verify release assets

Download these four files into a single folder on the **server VM** (directly over HTTPS, no GitHub account required):
- `versionary-v0.1.0-beta.1.tar.gz`
- `versionary-v0.1.0-beta.1-manifest.json`
- `versionary-v0.1.0-beta.1-agent.tar.gz`
- `SHA256SUMS`

Using `curl` on the fresh VM:

```bash
mkdir -p "$HOME/versionary-beta1"
cd "$HOME/versionary-beta1" || exit 1
BASE='https://github.com/broncbash/Versionary/releases/download/v0.1.0-beta.1'
for file in versionary-v0.1.0-beta.1.tar.gz \
            versionary-v0.1.0-beta.1-manifest.json \
            versionary-v0.1.0-beta.1-agent.tar.gz SHA256SUMS; do
  curl --fail --location --show-error --output "$file" "$BASE/$file" || exit 1
done
sha256sum -c SHA256SUMS
```

**Stop** unless every checksum passes. Expected main archive SHA256: `4309194d3d993a0a7d1c238d0ac514963b53c80afd5263c304f36a11dc26542a`. Expected agent archive SHA256: `936fc9c05e7b7f6d4b4c5aff4805d225da915311594af9e862797d024e76257b`.

Extract the main release archive to a separate directory and enter it:

```bash
mkdir -p "$HOME/versionary-beta1/source"
tar -xzf "$HOME/versionary-beta1/versionary-v0.1.0-beta.1.tar.gz" \
  -C "$HOME/versionary-beta1/source"
cd "$HOME/versionary-beta1/source" || exit 1
```

The commands below assume you remain in this extracted source directory.

## 2. Install the server (disposable VM only)

Choose the **server VM's own fixed private IP**, for example `192.168.122.75`. Replace the placeholder in the following command:

```bash
SERVER_IP=192.168.122.75  # REPLACE with your actual server VM IP
RELEASE_DIR="$HOME/versionary-beta1"
python3 installer/versionary-server-install.py \
  --archive "$RELEASE_DIR/versionary-v0.1.0-beta.1.tar.gz" \
  --manifest "$RELEASE_DIR/versionary-v0.1.0-beta.1-manifest.json" \
  --mode dry-run \
  --tls-identity "$SERVER_IP" \
  --bind-address "$SERVER_IP" --port 8766
```

**Expected:** `DRY_RUN=PASS` and `INSTALL_EXECUTED=NO`. The dry-run checks archive integrity but does not exercise every installation precondition. If it fails, **stop** and diagnose; do not bypass verification.

On a **fresh disposable VM only**, with the intended IP verified and explicit operator approval:

```bash
sudo python3 installer/versionary-server-install.py \
  --archive "$RELEASE_DIR/versionary-v0.1.0-beta.1.tar.gz" \
  --manifest "$RELEASE_DIR/versionary-v0.1.0-beta.1-manifest.json" \
  --mode install --confirm-disposable \
  --tls-identity "$SERVER_IP" \
  --bind-address "$SERVER_IP" --port 8766
```

The installer creates a `versionary` service account, private state at `/var/lib/versionary`, application at `/opt/versionary`, TLS certificates and `versionary-server.service`. It refuses an existing installation. On failure it may preserve partial state and require manual recovery: **do not blindly rerun or delete it**.

## 3. Explicitly enable beta enrollment and reporting

**These are disabled by default.** On the server VM, inspect the generated service configuration first:

```bash
sudo systemctl cat versionary-server.service
sudo systemctl status --no-pager versionary-server.service
```

For this isolated beta test only, use a systemd drop-in to enable the two opt-in gates:

```bash
sudo install -d -m 755 /etc/systemd/system/versionary-server.service.d
printf '%s\n' '[Service]' \
  'Environment=VERSIONARY_BETA_ENROLLMENT=true' \
  'Environment=VERSIONARY_BETA_REPORTING=true' \
  | sudo tee /etc/systemd/system/versionary-server.service.d/beta-fleet.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart versionary-server.service
sudo systemctl is-active versionary-server.service
```

Keep `VERSIONARY_DISTRIBUTION_ENABLED=false`. These changes deliberately authorize **enrollment and observer-only reporting**, **not** package installation or unattended patching. Do not expose the server to the public internet.

Confirm health with the **server's own CA** (no `-k` / insecure TLS bypass):

```bash
curl --cacert /var/lib/versionary/certs/ca.crt \
  "https://$SERVER_IP:8766/health"
```

Expected JSON includes `"status":"online"`, `"mode":"isolated-https-beta"`, `"production":false`.

## 4. Open the dashboard and obtain the CA

Open in your browser:

```text
https://SERVER_IP:8766/admin/dashboard
```

The generated administrator token is stored privately on the server at `/var/lib/versionary/admin-token`. Read it **locally and privately** for dashboard authentication; do not paste it into chat, logs or documentation. A browser that does not yet trust the generated CA may show a certificate warning; install/trust the CA properly instead of disabling TLS verification.

The **public CA certificate** is normally:

```text
/var/lib/versionary/certs/ca.crt
```

Securely transfer **only** that CA certificate and the agent release archive to the agent VM, verifying the CA's identity/fingerprint through a trusted channel. Do **not** transfer `ca.key`, `server.key`, the admin token, or agent credential files.

## 5. Prepare the agent VM

On the **agent VM**, obtain the same verified main release archive (for the guided installer scripts) and the verified agent archive, then extract the main archive as in step 1. Place the server's CA certificate at a known absolute path, for example `$HOME/versionary-beta1/ca.crt`.

For Arch/CachyOS, the guided installer can install missing `python`, `python-cryptography`, `curl`, `ca-certificates`, `pacman-contrib` **only if** you explicitly add `--install-deps`. For Debian/Ubuntu it can install `python3`, `python3-cryptography`, `curl`, `ca-certificates` with the same opt-in. That flag authorizes dependency package installation, not Versionary patch deployment. Other distributions are not supported by this dependency automation.

From the **extracted release directory** on the agent VM, set your real server URL and CA path:

```bash
SERVER_URL="https://192.168.122.75:8766"  # REPLACE with real server VM IP
AGENT_ARCHIVE="$HOME/versionary-beta1/versionary-v0.1.0-beta.1-agent.tar.gz"
CA_CERT="$HOME/versionary-beta1/ca.crt"
sudo bash installer/versionary-agent-guided-install.sh \
  --distribution "$AGENT_ARCHIVE" \
  --ca-cert "$CA_CERT" \
  --server "$SERVER_URL"
```

If the installer reports missing dependencies, review the requested packages and rerun with `--install-deps` **only if authorized**. You may instead omit all flags and answer its interactive prompts. **Do not use `--enable-timer` unless you want the optional daily observer-only reporting timer.**

The guided installer detects an existing installation and refuses incompatible server reconfiguration. It registers the new agent as pending and waits up to about **10 minutes** for approval.

## 6. Approve enrollment

While the agent installer waits, open the server dashboard at `https://SERVER_IP:8766/admin/dashboard`. Find the **pending** agent and approve it. Return to the agent terminal. The installer should enroll, send a heartbeat and attempt the first update report. If the report fails, check scanner dependencies and retry manually.

If approval takes longer than 10 minutes, preserve the installed identity and configuration. After approval, rerun the guided installer; it is designed to recognize existing state rather than re-register blindly.

## 7. Verify the agent and report

On the **agent VM**:

```bash
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system status
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system heartbeat
sudo python3 /opt/versionary-agent/versionary_agent_cli.py --system report
```

Refresh the server dashboard. Confirm the agent appears, has a recent heartbeat and shows its package-update inventory. A report of **zero updates** can be legitimate.

The reporting timer is **disabled by default**. To opt in later, after confirming enrollment and reporting work:

```bash
sudo systemctl enable --now versionary-agent.timer
sudo systemctl status --no-pager versionary-agent.timer
```

This timer performs observer-only reporting; it does not apply updates.

## Quick troubleshooting

| Symptom | Check |
|---|---|
| `sha256sum` mismatch | Stop. Redownload from the authorized GitHub release. Never disable verification. |
| `DRY_RUN` fails | Confirm both archive and manifest are from the same release and inspect error. Do not force install. |
| Server installer refuses | Fresh VM required; check systemd, existing `versionary` user, application/state paths, bind IP, `venv`, and pip. Preserve any partial state. |
| Server not reachable | `systemctl status versionary-server.service`, firewall/network reachability, correct server IP and port. |
| TLS error | Use the correct server CA and matching hostname/IP SAN; never use insecure TLS flags. |
| Agent remains pending | Confirm enrollment/reporting gates and approve it in the dashboard. |
| `checkupdates` missing on Arch | Install `pacman-contrib` after authorization or use guided installer `--install-deps`. |
| Debian agent dependencies missing | Ensure `python3-cryptography`, `curl` and CA certificates are installed. |
| Report fails | Run `--system report`, inspect output, check scanner availability and server reporting gate. |
| Timer not running | Timer is off by design until explicitly enabled. |
| Existing/partial installation | Do not delete private state or blindly reinstall; inspect first. |

## Security and current limitations

- This is a **controlled beta**, not production-approved. Public release downloads do not require GitHub authentication.
- Enrollment and reporting require explicit administrator opt-in. Every new agent requires approval.
- Versionary **does not automatically install package updates or reboot machines**.
- Server installer uses a fresh-state model; recovery/upgrade workflows are not production-ready.
- Guided agent installer was accepted on a disposable Arch VM; broader distro testing remains on the roadmap.
- Some product capabilities, including certificate management GUI, discovery, upgrade/uninstall UX and administrator-triggered patch installation, are **planned**, not shipped.
- For exact implemented flags and planned switches, see [COMMAND-REFERENCE.md](COMMAND-REFERENCE.md). For future work, see [ROADMAP.md](ROADMAP.md).

**Success criterion:** the HTTPS health endpoint returns online, the dashboard loads, the approved agent appears, and the agent's initial update report is visible. No package updates or reboots have been executed by Versionary.
