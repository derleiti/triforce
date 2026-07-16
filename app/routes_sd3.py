from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from typing import Annotated, Optional
import base64

from app.schemas.sd3 import ImageGenerationRequest
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()
API_KEY = settings.stable_diffusion_api_key

# Provider prefixes that should bypass ComfyUI and route to nova_frontend._image_proxy
_KNOWN_PREFIXES = (
    "replicate/", "cloudflare/", "@cf/", "openrouter/", "hf/",
    "gemini/", "openai/", "anthropic/", "ollama/",
    "mistral/", "groq/", "cerebras/", "github/",
)
_REPLICATE_OWNERS = (
    "black-forest-labs/", "stability-ai/", "ideogram-ai/", "recraft-ai/",
    "bytedance/", "meta/", "mistralai/", "deepseek-ai/", "snowflake/",
    "ibm-granite/", "minimax/", "kwaivgi/", "lightricks/", "tencent/",
    "google/", "openai/", "suno-ai/", "lucataco/", "hexgrad/",
    "riffusion/", "vaibhavs10/", "replicate/",
)


def _normalize_image_model(model: str) -> str:
    """Add provider prefix when frontend strips it. @cf/X -> cloudflare/@cf/X,
    bare 'owner/name' -> replicate/owner/name."""
    if not model:
        return model
    m = model.lower()
    if m.startswith("@cf/"):
        return f"cloudflare/{model}"
    if any(m.startswith(p) for p in _KNOWN_PREFIXES):
        return model
    if "gpt-image" in m or "dall-e" in m:
        return model
    # Bare owner/name → assume Replicate
    if "/" in model and any(m.startswith(p) for p in _REPLICATE_OWNERS):
        return f"replicate/{model}"
    return model


def _is_cloud_provider_model(model: str) -> bool:
    """True if normalized model belongs to a cloud provider (not ComfyUI)."""
    if not model:
        return False
    m = model.lower()
    if m.startswith(("replicate/", "cloudflare/", "openrouter/", "hf/", "@cf/")):
        return True
    if "gpt-image" in m or "dall-e" in m:
        return True
    if m.startswith("gemini/") and any(x in m for x in
            ("imagen", "nano-banana", "flash-image", "pro-image")):
        return True
    if any(m.startswith(p) for p in _REPLICATE_OWNERS):
        return True
    return False


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")


@router.post("/images/generate")
async def generate_image(
    request: ImageGenerationRequest
):
    logger.debug("Received image generation request: %s", request.model_dump_json())

    # ── Cloud-provider short-circuit ─────────────────────────────────────
    # If the requested model is a cloud-provider model (Replicate FLUX/SDXL,
    # Cloudflare Workers AI, Gemini Imagen/Nano Banana, OpenRouter image,
    # OpenAI gpt-image/DALL-E, HuggingFace), delegate to nova_frontend's
    # _image_proxy which knows each provider's API. Avoids the ComfyUI 503.
    canonical = _normalize_image_model(request.model or "")
    if _is_cloud_provider_model(canonical):
        try:
            from app.routes.nova_frontend import _image_proxy, ImageRequest
            logger.info("Routing /v1/images/generate model '%s' (canonical '%s') to cloud provider proxy",
                        request.model, canonical)
            proxy_req = ImageRequest(
                model=canonical,
                prompt=request.prompt,
                size=f"{request.width}x{request.height}",
                quality="medium",
                n=1,
            )
            proxy_result = await _image_proxy(proxy_req)
            # Convert _image_proxy response → /v1/images/generate response shape
            # The frontend expects images as data: URLs (data:image/png;base64,...)
            # — same format as the legacy ComfyUI path. Raw base64 alone is not
            # enough; the JS sets <img src="..."> directly.
            data_blocks = (proxy_result.get("result", {}) or {}).get("data", []) or []
            data_urls = []
            for item in data_blocks:
                if not isinstance(item, dict):
                    continue
                if item.get("b64_json"):
                    ct = item.get("content_type", "image/png") or "image/png"
                    data_urls.append(f"data:{ct};base64,{item['b64_json']}")
                elif item.get("url"):
                    # Replicate-style: fetch URL and inline as data: URL
                    try:
                        import httpx
                        async with httpx.AsyncClient(timeout=60.0) as cli:
                            r = await cli.get(item["url"])
                            if r.status_code == 200:
                                ct = r.headers.get("content-type", "image/png").split(";")[0]
                                b64 = base64.b64encode(r.content).decode("utf-8")
                                data_urls.append(f"data:{ct};base64,{b64}")
                            else:
                                logger.warning("Could not fetch Replicate image %s: HTTP %d",
                                               item["url"], r.status_code)
                    except Exception as fetch_exc:
                        logger.warning("Image URL fetch failed: %s", fetch_exc)
            if not data_urls:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Provider '{proxy_result.get('provider', 'unknown')}' returned no image data",
                )
            return JSONResponse({
                "images": data_urls,
                "model": canonical,
                "provider": proxy_result.get("provider", "cloud"),
            })
        except HTTPException:
            # _image_proxy raises clean HTTPExceptions (paid-tier gates, missing keys etc.)
            raise
        except Exception as e:
            logger.exception("Cloud provider proxy failed for '%s': %s", canonical, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cloud provider error: {e}",
            )

    # Cloud-provider routing is the only supported path. If the model didn't
    # match _is_cloud_provider_model() above, return a clear error pointing
    # the caller at supported providers. The legacy ComfyUI/A1111 sd3_service
    # has been removed (we no longer self-host GPU inference).
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Model '{request.model}' is not a recognized cloud provider model. "
            "Supported prefixes: replicate/, cloudflare/, openrouter/, gemini/ "
            "(imagen/nano-banana/flash-image/pro-image), openai/. "
            "Local ComfyUI/A1111 routing has been removed."
        ),
    )

