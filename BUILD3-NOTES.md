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
