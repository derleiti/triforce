from __future__ import annotations

import asyncio
import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import httpx
import google.generativeai as genai
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
        resolved_type = content_type or "image/png"

        if resolved_bytes is None:
            assert image_url is not None
            resolved_type, resolved_bytes = await _download_image(image_url)

        if resolved_bytes is None:
            raise api_error("Image bytes missing", status_code=422, code="missing_image")

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

    # ── OpenRouter / Mistral / GitHub / Cloudflare fallback ──────────────────
    # These providers all use OpenAI-compatible vision format.
    settings = get_settings()
    provider = model.provider if model else request_model.split("/")[0].lower()

    OPENAI_COMPAT_PROVIDERS = {"openrouter", "mistral", "github", "groq", "cerebras"}

    if provider in OPENAI_COMPAT_PROVIDERS or request_model.startswith(("openrouter/", "mistral/", "github/", "groq/")):
        resolved_bytes = image_bytes
        resolved_type = content_type or "image/jpeg"

        if resolved_bytes is None:
            assert image_url is not None
            resolved_type, resolved_bytes = await _download_image(image_url)
        if resolved_bytes is None:
            raise api_error("Image bytes missing", status_code=422, code="missing_image")

        def _detect_mime2(data: bytes) -> str:
            if data[:3] == b"\xff\xd8\xff": return "image/jpeg"
            if data[:4] == b"\x89PNG": return "image/png"
            if data[:6] in (b"GIF87a", b"GIF89a"): return "image/gif"
            if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return "image/webp"
            return resolved_type
        resolved_type = _detect_mime2(resolved_bytes)

        _persist_temp_file(resolved_bytes, filename)
        return await _analyze_with_openai_compat(
            request_model, prompt, resolved_bytes, resolved_type, provider, settings
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
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)
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


async def _analyze_with_openai_compat(
    model: str,
    prompt: str,
    image_bytes: bytes,
    content_type: str,
    provider: str,
    settings,
) -> str:
    """OpenAI-compatible vision call for openrouter/mistral/github/groq."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{b64}"

    # Pick endpoint + auth header
    if provider == "openrouter" or model.startswith("openrouter/"):
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        clean_model = model[len("openrouter/"):] if model.startswith("openrouter/") else model
        extra_headers = {"HTTP-Referer": "https://ailinux.me", "X-Title": "AILinux Nova"}
    elif provider == "mistral" or model.startswith("mistral/"):
        api_key = os.getenv("MISTRAL_API_KEY", "")
        base_url = "https://api.mistral.ai/v1"
        clean_model = model[len("mistral/"):] if model.startswith("mistral/") else model
        extra_headers = {}
    elif provider == "github" or model.startswith("github/"):
        api_key = os.getenv("GITHUB_TOKEN", "")
        base_url = "https://models.inference.ai.azure.com"
        clean_model = model[len("github/"):] if model.startswith("github/") else model
        extra_headers = {}
    elif provider == "groq" or model.startswith("groq/"):
        api_key = os.getenv("GROQ_API_KEY", "")
        base_url = "https://api.groq.com/openai/v1"
        clean_model = model[len("groq/"):] if model.startswith("groq/") else model
        extra_headers = {}
    else:
        raise api_error(f"No API key configured for provider: {provider}", status_code=503, code="provider_unavailable")

    if not api_key:
        raise api_error(f"API key missing for provider: {provider}", status_code=503, code="provider_unavailable")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **extra_headers}
    payload = {
        "model": clean_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            if r.status_code >= 400:
                raise api_error(f"{provider} vision error: {r.text[:300]}", status_code=r.status_code, code=f"{provider}_vision_error")
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except httpx.RequestError as exc:
        raise api_error(f"Failed to reach {provider}: {exc}", status_code=502, code=f"{provider}_unreachable") from exc


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