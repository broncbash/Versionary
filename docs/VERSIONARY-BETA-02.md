# Versionary Beta 0.2 — Local observer controls

This opt-in development batch adds a status CLI, explicit scan command, and **inert** systemd user timer preview. It does not install, enable, or start a timer. It does not upgrade packages, deploy to the homelab, or push to GitHub.

Run `./.venv/bin/python versionary_beta_control.py status` to inspect the existing local beta agent without printing its secret token. Run `./.venv/bin/python versionary_beta_control.py scan` to initiate an explicit read-only scan. Run `./.venv/bin/python versionary_beta_control.py timer-preview` to create example service/timer files in `.versionary-timer-preview/` for review. **Do not install or enable these until explicitly approved.**

The existing `.versionary-local-beta/agent.json` identity is reused. Server remains bound to 127.0.0.1 when launched with `versionary_local_beta.py serve`. The scan command uses an in-process API; this is not yet a separately installed remote agent.

Remaining work: end-to-end scheduling tests, user service lifecycle, real distro artwork, robust server lifecycle, and pre-release review of SQLite resource warnings and httpx deprecation.
