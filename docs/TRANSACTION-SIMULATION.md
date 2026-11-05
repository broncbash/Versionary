# Coordinated transaction model

The experimental `installer/transaction-simulation.py` models a five-asset generation change (release, configuration, CA, systemd service, timer) entirely **in memory**. It records simulated journal states and can inject a failure at each checkpoint, then model recovery to the prior generation.

```bash
python installer/transaction-simulation.py
python installer/transaction-simulation.py --fail-after ca
```

This is a **state-machine exercise**, not a filesystem transaction, durable journal, crash-safe installer, actual backup, service manager, or production rollback. No real files are changed. It cannot establish recovery from power loss or filesystem races. Those require separately reviewed disposable filesystem tests and independent security review. Production installation remains disabled.
