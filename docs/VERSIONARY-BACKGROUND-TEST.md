# Versionary background observer: isolated test batch

`versionary_background.py --dry-run` verifies existing local beta identity without scanning.
Without `--dry-run`, it launches `versionary_local_beta.py scan` in a separate
process, with a 240-second timeout and a nonblocking lock in the existing
private state directory. It suppresses child output so credentials cannot be
accidentally printed to journal logs. It never installs, enables, or starts a
systemd unit. It never upgrades packages.

This batch intentionally does **not** modify the earlier timer preview, which
still points to the interactive scan command. Before approving activation,
regenerate that preview to invoke this runner and separately review service
sandboxing, permissions, user-session behavior, and failure reporting.

The focused tests use mocked subprocess calls and temporary directories. No
real scans or network requests occur during testing. A real read-only scan
can later be triggered explicitly with `python versionary_background.py`.
