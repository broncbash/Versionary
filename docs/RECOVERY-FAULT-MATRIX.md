# Offline recovery fault matrix

`installer/recovery-fault-matrix.py` runs only disposable, offline recovery experiments. It is not an installer or production rollback tool.

Run `.venv/bin/python installer/recovery-fault-matrix.py --summary` for 37 cases or add `--exhaustive` for 65 cases. Use `--max-cases 1` for a quick smoke check. Failed cases return a nonzero exit code; without `--summary`, output includes case-level results and durations.

Default cases cover five switch interruptions, 25 switch/recovery interruption pairs, and seven corruption or symlink refusal scenarios. Exhaustive mode runs corruption scenarios at each switch checkpoint.

The ordinary desktop checkpoint remains `bash installer/local-check.sh --protocol-check`. Hosted CI is not configured.

This harness uses placeholder data in temporary directories and does not install software, start systemd, enroll agents or call external services. It does not model real power failures, concurrent hostile writers, authenticated backups or atomic multi-asset production rollback. Production deployment remains prohibited without explicit approval.
