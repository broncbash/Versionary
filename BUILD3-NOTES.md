# ARBY PATCH COMMAND — Build 3 checkpoint 1

Offline certificate import/validation foundation; not a production release.

New files:
- `certificate_management.py`: validates server certificate/key match, validity dates, SAN hostname/IP, optional EKU, rejects CA leaf, and safely installs to a preexisting private directory without overwriting.
- `installer/manage-certificates.py`: CLI `check` and `import` (both leave TLS proxy untouched).
- `tests/test_certificate_management.py`: six new regression tests.

Run tests in the project venv: `python -m unittest discover -s tests -q`.

Certificate import example (after creating a private destination directory):
`python installer/manage-certificates.py check --cert /path/to/server.crt --key /path/to/server.key --hostname example.test`

Security limitations: the import workflow currently supports unencrypted PEM private keys only; no chain-of-trust validation, key rotation, CA distribution, TLS proxy reload, or GUI. Do not use as a live deployment. Keep private keys out of Git.

Offline validation: 440 tests passed with Python 3.11 and locally installed dependencies. Desktop Python 3.14 verification remains required.

## Certificate inspection checkpoint

Added read-only `inspect` command to `installer/manage-certificates.py`,
including expiry warnings, SAN hostname comparison, SHA-256 fingerprint,
and private-key-free status checks. This does not install, rotate, or reload
certificates. Example:

```bash
python installer/manage-certificates.py inspect --cert /path/to/server.crt --hostname patch.example.org --warning-days 30
```

The `check` and `import` commands still require `--key` and `--hostname`.

## Offline certificate renewal checkpoint

`certificate_renewal.py` and `installer/manage-certificates.py renew` issue a **new**
server certificate/key signed by an existing local CA. Requires a private CA
key (0600), a valid matching CA certificate, and an **existing empty/private**
output directory (0700). Refuses overwrites. It does **not** change a TLS
proxy, rotate CA trust, or restart any service. The caller must validate and
approve deployment separately. Keep CA keys offline and out of Git.

Example (output directory must already exist and be chmod 700):

```bash
python installer/manage-certificates.py renew \
  --ca-cert /secure/ca.crt --ca-key /secure/ca.key \
  --hostname patch.example.test --destination /secure/new-leaf
```

## Installer configuration preflight (read-only)

`python installer/settings-preflight.py --path /path/to/settings.json` validates
configuration and reports readiness without changing services or files. Use
`--require-network` to require an HTTPS origin. This is **not** a production
installer and does not activate network features, manage trust, or reload TLS.

## Runtime configuration bridge (staging)

`runtime_configuration.py` computes fail-closed *effective* enrollment/reporting
flags from validated settings plus explicit environment gates. The separate
`installer/runtime-status.py` command reports effective status without modifying
files or services. This bridge is not yet connected to the production routers;
existing environment-only behavior is unchanged. Integration requires explicit
review of V2 enrollment isolation before enabling. A settings file by itself
never activates network features.
