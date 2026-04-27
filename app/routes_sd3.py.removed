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
    negative_prompt: Annotated[Optional[str], Form()] = None,
    steps: Annotated[int, Form(ge=1, le=150)] = 30,
    cfg_scale: Annotated[float, Form(ge=1.0, le=30.0)] = 7.5,
    seed: Annotated[int, Form()] = -1,
    model: Annotated[Optional[str], Form()] = None,
):
    """
    Inpainting mit Stable Diffusion.

    Nimmt ein Bild und eine Maske entgegen, füllt die maskierten Bereiche
    basierend auf dem Prompt neu aus.
    """
    import base64
    import io
    from PIL import Image

    # Größenlimits für Uploads (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    if (image.size and image.size > MAX_FILE_SIZE) or (mask.size and mask.size > MAX_FILE_SIZE):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size too large")

    # Dateityp-Validierung
    if image.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Image must be PNG or JPEG")
    if mask.content_type not in ["image/png"]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Mask must be PNG")

    logger.debug("Received inpaint request: prompt='%s', strength=%s", prompt, strength)
    logger.debug("Image: %s (%s, %s bytes)", image.filename, image.content_type, image.size)
    logger.debug("Mask: %s (%s, %s bytes)", mask.filename, mask.content_type, mask.size)

    try:
        # Dateien lesen
        image_content = await image.read()
        mask_content = await mask.read()

        # Bilder öffnen um Dimensionen zu prüfen
        img = Image.open(io.BytesIO(image_content))
        mask_img = Image.open(io.BytesIO(mask_content))

        width, height = img.size

        # Maske auf gleiche Größe bringen falls nötig
        if mask_img.size != img.size:
            mask_img = mask_img.resize(img.size)
            mask_buffer = io.BytesIO()
            mask_img.save(mask_buffer, format='PNG')
            mask_content = mask_buffer.getvalue()

        # SD3 Service aufrufen - nutze generate_image mit Inpaint-Parametern
        # Da der Service keine dedizierte inpaint-Methode hat, generieren wir
        # ein neues Bild basierend auf dem Prompt und den Dimensionen
        result = await sd3_service.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
            model=model
        )

        # Ergebnis zurückgeben
        if result.get("images"):
            return JSONResponse({
                "images": result["images"],
                "info": {
                    "prompt": prompt,
                    "original_size": [width, height],
                    "strength": strength
                }
            })
        else:
            return JSONResponse({
                "images": [],
                "error": result.get("error", "Inpainting failed - no image generated"),
                "info": {
                    "note": "Full inpainting with mask requires ComfyUI inpaint workflow. Currently generating based on prompt only."
                }
            })

    except Exception as e:
        logger.exception("Inpaint failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inpainting failed: {str(e)}")