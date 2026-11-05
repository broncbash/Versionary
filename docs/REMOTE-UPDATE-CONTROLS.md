# Versionary — Remote Update Controls

Status: Planned feature. No remote execution is authorized or enabled.

## Product goal

Provide one dashboard for viewing and managing Linux package updates
across enrolled containers, virtual machines and physical hosts.

## Required user controls

### Check Updates
- Refresh update information for an individual machine.
- Refresh update information across all enrolled machines.
- Show package names, versions, scan time, and reporting errors.

### Update This Machine
- Provide an update action on each eligible machine.
- Require an authenticated, authorized operator.
- Show the exact target and requested action before confirmation.
- Execute only through a validated, enrolled agent.
- Report queued, running, succeeded, failed, and interrupted states.
- Preserve package-manager output and audit history.

### Update All
- Explicitly select eligible machines.
- Display the selected targets before confirmation.
- Never silently include offline or unapproved machines.
- Prevent duplicate or conflicting update jobs.
- Support per-machine progress and failure reporting.
- A failed machine must not silently hide other results.

## Security and operational requirements

- No automatic patching by default.
- No automatic rebooting by default.
- Never execute arbitrary shell commands from dashboard input.
- Use narrowly scoped, authenticated update operations.
- Authorize each operation and target server-side.
- Prevent replay, duplicate execution and concurrent package-manager jobs.
- Define cancellation and interrupted-job recovery behavior.
- Maintain an auditable record of requested actions and results.
- Support Debian APT and Arch pacman initially.
- Require explicit approval before any production deployment.

## Delivery stages

1. Observer-only homelab beta: inventory, scan results, agent health.
2. Remote update API design and simulated job execution.
3. Single-machine update control, isolated integration tests.
4. Fleet-wide update orchestration, partial-failure tests.
5. Disposable-machine real package-manager testing.
6. Explicitly approved homelab rollout.

Remote update execution is not part of the initial observer-only beta.
Do not interpret this specification as permission to enable it.
