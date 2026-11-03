# Versionary RC2 — Real Installation Acceptance Report

Date: 2026-11-02
Status: Real installation and reboot acceptance PASSED
Production approval: NO
Next milestone: Destructive failure-recovery acceptance on a separate disposable target

## 1. Executive summary

Versionary RC2 successfully completed its first real installation on a
cloned Arch Linux virtual machine.

This was not a mocked installer execution or simulated systemd environment.

The actual packaged installer:

- Validated the release archive and manifest.
- Created the dedicated Versionary service account.
- Installed the packaged application into /opt/versionary.
- Created protected application state under /var/lib/versionary.
- Created a Python virtual environment.
- Installed pinned Python dependencies.
- Initialized an isolated HTTPS server and certificate authority.
- Registered and enabled versionary-server.service.
- Started the server.
- Completed its installer-level HTTPS health verification.

Independent verification subsequently confirmed that systemd was active
and enabled, the HTTPS endpoint responded successfully, the TLS certificate
validated against the generated CA, and the certificate matched the
acceptance VM's IP address.

A full VM reboot was then performed. The service automatically restarted
and the verified HTTPS health endpoint remained functional.

This is a successful disposable-VM installation acceptance milestone.
It is NOT production approval.

## 2. Development environment

Development desktop:
- Operating system: Arch/CachyOS Linux
- Local repository: ~/Projects/arby-patch-command
- Working branch at last report: feature/versionary-agent-rename
- Python environment: .venv/bin/python
- No hosted CI was used.

The repository has substantial modified and untracked local development
work. Preserve all of it.

Do not use git reset --hard, git clean, broad deletion, or blanket
replacements of existing source files.

Do not modify live homelab containers CT104 or CT102 without approval.

## 3. Regression acceptance

Command:

    ./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'

Final result:
- Tests executed: 1391
- Passed: 1390
- Skipped: 1
- Failures: 0
- Errors: 0
- Duration: 27.481 seconds

Log:

    /tmp/versionary-regression-final-20261102-155956.log

The final regression followed correction of outdated static assertions
in tests/test_versionary_https_beta.py.

The runtime uses configurable bind address and HTTPS port functions.
Earlier assertions incorrectly expected hard-coded host and port values.

The source runtime was not changed by those final test corrections.

## 4. Verified release candidate

Release directory:

    ~/Projects/versionary-release-candidates/
      versionary-rc2-hardened-20261102-160208-598242/

The builder interprets --output as a DIRECTORY, not an archive filename.

Because an earlier orchestration script passed a filename-shaped directory,
the actual release files are located inside a directory named
versionary-rc2.tar.gz.

Archive:

    versionary-rc2.tar.gz/
      versionary-rc2-20261102-160208-634498.tar.gz

Manifest:

    versionary-rc2.tar.gz/
      versionary-rc2-20261102-160208-634498.json

Archive SHA256:

    36c865e384b542954504d52e9962a8cae7d5162a966da14a2871990bbef5d92b

Packaged files: 133

Verification results:
- Builder: PASS
- Archive/manifest integrity: PASS
- Archive safety audit: PASS
- Packaged installer matches local source: PASS
- HTTPS hardening present in packaged installer: PASS
- Independent release validator: PASS

Relevant scripts:

    installer/build-versionary-release.py
    installer/validate-versionary-release.py
    installer/versionary-server-install.py

Do not overwrite or remove previous release candidates.

## 5. Acceptance virtual machine

Acceptance VM:
- IP: 192.168.122.92
- Guest OS: Arch Linux
- Hostname inherited from clone: versionary-beta09
- User: ronb
- Networking: libvirt default NAT
- Purpose: Disposable RC2 acceptance

Important: This VM was cloned from a previous Beta09 test VM.
It was not a fresh operating-system installation.

Original Beta09 VM:
- Name: Versionary-Beta09
- Previously observed IP: 192.168.122.60
- Must remain untouched unless explicitly authorized.

The cloned VM initially contained inherited beta systemd units.

The old server service attempted to bind to 192.168.122.60, which
was not the clone's IP.

