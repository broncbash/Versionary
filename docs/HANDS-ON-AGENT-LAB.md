# Hands-on desktop agent lab

This is the first retained, inspectable **desktop-only** agent installation demonstration. It does not start the web server or provide a live fleet dashboard. It stages a real agent distribution and its inactive systemd unit files in an isolated directory; it does not install anything on the host.

## Run on your Arch desktop

From your existing development checkout:

```bash
cd ~/Projects/arby-patch-command
git pull --ff-only
.venv/bin/python installer/local-readiness.py
```

For an inspectable workspace, create a **new private empty directory** and run:

```bash
LAB="$(mktemp -d -t patch-command-demo-XXXXXXXX)"
.venv/bin/python installer/try-agent-lab.py --workspace "$LAB"
```

The command prints the workspace path, staged root, agent package path, and an asset inventory. It generates a disposable CA, builds the agent package, stages it in `$LAB/isolated-root`, audits it, and leaves the files for inspection. You can inspect `$LAB/isolated-root/etc/versionary-agent/config.json`, inactive service/timer files, and the package archive. The test server URL is a loopback placeholder, **not** a running endpoint.

When finished, remove only the specific workspace you created. Do not use a directory containing personal or live installation files.

To run a completely ephemeral trial without retained files:

```bash
.venv/bin/python installer/try-agent-lab.py
```

## What this does not do

It does not enroll an agent, discover LAN machines, start systemd, run patch updates, contact a live server, or deploy to CT104/CT102. The staged private key and CA are test artifacts, not trusted production credentials. The existing local HTTPS acceptance tests exercise protocol flows separately in a disposable environment.

This is a hands-on **installation staging demo**, not yet an end-to-end running Patch Command product. Production installation remains disabled until explicitly approved and reviewed.
