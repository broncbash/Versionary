# Versionary beta.3 development handoff

Repository: broncbash/Versionary
Working directory: ~/Projects/arby-patch-command
Development branch: fix/beta3-agent-distribution

## Confirmed issue

Public beta.2 agent installer passed a raw agent archive
to the guided installer, which requires a complete distribution.

## Fix

install-versionary-agent.sh now stages the raw archive,
builds the complete distribution, verifies it, and passes
the correct archive to the guided installer.

Cached distribution reuse has been disabled.

## Regression coverage

tests/test_beta3_agent_installer_handoff.py

Prior successful full suite:
1702 tests, zero failures, one skipped.

## Release requirements

Prepare v0.1.0-beta.3 without rewriting beta.2.
Use a verified new source archive checksum pin.
Ensure published asset filenames match installer expectations.
Update public documentation and quick-start commands.
Verify all assets before publishing.

## Operational constraints

Do not modify live Proxmox containers.
Do not modify working beta server or Arch agent.
Preserve untracked local files and backups.
No branch cleanup during release preparation.
No automatic package updates or production enablement.

## Next acceptance

Fresh Debian VM agent installation using the corrected
public installer.
