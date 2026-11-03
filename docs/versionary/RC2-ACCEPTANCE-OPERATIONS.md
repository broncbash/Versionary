# Versionary RC2 — Acceptance VM Operations Reference

Date: 2026-11-02

## Environment

VM IP: 192.168.122.92
VM hostname: versionary-beta09 (inherited)
Service: versionary-server.service
Application: /opt/versionary
State: /var/lib/versionary
HTTPS port: 8766
TLS identity: 192.168.122.92

## Connect

From development desktop:

    ssh ronb@192.168.122.92

## Check systemd

    systemctl is-active versionary-server.service
    systemctl is-enabled versionary-server.service
    systemctl status versionary-server.service --no-pager

## Verify HTTPS

The CA is inside a protected directory.

Do not weaken filesystem permissions to access it.

    sudo curl --fail --silent --show-error       --cacert /var/lib/versionary/certs/ca.crt       https://192.168.122.92:8766/health

Expected response:

    {"status":"online","mode":"isolated-https-beta","production":false}

## Verify certificate identity

    sudo openssl s_client       -connect 192.168.122.92:8766       -CAfile /var/lib/versionary/certs/ca.crt       -verify_ip 192.168.122.92       -verify_return_error </dev/null

Expected: Verify return code: 0 (ok).

## Inspect logs

    sudo journalctl -u versionary-server.service       -b --no-pager -n 80

Review logs for secrets before sharing.

## Inspect service definition

    systemctl cat versionary-server.service

## Protected state

    /var/lib/versionary

Contains private administrative credentials and TLS material.

Never publish the state directory or its contents.

## Release files on VM

    ~/versionary-rc2-20261102-160208-634498.tar.gz
    ~/versionary-rc2-20261102-160208-634498.json
    ~/versionary-rc2-installer.py

## Important operational limitations

This is an isolated HTTPS beta, not production.

The original Beta09 VM must not be modified.

The successful RC2 installation should be preserved while destructive
failure recovery is tested on another disposable environment.

No unattended updates or reboots are authorized by this document.
