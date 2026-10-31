# Versionary — Command Reference

Status: Development CLI reference, 2026-10-31.

All commands below run from the repository root.

Python executable:
.venv/bin/python

## Portable setup

Script:
installer/versionary-agent-setup.py

Options:

--server URL
    HTTPS server origin. No path, query, or embedded credentials.

--ca-cert PATH
    Existing trusted CA certificate file.

--state-dir PATH
    Private agent state directory.
    Default: ~/.local/state/versionary-agent

--interactive
    Prompt for missing settings. Requires a terminal.

--dry-run
    Validate and preview without writing configuration.

-h, --help
    Display command help.

Example:

.venv/bin/python installer/versionary-agent-setup.py \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt \
  --dry-run

## Agent CLI

Script:
versionary_agent_cli.py

Global option:

--state-dir PATH
    Private state directory.
    Must appear before the subcommand.

Subcommands:

setup
    Save HTTPS origin and CA path.
    Refuses to overwrite configuration.

status
    Show configured server, identity, and local credential state.

register
    Request registration using the enrollment protocol.

enroll
    Complete enrollment after administrator approval.

heartbeat
    Send an authenticated heartbeat.

report
    Scan package update availability and submit a report.

## Agent CLI setup options

setup --server URL --ca-cert PATH

setup --interactive

Example:

.venv/bin/python versionary_agent_cli.py \
  setup \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt

## Lifecycle command sequence

1. Configure:

.venv/bin/python versionary_agent_cli.py setup \
  --server https://server.example:8443 \
  --ca-cert /absolute/path/to/ca.crt

2. Inspect:

.venv/bin/python versionary_agent_cli.py status

3. Register:

.venv/bin/python versionary_agent_cli.py register

4. Obtain administrator approval on the server.

5. Enroll:

.venv/bin/python versionary_agent_cli.py enroll

6. Send heartbeat:

.venv/bin/python versionary_agent_cli.py heartbeat

7. Send report:

.venv/bin/python versionary_agent_cli.py report

## Return codes

0
    Command completed successfully.

1
    Handled operational/configuration error.
    The report command also returns 1 when local scan status
    is unsuccessful.

2
    Common argparse usage error, such as an unknown command
    or missing required command-line arguments.

## Important security notes

- Never paste live credentials or private keys into commands.
- A CA file must already exist before setup.
- The CA must be trusted for the intended server.
- HTTPS hostname/IP verification happens during connection.
- Registration and enrollment require a reachable server
  with the relevant feature gates enabled.
- Server-side approval is a separate administrative action.
- No command listed here installs patches or reboots machines.

## Not implemented yet

Do not assume the existence of commands named:

install
upgrade
uninstall
service enable
service start
certificate rotate

These are roadmap items, not current CLI functionality.
