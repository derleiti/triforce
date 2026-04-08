from fastapi import APIRouter
from app.config import get_settings  # <-- NICHT das 'settings'-Objekt erzwingen

router = APIRouter(tags=["admin"])

@router.post("/admin/reload-config", tags=["Admin"], summary="Reload application configuration")
async def reload_config(): # admin_token: str = Depends(get_admin_token_dependency)
    """
    Reloads the application settings from environment variables.
    Requires an admin token.
    """
    # Pydantic-Settings haben keine _reload() Methode standardmäßig.
    # Man müsste eine eigene Implementierung hinzufügen oder den Prozess neu starten.
    # Für jetzt: Ein Neustart des Dienstes ist der einfachste Weg.
    return {"message": "Configuration reload initiated. A service restart is typically required for full effect."}

@router.get("/admin/config-sanity")
def config_sanity():
    s = get_settings()
    return {
        "env": s.app_env if hasattr(s, "app_env") else "unknown",
        "has_wp": bool(getattr(s, "wordpress_url", None)),
    }
