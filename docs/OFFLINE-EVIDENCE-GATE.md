# Offline evidence gate

The new `installer/offline-evidence-gate.py` validates two **locally generated JSON reports** and an operator-reported unittest count. It is read-only, performs no test execution or installation, and **never authorizes production deployment**.

## Evidence inputs

- `--beta-json`: JSON from `installer/beta-selftest.py --protocol-check`, including successful package staging, integrity and TLS checks, plus explicit false production-side-effect flags.
- `--matrix-json`: JSON from `installer/recovery-fault-matrix.py --exhaustive` (without `--summary` is also accepted). It must report all 65 scenarios passed, zero failures, and explicit false production-side-effect flags.
- `--tests`: number of passing local regression tests, minimum 716 for this experimental baseline. This count is **operator-asserted**, not independently authenticated.

Example after collecting the two reports locally:

```bash
.venv/bin/python installer/offline-evidence-gate.py --beta-json /path/to/beta.json --matrix-json /path/to/matrix.json --tests 732
```

The tool prints machine-readable JSON and exits nonzero if evidence is missing, malformed, incomplete, or inconsistent. It rejects symlinked evidence files, oversized evidence and duplicate JSON keys. A passing result means **only that supplied disposable-test evidence satisfies the specified shape and claims**. It does not prove evidence provenance, attest to the source revision, independently execute tests, or imply deployment permission.

## Safety

The report always contains `production_approved: false` and `deployment_permitted: false`. No GitHub-hosted CI is configured. Do not treat this gate as a production approval workflow.
