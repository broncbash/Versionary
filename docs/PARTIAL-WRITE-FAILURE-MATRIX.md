# Post-write Disposable Failure Matrix

## Purpose

Verify that the existing disposable installation trial removes its
temporary workspace when a staging subprocess completes its writes
but the coordinator receives an injected failure.

## Covered phases

- Agent package installation
- CA certificate installation
- Configuration installation
- Systemd unit staging
- Installation audit

The harness runs each real subprocess before injecting its failure.

## Limits

These tests simulate an exception after a subprocess exits successfully.
They do not inject a failure in the middle of an individual file write,
simulate SIGKILL, or verify crash durability.

Temporary workspace deletion is not in-place rollback.

No production installation, service activation, enrollment, or network
communication is authorized by this test suite.
