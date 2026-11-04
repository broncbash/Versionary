# Versionary Installation Guide

## Release status

Versionary is in controlled-beta development.

The unified installation kit passed local acceptance testing on
November 4, 2026. Production deployment remains disabled.

The server release passed archive integrity verification, dependency
validation, and installer dry-run acceptance.

The agent installer successfully installed into a disposable
filesystem outside the development repository.

A real server installation in an explicitly approved disposable VM
remains outstanding.

## Building the unified kit

From the Versionary source repository:

    python3 installer/build-unified-installation-kit.py \
      --server-archive /path/to/versionary-rc2-release.tar.gz \
      --server-manifest /path/to/versionary-rc2-release.json \
      --output /path/to/versionary-unified-install-kit.tar.gz

The server release archive and manifest must already exist.

The unified kit contains both installer entry points, their
supporting modules, the agent distribution, systemd templates,
and the verified server release.

## Extracting the kit

Verify the archive checksum against a trusted release record.

    mkdir versionary-preview
    tar -xzf versionary-unified-install-kit.tar.gz \
      -C versionary-preview
    cd versionary-preview/versionary-install-kit

Only extract archives from trusted sources.

## Server installation preview

    python3 installer/install-versionary-server

The unified kit's server launcher automatically locates its
bundled release archive and manifest.

The default operation is a verified dry run.

A successful dry run does not install or start the server.

The existing RC2 backend's installation mode creates system
resources and manages systemd services. It must only be tested
inside an explicitly approved disposable VM.

Do not use installation mode on a production machine.

## Agent installation preview

    python3 installer/install-versionary-agent

The agent installer supports interactive prompts and scriptable
command-line arguments.

For a non-installing validation:

    python3 installer/install-versionary-agent \
      --server https://versionary.example.test \
      --ca-cert /path/to/ca.crt \
      --dry-run

For a disposable-root installation test:

    python3 installer/install-versionary-agent \
      --server https://versionary.example.test \
      --ca-cert /path/to/ca.crt \
      --root /path/to/disposable-root \
      --execute-disposable \
      --yes

Never use the live system root for disposable testing.

The tested agent installation creates application files,
configuration, a public CA certificate, and systemd unit files.

It does not perform agent enrollment, registration, or
service activation.

## Certificates and configuration

Use the actual server hostname or IP address in the server URL.

The server's TLS certificate must have a matching subject
alternative name (SAN).

The agent must trust the CA that issued the server certificate.

Do not hard-code homelab addresses or private CA fingerprints.

Never distribute private keys or enrollment credentials
inside a public installation archive.

## Batch 32 acceptance results

- Unified outer archive: 22 files
- Server release: 137 files
- Server archive verification: PASS
- Server installer dry run: PASS
- Agent disposable installation: PASS
- Agent systemd unit installation: PASS
- Service activation: NOT PERFORMED
- Enrollment: NOT PERFORMED
- Production deployment: NOT PERFORMED
- GitHub mutation: NOT PERFORMED

The outer archive's filename-based private-material check is
not a comprehensive inspection of nested archive contents.

## Remaining beta readiness gates

1. Automated installation-kit regression coverage
2. Full local regression checkpoint
3. Real server installation in an approved disposable VM
4. Server-to-agent enrollment and connectivity acceptance
5. Production installation and configuration workflow
6. Documentation review and approved GitHub integration
7. Explicit controlled-beta deployment authorization

Passing local tests does not constitute production approval.
