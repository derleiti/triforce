"""
Text-to-Image API routes using the ComfyUI backend.

This module exposes synchronous and streaming endpoints that orchestrate
ComfyUI workflows for Stable Diffusion based image generation.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

# Allow importing the local comfy_client helper
sys.path.append(os.getcwd())

from app.config import get_settings
from app.schemas.txt2img import ImageData, Txt2ImgRequest, Txt2ImgResponse
from app.services.model_registry import registry
import comfy_client

logger = logging.getLogger("ailinux.txt2img")
router = APIRouter()

# Global ComfyUI client instance (shared across requests)
_comfy_client = None

# Keywords that hint at workflow selection
_SD35_MODEL_HINTS = ("sd3.5", "sd35", "sd 3.5", "sd-3.5", "sd3_5")
_SDXL_MODEL_HINTS = ("sdxl", "xl", "flux")

# Default SD 3.5 supporting model filenames (must exist under ComfyUI /models)
_SD35_CLIP_G = "clip_g_sd35.safetensors"
_SD35_CLIP_L = "clip_l_sd35.safetensors"
_SD35_T5 = "t5xxl_fp16_sd35.safetensors"  # Using fp16 for better quality with 24GB VRAM


def get_comfy_client():
    """Return a cached ComfyUI client instance (initialise on first use)."""
    global _comfy_client
    if _comfy_client is None:
        settings = get_settings()
        if not settings.comfyui_url:
            raise HTTPException(
                status_code=503,
                detail={"error": {"message": "ComfyUI URL is not configured", "code": "comfyui_unavailable"}},
            )

        _comfy_client = comfy_client.ComfyUIClient(
            base_url=str(settings.comfyui_url),
            username=settings.stable_diffusion_username,
            password=settings.stable_diffusion_password,
            timeout=settings.request_timeout,
        )
    return _comfy_client


async def _select_default_model() -> Optional[str]:
    """Return the first image-capable model from the registry or fall back to configured defaults."""
    settings = get_settings()

    try:
        models = await registry.list_models()
        for model in models:
            if "image_gen" in (model.capabilities or []):
                logger.debug("Selected registry image model '%s' as default", model.id)
                return model.id
    except Exception as exc:  # pragma: no cover - network errors are best-effort
        logger.warning("Unable to load model registry for image defaults: %s", exc)

    fallback = [
        name.strip()
        for name in (settings.stable_diffusion_default_models or "").split(",")
        if name.strip()
    ]
    if fallback:
        logger.debug("Falling back to configured Stable Diffusion defaults: %s", fallback[0])
        return fallback[0]
    return None


def _normalize_dimension(value: int) -> int:
    """Clamp dimension to the supported range (64-4096) and snap to multiples of 64 for ComfyUI."""
    clamped = max(64, min(4096, value))
    remainder = clamped % 64
    if remainder:
        snapped = clamped - remainder
        if snapped < 64:
            snapped = 64
        logger.debug("Adjusted dimension from %s to %s to satisfy 64px alignment", value, snapped)
        return snapped
    return clamped


def _calculate_timeout(width: int, height: int, workflow_type: str) -> int:
    """
    Calculate dynamic timeout based on image resolution and workflow complexity.

    Timeout calculation:
    - Base timeout depends on workflow type (SD 1.5 is fastest, SD3.5 is slowest)
    - Scales linearly with total pixel count
    - Examples:
      - SD 1.5 @ 512x512: ~180s (3 min)
      - SDXL @ 1024x1024: ~480s (8 min)
      - SD3.5 @ 2048x2048: ~900s (15 min)
      - 4K @ 3840x2160: ~1200s (20 min)

    Args:
        width: Image width in pixels
        height: Image height in pixels
        workflow_type: Type of workflow ('sd15', 'sdxl', 'sd35')

    Returns:
        Timeout in seconds
    """
    total_pixels = width * height

    # Base timeout per megapixel (1M pixels) for each workflow type
    # SD 1.5: 70s per MP, SDXL: 100s per MP, SD3.5: 200s per MP (slower due to triple CLIP + T5)
    timeout_per_megapixel = {
        'sd15': 70,
        'sdxl': 100,
        'sd35': 200,  # SD3.5 is significantly slower due to triple text encoders
    }

    base_rate = timeout_per_megapixel.get(workflow_type, 100)
    megapixels = total_pixels / 1_000_000

    # Calculate timeout with a minimum of 240s (4 min) and maximum of 1800s (30 min)
    # Minimum accounts for model loading time on first generation
    calculated_timeout = int(base_rate * megapixels)
    timeout = max(240, min(1800, calculated_timeout))

    logger.info(
        "Calculated timeout for %dx%d (%s workflow, %.2f MP): %d seconds (%.1f minutes)",
        width, height, workflow_type, megapixels, timeout, timeout / 60
    )

    return timeout


def _resolve_workflow_type(model: str, requested: Optional[str]) -> str:
    """Resolve the workflow type to execute based on the model name and user preference."""
    option = (requested or "auto").lower()
    if option not in {"auto", "sd15", "sd35", "sdxl"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Unsupported workflow type '{requested}'. Use 'auto', 'sd15', 'sd35', or 'sdxl'.",
                    "code": "invalid_workflow",
                }
            },
        )

    lowered = model.lower()
    if option == "auto":
        lowered = model.lower()
        if any(hint in lowered for hint in _SD35_MODEL_HINTS):
            return "sd35"
        if any(hint in lowered for hint in _SDXL_MODEL_HINTS):
            return "sdxl"
        return "sd15"
    # Force SD3.5 workflow even if caller requested SDXL/SD15
    if option != "sd35" and any(hint in lowered for hint in _SD35_MODEL_HINTS):
        logger.debug("Overriding workflow '%s' to sd35 for model '%s'", option, model)
        return "sd35"
    return option


async def _create_workflow(request: Txt2ImgRequest, model: str, workflow_type: str, width: int, height: int) -> dict:
    """Build the appropriate ComfyUI workflow payload."""
    workflow_kwargs = {
        "prompt": request.prompt,
        "negative_prompt": request.negative_prompt or "",
        "width": width,
        "height": height,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "seed": request.seed,
        "model_name": model,
    }

    if workflow_type == "sd35":
        logger.debug("Creating SD3.5 workflow for model '%s'", model)
        return await comfy_client.create_sd35_workflow(
            clip_g_name=_SD35_CLIP_G,
            clip_l_name=_SD35_CLIP_L,
            t5_name=_SD35_T5,
            **workflow_kwargs,
        )

    if workflow_type == "sdxl":
        logger.debug("Creating SDXL workflow for model '%s'", model)
        return await comfy_client.create_sdxl_workflow(**workflow_kwargs)

    logger.debug("Creating SD 1.5 workflow for model '%s'", model)
    return await comfy_client.create_minimal_workflow(**workflow_kwargs)


async def _collect_images(
    client: comfy_client.ComfyUIClient,
    result_payload: dict,
    requested_seed: int,
) -> List[ImageData]:
    """Download generated images from the ComfyUI history payload."""
    images: List[ImageData] = []
    outputs = result_payload.get("outputs") or {}

    for node_output in outputs.values():
        for image_info in node_output.get("images", []):
            filename = image_info.get("filename")
            if not filename:
                continue

            try:
                image_bytes = await client.download_output_image(
                    filename=filename,
                    subfolder=image_info.get("subfolder", ""),
                    image_type=image_info.get("type", "output"),
                )
            except Exception as exc:  # pragma: no cover - network failure
                logger.error("Failed to download ComfyUI image '%s': %s", filename, exc)
                continue

            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            image_seed = image_info.get("seed")
            if image_seed is None and requested_seed != -1:
                image_seed = requested_seed

            images.append(
                ImageData(
                    filename=filename,
                    data=b64_data,
                    seed=image_seed,
                )
            )

    return images


def _encode_event(payload: dict) -> str:
    """Serialise a server-sent event payload."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/txt2img", response_model=Txt2ImgResponse)
