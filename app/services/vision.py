from __future__ import annotations

import asyncio
import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import httpx
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    _GENAI_AVAILABLE = False
from PIL import Image
import io

from ..config import get_settings
from ..services.model_registry import ModelInfo
from ..utils.errors import api_error
from ..utils.http import extract_http_error
from ..utils.http_client import HttpClient
from ..utils.model_helpers import strip_provider_prefix

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB

# Anthropic Claude model aliases for vision
ANTHROPIC_VISION_ALIASES = {
    "anthropic/claude-sonnet-4": "claude-sonnet-4-20250514",
    "anthropic/claude-opus-4": "claude-opus-4-20250514",
    "anthropic/claude-3.5-sonnet": "claude-sonnet-4-20250514",
    "anthropic/claude-3.5-haiku": "claude-3-5-haiku-20241022",
    "anthropic/claude-3-opus": "claude-3-opus-20240229",
    "anthropic/claude-3-sonnet": "claude-3-sonnet-20240229",
    "anthropic/claude-3-haiku": "claude-3-haiku-20240307",
    "anthropic/claude": "claude-sonnet-4-20250514",
    "claude": "claude-sonnet-4-20250514",
}
TEMP_RETENTION_SECONDS = 120


async def analyze(
    model: ModelInfo,
    request_model: str,
    prompt: str,
    image_url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    content_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    if not prompt.strip():
        raise api_error("Prompt is required", status_code=422, code="missing_prompt")

    if image_bytes is None and not image_url:
        raise api_error("Either image_url or image data is required", status_code=422, code="missing_image")

    # Validate size
    if image_bytes is not None:
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise api_error(
                f"Image exceeds maximum allowed size ({MAX_IMAGE_BYTES} bytes).",
                status_code=413,
                code="image_too_large",
            )

    # Validate content type if provided
    ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
    if content_type:
        if content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise api_error(
                f"Unsupported image content type: {content_type}.",
                status_code=415,
                code="unsupported_image_type",
            )

    # If only URL provided, we should download and validate size before proceeding for providers
    if image_bytes is None and image_url:
        # try lightweight HEAD first
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(get_settings().request_timeout)) as client:
                head = await client.head(image_url, follow_redirects=True)
                ct = head.headers.get("content-type")
                cl = head.headers.get("content-length")
                if ct and ct.lower() not in ALLOWED_CONTENT_TYPES:
                    raise api_error("Remote image has unsupported content-type.", status_code=415, code="unsupported_remote_image_type")
                if cl and int(cl) > MAX_IMAGE_BYTES:
                    raise api_error("Remote image exceeds maximum allowed size.", status_code=413, code="remote_image_too_large")
        except Exception:
            # fallback: we'll download and validate below in _download_image if needed
            pass

    if image_bytes is not None and content_type is None:
        content_type = "image/png"

    if model.provider == "ollama":
        resolved_bytes = image_bytes
        resolved_name = filename

        if resolved_bytes is None:
            assert image_url is not None
            _, resolved_bytes = await _download_image(image_url)
            if not resolved_name and image_url:
                resolved_name = image_url.split("/")[-1]

        if resolved_bytes is None:
            raise api_error("Image bytes missing", status_code=422, code="missing_image")

        _persist_temp_file(resolved_bytes, resolved_name)
        return await _analyze_with_ollama_data(
            request_model,
            prompt,
            resolved_bytes,
        )

    if model.provider == "gemini":
        settings = get_settings()
        if not settings.gemini_api_key:
            raise api_error("Gemini support is not configured", status_code=503, code="gemini_unavailable")
        if image_bytes is not None:
            _persist_temp_file(image_bytes, filename)
            return await _analyze_with_gemini_data(
                request_model,
                prompt,
                image_bytes,
                api_key=settings.gemini_api_key,
            )
        assert image_url is not None
        return await _analyze_with_gemini_url(
            request_model,
            prompt,
            image_url,
            api_key=settings.gemini_api_key,
        )

    if model.provider == "anthropic":
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise api_error("Anthropic Claude support is not configured", status_code=503, code="anthropic_unavailable")

        resolved_bytes = image_bytes
        resolved_type = content_type or "image/jpeg"

        if resolved_bytes is None:
            assert image_url is not None
            resolved_type, resolved_bytes = await _download_image(image_url)

        if resolved_bytes is None:
            raise api_error("Image bytes missing", status_code=422, code="missing_image")

        # Detect actual MIME from magic bytes
        if len(resolved_bytes) >= 3 and resolved_bytes[0] == 0xFF and resolved_bytes[1] == 0xD8 and resolved_bytes[2] == 0xFF:
            resolved_type = "image/jpeg"
        elif len(resolved_bytes) >= 4 and resolved_bytes[0] == 0x89 and resolved_bytes[1:4] == b"PNG":
            resolved_type = "image/png"
        elif len(resolved_bytes) >= 6 and resolved_bytes[:6] in (b"GIF87a", b"GIF89a"):
            resolved_type = "image/gif"
        elif len(resolved_bytes) >= 12 and resolved_bytes[:4] == b"RIFF" and resolved_bytes[8:12] == b"WEBP":
            resolved_type = "image/webp"
        _persist_temp_file(resolved_bytes, filename)
        return await _analyze_with_anthropic_data(
            request_model,
            prompt,
            resolved_bytes,
            content_type=resolved_type,
            api_key=settings.anthropic_api_key,
            max_tokens=settings.anthropic_max_tokens,
            timeout=settings.anthropic_timeout_ms / 1000.0,
        )

    # ── OpenAI-compat providers (openrouter, github, groq, mistral, cerebras) ──
    if model.provider in _OPENAI_COMPAT_VISION_PROVIDERS:
        if image_bytes is not None:
            return await _analyze_openai_compat_vision(
                model.provider, request_model, prompt,
                image_bytes=image_bytes, content_type=content_type or "image/jpeg",
            )
        else:
            return await _analyze_openai_compat_vision(
                model.provider, request_model, prompt,
                image_url=image_url,
            )

    # ── Cloudflare Workers AI vision ──────────────────────────────────────────
    if model.provider == "cloudflare":
        if image_bytes is not None:
            return await _analyze_cloudflare_vision(
                request_model, prompt,
                image_bytes=image_bytes, content_type=content_type or "image/jpeg",
            )
        else:
            return await _analyze_cloudflare_vision(
                request_model, prompt, image_url=image_url,
            )

    raise api_error("Selected model does not support vision analysis", status_code=400, code="unsupported_provider")


