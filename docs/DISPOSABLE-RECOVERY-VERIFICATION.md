# Disposable Recovery Verification

## Scope

This test battery covers two existing mechanisms:

1. Disposable agent trial cleanup
2. Self-contained filesystem transaction recovery

These mechanisms have different guarantees.

## Disposable agent trial

The existing disposable-install-trial.py creates its
own temporary workspace and performs staging and
verification.

Failure injection tests substitute the staging entry
point to force exceptions during:

- Initial staging
- Post-staging verification

Tests verify that the temporary workspace is removed
after each injected exception.

The tests also verify cleanup after successful
execution.

These injected tests do not exercise actual package
extraction, certificate installation, or systemd file
generation. Those operations are covered separately
by the existing installer tests.

## Transaction simulation

The existing disposable-filesystem-transaction.py
simulates asset replacement and journaled recovery.

Tests exercise every declared failure checkpoint:

- prepared
- release
- config
- ca
- service
- timer
- verified

Each checkpoint must restore the simulated previous
generation and report a recovered journal state.

The simulation is not connected to actual agent
installation and does not establish atomic rollback
for real installation assets.

## Safety guarantees

Neither workflow authorizes production installation,
service activation, agent enrollment, or live-host
modification.

## Remaining verification

- Execute the full onboarding coordinator with a
  valid disposable CA and agent package
- Inject failures into actual installer subprocesses
- Verify real staged artifacts and permissions
- Examine interrupted-process and cleanup failures
- Design a separate production-safe transaction model

Production deployment remains disabled.
