# Patch Command — Unified Setup Wizard

## Status

Version 1 is a read-only installation planner.

It does not install software, modify services, enroll agents,
contact a server, or enable production deployment.

## Agent planning

Run:

    .venv/bin/python installer/setup-wizard.py \
      --role agent \
      --server https://patch.example.test \
      --ca-cert /path/to/trusted-ca.pem

The wizard delegates agent readiness evaluation to the
existing beta installation planner.

## JSON output

Add:

    --format json

JSON output is suitable for automation and test harnesses.

Exit codes:

- 0: Ready for an isolated test.
- 1: Planning completed, but not ready.
- 2: Invalid input or prohibited installation request.

## Interactive planning

Run:

    .venv/bin/python installer/setup-wizard.py --interactive

The wizard prompts for the role and, for agent installations,
the HTTPS server address and trusted CA certificate path.

## Server planning

Run:

    .venv/bin/python installer/setup-wizard.py --role server

Server installation orchestration is not yet implemented.
The wizard reports this explicitly.

## Safety boundaries

The wizard never invokes systemctl, package managers, enrollment,
or production installation.

The --install flag is deliberately rejected.

Production approval requires a separate development and
security-review milestone.

## Validation and integration

The wizard rejects malformed HTTPS origins, including:

- HTTP URLs
- Embedded credentials
- Paths and query strings
- Invalid or zero-valued ports
- Whitespace and backslashes
- Missing hostnames

Agent planning delegates to the existing beta installation
planner rather than introducing a competing readiness engine.

## Verified development baseline

- Focused wizard tests: 19 passing
- Complete regression suite: 783 passing
- Packaging, beta, and compatibility checks: passing
- Production deployment: disabled
- Hosted CI: not used

The wizard remains read-only. Successful planning does not
constitute authorization to install or enroll an agent.
