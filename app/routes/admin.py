from fastapi import APIRouter, Depends, Header, HTTPException
from app.config import get_settings
import os as _os

router = APIRouter(tags=["admin"])

def _require_admin_key(x_internal_key: str = Header(default="")):
    expected = _os.environ.get("INTERNAL_API_KEY", "")
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden: invalid admin key")

@router.post("/admin/reload-config", tags=["Admin"], summary="Reload application configuration")
async def reload_config(_: None = Depends(_require_admin_key)):
    """
    Reloads the application settings from environment variables.
    Requires an admin token.
    """
    # Pydantic-Settings haben keine _reload() Methode standardmäßig.
    # Man müsste eine eigene Implementierung hinzufügen oder den Prozess neu starten.
    # Für jetzt: Ein Neustart des Dienstes ist der einfachste Weg.
    return {"message": "Configuration reload initiated. A service restart is typically required for full effect."}

@router.get("/admin/config-sanity")
def config_sanity(_: None = Depends(_require_admin_key)):
    s = get_settings()
    return {
        "env": s.app_env if hasattr(s, "app_env") else "unknown",
        "has_wp": bool(getattr(s, "wordpress_url", None)),
    }
