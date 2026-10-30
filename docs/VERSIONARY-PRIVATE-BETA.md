# Versionary — Private Beta 0.1

Versionary is the working public-facing name of the experimental, observer-only Linux patch visibility platform. Legacy `arby-*` names and environment variables remain for compatibility during the transition. Do not globally rename paths or database keys without a migration plan.

## Verified milestones

- Local desktop demonstration: simulated fleet, no live agent or production credentials.
- Dashboard: Versionary branding and distribution identification badges (initials, not licensed logo assets).
- API integration acceptance: temporary SQLite database, pending registration, administrator approval and one-time credential, authenticated heartbeat and package report, read-only inventory, revocation and disabled-by-default reporting.

## What the integration test does **not** prove

- No installed agent daemon, package scan, TLS transport, network service, installer, or browser-to-server live workflow is exercised.
- The test uses an in-process HTTP client and synthetic update packages; it does not patch the host.
- It does not authorize live enrollment, exposing the server, enabling production gates, or deploying to any homelab container.

## Next usable-beta milestone

Build an isolated loopback HTTPS development launcher and disposable agent client that sends a real read-only package inventory to a separate temporary database. Add administrator UI onboarding and a consistent Versionary identity, then validate the whole workflow before requesting approval for any real deployment.

## Safety and workflow

Run `./.venv/bin/python installer/local-readiness.py` locally. Keep branch `feature/runtime-visibility`; no push or merge without explicit approval. Preserve unrelated untracked files. Do not touch CT104 or CT102. Maintain observer-only semantics.