async def analyze_from_url(model: ModelInfo, request_model: str, image_url: str, prompt: str) -> str:
    return await analyze(model, request_model, prompt, image_url=image_url)


async def analyze_from_upload(
    model: ModelInfo,
    request_model: str,
    prompt: str,
    image_bytes: bytes,
    content_type: Optional[str],
    filename: Optional[str],
) -> str:
    return await analyze(
        model,
        request_model,
        prompt,
        image_bytes=image_bytes,
        content_type=content_type,
        filename=filename,
    )


def _persist_temp_file(data: bytes, filename: Optional[str]) -> None:
    suffix = ""
    if filename and "." in filename:
        suffix = filename[filename.rfind("."):]
    fd, temp_path = tempfile.mkstemp(prefix="novaai_upload_", suffix=suffix)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    path = Path(temp_path)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    loop.call_later(
        TEMP_RETENTION_SECONDS,
        lambda: path.exists() and path.unlink(missing_ok=True),
    )


def _optimize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert to RGB to avoid transparency issues/palette modes
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size
            if width > max_size or height > max_size:
                ratio = min(max_size / width, max_size / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            out_io = io.BytesIO()
            img.save(out_io, format='JPEG', quality=85)
            return out_io.getvalue()
    except Exception:
        return image_bytes


async def _analyze_with_ollama_data(
    model: str,
    prompt: str,
    image_bytes: bytes,
) -> str:
    settings = get_settings()
    
    # Optimize image to prevent Ollama OOM/crashes
    image_bytes = _optimize_image(image_bytes)
    
    url = httpx.URL(str(settings.ollama_base)).join("/api/chat")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [encoded],
            }
        ],
        "stream": False,
    }
    try:
        return await _dispatch_ollama(url, body, timeout_ms=settings.ollama_timeout_ms)
    except Exception as exc:
        raise api_error("Ollama vision call failed", status_code=502, code="ollama_vision_failed") from exc