async def generate_image(request: Txt2ImgRequest) -> Txt2ImgResponse:
    """Generate an image synchronously via ComfyUI."""
    try:
        client = get_comfy_client()
        model = request.model or await _select_default_model()
        if not model:
            return Txt2ImgResponse(
                images=[],
                error="No image generation models are registered. Add a ComfyUI checkpoint to continue.",
            )

        workflow_type = _resolve_workflow_type(model, request.workflow_type)
        width = _normalize_dimension(request.width)
        height = _normalize_dimension(request.height)

        workflow = await _create_workflow(request, model, workflow_type, width, height)

        # Calculate dynamic timeout based on resolution
        timeout = _calculate_timeout(width, height, workflow_type)

        logger.info("Submitting txt2img request with model '%s' (workflow: %s)", model, workflow_type)
        prompt_id = await client.submit_prompt(workflow)

        logger.debug("Waiting for ComfyUI prompt '%s' to complete (timeout: %ds)", prompt_id, timeout)
        result = await client.wait_for_result(prompt_id, max_wait=timeout)

        images = await _collect_images(client, result, request.seed)
        if not images:
            logger.warning("ComfyUI completed prompt '%s' without returning images", prompt_id)
            return Txt2ImgResponse(
                images=[],
                prompt_id=prompt_id,
                model=model,
                workflow_type=workflow_type,
                error="No images were generated",
            )

        logger.info("Generated %s image(s) for prompt '%s'", len(images), prompt_id)
        return Txt2ImgResponse(
            images=images,
            prompt_id=prompt_id,
            model=model,
            workflow_type=workflow_type,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in txt2img generation: %s", exc, exc_info=True)
        return Txt2ImgResponse(
            images=[],
            error=str(exc),
        )


@router.get("/txt2img/queue")
async def get_queue_status():
    """Return the ComfyUI queue status."""
    try:
        client = get_comfy_client()
        return await client.get_queue_status()
    except Exception as exc:
        logger.error("Error getting queue status: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to get queue status", "code": "queue_status_error"}},
        ) from exc


