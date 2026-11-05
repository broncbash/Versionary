# Unified Onboarding v1

## Purpose

Unified Onboarding provides one entry point for reviewing
a proposed Patch Command installation.

It integrates the existing installation-preview module.

No installation or enrollment occurs.

## Interactive mode

    .venv/bin/python installer/onboard.py --interactive

The wizard prompts for:

- Installation role
- HTTPS server URL for an agent
- Certificate mode
- Existing CA path when required
- Optional preview acknowledgment

Acknowledgment does not execute installation.

## Scriptable mode

Existing CA:

    .venv/bin/python installer/onboard.py \
      --role agent \
      --server https://patch.example.test \
      --ca-cert /path/to/ca.pem \
      --format json

Proposed disposable test CA:

    .venv/bin/python installer/onboard.py \
      --role agent \
      --server https://patch.example.test \
      --certificate-mode generate-test-ca \
      --format json

The latter does not generate a certificate.

## Review acknowledgment

Add:

    --acknowledge-preview

This changes only the returned review status.

It does not authorize or execute installation.

## Server role

Server onboarding currently returns not-implemented.

## Safety

- Production installation disabled
- Live host changes disabled
- Service activation disabled
- Agent enrollment disabled
- Network requests disabled
- Disposable installation execution not yet connected

The onboarding workflow is intentionally separate from
the existing disposable staging engine until its integration
and rollback behavior have been reviewed and tested.

## Integrated readiness reporting

The onboarding JSON response includes a `readiness` object
derived from the existing beta installation planner.

The readiness report contains:

- Isolated-test readiness
- Production readiness (always false)
- Individual preflight checks
- Failed checks and actionable blockers
- The next safe action

For repeatable offline testing, the CLI accepts:

    --package /path/to/agent-package.tar.gz
    --os-release /path/to/test-os-release

Selecting `generate-test-ca` leaves readiness pending until
the test CA has actually been created. No certificate is
generated during onboarding.

The existing planner's production and enrollment gates
remain visible even if disposable testing is ready.

The onboarding interface does not execute staging or
authorize changes to live systems.