async def _dispatch_ollama(url: httpx.URL, payload: dict, timeout_ms: Optional[int] = None) -> str:
    settings = get_settings()
    timeout = httpx.Timeout(timeout_ms / 1000 if timeout_ms else settings.request_timeout)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.RequestError as exc:
        raise api_error(
            f"Failed to reach Ollama backend: {exc}",
            status_code=502,
            code="ollama_unreachable",
        ) from exc

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message, code = extract_http_error(
            exc.response,
            default_message="Ollama returned an error",
            default_code="ollama_error",
        )
        raise api_error(message, status_code=exc.response.status_code, code=code) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise api_error(
            "Ollama returned malformed JSON",
            status_code=502,
            code="ollama_invalid_response",
        ) from exc

    message = data.get("message") or {}
    text = _extract_ollama_text(message.get("content"))
    if not text:
        text = _extract_ollama_text(data.get("response"))
    if not text:
        raise api_error("Vision model returned no response", status_code=502, code="empty_response")
    return text


def _extract_ollama_text(content: Optional[object]) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item and item["text"]:
                    fragments.append(str(item["text"]))
                elif "content" in item and item["content"]:
                    fragments.append(str(item["content"]))
            elif isinstance(item, str):
                fragments.append(item)
        return "".join(fragments)
    if isinstance(content, dict):
        text_value = content.get("text") or content.get("content")
        if isinstance(text_value, str):
            return text_value
    return str(content)


async def _analyze_with_gemini_data(
    model: str,
    prompt: str,
    image_bytes: bytes,
    *,
    api_key: str,
) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    
    return await _dispatch_gemini(model, prompt, img, api_key)


async def _analyze_with_gemini_url(
    model: str,
    prompt: str,
    image_url: str,
    *,
    api_key: str,
) -> str:
    _, image_data = await _download_image(image_url)
    img = Image.open(io.BytesIO(image_data))
    return await _dispatch_gemini(model, prompt, img, api_key=api_key)


async def _dispatch_gemini(model_name: str, prompt: str, image: Image, api_key: str) -> str:
    if not _GENAI_AVAILABLE or genai is None:
        raise api_error("google-generativeai not installed", status_code=503, code="genai_unavailable")
    genai.configure(api_key=api_key)
    target_model = strip_provider_prefix(model_name)
    model = genai.GenerativeModel(target_model)
    
    try:
        response = await model.generate_content_async([prompt, image])
    except Exception as exc:
        raise api_error(
            f"Failed to reach Gemini API: {exc}",
            status_code=502,
            code="gemini_unreachable",
        ) from exc

    if response.text:
        return response.text
    else:
        raise api_error("Gemini response was empty", status_code=502, code="empty_response")


