# Versionary Beta 0.9 — Settings and certificates

Status: staging-only development interface. Production deployment is not approved.

## Server Settings page

`/admin/settings` is an administrator interface for storing validated preferences.
The admin token is kept in page memory, not browser persistent storage.

The `tls_mode` choices are **external**, **local_ca**, and **provided**.
Selecting a mode saves a preference. It does **not** provision a certificate,
change a reverse proxy, enable enrollment or reporting, restart a service,
or alter the effective runtime configuration.

The Settings API returns `applied: false` for saved settings. The read-only
`/api/v1/admin/settings/runtime-status` endpoint reports effective gates.
Do not confuse saved preferences with activated runtime features.

## Offline certificate CLI

`installer/manage-certificates.py` supports:

- `inspect`: read-only expiry, SAN and fingerprint report
- `check`: validate an existing certificate/private-key pair for a hostname/IP
- `import`: copy a validated pair into an existing empty private directory
- `renew`: issue a replacement using explicitly supplied issuer material

Use `python installer/manage-certificates.py --help` to inspect arguments.
Certificate import and renewal require private-key handling. Never paste keys
into chats or logs. The CLI does not reload the running TLS proxy.

The `hostname` must match a DNS or IP Subject Alternative Name in the leaf
certificate. Trust distribution to agents is a separate operation.

## Beta 0.9 completion criteria

- Settings clearly distinguish staged preferences from runtime state.
- Certificate tooling remains separate from the browser and does not leak keys.
- Invalid TLS mode changes are rejected without modifying stored settings.
- Unauthorized callers cannot read or mutate server settings.
- Disposable acceptance tests cover the supported interface contract.

Production TLS provisioning, proxy reload, and live deployment remain outside
this batch and require explicit authorization and separate acceptance.
