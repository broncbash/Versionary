# Beta installation planning

Run `python installer/beta-install-plan.py --server https://example.test --ca-cert /path/to/ca.crt` after building the agent archive. The JSON report is read-only and lists prerequisites, failed checks, planned phases, and approvals. An exit code of zero means only that isolated-test prerequisites passed. Production readiness always remains false.

This planner does not create a test root, install files, enroll agents, contact a server, start systemd, or provide rollback. It requires a separate review of backup and rollback before any live installation. The existing `installer/stage-beta.py` can stage an inert agent in a pre-existing disposable test directory. Do not use a live container without explicit authorization.
