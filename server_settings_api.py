"""Admin-only settings preview endpoints; no live configuration reload."""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from admin_auth import require_admin
from server_settings import DEFAULT_PATH, SettingsError, load, save

router = APIRouter(prefix='/api/v1/admin/settings', tags=['admin-settings'], dependencies=[Depends(require_admin)])

class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    public_url: str | None = None
    enrollment_enabled: bool | None = None
    reporting_enabled: bool | None = None
    scan_interval_minutes: int | None = None
    appearance: str | None = None
    tls_mode: str | None = None

def path():
    return os.environ.get('ARBY_SETTINGS_PATH', str(DEFAULT_PATH))

@router.get('')
def get_settings():
    try:
        return {'settings': load(path()), 'applied': False}
    except SettingsError as exc:
        raise HTTPException(409, str(exc)) from exc

@router.patch('')
def patch_settings(patch: SettingsPatch):
    changes = patch.model_dump(exclude_unset=True)
    try:
        return {'settings': save(changes, path()), 'applied': False}
    except SettingsError as exc:
        raise HTTPException(422, str(exc)) from exc
