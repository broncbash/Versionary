# Read-only rollback planner

This tool compares the **current assets** in an existing disposable installation root with a previously verified private asset snapshot. It does not install, restore, delete, enable services, enroll agents, or touch a production filesystem.

```bash
python installer/rollback-plan.py --root /path/to/disposable-root --snapshot /path/to/private/snapshot
```

The JSON output lists four allowlisted assets (configuration, public CA, systemd service and timer), each classified as `unchanged`, `create`, `replace` or `remove`, including current and proposed sizes, modes and SHA-256 digests. It also lists blockers, and **always** reports `apply_allowed: false` and `changes_made: false`.

The planner refuses the real root, overlapping paths, unsafe source assets and invalid snapshot contents. It does not inspect private state contents or credential material; the presence of private state is reported as an additional blocker. Proposed removals require explicit review.

**Limits:** This is an advisory filesystem diff, not an executable transaction, dependency resolver, compatibility assessment or proof of certificate trust. A snapshot with internally consistent digests can still be forged by an attacker with write access. The comparison is not an atomic view of concurrently changing files. It does not cover code release contents or service state. No production use is authorized.
