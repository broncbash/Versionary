"""Opt-in, loopback-only HTTPS beta. Not a production deployment."""
import argparse
import hashlib
import os
import secrets
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / ".versionary-https-beta"
CERTS = STATE / "certs"
DB = STATE / "agents.db"
AUTH = STATE / "admin-token"


def require_private_directory(path):
    if path.is_symlink():
        raise RuntimeError("Refusing symlinked beta state directory")
    if path.exists():
        mode = path.stat().st_mode
        if not stat.S_ISDIR(mode) or mode & 0o077:
            raise RuntimeError("Beta state directory must be private")
    else:
        path.mkdir(mode=0o700)


def prepare_state():
    require_private_directory(STATE)
    if not AUTH.exists():
        fd = os.open(
            AUTH,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(36) + "\\n")
    if AUTH.is_symlink() or AUTH.stat().st_mode & 0o077:
        raise RuntimeError("Admin token must be a private regular file")
    if not stat.S_ISREG(AUTH.stat().st_mode):
        raise RuntimeError("Invalid admin token file")


def require_private_file(path):
    if path.is_symlink():
        raise RuntimeError("Refusing symlinked beta credential or key")

    mode = path.stat().st_mode

    if not stat.S_ISREG(mode):
        raise RuntimeError("Expected a regular file")

    if mode & 0o077:
        raise RuntimeError("Private file permissions are too broad")


def validate_certificates():
    require_private_directory(CERTS)

    require_private_file(CERTS / "ca.key")
    require_private_file(CERTS / "server.key")

    for name in ("ca.crt", "server.crt"):
        path = CERTS / name

        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise RuntimeError("Invalid certificate file")


def configure():
    prepare_state()
    import agent_registry
    agent_registry.DB_PATH = DB
    agent_registry.initialize_database()
    os.environ["ARBY_ADMIN_TOKEN_HASH"] = hashlib.sha256(
        AUTH.read_text().strip().encode()
    ).hexdigest()
    # Isolated HTTPS beta features require explicit opt-in.
    # Neither enrollment nor reporting is enabled by default.
    os.environ["ARBY_AGENT_REPORTING_ENABLED"] = (
        "true"
        if os.environ.get("VERSIONARY_BETA_REPORTING") == "true"
        else "false"
    )
    os.environ["ARBY_ENROLLMENT_V2_ENABLED"] = (
        "true"
        if os.environ.get("VERSIONARY_BETA_ENROLLMENT") == "true"
        else "false"
    )
    os.environ["ARBY_SETTINGS_RUNTIME_ENABLED"] = "false"


def create_app():
    configure()
    from fastapi import FastAPI
    from admin_agents_api import router as inventory
    from versionary_https_beta_admin import router as administration
    from dashboard_ui import router as dashboard
    from agent_reporting_api import router as reporting
    from enrollment_v2_api import router as enrollment

    app = FastAPI(
        title="Versionary Isolated HTTPS Beta",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    for router in (inventory, administration, dashboard, reporting, enrollment):
        app.include_router(router)

    @app.get("/health")
    def health():
        return {
            "status": "online",
            "mode": "isolated-https-beta",
            "production": False,
        }

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "serve", "status"))
    args = parser.parse_args()

    if args.command == "status":
        print("State directory exists:", STATE.exists())
        print("Certificates exist:", (CERTS / "server.crt").exists())
        return

    prepare_state()

    if args.command == "init":
        if CERTS.exists():
            raise SystemExit("Certificates already exist; refusing replacement")
        import importlib.util
        source = ROOT / "installer/generate-certificates.py"
        spec = importlib.util.spec_from_file_location("versionary_certgen", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate("127.0.0.1", CERTS)
        configure()
        print("[OK] Isolated HTTPS beta initialized")
        print("Server URL: https://127.0.0.1:8766")
        print("CA certificate:", CERTS / "ca.crt")
        print("Admin token stored privately:", AUTH)
        return

    if not (CERTS / "server.crt").is_file():
        raise SystemExit("Run init before serve")

    validate_certificates()
    app = create_app()

    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8766,
        ssl_certfile=str(CERTS / "server.crt"),
        ssl_keyfile=str(CERTS / "server.key"),
        log_level="info",
    )


if __name__ == "__main__":
    main()
