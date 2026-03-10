from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v1/frontend/dashboard", tags=["nova-frontend"])

def _base_url() -> str:
    return (os.getenv("TRIFORCE_PUBLIC_BASE_URL") or os.getenv("TRIFORCE_BASE_URL") or "http://127.0.0.1:9000").rstrip("/")

def _openai_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("CHATGPT_API_KEY")

def _pick(d: Dict[str, Any], *keys: str, default=None):
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return default

class ChatRequest(BaseModel):
    model: str
    # Accept single-turn (message: str) OR multi-turn (messages: list) from JS
    message: str = ""
    messages: Optional[List[Dict[str, Any]]] = None
    system: str = ""
    temperature: float = 0.4
    max_tokens: int = 1200

class VisionRequest(BaseModel):
    model: str
    prompt: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    mime_type: str = "image/png"
    temperature: float = 0.2
    max_tokens: int = 1200

class ImageRequest(BaseModel):
    model: str
    prompt: str
    size: str = "1024x1024"
    quality: str = "medium"
    n: int = 1

class VideoRequest(BaseModel):
    model: str
    prompt: str
    seconds: int = 8
    size: str = "1280x720"

def _provider(model: Dict[str, Any]) -> str:
    raw = str(_pick(model, "provider", "owned_by", "vendor", default="")).lower()
    mid = str(_pick(model, "id", "model", "name", default="")).lower()

    if "openai" in raw or mid.startswith("gpt-") or "dall-e" in mid or "gpt-image" in mid or "sora" in mid:
        return "openai"
    if "anthropic" in raw or "claude" in mid:
        return "anthropic"
    if "google" in raw or "gemini" in mid or "imagen" in mid or "veo" in mid:
        return "google"
    if "mistral" in raw or "pixtral" in mid or "ministral" in mid:
        return "mistral"
    if "groq" in raw:
        return "groq"
    if "cloudflare" in raw or mid.startswith("@cf/") or mid.startswith("cf/"):
        return "cloudflare"
    if "cerebras" in raw:
        return "cerebras"
    if "openrouter" in raw:
        return "openrouter"
    if "ollama" in raw:
        return "ollama"
    return raw or "unknown"

def _categorize(model: Dict[str, Any]) -> Dict[str, Any]:
    mid = str(_pick(model, "id", "model", "name", default=""))
    name = str(_pick(model, "name", "display_name", default=mid))
    provider = _provider(model)
    blob = json.dumps(model, default=str).lower() + " " + mid.lower() + " " + name.lower()

    caps = {
        "chat": False,
        "vision": False,
        "media_image": False,
        "media_video": False,
        "backend_supported": False,
    }

    if any(x in blob for x in ["gpt-", "claude", "gemini", "mistral", "ministral", "pixtral", "llama", "qwen", "deepseek", "command-r", "chat"]):
        caps["chat"] = True

    if any(x in blob for x in ["vision", "image understanding", "image-to-text", "multimodal", "pixtral", "gpt-4o", "claude-3", "claude-4", "gemini", "llama-4-scout"]):
        caps["vision"] = True

    # image_gen: check capabilities list from model_registry output
    caps_list = model.get("capabilities", [])
    if "image_gen" in caps_list or any(x in blob for x in ["gpt-image", "dall-e", "imagen", "image generation", "text-to-image", "flux", "stable diffusion", "image_gen"]):
        caps["media_image"] = True

    if "video_gen" in caps_list or any(x in blob for x in ["sora", "veo", "video generation", "text-to-video", "video_gen"]):
        caps["media_video"] = True

    if provider in {"openai", "anthropic", "google", "mistral", "groq", "cloudflare", "cerebras", "openrouter", "ollama"}:
        caps["backend_supported"] = caps["chat"] or caps["vision"]

    return {
        "id": mid,
        "name": name,
        "provider": provider,
        **caps,
        "categories": [k for k in ("chat", "vision", "media_image", "media_video") if caps[k]],
    }

async def _get_models() -> List[Dict[str, Any]]:
    urls = [
        f"{_base_url()}/v1/models",
        f"{_base_url()}/models",
        f"{_base_url()}/v1/tristar/models",
    ]
    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                data = r.json()
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
                if isinstance(data, dict):
                    for k in ("models", "data", "items", "available_models"):
                        if isinstance(data.get(k), list):
                            return [x for x in data[k] if isinstance(x, dict)]
            except Exception:
                pass
    return []

