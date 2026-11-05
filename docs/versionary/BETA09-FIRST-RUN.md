# Versionary Beta 0.9 — Guided First Run

## Agent experience

Run `python installer/versionary-first-run.py` from a checkout with its Python dependencies installed. Use `--guide` for a noninteractive, read-only preview.

The interactive menu configures a private HTTPS origin and CA path, checks status, registers an agent, completes enrollment after **manual admin approval**, and sends a heartbeat or read-only update report. It calls the existing Versionary CLI; no separate protocol implementation is introduced.

**The server must already be running with a valid HTTPS certificate**, and the operator must explicitly enable `ARBY_ENROLLMENT_V2_ENABLED=true` and `ARBY_AGENT_REPORTING_ENABLED=true` in a disposable beta environment. Both are disabled by default. This batch exposes the existing v2 enrollment routes in the real FastAPI application but does not enable them.

The administrator still approves pending registrations through the existing authenticated API. There is not yet a complete dashboard-driven approval wizard.

## Limitations

This is a source-checkout guided beta workflow, **not a standalone binary, production installer, or production approval**. It does not install or start systemd services, configure the server, provision TLS, change any live container, automatically enroll, apply patches, or reboot. A separately approved disposable VM trial is still needed.