@router.post("/txt2img/stream")
async def generate_image_stream(request: Txt2ImgRequest):
    """Generate images with a streaming server-sent event response."""

    async def generate():
        try:
            client = get_comfy_client()
            model = request.model or await _select_default_model()
            if not model:
                yield _encode_event(
                    {
                        "status": "error",
                        "error": "No image generation models are registered. Add a ComfyUI checkpoint to continue.",
                    }
                )
                return

            workflow_type = _resolve_workflow_type(model, request.workflow_type)
            width = _normalize_dimension(request.width)
            height = _normalize_dimension(request.height)
            workflow = await _create_workflow(request, model, workflow_type, width, height)

            # Calculate dynamic timeout based on resolution
            timeout = _calculate_timeout(width, height, workflow_type)

            prompt_id = await client.submit_prompt(workflow)
            yield _encode_event(
                {
                    "status": "submitted",
                    "prompt_id": prompt_id,
                    "model": model,
                    "workflow_type": workflow_type,
                    "timeout": timeout,
                }
            )

            result = await client.wait_for_result(prompt_id, max_wait=timeout)
            images = await _collect_images(client, result, request.seed)

            if images:
                payload = {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "model": model,
                    "workflow_type": workflow_type,
                    "images": [image.model_dump() for image in images],
                }
            else:
                payload = {
                    "status": "error",
                    "error": "No images generated",
                    "prompt_id": prompt_id,
                    "model": model,
                    "workflow_type": workflow_type,
                }

            yield _encode_event(payload)

        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                message = detail.get("error", {}).get("message", str(exc))
            else:
                message = str(detail)

            yield _encode_event({"status": "error", "error": message})

        except Exception as exc:  # pragma: no cover - network failure
            logger.error("Error in streaming txt2img: %s", exc, exc_info=True)
            yield _encode_event({"status": "error", "error": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
