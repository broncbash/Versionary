# Runtime visibility milestone — development only

This milestone provides a **read-only** way for administrators to inspect effective
network feature gates. It does **not** connect the bridge to live agent routes,
change TLS, enable enrollment, install an agent, or restart a service.

## What is available

- Web UI: `/admin/settings` → **Check runtime gates** (admin bearer token required).
- API: `GET /api/v1/admin/settings/runtime-status` (admin bearer token required).
- CLI: `python installer/settings-cli.py --path /path/to/settings.json runtime-status`.
- Legacy CLI: `python installer/runtime-status.py --path /path/to/settings.json`
  returns the same effective flags, without the API envelope.
- CI: `.github/workflows/tests.yml` builds the agent distribution archive from
  tracked source, validates it, then runs Python unit tests.

The runtime report includes `runtime_enabled`, `configuration_valid`,
`registration_enabled`, and `reporting_enabled`. It reflects what the
**staging bridge would allow**; it is **not proof that live routers use these
flags**. Currently the legacy agent routes still read their original environment
switches, and the new bridge remains disconnected.

## Safety boundaries

1. All feature switches default to disabled.
2. Staged settings alone never activate enrollment or reporting.
3. The runtime bridge requires a valid private settings file, HTTPS origin,
   explicit runtime gate, and each feature's existing environment gate.
4. The status API requires admin authentication and does not write files.
5. The CI workflow does not deploy to the homelab.
6. Do **not** set live agent environment gates or merge/deploy this milestone
   as a production activation mechanism without a separate V2 security review.

## Before production

- Review the legacy environment-only agent routes and the separate V2 enrollment
  routes; design one coherent activation boundary and add end-to-end tests.
- Validate certificate trust, server HTTPS configuration, and admin token
  handling before exposing the Settings page to any untrusted network.
- Preserve the current production service until a backed-up, explicitly
  approved, reversible rollout is ready.
