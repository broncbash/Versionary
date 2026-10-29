# Installation asset inventory (isolated beta)

Before implementing multi-file backup and rollback, `installer/installation-inventory.py` records a **read-only** inventory of selected files in a pre-existing disposable installation root.

```bash
python installer/installation-inventory.py --root /path/to/disposable-test-root
```

It reports presence, SHA-256, size, and permissions of agent configuration, CA trust, and the two inactive systemd unit files. It checks the private state directory's ownership and mode **without reading its contents**. It rejects `/`, symlinked file and directory components, unexpected owners, group/other-writable paths, hardlinked assets, and oversized files.

**This is not a backup or rollback mechanism.** It does not preserve any file bytes, restore assets, handle service lifecycle, or guarantee a consistent concurrent snapshot. In particular, private credentials and enrollment state are not copied, printed, or restored. The production installer remains gated. The next phase is designing a secure snapshot format and a restore procedure with interruption and concurrency tests before considering a live target.
