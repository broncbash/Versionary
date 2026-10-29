"""Read-only administrator inventory for beta dashboard; no agent activation."""
import sqlite3
from contextlib import closing

from fastapi import APIRouter, Depends, HTTPException
from admin_auth import require_admin
import agent_registry

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/agents")
def list_agents(_: None = Depends(require_admin)):
    """List registered agents and their latest reports without exposing secrets."""
    path = agent_registry.DB_PATH
    if not path.is_file():
        return {"agents": [], "count": 0}
    try:
        # Read-only URI avoids accidentally creating or modifying the database.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""
                SELECT a.id, a.hostname, a.platform, a.status,
                       a.registered_at, a.last_seen,
                       (SELECT r.timestamp FROM scan_reports r
                        WHERE r.agent_id = a.id
                        ORDER BY r.timestamp DESC, r.id DESC LIMIT 1) AS scan_at,
                       (SELECT r.status FROM scan_reports r
                        WHERE r.agent_id = a.id
                        ORDER BY r.timestamp DESC, r.id DESC LIMIT 1) AS scan_status,
                       (SELECT r.count FROM scan_reports r
                        WHERE r.agent_id = a.id
                        ORDER BY r.timestamp DESC, r.id DESC LIMIT 1) AS updates
                FROM agents a ORDER BY a.hostname COLLATE NOCASE, a.id
            """).fetchall()
    except (sqlite3.DatabaseError, OSError):
        raise HTTPException(status_code=503, detail="Agent inventory unavailable") from None
    agents = [dict(row) for row in rows]
    return {"agents": agents, "count": len(agents)}