async def _chat_proxy(payload: Dict[str, Any]) -> Dict[str, Any]:
    urls = [
        f"{_base_url()}/v1/chat/completions",
        f"{_base_url()}/chat/completions",
    ]
    async with httpx.AsyncClient(timeout=120.0) as client:
        for url in urls:
            try:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
    raise HTTPException(status_code=502, detail="chat proxy failed")

async def _vision_proxy(model: str, prompt: str, image_url: Optional[str], image_base64: Optional[str], mime_type: str) -> Dict[str, Any]:
    """
    Route vision requests to the real /v1/images/analyze endpoint.
    - URL input  -> GET/POST /v1/images/analyze  (JSON body)
    - Base64 input -> POST /v1/images/analyze/upload (multipart)
    Does NOT tunnel through the chat endpoint (avoids content: str validator crash).
    """
    base = _base_url()

    if image_url:
        payload = {"model": model, "image_url": image_url, "prompt": prompt}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base}/v1/images/analyze", json=payload)
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()

    # Base64 path — multipart upload
    if not image_base64:
        raise HTTPException(status_code=400, detail="image_url or image_base64 required")

    try:
        image_bytes = base64.b64decode(image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {exc}")

    ext = mime_type.split("/")[-1] if "/" in mime_type else "png"
    filename = f"upload.{ext}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        files = {"image_file": (filename, image_bytes, mime_type)}
        data = {"model": model, "prompt": prompt}
        r = await client.post(f"{base}/v1/images/analyze/upload", files=files, data=data)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

async def _image_proxy(req: ImageRequest) -> Dict[str, Any]:
    """
    Multi-provider image generation:
    - OpenAI (gpt-image, dall-e) -> OpenAI API direct
    - SD/ComfyUI/FLUX/others     -> internal /v1/txt2img
    """
    m = req.model.lower()

    # OpenAI direct path
    if "gpt-image" in m or "dall-e" in m:
        key = _openai_key()
        if not key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing for OpenAI image generation")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {"model": req.model, "prompt": req.prompt, "size": req.size, "quality": req.quality, "n": req.n}
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload)
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return {"ok": True, "mode": "media_image", "provider": "openai", "result": r.json()}

    # Internal txt2img path (SD, ComfyUI, FLUX via together, cloudflare SD, etc.)
    base = _base_url()
    payload = {"prompt": req.prompt, "model": req.model, "size": req.size, "n": req.n}
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(f"{base}/v1/txt2img", json=payload)
        if r.status_code == 200:
            return {"ok": True, "mode": "media_image", "provider": "internal", "result": r.json()}
        # Fallback: try sd3 /images/generate endpoint
        r2 = await client.post(f"{base}/v1/images/generate", json={"prompt": req.prompt, "model": req.model})
        if r2.status_code == 200:
            return {"ok": True, "mode": "media_image", "provider": "internal_sd3", "result": r2.json()}
        raise HTTPException(
            status_code=r.status_code,
            detail=f"image generation not wired for model: {req.model} (tried txt2img + images/generate)"
        )

async def _video_proxy(req: VideoRequest) -> Dict[str, Any]:
    """
    Multi-provider video generation:
    - OpenAI Sora -> OpenAI API direct
    - Others      -> unsupported (honest error)
    """
    m = req.model.lower()

    if "sora" in m:
        key = _openai_key()
        if not key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing for Sora")
        headers = {"Authorization": f"Bearer {key}"}
        data = {"model": req.model, "prompt": req.prompt, "seconds": str(req.seconds), "size": req.size}
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post("https://api.openai.com/v1/videos", headers=headers, data=data)
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return {"ok": True, "mode": "media_video", "provider": "openai", "result": r.json()}

    # Gemini Veo — no internal adapter yet, honest error
    if "veo" in m:
        raise HTTPException(
            status_code=501,
            detail="Gemini Veo video generation not yet wired internally. Provider: google. Adapter: pending."
        )

    raise HTTPException(
        status_code=400,
        detail=f"video generation not wired for model: {req.model}. Supported: sora (OpenAI)."
    )