async def _download_image(url: str) -> Tuple[str, bytes]:
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout)
    try:
        _headers = {
            "User-Agent": "Mozilla/5.0 (compatible; TriForce-Vision/1.0; +https://ailinux.me)",
            "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True, headers=_headers)
            if response.status_code == 403:
                raise api_error(
                    f"Bild-URL blockiert (403 Forbidden). Direkte Bild-URLs (jpg/png) verwenden statt Webseiten.",
                    status_code=422, code="image_access_denied"
                )
            response.raise_for_status()

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_BYTES:
                raise api_error("Image exceeds 10MB limit", status_code=413, code="image_too_large")

            data = response.content
            if len(data) > MAX_IMAGE_BYTES:
                raise api_error("Image exceeds 10MB limit", status_code=413, code="image_too_large")

            content_type = response.headers.get("Content-Type") or "image/png"
            return content_type, data
    except httpx.RequestError as exc:
        raise api_error(
            f"Failed to download image: {exc}",
            status_code=502,
            code="image_download_failed",
        ) from exc


async def _analyze_with_anthropic_data(
    model: str,
    prompt: str,
    image_bytes: bytes,
    *,
    content_type: str,
    api_key: str,
    max_tokens: int = 4096,
    timeout: float = 120.0,
) -> str:
    """Analyze an image using Anthropic Claude's vision capabilities.

    Claude supports vision for Claude 3+ models. Images are sent as base64-encoded
    data within the message content.
    """
    # Optimize image to prevent issues with large images
    optimized_bytes = _optimize_image(image_bytes, max_size=2048)

    # Map model aliases
    target_model = ANTHROPIC_VISION_ALIASES.get(model)
    if not target_model:
        stripped = strip_provider_prefix(model)
        target_model = ANTHROPIC_VISION_ALIASES.get(stripped, stripped)

    # Cap max_tokens per model limit (claude-3-haiku has 4096 max)
    CLAUDE3_MAX_TOKENS = {
        "claude-3-haiku-20240307": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-opus-20240229": 4096,
    }
    if target_model in CLAUDE3_MAX_TOKENS:
        max_tokens = min(max_tokens, CLAUDE3_MAX_TOKENS[target_model])

    # Map content type to Anthropic media type
    media_type_map = {
        "image/png": "image/png",
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/webp": "image/webp",
        "image/gif": "image/gif",
    }
    media_type = media_type_map.get(content_type.lower(), "image/png")

    # Encode image to base64
    encoded = base64.b64encode(optimized_bytes).decode("ascii")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Anthropic vision API format
    body = {
        "model": target_model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }

    url = "https://api.anthropic.com/v1/messages"
    client = HttpClient(base_url="https://api.anthropic.com")

    try:
        response = await client.post(
            url,
            headers=headers,
            json=body,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            error_data = exc.response.json()
            error_msg = error_data.get("error", {}).get("message", "Anthropic API error")
        except Exception:
            error_msg = f"Anthropic API returned status {exc.response.status_code}"
        raise api_error(error_msg, status_code=exc.response.status_code, code="anthropic_vision_error") from exc
    except Exception as exc:
        raise api_error(
            f"Failed to reach Anthropic API: {exc}",
            status_code=502,
            code="anthropic_unreachable",
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise api_error(
            "Anthropic returned malformed JSON",
            status_code=502,
            code="anthropic_invalid_response",
        ) from exc

    # Extract text from response content blocks
    content_blocks = data.get("content", [])
    text_parts = []
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "")
            if text:
                text_parts.append(text)

    if not text_parts:
        raise api_error("Anthropic vision model returned no response", status_code=502, code="empty_response")

    return "\n".join(text_parts)

# ── OpenAI-compatible Vision Handler ────────────────────────────────────────
# Supports: openrouter, github, groq, mistral, cerebras
# All use POST /chat/completions with image_url or base64 content parts.

_OPENAI_COMPAT_VISION_PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "key_attr": "openrouter_api_key",
    },
    "github": {
        "base_url": "https://models.inference.ai.azure.com/chat/completions",
        "key_attr": "github_token",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "key_attr": "groq_api_key",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "key_attr": "mistral_api_key",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1/chat/completions",
        "key_attr": "cerebras_api_key",
    },
}


