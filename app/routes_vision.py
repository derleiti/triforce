import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision")

# API-Key aus Settings laden (nicht hardcoded!)
settings = get_settings()

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Verify API key from settings - shared auth for vision endpoints."""
    expected_key = settings.stable_diffusion_api_key
    if not expected_key:
        # Kein API-Key konfiguriert = Endpoint deaktiviert
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vision API not configured")
    if x_api_key is None or x_api_key != expected_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

class ImageURLPayload(BaseModel):
    image_url: str

@router.post("/overlay-data", dependencies=[Depends(verify_api_key)])
async def overlay_data(payload: ImageURLPayload):
    # TODO: Vision-Analyse durchführen
    # In einer echten Implementierung würde hier die image_url verarbeitet werden
    logger.debug("Received vision overlay request for image_url: %s", payload.image_url)

    demo = {
        "boxes": [
            {"x":120,"y":90,"w":220,"h":160,"label":"Katze","conf":0.92},
            {"x":480,"y":240,"w":150,"h":100,"label":"Tasse","conf":0.81}
        ]
    }
    return JSONResponse(demo)