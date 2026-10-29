"""Portable, validated agent connection configuration."""
import ipaddress
import json
import os
import stat
import urllib.parse
from pathlib import Path

DEFAULT_CONFIG = Path("/etc/arby-patch-agent/config.json")
DEFAULT_CA = Path("/etc/arby-patch-agent/ca.crt")

class ConfigurationError(RuntimeError):
    pass

def validate_server(server):
    if not isinstance(server, str) or len(server) > 2048:
        raise ConfigurationError("Server must be an HTTPS URL")
    try:
        url = urllib.parse.urlsplit(server)
        port = url.port
    except ValueError as exc:
        raise ConfigurationError("Invalid server URL") from exc
    if (url.scheme != "https" or not url.hostname or
        url.username is not None or url.password is not None or
        url.path not in ("", "/") or url.query or url.fragment or
        any(ch.isspace() for ch in server)):
        raise ConfigurationError("Server must be a bare HTTPS origin")
    if port is not None and not 1 <= port <= 65535:
        raise ConfigurationError("Invalid server port")
    return server.rstrip("/")

def validate_config(data):
    if not isinstance(data, dict) or set(data) != {"server", "ca_cert"}:
        raise ConfigurationError("Configuration requires server and ca_cert")
    server = validate_server(data["server"])
    ca = data["ca_cert"]
    if not isinstance(ca, str) or not ca.startswith("/") or "\x00" in ca:
        raise ConfigurationError("CA path must be absolute")
    return {"server": server, "ca_cert": ca}

def load_config(path=DEFAULT_CONFIG):
    path = Path(path)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            raise ConfigurationError("Unsafe configuration file")
        return validate_config(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise ConfigurationError("Agent is not configured; run installer setup") from exc
    except (OSError, ValueError) as exc:
        raise ConfigurationError("Invalid agent configuration") from exc

def connection(server=None, ca_cert=None):
    if server is not None:
        validate_server(server)
    if server is None or ca_cert is None:
        config = load_config()
        server = config["server"] if server is None else server
        ca_cert = config["ca_cert"] if ca_cert is None else ca_cert
    return validate_server(server), Path(ca_cert)