async def _analyze_openai_compat_vision(
    provider: str,
    model: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    image_url: Optional[str] = None,
    content_type: str = "image/png",
    timeout: float = 120.0,
) -> str:
    """Generic OpenAI /chat/completions vision handler for all compatible providers."""
    from ..config import get_settings
    cfg = _OPENAI_COMPAT_VISION_PROVIDERS[provider]
    settings = get_settings()
    api_key = getattr(settings, cfg["key_attr"], None)
    if not api_key:
        raise api_error(
            f"{provider.title()} API Key nicht konfiguriert ({cfg['key_attr']})",
            status_code=503, code="provider_key_missing",
        )
    target_model = strip_provider_prefix(model)

    # Build image content part
    if image_bytes is not None:
        optimized = _optimize_image(image_bytes, max_size=1536)
        b64 = base64.b64encode(optimized).decode("ascii")
        # BUG-FIX 2026-03-11: _optimize_image always outputs JPEG regardless of input.
        # Original content_type caused MIME mismatch -> "Invalid image data" from GitHub etc.
        actual_mime = "image/jpeg"
        image_part = {
            "type": "image_url",
            "image_url": {"url": f"data:{actual_mime};base64,{b64}"},
        }
    elif image_url is not None:
        image_part = {"type": "image_url", "image_url": {"url": image_url}}
    else:
        raise api_error("Kein Bild angegeben", status_code=422, code="missing_image")

    body = {
        "model": target_model,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    image_part,
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://ailinux.me"
        headers["X-Title"] = "Nova AI"

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(cfg["base_url"], json=body, headers=headers)
        if r.status_code >= 400:
            try:
                err = r.json().get("error", {})
                msg = err.get("message", r.text) if isinstance(err, dict) else str(err)
            except Exception:
                msg = r.text[:300]
            raise api_error(
                f"{provider.title()} Vision Fehler: {msg}",
                status_code=r.status_code, code="provider_vision_error",
            )
        rdata = r.json()
        choices = rdata.get("choices", [])
        if not choices:
            raise api_error("Leere Antwort vom Provider", status_code=500, code="empty_response")
        return choices[0].get("message", {}).get("content", "")


async def _analyze_cloudflare_vision(
    model: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    image_url: Optional[str] = None,
    content_type: str = "image/png",
    timeout: float = 120.0,
) -> str:
    """Cloudflare Workers AI vision — uses /v1/chat/completions compatible endpoint."""
    from ..config import get_settings
    settings = get_settings()
    cf_account = settings.cloudflare_account_id
    cf_token = settings.cloudflare_api_token
    if not cf_account or not cf_token:
        raise api_error(
            "Cloudflare Account ID oder API Token fehlt",
            status_code=503, code="cloudflare_unavailable",
        )
    cf_model = strip_provider_prefix(model)  # @cf/meta/llama-3.2-11b-vision-instruct
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/{cf_model}"

    # CF uses OpenAI-style chat/completions body
    if image_bytes is not None:
        optimized = _optimize_image(image_bytes, max_size=1024)
        b64 = base64.b64encode(optimized).decode("ascii")
        # BUG-FIX 2026-03-11: _optimize_image always outputs JPEG
        img_content = f"data:image/jpeg;base64,{b64}"
    elif image_url is not None:
        img_content = image_url
    else:
        raise api_error("Kein Bild angegeben", status_code=422, code="missing_image")

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_content}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {cf_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        # BUG-FIX 2026-03-11: CF llama-3.2-11b-vision-instruct requires model
        # license agreement via sending "agree" as first prompt. Auto-agree on 403.
        for _attempt in range(2):
            r = await client.post(url, json=body, headers=headers)
            if r.status_code == 403:
                try:
                    err_body = r.json()
                    msg = str(err_body.get("errors", err_body))[:400]
                except Exception:
                    msg = r.text[:400]
                if "Model Agreement" in msg and _attempt == 0:
                    agree_body = {"messages": [{"role": "user", "content": "agree"}], "max_tokens": 10}
                    await client.post(url, json=agree_body, headers=headers)
                    continue
                raise api_error(
                    f"Cloudflare Vision Fehler: {msg}",
                    status_code=r.status_code, code="cloudflare_vision_error",
                )
            if r.status_code >= 400:
                try:
                    err_body = r.json()
                    msg = str(err_body.get("errors", err_body))[:200]
                except Exception:
                    msg = r.text[:200]
                raise api_error(
                    f"Cloudflare Vision Fehler: {msg}",
                    status_code=r.status_code, code="cloudflare_vision_error",
                )
            break
        rdata = r.json()
        # CF returns: {"result": {"response": "..."}} or choices[]
        result = rdata.get("result", {})
        if isinstance(result, dict):
            text = result.get("response") or result.get("content") or ""
            if text:
                return text
        choices = rdata.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return str(result)[:500]
