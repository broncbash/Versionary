# Disposable Onboarding Trial

## Purpose

Connect the unified onboarding readiness report to the existing
temporary-workspace installation trial.

This is an isolated test facility, not a production installer.

## Execution requirements

- Agent role only
- Explicit existing CA certificate
- Explicit agent package
- Passing isolated-test preflight
- Exact confirmation token: RUN-DISPOSABLE-TRIAL

## Example

    python installer/onboarding-disposable-trial.py \
      --server https://patch.example.test \
      --ca-cert /path/to/test-ca.pem \
      --package /path/to/agent.tar.gz \
      --confirm RUN-DISPOSABLE-TRIAL

The command does not accept a target installation root.

## Safety boundaries

The existing disposable trial creates its own temporary directory,
stages the agent, audits the installation, and removes the workspace.

No production installation, service activation, agent enrollment,
or external server communication is authorized.

This is not an atomic multi-asset rollback mechanism.

The filesystem transaction simulation is retained separately.
It is not used to mutate real installation assets.

The snapshot restoration system remains restricted to empty
disposable destinations.

## Future work

- Failure-injection testing across real staging phases
- More detailed recovery and cleanup evidence
- Stronger filesystem and symlink boundary verification
- A reviewed, explicit production installation design
