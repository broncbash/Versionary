# Versionary Beta 0.9 — Local Dashboard Demonstration

Run from the repository on your development desktop:

```bash
.venv/bin/python installer/versionary-dashboard-demo.py --preview
.venv/bin/python installer/versionary-dashboard-demo.py
```

Open `http://127.0.0.1:8769/admin/dashboard` **on the same computer**. Paste the printed administrator token into the dashboard and select **Refresh fleet**. You should see one pending Debian agent and one approved Arch agent with a heartbeat and an empty successful update report. Try approving the pending agent in the dashboard.

The launcher binds only to `127.0.0.1`, creates a random administrator token, and seeds an ephemeral SQLite database. Registration, reporting, v2 enrollment, and settings runtime mutation are explicitly disabled. Ctrl+C stops the server and removes the temporary database. No agent is installed or contacted; sample data is clearly labeled.

This is a **hands-on dashboard demonstration**, not a complete server installer, HTTPS deployment, or live agent onboarding. Do not use the HTTP demonstration for real infrastructure or remote access. Do not approve production deployment based on this demo.
