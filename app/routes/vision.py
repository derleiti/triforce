from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field, HttpUrl

from ..services.model_registry import registry
from ..services import vision as vision_service
from ..utils.errors import api_error
from ..utils.throttle import request_slot

import logging

router = APIRouter(tags=["vision"])

logger = logging.getLogger("ailinux.vision.routes")


class VisionRequest(BaseModel):
    model: str
    image_url: HttpUrl
    prompt: str = Field(..., min_length=1)


@router.post("/images/analyze")
async def analyze_image(payload: VisionRequest) -> dict[str, str]:
    if not payload.image_url:
        raise HTTPException(status_code=400, detail="Image URL is required for vision models.")
    try:
        model = await registry.get_model(payload.model)
        if not model or "vision" not in model.capabilities:
            raise api_error("Requested model does not support vision analysis", status_code=404, code="model_not_found")

        async with request_slot():
            text = await vision_service.analyze_from_url(model, payload.model, str(payload.image_url), payload.prompt)
        return {"text": text}
    except Exception as e:
        logger.exception("Error during vision analysis (URL-based): %s", e)
        raise


@router.post("/images/analyze/upload")
async def analyze_image_upload(
    model: str = Form(...),
    prompt: str = Form(...),
    image_file: UploadFile = File(...),
) -> dict[str, str]:
    try:
        entry = await registry.get_model(model)
        if not entry or "vision" not in entry.capabilities:
            raise api_error("Requested model does not support vision analysis", status_code=404, code="model_not_found")

        data = await image_file.read()
        if not data:
            logger.error("Image upload was empty for vision analysis", extra={"code": "empty_upload"})
            raise api_error("Image upload was empty", status_code=422, code="empty_upload")

        async with request_slot():
            text = await vision_service.analyze_from_upload(
                entry,
                model,
                prompt,
                data,
                image_file.content_type,
                image_file.filename,
            )
        return {"text": text}
    except Exception as e:
        logger.exception("Error during vision analysis (upload-based): %s", e)
        raise
