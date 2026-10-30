# Versionary Beta 0.2 — inactive background timer integration

The preview in `.versionary-timer-integration-preview/` is **not** installed
into any systemd directory. It runs `versionary_background.py`, the existing
lock-protected runner, rather than calling the scan directly. This batch does
not invoke any real scan, start a server, or install/enable/start units.

The user timer proposes a first scan 10 minutes after the user manager starts,
then at least six hours after the preceding service becomes inactive. It has a
random delay of up to two minutes and five-minute accuracy. It is **not** an
always-on service: when the user manager is stopped, scans do not occur. The
server is not started by the timer. The scan currently runs in-process using
the private local beta database, so it does not require a running web server.

The generated service is a user service, not a system service. It has a
300-second service timeout; the background runner has a 240-second child timeout.
The runner suppresses child stdout/stderr, and the unit discards stdout.
No packages are installed or upgraded.

To verify again without changing state:
`./.venv/bin/python versionary_timer_integration.py --verify-only`

Before considering activation: confirm user-manager behavior, path portability,
CachyOS update scanner availability, private-state permissions, and lifecycle
handling. Activation requires separate explicit approval. No production
homelab or GitHub changes are included.
