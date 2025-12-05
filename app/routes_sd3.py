from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Annotated, Optional

from app.services.sd3 import sd3_service
from app.schemas.sd3 import ImageGenerationRequest
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()
API_KEY = settings.stable_diffusion_api_key

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

@router.post("/images/generate")
async def generate_image(
    request: ImageGenerationRequest
):
    logger.debug("Received image generation request: %s", request.model_dump_json())
    try:
        result = await sd3_service.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            sampler_name=request.sampler_name,
            seed=request.seed,
            model=request.model,
        )
        return JSONResponse(result)
    except ValidationError as e:
        logger.error("ImageGenerationRequest validation error: %s", e.json())
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        logger.exception("Error during image generation: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/mask-inpaint", dependencies=[Depends(verify_api_key)])
async def mask_inpaint(
    image: UploadFile,
    mask: UploadFile,
    prompt: Annotated[str, Form()],
    strength: Annotated[float, Form(ge=0.0, le=1.0)] = 0.7,
):
    # Größenlimits für Uploads (z.B. 5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    if (image.size and image.size > MAX_FILE_SIZE) or (mask.size and mask.size > MAX_FILE_SIZE):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size too large")

    # Dateityp-Validierung (optional, aber empfohlen)
    if image.content_type not in ["image/png", "image/jpeg"] or mask.content_type not in ["image/png"]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported media type")

    # TODO: SD3-Pipeline anstoßen, Files zwischenspeichern, Job ausführen
    # Für diese Demo lesen wir die Dateien nicht wirklich oder verarbeiten sie.
    # In einer echten Implementierung würden Sie hier die Inhalte lesen:
    # image_content = await image.read()
    # mask_content = await mask.read()

    logger.debug("Received inpaint request: prompt='%s', strength=%s", prompt, strength)
    logger.debug("Image: %s (%s, %s bytes)", image.filename, image.content_type, image.size)
    logger.debug("Mask: %s (%s, %s bytes)", mask.filename, mask.content_type, mask.size)

    # Simulierte Rückgabe
    return JSONResponse({"image_url": "/media/out/inpainted_001.png"})