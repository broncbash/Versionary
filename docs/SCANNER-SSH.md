## Portable SSH transport configuration (development)

The legacy APT and Arch SSH scanners now share `scanner_ssh_config.py`.
If `ARBY_SCANNER_SSH_CONFIG_PATH` is unset, the original scanner identity,
known-hosts file, and SSH user are preserved for migration compatibility.
When explicitly set, the path must point to a private regular JSON file.
Missing, malformed, public, or symlinked configuration fails closed before
starting SSH. The scanner returns an error status rather than falling back.

Example (replace with your own paths and restricted SSH user):

```json
{
  "identity_file": "/etc/patch-command/ssh/scanner_ed25519",
  "known_hosts_file": "/etc/patch-command/ssh/known_hosts",
  "username": "patch-scanner"
}
```

Store this file with mode 0600, then set
`ARBY_SCANNER_SSH_CONFIG_PATH=/etc/patch-command/ssh.json` in a **development**
service environment. The identity and known-hosts paths must be absolute and
normalized; SSH user input is restricted to a safe character set. The scanner
still enforces `StrictHostKeyChecking=yes`, `BatchMode=yes`, and
`IdentitiesOnly=yes`.

This is transport *configuration*, not credential creation or host-key
enrollment. Operators must provision their SSH keys and known-hosts trust
separately. No live service or production configuration has been changed.

## Read-only preflight CLI

Use `python3 installer/scanner-preflight.py` to inspect effective scanner
configuration **without connecting to any host**. It reads and validates the
inventory and SSH configuration, prints JSON, and returns exit code 0 when
both configurations validate or 1 when either fails. The output includes
configured target labels, hostnames, platform types, and the SSH username,
but never reveals identity-file or known-hosts file paths.

For isolated tests, pass `--inventory-path /path/to/inventory.json` and
`--ssh-path /path/to/ssh.json`. Those explicit paths override the corresponding
environment variables. A valid preflight means the configuration format is
valid; it does **not** establish that an SSH key exists, that host trust is
provisioned, or that any remote machine is reachable.
