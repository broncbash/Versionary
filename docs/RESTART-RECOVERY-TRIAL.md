# Independent-process disposable recovery trial

`installer/restart-recovery-trial.py` creates a temporary directory, stages five placeholder assets, launches a child Python worker, and forces that worker to exit after a selected checkpoint. A **separate child process** then reads the journal and restores the prior files. The parent verifies the final state.

```bash
python installer/restart-recovery-trial.py --stop-at ca
python installer/restart-recovery-trial.py --stop-at timer --tamper journal
python installer/restart-recovery-trial.py --stop-at release --tamper backup
```

This is a **controlled process-exit demonstration**, not a production-ready crash-recovery engine. It does not simulate power loss, kernel crashes, torn writes, hostile directory replacement, all journal interruption windows, or concurrent installers. The journal has no external authentication, the worker path is an internal test-only interface, and this exercise does not operate on an installation root. There is no service start, enrollment, credential access, or live deployment. Filesystem transactions across assets are not atomic.

Before production design: durable directory sync, interrupted recovery restart, strict directory-fd containment, trust anchors, locking, and independent security review.
