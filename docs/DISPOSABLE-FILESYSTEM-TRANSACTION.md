# Disposable filesystem transaction trial

Run an isolated demonstration of five coordinated file-generation changes:

```bash
python installer/disposable-filesystem-transaction.py
python installer/disposable-filesystem-transaction.py --fail-after ca
```

The trial **creates its own temporary root** and accepts no filesystem destination argument. It writes separate prior, candidate, and active asset generations, fsyncs staged files, performs per-file replacement, and persists a small journal with each checkpoint. At a selected checkpoint, it simulates failure and restores the previous generation from its local backup. The temporary root is automatically removed at exit. Unit tests cover each checkpoint.

**This is not a production transaction engine.** In particular, this is a controlled injected failure handled within one process, **not** recovery after SIGKILL, abrupt power loss, or an independently restarted recovery process. Journal records are not independently authenticated; directory and inode races are not comprehensively defended; the simulated release is a placeholder file, not an actual package or symlink. There is no service lifecycle, trust rotation, real installation path, persistent backup retention, or authorized live apply. Multi-file replacement is not atomic. Do not use this as a production installer.

Next gates: independently restarted recovery against a *disposable* retained root; tamper and disk-failure tests; explicit trust and rollback policies; review before any live installation design.
