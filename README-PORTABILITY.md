# ARBY PATCH COMMAND — Portable configuration development build

## Status

**Development preview, not production-ready.** This bundle contains a first coordinated implementation of portable agent settings, local certificate generation, and installer test-mode options. The server Settings GUI, authenticated configuration API, production installer, certificate rotation, and complete end-to-end enrollment are **not yet implemented**. No systemd units are enabled by the test installer.

## Agent configuration

The installed agent reads `/etc/versionary-agent/config.json` at runtime. Required fields:

```json
{"server": "https://patch.example.net:8443", "ca_cert": "/etc/versionary-agent/ca.crt"}
```

The installer refuses to overwrite an existing configuration with different values. Changing a configured server or CA will require an explicit migration workflow (future work).

## Isolated tests

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
bash installer/install-agent.sh --test-install --server https://patch.example.net:8443
bash installer/install-agent.sh --test-install --server https://10.20.30.40:8443
```

`--test-install` generates an ephemeral local CA if `--ca-cert` is omitted. This CA is test-only and deleted with the temporary installation root; it is **not** a running server certificate. You may pass `--ca-cert /path/to/ca.crt` to use your own public CA certificate. `--interactive` prompts for missing inputs when attached to a terminal.

For a manually requested local server certificate and CA:

```sh
python3 installer/generate-certificates.py --hostname patch.example.net --output /path/to/private-output
```

The output directory must be private. **Never upload or distribute `ca.key` or `server.key`.** TLS proxy integration and automatic renewals are future work.

## Safety

`--install` remains intentionally disabled. V2 server router is not included in production `main.py`. No service starts, scheduling, upgrades, or reboots are performed. Do not deploy this development bundle directly over a live installation.

## Open work before release

- Replace legacy V1 reporting with V2-compatible server endpoints and integration tests.
- Implement server-side settings API with admin authorization, audit logging, and safe restart/rollback semantics.
- Build user-friendly GUI Settings and equivalent admin CLI.
- Implement production installation, migration, CA pinning/trust onboarding and rotation.
- Add realistic TLS handshake and end-to-end enrollment tests.

## Build 2: server Settings backend (staging only)

Added `server_settings.py`, `server_settings_api.py`, `installer/settings-cli.py`, and regression tests. The authenticated endpoints are `GET /api/v1/admin/settings` and `PATCH /api/v1/admin/settings`, using the existing `ARBY_ADMIN_TOKEN_HASH` administrator bearer-token check. They share validation and atomic JSON persistence with the CLI. Set `ARBY_SETTINGS_PATH` to override the default `/var/lib/arby-patch-command/settings.json` path for development. The directory must already exist and not be group/world writable; the saved file is private (0600).

For isolated CLI experiments, create a private temporary directory and run:

```sh
mkdir -m 700 /tmp/arby-settings-demo
python3 installer/settings-cli.py --path /tmp/arby-settings-demo/settings.json show
python3 installer/settings-cli.py --path /tmp/arby-settings-demo/settings.json set public_url https://patch.example.net:8443
python3 installer/settings-cli.py --path /tmp/arby-settings-demo/settings.json set appearance dark
```

**Important:** These settings are **staged only**, indicated by `"applied": false` in API responses. The new API does not activate enrollment/reporting, configure a TLS proxy, rotate certificates, change agent schedules, or apply settings to live services. Existing endpoints remain unchanged. This is intentionally not a production release; do not deploy to CT 104 yet.
