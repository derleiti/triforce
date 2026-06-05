import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.config import get_settings
from app.services import vision
from app.services.model_registry import registry as model_registry

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
    prompt: Optional[str] = "Analyze this image and identify all objects. Return bounding boxes with labels and confidence scores in JSON format: {boxes: [{x, y, w, h, label, conf}]}"
    model: Optional[str] = None

@router.post("/overlay-data", dependencies=[Depends(verify_api_key)])
async def overlay_data(payload: ImageURLPayload):
    """
    Vision-Analyse für Overlay-Daten (Objekterkennung).

    Nutzt Gemini, Ollama oder Anthropic Vision-Modelle für die Analyse.
    """
    logger.debug("Received vision overlay request for image_url: %s", payload.image_url)

    try:
        # Model auswählen - bevorzuge Gemini für Vision
        model_id = payload.model
        if not model_id:
            # Versuche ein Vision-fähiges Model zu finden
            for preferred in ["gemini/gemini-2.0-flash", "gemini/gemini-1.5-flash", "ollama/llava", "anthropic/claude-sonnet-4"]:
                model_info = await model_registry.get_model(preferred)
                if model_info:
                    model_id = preferred
                    break

        if not model_id:
            raise HTTPException(status_code=503, detail="No vision model available")

        model_info = await model_registry.get_model(model_id)
        if not model_info:
            raise HTTPException(status_code=400, detail=f"Model not found: {model_id}")

        # Vision-Analyse durchführen
        result = await vision.analyze_from_url(
            model=model_info,
            request_model=model_id,
            image_url=payload.image_url,
            prompt=payload.prompt
        )

        # Versuche JSON aus der Antwort zu extrahieren
        import json
        import re

        # Suche nach JSON in der Antwort
        json_match = re.search(r'\{[^{}]*"boxes"[^{}]*\[.*?\][^{}]*\}', result, re.DOTALL)
        if json_match:
            try:
                return JSONResponse(json.loads(json_match.group()))
            except json.JSONDecodeError:
                pass

        # Fallback: Rohe Antwort als Text zurückgeben
        return JSONResponse({
            "boxes": [],
            "raw_response": result,
            "message": "Vision analysis completed but no structured boxes found"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Vision analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")