@router.get("/health")
async def health() -> Dict[str, Any]:
    models = await _get_models()
    return {"ok": True, "status": "ok", "model_count": len(models)}

@router.get("/config")
async def config() -> Dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "routes": {
            "health": "/v1/frontend/dashboard/health",
            "models": "/v1/frontend/dashboard/models",
            "chat": "/v1/frontend/dashboard/chat",
            "vision": "/v1/frontend/dashboard/vision",
            "media_image": "/v1/frontend/dashboard/media/image",
            "media_video": "/v1/frontend/dashboard/media/video",
        }
    }

@router.get("/models")
async def models() -> Dict[str, Any]:
    raw = await _get_models()
    items = [_categorize(m) for m in raw]
    items.sort(key=lambda x: (not x["backend_supported"], x["provider"], x["name"].lower()))
    return {
        "ok": True,
        "count": len(items),
        "categories": {
            "chat": [m for m in items if m["chat"]],
            "vision": [m for m in items if m["vision"]],
            "media_image": [m for m in items if m["media_image"]],
            "media_video": [m for m in items if m["media_video"]],
        },
        "models": items,
    }

@router.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    # Build messages: prefer req.messages[] (multi-turn from JS), fall back to req.message string
    if req.messages:
        messages = list(req.messages)
        # Prepend system prompt if provided and not already in messages
        if req.system.strip() and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": req.system.strip()})
    else:
        if not req.message:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Either 'message' or 'messages' required")
        messages = []
        if req.system.strip():
            messages.append({"role": "system", "content": req.system.strip()})
        messages.append({"role": "user", "content": req.message})
    raw = await _chat_proxy({
        "model": req.model,
        "messages": messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "stream": False,
    })
    # Normalize response: extract text from raw
    text = None
    if isinstance(raw, dict):
        text = (raw.get("text") or raw.get("content") or raw.get("response")
                or (raw.get("choices") or [{}])[0].get("message", {}).get("content"))
    return {"ok": True, "mode": "chat", "content": text or str(raw), "raw": raw}

@router.post("/vision")
async def vision(req: VisionRequest) -> Dict[str, Any]:
    if not req.image_url and not req.image_base64:
        raise HTTPException(status_code=400, detail="image_url or image_base64 required")
    result = await _vision_proxy(req.model, req.prompt, req.image_url, req.image_base64, req.mime_type)
    return {"ok": True, "mode": "vision", "raw": result}

@router.post("/media/image")
async def media_image(req: ImageRequest) -> Dict[str, Any]:
    return await _image_proxy(req)

@router.post("/media/video")
async def media_video(req: VideoRequest) -> Dict[str, Any]:
    return await _video_proxy(req)

@router.get("/downloads")
async def downloads() -> Dict[str, Any]:
    """Return available client downloads with metadata."""
    import glob, os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    deploy_dir = _os.path.join(base, "client-deploy")
    latest_dir = _os.path.join(base, "client-releases", "latest")

    # Read version info
    def _read(p: str) -> str:
        try:
            return open(p).read().strip()
        except Exception:
            return ""

    version = _read(_os.path.join(latest_dir, "VERSION")) or "4.3.6"
    build_date = _read(_os.path.join(latest_dir, "BUILD_DATE")) or ""

    files = []
    total_bytes = 0
    # Scan latest .deb
    for pattern in ["*.deb", "*.apk", "*.exe"]:
        for fp in sorted(glob.glob(_os.path.join(deploy_dir, pattern))):
            fname = _os.path.basename(fp)
            size = _os.path.getsize(fp)
            total_bytes += size
            ext = fname.rsplit(".", 1)[-1].upper()
            platform = "Linux" if ext == "DEB" else ("Android" if ext == "APK" else "Windows")
            files.append({
                "name": fname,
                "platform": platform,
                "size": size,
                "version": version,
                "url": f"/downloads/{fname}",
            })

    # Newest first
    files.sort(key=lambda x: x["name"], reverse=True)
    # Only latest per platform
    seen = set()
    unique = []
    for f in files:
        key = (f["platform"], f["version"])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return {"ok": True, "version": version, "build_date": build_date, "files": unique, "total_bytes": total_bytes}