Actions completed on the clone:
- Disabled and stopped the inherited server service.
- Quarantined inherited server and agent systemd unit definitions.
- Reloaded systemd.
- Confirmed the RC2 installation paths were clear.
- Confirmed no versionary service account existed.

Quarantine location on clone:

    /home/ronb/versionary-pre-rc2-services

The inherited agent application and data were not deleted:

    /opt/versionary-agent
    /var/lib/versionary-agent

Other inherited beta files may remain in the user's home directory.
Do not treat the VM as a completely clean Arch image.

## 6. Real installation details

Installer invocation used:

    sudo python "$HOME/versionary-rc2-installer.py"       --archive "$HOME/versionary-rc2-20261102-160208-634498.tar.gz"       --manifest "$HOME/versionary-rc2-20261102-160208-634498.json"       --mode install       --confirm-disposable       --app-dir /opt/versionary       --state-dir /var/lib/versionary       --tls-identity 192.168.122.92       --bind-address 192.168.122.92       --port 8766

The installer dry-run passed before actual installation.

Actual installation output:
- INSTALL=PASS
- INSTALL_EXIT_CODE=0
- SERVICE=versionary-server.service
- PRODUCTION_APPROVED=NO

Installed application:

    /opt/versionary

Protected state:

    /var/lib/versionary

Certificate authority:

    /var/lib/versionary/certs/ca.crt

Private admin credential:

    /var/lib/versionary/admin-token

Do not print, copy into documentation, or commit the admin token.

Service:

    versionary-server.service

HTTPS endpoint:

    https://192.168.122.92:8766/health

## 7. Independent HTTPS verification

Service status:
- Active: active
- Enabled: enabled

Verified HTTPS response:

    {"status":"online","mode":"isolated-https-beta","production":false}

The CA certificate was located inside a protected state directory.

An unprivileged curl invocation could not access the CA file.
This was an access-control limitation, not a certificate validation
failure.

Verification was rerun with sudo, without changing permissions.

OpenSSL reported:

    Verification: OK
    Verify return code: 0 (ok)

The certificate was verified for IP identity 192.168.122.92.

## 8. Reboot persistence

The acceptance VM was rebooted.

After reconnecting:
- versionary-server.service was active.
- versionary-server.service was enabled.
- The verified HTTPS health endpoint returned online.
- The response continued to report production=false.

Result: REBOOT_PERSISTENCE=PASS.

## 9. Remaining acceptance work

The following work remains open:

1. Preserve the successful installation as a known-good baseline.
2. Use a separate disposable clone or safely restorable snapshot
   for destructive failure-injection testing.
3. Test real installer recovery after dependency-install failure.
4. Test real installer recovery after HTTPS initialization failure.
5. Test real installer recovery after systemd startup failure.
6. Test recovery-marker write failure.
7. Verify cleanup subprocess failures cannot mask the original
   installer exception.
8. Verify protected application/state preservation after failure.
9. Verify rerun refusal against an incomplete installation.
10. Review release readiness after recovery acceptance.
11. Review and reconcile outstanding local source changes.
12. Plan controlled GitHub integration with explicit authorization.

Previously, four mocked real-install-function recovery scenarios passed.
Those tests do not replace destructive failure-injection acceptance on
a disposable VM.

## 10. Safety constraints

- Do not modify Versionary-Beta09.
- Do not modify homelab CT104 or CT102 without approval.
- Do not delete untracked local data.
- Do not use hosted CI.
- Do not assume production approval.
- Do not print or commit private credentials.
- Do not repeat installation over an existing RC2 state directory.
- Do not perform destructive recovery tests on the successful
  acceptance installation without a verified restoration plan.
- No automatic GitHub push or merge.

## 11. Acceptance verdict

REAL_INSTALLATION=PASS
RELEASE_INTEGRITY=PASS
HTTPS_VERIFICATION=PASS
REBOOT_PERSISTENCE=PASS
DESTRUCTIVE_RECOVERY_ACCEPTANCE=PENDING
PRODUCTION_APPROVED=NO
